import uuid
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy import delete, select

from app.db.models.simulation_timeseries import SimulationTimeseries
from app.db.session import SessionLocal


class SimulationTimeseriesStore:
    _BATCH_SIZE = 1000

    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory

    def replace_timeseries(
        self,
        simulation_dataset_id: uuid.UUID,
        rows: List[Dict[str, Any]],
    ) -> None:
        with self._session_factory() as session:
            records: List[SimulationTimeseries] = []
            for row in rows:
                records.append(
                    SimulationTimeseries(
                        id=uuid.uuid4(),
                        simulation_dataset_id=simulation_dataset_id,
                        variable_id=uuid.UUID(row["variable_id"]),
                        timestamp=row["timestamp"],
                        value=row["value"],
                    )
                )

            for start in range(0, len(records), self._BATCH_SIZE):
                session.add_all(records[start:start + self._BATCH_SIZE])
                session.flush()
            session.commit()

    def delete_by_simulation_dataset_id(self, simulation_dataset_id: uuid.UUID) -> None:
        with self._session_factory() as session:
            session.execute(
                delete(SimulationTimeseries).where(
                    SimulationTimeseries.simulation_dataset_id == simulation_dataset_id
                )
            )
            session.commit()

    def list_by_simulation_dataset_id(
        self,
        simulation_dataset_id: uuid.UUID,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        with self._session_factory() as session:
            stmt = (
                select(SimulationTimeseries)
                .where(SimulationTimeseries.simulation_dataset_id == simulation_dataset_id)
                .order_by(SimulationTimeseries.timestamp.asc())
                .limit(limit)
            )
            rows = session.execute(stmt).scalars().all()
            return [self._to_dict(row) for row in rows]

    @staticmethod
    def _to_dict(obj: SimulationTimeseries) -> Dict[str, Any]:
        return {
            "id": str(obj.id),
            "simulation_dataset_id": str(obj.simulation_dataset_id),
            "variable_id": str(obj.variable_id),
            "timestamp": obj.timestamp.isoformat() if obj.timestamp else None,
            "value": obj.value,
            "created_at": obj.created_at.isoformat() if obj.created_at else None,
        }
