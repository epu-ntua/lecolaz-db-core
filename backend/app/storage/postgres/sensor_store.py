import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import or_, select
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
        """Preserve local fields and IDs; opt in when the source owns location.

        HAM locations are locally managed, so the default never writes them.
        OpenMeteo opts in because its station supplies the location. The caller
        chooses ownership; this store does not branch on sensor_family.
        starting_date and space remain local regardless of this option.
        """
        if not rows:
            return {"selected": 0, "inserted_or_updated": 0, "verified": 0}

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
        fields = ["name", "sensor_metadata"] + (["location"] if source_location else [])
        statement = statement.on_conflict_do_update(
            index_elements=[Sensor.sensor_family, Sensor.external_id],
            set_={field: getattr(statement.excluded, field) for field in fields},
            where=or_(
                *[
                    getattr(Sensor, field).is_distinct_from(
                        getattr(statement.excluded, field)
                    )
                    for field in fields
                ]
            ),
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

    def get_by_id_and_sensor_family(
        self, sensor_id: uuid.UUID, sensor_family: str
    ) -> Optional[Dict[str, Any]]:
        statement = select(
            Sensor.id, Sensor.external_id, Sensor.starting_date, Sensor.sensor_metadata
        ).where(Sensor.id == sensor_id, Sensor.sensor_family == sensor_family)
        with self._session_factory() as session:
            row = session.execute(statement).mappings().one_or_none()
            return dict(row) if row is not None else None
