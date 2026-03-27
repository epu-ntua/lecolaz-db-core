import uuid
from typing import Optional, List, Dict, Any

from sqlalchemy import select

from app.db.models.dataset import Dataset
from app.db.session import SessionLocal
from app.db.models.simulation_dataset import SimulationDataset


class SimulationStore:
    """
    PostgreSQL-backed implementation of simulation metadata persistence.
    Mirrors DatasetStore boundary rules:
    - DB only (no FastAPI, no business workflows)
    - Returns dicts (no ORM leaks)
    """

    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory

    def create_simulation_record(
        self,
        simulation_id: uuid.UUID,
        dataset_id: uuid.UUID,
        filename: str,
        format: str,
        extra: Optional[dict] = None,
    ) -> None:
        with self._session_factory() as session:
            obj = SimulationDataset(
                id=simulation_id,
                dataset_id=dataset_id,
                filename=filename,
                format=format,
                extra=extra,
            )
            session.add(obj)
            session.commit()

    def list_simulation_models(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._session_factory() as session:
            stmt = (
                select(SimulationDataset, Dataset.status, Dataset.dataset_metadata)
                .join(Dataset, Dataset.id == SimulationDataset.dataset_id)
                .order_by(SimulationDataset.created_at.desc())
                .limit(limit)
            )
            rows = session.execute(stmt).all()
            return [
                self._to_dict(simulation, dataset_status, dataset_metadata)
                for simulation, dataset_status, dataset_metadata in rows
            ]

    def get_simulation_by_id(
        self,
        simulation_id: uuid.UUID,
    ) -> Optional[Dict[str, Any]]:
        with self._session_factory() as session:
            stmt = (
                select(SimulationDataset, Dataset.status, Dataset.dataset_metadata)
                .join(Dataset, Dataset.id == SimulationDataset.dataset_id)
                .where(SimulationDataset.id == simulation_id)
            )
            row = session.execute(stmt).first()
            return self._to_dict(row[0], row[1], row[2]) if row else None

    def get_simulation_by_dataset_id(
        self,
        dataset_id: uuid.UUID,
    ) -> Optional[Dict[str, Any]]:
        with self._session_factory() as session:
            stmt = (
                select(SimulationDataset, Dataset.status, Dataset.dataset_metadata)
                .join(Dataset, Dataset.id == SimulationDataset.dataset_id)
                .where(SimulationDataset.dataset_id == dataset_id)
            )
            row = session.execute(stmt).first()
            return self._to_dict(row[0], row[1], row[2]) if row else None

    @staticmethod
    def _to_dict(
        obj: SimulationDataset,
        dataset_status: str | None,
        dataset_metadata: dict | None,
    ) -> Dict[str, Any]:
        return {
            "id": str(obj.id),
            "dataset_id": str(obj.dataset_id),
            "filename": obj.filename,
            "format": obj.format,
            "status": dataset_status,
            "created_at": obj.created_at.isoformat() if obj.created_at else None,
            "extra": dataset_metadata,
        }
