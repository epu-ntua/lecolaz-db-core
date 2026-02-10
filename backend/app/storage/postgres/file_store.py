"""
FileStore (PostgreSQL implementation)

What this module is:
- A storage adapter responsible ONLY for persisting and querying file-related metadata in PostgreSQL.
- It hides SQLAlchemy sessions and ORM models from the rest of the application.

What this module is NOT:
- Not an API layer (no FastAPI / HTTP concerns).
- Not business logic (no validation rules, no workflows, no orchestration).
- Not object storage (MinIO/S3 upload/download lives in a separate ObjectStore adapter).

Why it exists:
- To keep a clean boundary: the application asks for "file metadata operations",
  and this adapter translates those requests into database operations.
- To keep DB details isolated, making future changes (testing, refactors, alternate backends) safer.

Rule:
- Everything outside app/storage/ must NOT import SQLAlchemy Session/engine or ORM models.
"""

import uuid
from typing import Optional, List, Dict, Any

from sqlalchemy import select

from app.db.session import SessionLocal
from app.db.models.file_metadata import FileMetadata


class FileStore:
    """
    PostgreSQL-backed implementation of file metadata persistence.
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

    def create_file_metadata(
        self,
        file_id: uuid.UUID,
        filename: str,
        object_key: str,
        content_type: Optional[str],
        size_bytes: int,
        extra: Optional[dict] = None,
    ) -> None:
        """Insert a new file_metadata record."""
        with self._session_factory() as session:
            obj = FileMetadata(
                id=file_id,
                filename=filename,
                object_key=object_key,
                content_type=content_type,
                size_bytes=size_bytes,
                extra=extra,
            )
            session.add(obj)
            session.commit()

    def list_files(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._session_factory() as session:
            stmt = select(FileMetadata).order_by(FileMetadata.created_at.desc()).limit(limit)
            rows = session.execute(stmt).scalars().all()
            return [self._to_dict(r) for r in rows]

    def get_file_by_id(self, file_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        with self._session_factory() as session:
            stmt = select(FileMetadata).where(FileMetadata.id == file_id)
            row = session.execute(stmt).scalars().first()
            return self._to_dict(row) if row else None

    @staticmethod
    def _to_dict(obj: FileMetadata) -> Dict[str, Any]:
        return {
            "id": str(obj.id),
            "filename": obj.filename,
            "object_key": obj.object_key,
            "content_type": obj.content_type,
            "size_bytes": obj.size_bytes,
            "created_at": obj.created_at.isoformat() if obj.created_at else None,
            "extra": obj.extra,
        }
