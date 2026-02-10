import uuid
from typing import Optional, List, Dict, Any

from sqlalchemy import select

from app.db.session import SessionLocal
from app.db.models.bim_metadata import BimModel


class BimStore:
    """
    PostgreSQL-backed implementation of BIM metadata persistence.
    Mirrors FileStore boundary rules:
    - DB only (no FastAPI, no business workflows)
    - Returns dicts (no ORM leaks)
    """

    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory

    def create_bim_record(
        self,
        bim_id: uuid.UUID,
        file_id: uuid.UUID,
        format: str,
        schema: Optional[str] = None,
        extra: Optional[dict] = None,
    ) -> None:
        with self._session_factory() as session:
            obj = BimModel(
                id=bim_id,
                file_id=file_id,
                format=format,
                schema=schema,
                extra=extra,
            )
            session.add(obj)
            session.commit()

    def list_bim_models(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._session_factory() as session:
            stmt = select(BimModel).order_by(BimModel.created_at.desc()).limit(limit)
            rows = session.execute(stmt).scalars().all()
            return [self._to_dict(r) for r in rows]

    def get_bim_by_id(self, bim_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        with self._session_factory() as session:
            stmt = select(BimModel).where(BimModel.id == bim_id)
            row = session.execute(stmt).scalars().first()
            return self._to_dict(row) if row else None

    def get_bim_by_file_id(self, file_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        with self._session_factory() as session:
            stmt = select(BimModel).where(BimModel.file_id == file_id)
            row = session.execute(stmt).scalars().first()
            return self._to_dict(row) if row else None

    @staticmethod
    def _to_dict(obj: BimModel) -> Dict[str, Any]:
        return {
            "id": str(obj.id),
            "file_id": str(obj.file_id),
            "format": obj.format,
            "schema": obj.schema,
            "created_at": obj.created_at.isoformat() if obj.created_at else None,
            "extra": obj.extra,
        }
