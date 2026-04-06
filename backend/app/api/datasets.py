import uuid
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas import DatasetResponse
from app.storage.object.minio import MinioStore
from app.storage.postgres.dataset_store import DatasetStore


router = APIRouter(prefix="/datasets", tags=["Datasets"])


@router.get("", response_model=list[DatasetResponse])
def list_datasets(limit: int = 100):
    dataset_store = DatasetStore()
    return dataset_store.list_datasets(limit=limit)


@router.get("/{dataset_id}", response_model=DatasetResponse)
def get_dataset(dataset_id: uuid.UUID):
    dataset_store = DatasetStore()
    dataset = dataset_store.get_dataset_by_id(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.get("/{dataset_id}/download")
def download_dataset(dataset_id: uuid.UUID):
    dataset_store = DatasetStore()
    minio_store = MinioStore()

    dataset = dataset_store.get_dataset_by_id(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    object_key = dataset.get("object_key")
    if not object_key:
        raise HTTPException(status_code=500, detail="Dataset has no object key")

    try:
        response = minio_store.get_object_stream(object_key)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail="Failed to fetch file from object storage") from exc

    def file_iterator():
        try:
            for chunk in response.stream(32 * 1024):
                yield chunk
        finally:
            response.close()
            response.release_conn()

    filename = dataset["filename"] or f"{dataset_id}"
    content_type = dataset["content_type"] or "application/octet-stream"
    ascii_filename = filename.replace("\"", "")
    quoted_filename = quote(filename, safe="")

    return StreamingResponse(
        file_iterator(),
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename=\"{ascii_filename}\"; filename*=UTF-8''{quoted_filename}"
        },
    )
