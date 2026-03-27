import uuid
from typing import Optional, List, Dict, Any

from sqlalchemy import select

from app.db.session import SessionLocal
from app.db.models.bim_dataset import BimDataset


class BimStore:
    """
    PostgreSQL-backed implementation of BIM metadata persistence.
    Mirrors DatasetStore boundary rules:
    - DB only (no FastAPI, no business workflows)
    - Returns dicts (no ORM leaks)
    """

    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory

    def create_bim_record(
        self,
        bim_id: uuid.UUID,
        dataset_id: uuid.UUID,
        filename: str,
        format: str,
        schema: Optional[str] = None,
        extra: Optional[dict] = None,
    ) -> None:
        with self._session_factory() as session:
            obj = BimDataset(
                id=bim_id,
                dataset_id=dataset_id,
                filename=filename,
                format=format,
                schema=schema,
                extra=extra,
            )
            session.add(obj)
            session.commit()

    def list_bim_models(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._session_factory() as session:
            stmt = select(BimDataset).order_by(BimDataset.created_at.desc()).limit(limit)
            rows = session.execute(stmt).scalars().all()
            return [self._to_dict(r) for r in rows]

    def get_bim_by_id(self, bim_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        with self._session_factory() as session:
            stmt = select(BimDataset).where(BimDataset.id == bim_id)
            row = session.execute(stmt).scalars().first()
            return self._to_dict(row) if row else None

    def get_bim_by_dataset_id(self, dataset_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        with self._session_factory() as session:
            stmt = select(BimDataset).where(BimDataset.dataset_id == dataset_id)
            row = session.execute(stmt).scalars().first()
            return self._to_dict(row) if row else None

    @staticmethod
    def _to_dict(obj: BimDataset) -> Dict[str, Any]:
        return {
            "id": str(obj.id),
            "dataset_id": str(obj.dataset_id),
            "filename": obj.filename,
            "format": obj.format,
            "schema": obj.schema,
            "created_at": obj.created_at.isoformat() if obj.created_at else None,
            "extra": obj.extra,
        }
