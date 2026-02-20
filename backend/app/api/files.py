# app/api/files.py

import uuid
from fastapi import APIRouter, HTTPException, UploadFile, File, status

from app.services.file_ingestion_service import ingest_upload
from app.schemas import FileMetadataResponse, FileUploadResponse
from app.storage.postgres.file_store import FileStore

router = APIRouter(prefix="/files", tags=["Files"])


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)):
    data = await file.read()
    return ingest_upload(
        filename=file.filename,
        content_type=file.content_type,
        data=data,
    )

@router.get("", response_model=list[FileMetadataResponse])
def list_files(limit: int = 100):
    fs = FileStore()
    return fs.list_files(limit=limit)

@router.get("/{file_id}/download")
def download_file(file_id: uuid.UUID):
    # implement with a service in future when we have reverse proxy + presigned URLs working
    # fs = FileStore()
    # file = fs.get_file_by_id(file_id)

    # if not file:
    #     raise HTTPException(status_code=404, detail="File not found")

    # minio = MinioStore()
    # url = minio.get_presigned_get_url(file["object_key"])

    # return {
    #     "id": str(file["id"]),
    #     "filename": file["filename"],
    #     "download_url": url,
    #     "expires_in_seconds": 3600,
    # }

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Direct download not enabled yet (pending reverse proxy setup)",
    )
