from fastapi import APIRouter, UploadFile, File
import uuid

from storage.minio import MinioStore
from storage.postgres import PostgresStore

router = APIRouter()

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    data = await file.read()

    file_id = uuid.uuid4()
    object_key = f"uploads/{file_id}/{file.filename}"

    # Store file in MinIO
    minio = MinioStore()
    minio.put_object(
        object_key=object_key,
        data=data,
        content_type=file.content_type,
    )

    # Store metadata in Postgres
    pg = PostgresStore()
    pg.insert_file_metadata(
        file_id=file_id,
        filename=file.filename,
        object_key=object_key,
        content_type=file.content_type,
        size_bytes=len(data),
        extra=None,
    )

    return {
        "id": str(file_id),
        "filename": file.filename,
        "object_key": object_key,
    }
