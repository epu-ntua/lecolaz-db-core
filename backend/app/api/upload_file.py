from fastapi import APIRouter, UploadFile, File, HTTPException
import uuid

from storage.minio import MinioStore
from storage.postgres import PostgresStore

router = APIRouter()


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # Read file into memory (OK for now in early dev)
    data = await file.read()

    file_id = uuid.uuid4()
    object_key = f"uploads/{file_id}/{file.filename}"

    #Store file in MinIO FIRST
    minio = MinioStore()
    try:
        minio.put_object(
            object_key=object_key,
            data=data,
            content_type=file.content_type,
        )
    except Exception as e:
        # If storage fails, abort the request
        raise HTTPException(
            status_code=500,
            detail=f"File upload to storage failed: {str(e)}",
        )

    # Store metadata in Postgres ONLY if MinIO succeeded
    pg = PostgresStore()
    try:
        pg.insert_file_metadata(
            file_id=file_id,
            filename=file.filename,
            object_key=object_key,
            content_type=file.content_type,
            size_bytes=len(data),
            extra=None,
        )
    except Exception as e:
        # Metadata failed AFTER file upload
        # At this stage we choose to fail loudly
        minio.delete_object(object_key)
        raise HTTPException(
            status_code=500,
            detail=f"Metadata insert failed: {str(e)}",
        )

    return {
        "id": str(file_id),
        "filename": file.filename,
        "object_key": object_key,
    }
