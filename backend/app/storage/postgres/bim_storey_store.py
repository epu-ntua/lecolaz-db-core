import uuid
from typing import Any, Dict, List

from sqlalchemy import select

from app.db.models.bim_storey import BimStorey
from app.db.session import SessionLocal


class BimStoreyStore:
    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory

    def list_by_bim_dataset_id(
        self,
        bim_dataset_id: uuid.UUID,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        with self._session_factory() as session:
            stmt = (
                select(BimStorey)
                .where(BimStorey.bim_dataset_id == bim_dataset_id)
                .order_by(BimStorey.elevation.asc().nulls_last(), BimStorey.name.asc())
                .limit(limit)
            )
            rows = session.execute(stmt).scalars().all()
            return [self._to_dict(row) for row in rows]

    @staticmethod
    def _to_dict(obj: BimStorey) -> Dict[str, Any]:
        return {
            "id": str(obj.id),
            "bim_dataset_id": str(obj.bim_dataset_id),
            "global_id": obj.global_id,
            "name": obj.name,
            "elevation": obj.elevation,
            "created_at": obj.created_at.isoformat() if obj.created_at else None,
        }
