import uuid
from typing import Optional, List, Dict, Any

from sqlalchemy import delete, select

from app.db.models.dataset import Dataset
from app.db.session import SessionLocal
from app.db.models.bim_dataset import BimDataset
from app.db.models.bim_space import BimSpace
from app.db.models.bim_storey import BimStorey


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
            stmt = (
                select(BimDataset, Dataset.status)
                .join(Dataset, Dataset.id == BimDataset.dataset_id)
                .order_by(BimDataset.created_at.desc())
                .limit(limit)
            )
            rows = session.execute(stmt).all()
            return [self._to_dict(bim, dataset_status) for bim, dataset_status in rows]

    def get_bim_by_id(self, bim_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        with self._session_factory() as session:
            stmt = (
                select(BimDataset, Dataset.status)
                .join(Dataset, Dataset.id == BimDataset.dataset_id)
                .where(BimDataset.id == bim_id)
            )
            row = session.execute(stmt).first()
            return self._to_dict(row[0], row[1]) if row else None

    def get_bim_by_dataset_id(self, dataset_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        with self._session_factory() as session:
            stmt = (
                select(BimDataset, Dataset.status)
                .join(Dataset, Dataset.id == BimDataset.dataset_id)
                .where(BimDataset.dataset_id == dataset_id)
            )
            row = session.execute(stmt).first()
            return self._to_dict(row[0], row[1]) if row else None

    def update_bim_record(
        self,
        dataset_id: uuid.UUID,
        *,
        schema: Optional[str] = None,
        stats: Optional[dict] = None,
        units: Optional[list] = None,
        extra: Optional[dict] = None,
    ) -> Optional[Dict[str, Any]]:
        with self._session_factory() as session:
            stmt = select(BimDataset).where(BimDataset.dataset_id == dataset_id)
            obj = session.execute(stmt).scalars().first()
            if not obj:
                return None

            obj.schema = schema
            obj.stats = stats
            obj.units = units
            obj.extra = extra
            session.commit()
            session.refresh(obj)
            return self._to_dict(obj, None)

    def replace_spatial_structure(
        self,
        *,
        bim_dataset_id: uuid.UUID,
        storeys: List[Dict[str, Any]],
        spaces: List[Dict[str, Any]],
    ) -> None:
        with self._session_factory() as session:
            session.execute(
                delete(BimSpace).where(BimSpace.bim_dataset_id == bim_dataset_id)
            )
            session.execute(
                delete(BimStorey).where(BimStorey.bim_dataset_id == bim_dataset_id)
            )

            storey_ids_by_global_id: Dict[str, uuid.UUID] = {}
            for storey in storeys:
                obj = BimStorey(
                    bim_dataset_id=bim_dataset_id,
                    global_id=storey["global_id"],
                    name=storey.get("name"),
                    elevation=storey.get("elevation"),
                )
                session.add(obj)
                session.flush()
                storey_ids_by_global_id[storey["global_id"]] = obj.id

            for space in spaces:
                obj = BimSpace(
                    bim_dataset_id=bim_dataset_id,
                    global_id=space["global_id"],
                    name=space.get("name"),
                    raw_name=space.get("raw_name"),
                    storey_id=storey_ids_by_global_id.get(space.get("storey_global_id")),
                    area=space.get("area"),
                    volume=space.get("volume"),
                )
                session.add(obj)

            session.commit()

    @staticmethod
    def _to_dict(obj: BimDataset, dataset_status: str | None) -> Dict[str, Any]:
        return {
            "id": str(obj.id),
            "dataset_id": str(obj.dataset_id),
            "filename": obj.filename,
            "format": obj.format,
            "schema": obj.schema,
            "status": dataset_status,
            "stats": obj.stats,
            "units": obj.units,
            "created_at": obj.created_at.isoformat() if obj.created_at else None,
            "extra": obj.extra,
        }
