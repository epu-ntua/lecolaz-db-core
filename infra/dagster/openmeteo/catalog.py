"""Map and atomically register explicitly selected Enhydris timeseries."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import sessionmaker

from app.storage.postgres.observation_type_store import ObservationTypeStore
from app.storage.postgres.sensor_store import SensorStore

from infra.dagster.openmeteo import SENSOR_FAMILY
from app.integrations.openmeteo import parse_external_id, prepare_registration  # noqa: F401


def utc_starting_date(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError("Sensor starting_date must be timezone-aware")
    return value.astimezone(timezone.utc)


def observation_type_key(sensor: dict) -> str:
    key = (sensor.get("sensor_metadata") or {}).get("observation_type_key")
    # Reuse the strict positive ID grammar for the two-part type identity.
    parse_external_id(f"1/{key}")
    return key


def persist_registration(
    engine, sensor_rows: list[dict], type_rows: list[dict]
) -> dict:
    # Connection-bound sessions leave the shared transaction's commit to this block.
    with engine.begin() as connection:
        types = ObservationTypeStore(sessionmaker(bind=connection)).upsert_source_fields(
            SENSOR_FAMILY, type_rows
        )
        sensors = SensorStore(sessionmaker(bind=connection)).upsert_source_fields(
            SENSOR_FAMILY,
            sensor_rows,
            # Seed location from the station on insert; preserve local edits on refresh.
            source_location=True,
        )
    return {"sensors": sensors, "observation_types": types}


def load_sensor_catalog(engine) -> list[dict]:
    with engine.connect() as connection:
        rows = SensorStore(sessionmaker(bind=connection)).list_by_sensor_family(SENSOR_FAMILY)
    for row in rows:
        row["id"] = str(row["id"])
        row["starting_date"] = utc_starting_date(row["starting_date"])
        parse_external_id(row["external_id"])
        observation_type_key(row)
    return rows


def load_references(engine, expected: dict) -> tuple[dict, UUID]:
    with engine.connect() as connection:
        sensor = SensorStore(sessionmaker(bind=connection)).get_by_id_and_sensor_family(
            UUID(expected["id"]), SENSOR_FAMILY
        )
        if sensor is None:
            raise ValueError(
                "OpenMeteo sensor is unavailable; reload the code location"
            )
        for field in ("external_id", "starting_date"):
            if sensor[field] != expected[field]:
                raise ValueError(f"Sensor {field} changed; reload the code location")
        key = observation_type_key(sensor)
        if key != observation_type_key(expected):
            raise ValueError(
                "Sensor observation type changed; reload the code location"
            )
        types = ObservationTypeStore(sessionmaker(bind=connection)).get_id_map_by_sensor_family(
            SENSOR_FAMILY
        )
        if key not in types:
            raise ValueError(
                f"Missing OpenMeteo observation type {key}; register the sensor again"
            )
    return sensor, types[key]
