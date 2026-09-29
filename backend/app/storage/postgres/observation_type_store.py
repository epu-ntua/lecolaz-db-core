import uuid
from typing import Any, Dict, List

from sqlalchemy import Connection, or_, select
from sqlalchemy.dialects.postgresql import insert

from app.db.models.observation_type import ObservationType


class ObservationTypeStore:
    """Reading-type persistence; the caller owns the connection and transaction."""

    def __init__(self, connection: Connection):
        self._connection = connection

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
        changed = len(self._connection.execute(statement).scalars().all())
        keys = {row["key"] for row in rows}
        stored = set(
            self._connection.execute(
                select(ObservationType.key).where(
                    ObservationType.sensor_family == sensor_family,
                    ObservationType.key.in_(keys),
                )
            ).scalars()
        )
        if stored != keys:
            raise ValueError("Observation-type verification failed; rolling back")
        return {"selected": len(rows), "inserted_or_updated": changed, "verified": len(stored)}

    def get_id_map_by_sensor_family(self, sensor_family: str) -> Dict[str, uuid.UUID]:
        statement = select(ObservationType.key, ObservationType.id).where(
            ObservationType.sensor_family == sensor_family
        )
        return {key: type_id for key, type_id in self._connection.execute(statement)}
