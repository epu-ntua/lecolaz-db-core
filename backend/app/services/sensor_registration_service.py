"""Persist selections atomically, reload definitions, then backfill missing work."""

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.db.models.bim_dataset import BimDataset
from app.db.models.modular_component import ModularComponent
from app.db.models.sensor import Sensor
from app.db.session import engine
from app.schemas.sensors import SensorRegistrationRequest
from app.services.dagster_backfill_service import launch_sensor_backfills
from app.services.dagster_service import reload_sensor_location
from app.services.sensor_catalog_service import prepare_catalog
from app.storage.postgres.observation_type_store import ObservationTypeStore
from app.storage.postgres.sensor_store import SensorStore


class SensorBimNotFound(ValueError):
    pass


class SensorOnComponent(ValueError):
    pass


def list_eligible_sensors(sensor_family: str) -> list[dict]:
    rows, _ = prepare_catalog(sensor_family)
    stored = {
        row["external_id"]: row
        for row in SensorStore().list_registration_fields(sensor_family)
    }
    return [
        {
            "sensor_family": sensor_family,
            "external_id": row["external_id"],
            "location": row.get("location"),
            "name": row["name"],
            **stored.get(row["external_id"], {}),
            "registered": row["external_id"] in stored,
        }
        for row in rows
    ]


def register_sensors(request: SensorRegistrationRequest) -> dict:
    family = request.sensor_family
    external_ids = [selection.external_id for selection in request.sensors]
    sensor_rows, type_rows = prepare_catalog(family, external_ids)
    # Source calls finish before opening a transaction. All DB writes, including
    # observation types needed by ingestion, commit together or roll back together.
    with engine.begin() as connection:
        bim_ids = {selection.settings.bim_dataset_id for selection in request.sensors} - {None}
        if bim_ids:
            found = set(connection.execute(
                select(BimDataset.id).where(BimDataset.id.in_(bim_ids))
                .with_for_update(read=True, key_share=True)
            ).scalars())
            if found != bim_ids:
                raise SensorBimNotFound("One or more BIM datasets were not found")
            # A sensor is on a building or a component, never both (ck_sensors_single_link).
            # Refuse instead of silently moving it off its component.
            to_building = [
                selection.external_id
                for selection in request.sensors
                if selection.settings.bim_dataset_id is not None
            ]
            # Lock the rows (external_id order, like the writes below) so no component
            # link can land between this check and the update.
            rows = connection.execute(
                select(Sensor.name, ModularComponent.name)
                .outerjoin(ModularComponent, ModularComponent.id == Sensor.modular_component_id)
                .where(Sensor.sensor_family == family, Sensor.external_id.in_(to_building))
                .order_by(Sensor.external_id)
                .with_for_update(of=Sensor)
            ).all()
            on_component = [(sensor, component) for sensor, component in rows if component]
            if on_component:
                placed = ", ".join(f"{sensor} (on {component})" for sensor, component in on_component)
                raise SensorOnComponent(
                    f"Remove these sensors from their component first: {placed}"
                )
        sessions = sessionmaker(bind=connection)
        ObservationTypeStore(sessions).upsert_source_fields(family, type_rows)
        store = SensorStore(sessions)
        store.upsert_source_fields(family, sensor_rows, source_location=family == "openmeteo")
        store.update_registration_fields(
            family, [
                {
                    "external_id": selection.external_id,
                    # Exclude omitted settings, but retain explicit nulls for clearing.
                    **selection.settings.model_dump(exclude_unset=True),
                }
                for selection in request.sensors
            ]
        )
        saved = {row["external_id"]: row for row in store.list_registration_fields(family)}
        result = [saved[external_id] for external_id in external_ids]
    dagster = reload_sensor_location()
    backfills = launch_sensor_backfills(result) if dagster["status"] == "reloaded" else []
    return {"sensors": result, "dagster": dagster, "backfills": backfills}
