import uuid
from typing import Any, Dict, List

from sqlalchemy import delete, insert, select

from app.db.models.simulation_timeseries import SimulationTimeseries
from app.db.session import SessionLocal


class SimulationTimeseriesStore:
    _BATCH_SIZE = 10000

    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory

    def replace_timeseries(
        self,
        simulation_dataset_id: uuid.UUID,
        rows: List[Dict[str, Any]],
    ) -> None:
        with self._session_factory() as session:
            for start in range(0, len(rows), self._BATCH_SIZE):
                batch = rows[start:start + self._BATCH_SIZE]
                records = [
                    {
                        "id": uuid.uuid4(),
                        "simulation_dataset_id": simulation_dataset_id,
                        "variable_id": uuid.UUID(row["variable_id"]),
                        "timestamp": row["timestamp"],
                        "value": row["value"],
                    }
                    for row in batch
                ]
                session.execute(insert(SimulationTimeseries), records)
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

    def list_by_simulation_dataset_and_variable_id(
        self,
        simulation_dataset_id: uuid.UUID,
        variable_id: uuid.UUID,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        with self._session_factory() as session:
            stmt = (
                select(SimulationTimeseries)
                .where(SimulationTimeseries.simulation_dataset_id == simulation_dataset_id)
                .where(SimulationTimeseries.variable_id == variable_id)
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
