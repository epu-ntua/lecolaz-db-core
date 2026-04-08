import uuid
from typing import Optional, List, Dict, Any

from sqlalchemy import select

from app.db.models.dataset import Dataset
from app.db.session import SessionLocal
from app.db.models.simulation_dataset import SimulationDataset
from app.storage.postgres.dataset_store import DatasetStore


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
        metadata: Optional[dict] = None,
        extra: Optional[dict] = None,
    ) -> None:
        with self._session_factory() as session:
            obj = SimulationDataset(
                id=simulation_id,
                dataset_id=dataset_id,
                filename=filename,
                format=format,
                simulation_metadata=metadata,
                extra=extra,
            )
            session.add(obj)
            session.commit()

    def update_simulation_metadata(
        self,
        dataset_id: uuid.UUID,
        metadata: Optional[dict],
    ) -> Optional[Dict[str, Any]]:
        with self._session_factory() as session:
            stmt = select(SimulationDataset, Dataset.status, Dataset.dataset_metadata).join(
                Dataset, Dataset.id == SimulationDataset.dataset_id
            ).where(SimulationDataset.dataset_id == dataset_id)
            row = session.execute(stmt).first()
            if not row:
                return None

            simulation, dataset_status, dataset_metadata = row
            simulation.simulation_metadata = metadata
            simulation.extra = None
            session.commit()
            session.refresh(simulation)
            return self._to_dict(simulation, dataset_status, dataset_metadata)

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
        metadata = dict(obj.simulation_metadata or {})
        normalized_dataset_metadata = DatasetStore._normalize_metadata(dataset_metadata) or {}
        processing_error = normalized_dataset_metadata.get("processing_error")
        if processing_error is not None:
            metadata["processing_error"] = processing_error
        processed_at = normalized_dataset_metadata.get("processed_at")
        if processed_at is not None:
            metadata["processed_at"] = processed_at

        return {
            "id": str(obj.id),
            "dataset_id": str(obj.dataset_id),
            "filename": obj.filename,
            "format": obj.format,
            "status": dataset_status,
            "created_at": obj.created_at.isoformat() if obj.created_at else None,
            "metadata": metadata or None,
        }
