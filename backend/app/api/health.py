from fastapi import APIRouter
from storage.postgres import PostgresStore
from storage.minio import MinioStore

router = APIRouter()

@router.get("/health")
def health():
    pg = PostgresStore()

    minio = MinioStore()
    minio.connect()

    return {
        "status": "ok",
        "env": "loaded"
    }
