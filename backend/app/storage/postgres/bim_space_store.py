import uuid
from typing import Any, Dict, List

from sqlalchemy import select

from app.db.models.bim_space import BimSpace
from app.db.session import SessionLocal


class BimSpaceStore:
    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory

    def list_by_bim_dataset_id(
        self,
        bim_dataset_id: uuid.UUID,
        limit: int = 2000,
    ) -> List[Dict[str, Any]]:
        with self._session_factory() as session:
            stmt = (
                select(BimSpace)
                .where(BimSpace.bim_dataset_id == bim_dataset_id)
                .order_by(BimSpace.name.asc().nulls_last(), BimSpace.raw_name.asc().nulls_last())
                .limit(limit)
            )
            rows = session.execute(stmt).scalars().all()
            return [self._to_dict(row) for row in rows]

    def get_space_id_map_by_bim_dataset_id(
        self,
        bim_dataset_id: uuid.UUID,
    ) -> Dict[str, uuid.UUID]:
        with self._session_factory() as session:
            stmt = (
                select(BimSpace.id, BimSpace.global_id)
                .where(BimSpace.bim_dataset_id == bim_dataset_id)
            )
            rows = session.execute(stmt).all()
            return {
                global_id.casefold(): space_id
                for space_id, global_id in rows
                if isinstance(global_id, str) and global_id
            }

    @staticmethod
    def _to_dict(obj: BimSpace) -> Dict[str, Any]:
        return {
            "id": str(obj.id),
            "bim_dataset_id": str(obj.bim_dataset_id),
            "global_id": obj.global_id,
            "name": obj.name,
            "raw_name": obj.raw_name,
            "storey_id": str(obj.storey_id) if obj.storey_id else None,
            "area": obj.area,
            "volume": obj.volume,
            "created_at": obj.created_at.isoformat() if obj.created_at else None,
        }
