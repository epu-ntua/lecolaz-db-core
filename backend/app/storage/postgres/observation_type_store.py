import uuid
from typing import Any, Dict, List

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert

from app.db.models.observation_type import ObservationType
from app.db.session import SessionLocal


class ObservationTypeStore:
    """Reading-type persistence; uses a session factory for database access."""

    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory

    def upsert_source_fields(
        self, sensor_family: str, rows: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Upsert and verify selected types, preserving IDs and absent types."""
        if not rows:
            raise ValueError("Refusing to load an empty observation-type batch")
        records = [
            {
                "sensor_family": sensor_family,
                "key": row["key"],
                "label": row["label"],
                "unit": row["unit"],
                "type_metadata": row.get("type_metadata"),
            }
            for row in rows
        ]
        statement = insert(ObservationType).values(records)
        statement = statement.on_conflict_do_update(
            index_elements=[ObservationType.sensor_family, ObservationType.key],
            set_={
                "label": statement.excluded.label,
                "unit": statement.excluded.unit,
                "type_metadata": statement.excluded.type_metadata,
            },
            where=or_(
                ObservationType.label.is_distinct_from(statement.excluded.label),
                ObservationType.unit.is_distinct_from(statement.excluded.unit),
                ObservationType.type_metadata.is_distinct_from(statement.excluded.type_metadata),
            ),
        ).returning(ObservationType.key)
        with self._session_factory() as session:
            changed = len(session.execute(statement).scalars().all())
            keys = {row["key"] for row in rows}
            stored = set(
                session.execute(
                    select(ObservationType.key).where(
                        ObservationType.sensor_family == sensor_family,
                        ObservationType.key.in_(keys),
                    )
                ).scalars()
            )
            if stored != keys:
                raise ValueError("Observation-type verification failed; rolling back")
            session.commit()
            return {"selected": len(rows), "inserted_or_updated": changed, "verified": len(stored)}

    def get_id_map_by_sensor_family(self, sensor_family: str) -> Dict[str, uuid.UUID]:
        statement = select(ObservationType.key, ObservationType.id).where(
            ObservationType.sensor_family == sensor_family
        )
        with self._session_factory() as session:
            return {key: type_id for key, type_id in session.execute(statement)}
