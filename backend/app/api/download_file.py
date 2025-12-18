from fastapi import APIRouter, HTTPException, status
from storage.postgres import PostgresStore
from storage.minio import MinioStore
import uuid

router = APIRouter()

@router.get("/files/{file_id}/download")
def download_file(file_id: uuid.UUID):
    # pg = PostgresStore()
    # file = pg.get_file_by_id(file_id)

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