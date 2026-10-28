from datetime import datetime
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from app.db.models.observation_type import ObservationType
from app.db.models.observation_value import ObservationValue
from app.db.session import SessionLocal


class ObservationValueStore:
    """Observation persistence; uses a session factory for database access."""

    _BATCH_SIZE = 1000

    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory

    def list_observation_types(self, sensor_id: UUID) -> List[Dict[str, Any]]:
        recorded_types = select(ObservationValue.observation_type_id).where(
            ObservationValue.sensor_id == sensor_id
        ).distinct()
        statement = (
            select(ObservationType.id, ObservationType.unit, ObservationType.label)
            .where(ObservationType.id.in_(recorded_types))
            .order_by(ObservationType.label, ObservationType.unit, ObservationType.id)
        )
        with self._session_factory() as session:
            return [dict(row) for row in session.execute(statement).mappings()]

    def get_timestamp_bounds(self, sensor_id: UUID, observation_type_id: UUID) -> Dict[str, Any]:
        statement = select(
            func.min(ObservationValue.timestamp).label("start"),
            func.max(ObservationValue.timestamp).label("end"),
        ).where(
            ObservationValue.sensor_id == sensor_id,
            ObservationValue.observation_type_id == observation_type_id,
        )
        with self._session_factory() as session:
            return dict(session.execute(statement).mappings().one())

    def list_timeseries(
        self, sensor_id: UUID, observation_type_id: UUID, start: datetime, end: datetime
    ) -> List[Dict[str, Any]]:
        # Return the entire inclusive range so chart statistics are not truncated.
        statement = (
            select(ObservationValue.id, ObservationValue.timestamp, ObservationValue.value)
            .where(
                ObservationValue.sensor_id == sensor_id,
                ObservationValue.observation_type_id == observation_type_id,
                ObservationValue.timestamp >= start,
                ObservationValue.timestamp <= end,
            )
            .order_by(ObservationValue.timestamp)
        )
        with self._session_factory() as session:
            return [dict(row) for row in session.execute(statement).mappings()]

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
