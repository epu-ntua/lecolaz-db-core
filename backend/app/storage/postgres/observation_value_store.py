from typing import Any, Dict, List

from sqlalchemy.dialects.postgresql import insert

from app.db.models.observation_value import ObservationValue
from app.db.session import SessionLocal


class ObservationValueStore:
    """Observation persistence; uses a session factory for database access."""

    _BATCH_SIZE = 1000

    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory

    def upsert_rows(self, rows: List[Dict[str, Any]]) -> Dict[str, int]:
        """Write normalized rows in batches without committing between batches.

        Conflicts update only changed values; IDs and absent observations survive.
        The caller validates values and resolves sensor/type identities beforehand.
        """
        if not rows:
            return {"selected": 0, "inserted_or_updated": 0}

        with self._session_factory() as session:
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
                changed += len(session.execute(statement).scalars().all())
            session.commit()
            return {"selected": len(rows), "inserted_or_updated": changed}
