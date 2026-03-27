from fastapi import APIRouter
from app.schemas import HealthResponse
from app.storage.postgres.dataset_store import DatasetStore
from app.storage.object.minio import MinioStore

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
def health():
    # Check Postgres
    dataset_store = DatasetStore()
    dataset_store.health_check()

    # Check MinIO
    minio = MinioStore()
    minio._ensure_bucket()

    return {
        "status": "ok",
        "postgres": "ok",
        "minio": "ok",
    }
