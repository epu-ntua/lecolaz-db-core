from typing import Any, Dict, List

from sqlalchemy import Connection
from sqlalchemy.dialects.postgresql import insert

from app.db.models.observation_value import ObservationValue


class ObservationValueStore:
    """Observation persistence; the caller owns the connection and transaction."""

    _BATCH_SIZE = 1000

    def __init__(self, connection: Connection):
        self._connection = connection

    def upsert_rows(self, rows: List[Dict[str, Any]]) -> Dict[str, int]:
        """Write normalized rows in batches without committing between batches.

        Conflicts update only changed values; IDs and absent observations survive.
        The caller validates values and resolves sensor/type identities beforehand.
        """
        changed = 0
        for offset in range(0, len(rows), self._BATCH_SIZE):
            statement = insert(ObservationValue).values(rows[offset : offset + self._BATCH_SIZE])
            statement = statement.on_conflict_do_update(
                index_elements=[
                    ObservationValue.sensor_id,
                    ObservationValue.observation_type_id,
                    ObservationValue.timestamp,
                ],
                set_={"value": statement.excluded.value},
                where=ObservationValue.value.is_distinct_from(statement.excluded.value),
            ).returning(ObservationValue.id)
            changed += len(self._connection.execute(statement).scalars().all())
        return {"selected": len(rows), "inserted_or_updated": changed}
