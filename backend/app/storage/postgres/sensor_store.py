import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import Connection, or_, select
from sqlalchemy.dialects.postgresql import insert

from app.db.models.sensor import Sensor


class SensorStore:
    """Sensor persistence; the caller owns the connection and transaction.

    Returns plain records with native UUIDs and datetimes, without ORM objects.
    """

    def __init__(self, connection: Connection):
        self._connection = connection

    def upsert_source_fields(
        self, sensor_family: str, rows: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Upsert source fields, preserving local fields, IDs, and absent sensors."""
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
        statement = insert(Sensor).values(records)
        statement = statement.on_conflict_do_update(
            index_elements=[Sensor.sensor_family, Sensor.external_id],
            set_={
                "name": statement.excluded.name,
                "sensor_metadata": statement.excluded.sensor_metadata,
            },
            where=or_(
                Sensor.name.is_distinct_from(statement.excluded.name),
                Sensor.sensor_metadata.is_distinct_from(statement.excluded.sensor_metadata),
            ),
        ).returning(Sensor.external_id)
        changed = len(self._connection.execute(statement).scalars().all())
        external_ids = {row["external_id"] for row in rows}
        stored = set(
            self._connection.execute(
                select(Sensor.external_id).where(
                    Sensor.sensor_family == sensor_family,
                    Sensor.external_id.in_(external_ids),
                )
            ).scalars()
        )
        if stored != external_ids:
            raise ValueError("Sensor verification failed; rolling back")
        return {"selected": len(rows), "inserted_or_updated": changed, "verified": len(stored)}

    def list_by_sensor_family(self, sensor_family: str) -> List[Dict[str, Any]]:
        """Return the complete catalog in stable UUID order for ingestion discovery."""
        statement = (
            select(Sensor.id, Sensor.name, Sensor.external_id, Sensor.starting_date)
            .where(Sensor.sensor_family == sensor_family)
            .order_by(Sensor.id)
        )
        return [dict(row) for row in self._connection.execute(statement).mappings()]

    def get_by_id_and_sensor_family(
        self, sensor_id: uuid.UUID, sensor_family: str
    ) -> Optional[Dict[str, Any]]:
        statement = select(Sensor.id, Sensor.external_id, Sensor.starting_date).where(
            Sensor.id == sensor_id, Sensor.sensor_family == sensor_family
        )
        row = self._connection.execute(statement).mappings().one_or_none()
        return dict(row) if row is not None else None
