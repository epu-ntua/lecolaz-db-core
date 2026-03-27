# app/api/files.py

import uuid
from fastapi import APIRouter, HTTPException, status

from app.schemas import DatasetResponse
from app.storage.postgres.dataset_store import DatasetStore

router = APIRouter(prefix="/files", tags=["Files"])


@router.get("", response_model=list[DatasetResponse])
def list_files(limit: int = 100):
    dataset_store = DatasetStore()
    return dataset_store.list_datasets(limit=limit)

@router.get("/{file_id}/download")
def download_file(file_id: uuid.UUID):
    # implement with a service in future when we have reverse proxy + presigned URLs working
    # dataset_store = DatasetStore()
    # dataset = dataset_store.get_dataset_by_id(file_id)

    # if not dataset:
    #     raise HTTPException(status_code=404, detail="File not found")

    # minio = MinioStore()
    # url = minio.get_presigned_get_url(dataset["object_key"])

    # return {
    #     "id": str(dataset["id"]),
    #     "filename": dataset["filename"],
    #     "download_url": url,
    #     "expires_in_seconds": 3600,
    # }

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Direct download not enabled yet (pending reverse proxy setup)",
    )
