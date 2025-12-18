from fastapi import APIRouter
from storage.postgres import PostgresStore
from storage.minio import MinioStore

router = APIRouter()


@router.get("/health")
def health():
    # Check Postgres
    pg = PostgresStore()
    pg.health_check()

    # Check MinIO
    minio = MinioStore()
    minio._ensure_bucket()

    return {
        "status": "ok",
        "postgres": "ok",
        "minio": "ok",
    }
