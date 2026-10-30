import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from app.db.models.sensor import Sensor
from app.db.session import SessionLocal


class SensorStore:
    """Sensor persistence; uses a session factory for database access.

    Returns plain records with native UUIDs and datetimes, without ORM objects.
    Source metadata is opaque here: integrations interpret it. OpenMeteo needs it
    in catalog/detail reads to resolve the single observation type for each sensor.
    """

    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory

    def upsert_source_fields(
        self,
        sensor_family: str,
        rows: List[Dict[str, Any]],
        *,
        source_location: bool = False,
    ) -> Dict[str, int]:
        """Seed name/location on insert; refresh only provider metadata thereafter.

        source_location opts into seeding location (e.g. from OpenMeteo's station).
        Without override flags we cannot distinguish customized fields, so all
        existing names/locations stay local, even if the provider changes them.
        starting_date, space, and BIM links also remain local.
        """
        if not rows:
            return {"selected": 0, "inserted_or_updated": 0, "verified": 0}

        # Match lock ordering across UI and Dagster writers to avoid deadlocks
        # when concurrent batches contain the same sensors in different orders.
        rows = sorted(rows, key=lambda row: row["external_id"])
        records = [
            {
                "sensor_family": sensor_family,
                "external_id": row["external_id"],
                "name": row["name"],
                "sensor_metadata": row.get("sensor_metadata"),
            }
            for row in rows
        ]
        if source_location:
            for record, row in zip(records, rows):
                record["location"] = row.get("location")
        statement = insert(Sensor).values(records)
        statement = statement.on_conflict_do_update(
            index_elements=[Sensor.sensor_family, Sensor.external_id],
            set_={"sensor_metadata": statement.excluded.sensor_metadata},
            where=Sensor.sensor_metadata.is_distinct_from(statement.excluded.sensor_metadata),
        ).returning(Sensor.external_id)
        with self._session_factory() as session:
            changed = len(session.execute(statement).scalars().all())
            external_ids = {row["external_id"] for row in rows}
            stored = set(
                session.execute(
                    select(Sensor.external_id).where(
                        Sensor.sensor_family == sensor_family,
                        Sensor.external_id.in_(external_ids),
                    )
                ).scalars()
            )
            if stored != external_ids:
                raise ValueError("Sensor verification failed; rolling back")
            session.commit()
            return {
                "selected": len(rows),
                "inserted_or_updated": changed,
                "verified": len(stored),
            }

    def list_by_sensor_family(self, sensor_family: str) -> List[Dict[str, Any]]:
        """Return the complete catalog in stable UUID order for ingestion discovery."""
        statement = (
            select(
                Sensor.id,
                Sensor.name,
                Sensor.external_id,
                Sensor.starting_date,
                Sensor.sensor_metadata,
            )
            .where(Sensor.sensor_family == sensor_family)
            .order_by(Sensor.id)
        )
        with self._session_factory() as session:
            return [dict(row) for row in session.execute(statement).mappings()]

    def list_registration_fields(self, sensor_family: str) -> List[Dict[str, Any]]:
        statement = select(
            Sensor.id, Sensor.sensor_family, Sensor.external_id, Sensor.name,
            Sensor.location, Sensor.space, Sensor.starting_date, Sensor.bim_dataset_id,
            Sensor.modular_component_id,
        ).where(Sensor.sensor_family == sensor_family).order_by(Sensor.external_id)
        with self._session_factory() as session:
            return [dict(row) for row in session.execute(statement).mappings()]

    def list_registered(
        self,
        *,
        sensor_family: str | None = None,
        bim_dataset_id: uuid.UUID | None = None,
        modular_component_id: uuid.UUID | None = None,
        unassigned: bool = False,
    ) -> List[Dict[str, Any]]:
        """Return registered sensors without contacting their external providers.

        unassigned keeps only sensors linked to neither a building nor a component.
        """
        statement = select(
            Sensor.id, Sensor.sensor_family, Sensor.external_id, Sensor.name,
            Sensor.location, Sensor.space, Sensor.starting_date, Sensor.bim_dataset_id,
            Sensor.modular_component_id,
        ).where(
            Sensor.sensor_family.in_(("ham", "openmeteo")),
            Sensor.external_id.is_not(None),
        )
        if sensor_family is not None:
            statement = statement.where(Sensor.sensor_family == sensor_family)
        if bim_dataset_id is not None:
            statement = statement.where(Sensor.bim_dataset_id == bim_dataset_id)
        if modular_component_id is not None:
            statement = statement.where(Sensor.modular_component_id == modular_component_id)
        if unassigned:
            statement = statement.where(
                Sensor.bim_dataset_id.is_(None),
                Sensor.modular_component_id.is_(None),
            )
        statement = statement.order_by(Sensor.name, Sensor.external_id)
        with self._session_factory() as session:
            return [dict(row) for row in session.execute(statement).mappings()]

    def update_registration_fields(
        self, sensor_family: str, selections: List[Dict[str, Any]]
    ) -> None:
        """Only explicitly supplied local fields change on repeated registration."""
        with self._session_factory() as session:
            # Use the same sensor lock order as the source-field upsert above.
            for selection in sorted(selections, key=lambda row: row["external_id"]):
                fields = {
                    key: selection[key]
                    for key in ("starting_date", "bim_dataset_id", "name", "location", "space")
                    if key in selection
                }
                if fields:
                    session.execute(
                        update(Sensor).where(
                            Sensor.sensor_family == sensor_family,
                            Sensor.external_id == selection["external_id"],
                        ).values(**fields)
                    )
            session.commit()

    def update_modular_component_sensors(
        self,
        component_id: uuid.UUID,
        add: List[uuid.UUID],
        remove: List[uuid.UUID],
    ) -> List[uuid.UUID]:
        """Add and remove sensors on a component, all or nothing.

        Changes only the named sensors, so concurrent edits by other users are kept.
        Only free registered sensors (no building, no other component) can be added;
        removing a sensor that is not on the component is a no-op. Returns the ids
        that could not be added; if any, nothing is changed.
        """
        return self._update_sensor_links(
            Sensor.modular_component_id, Sensor.bim_dataset_id, component_id, add, remove
        )

    def connect_bim_sensors(
        self, bim_id: uuid.UUID, add: List[uuid.UUID]
    ) -> List[uuid.UUID]:
        """Connect free registered sensors to a building, all or nothing."""
        return self._update_sensor_links(
            Sensor.bim_dataset_id, Sensor.modular_component_id, bim_id, add, []
        )

    def _update_sensor_links(
        self, target_column, other_column, target_id: uuid.UUID,
        add: List[uuid.UUID], remove: List[uuid.UUID],
    ) -> List[uuid.UUID]:
        to_add, to_remove = set(add), set(remove)
        with self._session_factory() as session:
            # Lock in the family/external_id order the other writers use to avoid deadlocks.
            session.execute(
                select(Sensor.id)
                .where(Sensor.id.in_(to_add | to_remove))
                .order_by(Sensor.sensor_family, Sensor.external_id)
                .with_for_update()
            ).all()
            session.execute(
                update(Sensor)
                .where(
                    Sensor.id.in_(to_remove),
                    target_column == target_id,
                )
                .values({target_column: None})
            )
            added = set(
                session.execute(
                    update(Sensor)
                    .where(
                        Sensor.id.in_(to_add),
                        # Same visibility rules as list_registered.
                        Sensor.sensor_family.in_(("ham", "openmeteo")),
                        Sensor.external_id.is_not(None),
                        other_column.is_(None),
                        (target_column.is_(None)) | (target_column == target_id),
                    )
                    .values({target_column: target_id})
                    .returning(Sensor.id)
                ).scalars()
            )
            unavailable = sorted(to_add - added, key=str)
            if unavailable:
                session.rollback()
                return unavailable
            session.commit()
            return []

    def get_by_id_and_sensor_family(
        self, sensor_id: uuid.UUID, sensor_family: str
    ) -> Optional[Dict[str, Any]]:
        statement = select(
            Sensor.id, Sensor.external_id, Sensor.starting_date, Sensor.sensor_metadata
        ).where(Sensor.id == sensor_id, Sensor.sensor_family == sensor_family)
        with self._session_factory() as session:
            row = session.execute(statement).mappings().one_or_none()
            return dict(row) if row is not None else None
