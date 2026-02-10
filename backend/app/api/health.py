from fastapi import APIRouter
from app.storage.postgres.file_store import FileStore
from app.storage.object.minio import MinioStore

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health():
    # Check Postgres
    fs = FileStore()
    fs.health_check()

    # Check MinIO
    minio = MinioStore()
    minio._ensure_bucket()

    return {
        "status": "ok",
        "postgres": "ok",
        "minio": "ok",
    }
