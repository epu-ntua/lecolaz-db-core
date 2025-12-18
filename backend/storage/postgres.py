"""
PostgreSQL / TimescaleDB storage adapter.

Responsibilities:
- connect to the database
- store structured data
- store metadata (JSONB)
- retrieve/query data

NO business logic here.
"""
from sqlalchemy import create_engine, text
from core.config import settings
import uuid

class PostgresStore:
    def __init__(self):
        self.engine = create_engine(settings.POSTGRES_DSN)

    def insert_file_metadata(
        self,
        file_id: uuid.UUID,
        filename: str,
        object_key: str,
        content_type: str | None,
        size_bytes: int,
        extra: dict | None = None,
    ):
        query = text("""
            INSERT INTO file_metadata
            (id, filename, object_key, content_type, size_bytes, extra)
            VALUES
            (:id, :filename, :object_key, :content_type, :size_bytes, :extra)
        """)

        with self.engine.begin() as conn:
            conn.execute(
                query,
                {
                    "id": file_id,
                    "filename": filename,
                    "object_key": object_key,
                    "content_type": content_type,
                    "size_bytes": size_bytes,
                    "extra": extra,
                },
            )

    def list_files(self, limit: int = 100):
        query = text("""
            SELECT
                id,
                filename,
                object_key,
                content_type,
                size_bytes,
                created_at
            FROM file_metadata
            ORDER BY created_at DESC
            LIMIT :limit
        """)

        with self.engine.connect() as conn:
            result = conn.execute(query, {"limit": limit})
            rows = result.mappings().all()

        return rows
    
    def get_file_by_id(self, file_id):
        query = text("""
            SELECT
                id,
                filename,
                object_key,
                content_type,
                size_bytes,
                created_at
            FROM file_metadata
            WHERE id = :id
        """)

        with self.engine.connect() as conn:
            result = conn.execute(query, {"id": file_id})
            row = result.mappings().first()

        return row
