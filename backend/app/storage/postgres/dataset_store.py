"""
DatasetStore (PostgreSQL implementation)

What this module is:
- A storage adapter responsible ONLY for persisting and querying dataset metadata in PostgreSQL.

What this module is NOT:
- Not an API layer
- Not business logic
- Not object storage

Why it exists:
- To provide a clean interface for dataset metadata operations
- To isolate DB concerns from the rest of the system
"""

import uuid
from typing import Optional, List, Dict, Any

from sqlalchemy import select

from app.db.session import SessionLocal
from app.db.models.dataset import Dataset


class DatasetStore:
    """
        PostgreSQL-backed implementation of dataset metadata persistence.
    """

    def __init__(self, session_factory=SessionLocal):
        # session_factory() -> SQLAlchemy Session
        self._session_factory = session_factory

    def health_check(self) -> None:
        """Raises RuntimeError if DB is not reachable."""
        try:
            with self._session_factory() as session:
                session.execute(select(1))
        except Exception as e:
            raise RuntimeError(f"Postgres health check failed: {e}")

    def create_dataset(
        self,
        dataset_id: uuid.UUID,
        dataset_type: str,
        subtype: Optional[str],
        filename: str,
        object_key: str,
        content_type: Optional[str],
        size_bytes: int,
        status: str = "raw",
        source: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """Insert a new dataset record."""
        with self._session_factory() as session:
            obj = Dataset(
                id=dataset_id,
                type=dataset_type,
                subtype=subtype,
                filename=filename,
                object_key=object_key,
                content_type=content_type,
                size_bytes=size_bytes,
                status=status,
                source=source,
                dataset_metadata=metadata,
            )
            session.add(obj)
            session.commit()

    def list_datasets(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._session_factory() as session:
            stmt = select(Dataset).order_by(Dataset.created_at.desc()).limit(limit)
            rows = session.execute(stmt).scalars().all()
            return [self._to_dict(r) for r in rows]

    def get_dataset_by_id(self, dataset_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        with self._session_factory() as session:
            stmt = select(Dataset).where(Dataset.id == dataset_id)
            row = session.execute(stmt).scalars().first()
            return self._to_dict(row) if row else None

    def update_dataset_status(
        self,
        dataset_id: uuid.UUID,
        status: str,
        metadata_patch: Optional[dict] = None,
    ) -> Optional[Dict[str, Any]]:
        with self._session_factory() as session:
            stmt = select(Dataset).where(Dataset.id == dataset_id)
            obj = session.execute(stmt).scalars().first()
            if not obj:
                return None

            obj.status = status
            if metadata_patch:
                merged_metadata = dict(obj.dataset_metadata or {})
                merged_metadata.update(metadata_patch)
                obj.dataset_metadata = merged_metadata

            session.commit()
            session.refresh(obj)
            return self._to_dict(obj)

    @staticmethod
    def _to_dict(obj: Dataset) -> Dict[str, Any]:
        return {
            "id": str(obj.id),
            "type": obj.type,
            "subtype": obj.subtype,
            "filename": obj.filename,
            "object_key": obj.object_key,
            "content_type": obj.content_type,
            "size_bytes": obj.size_bytes,
            "status": obj.status,
            "source": obj.source,
            "created_at": obj.created_at.isoformat() if obj.created_at else None,
            "updated_at": obj.updated_at.isoformat() if obj.updated_at else None,
            "metadata": obj.dataset_metadata,
        }
