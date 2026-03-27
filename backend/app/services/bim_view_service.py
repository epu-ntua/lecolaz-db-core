import uuid

from app.storage.postgres.bim_store import BimStore
from app.storage.postgres.dataset_store import DatasetStore
from app.storage.object.minio import MinioStore


def get_bim_view_file(bim_id: str):
    bim_store = BimStore()
    dataset_store = DatasetStore()
    minio_store = MinioStore()

    # Convert string to UUID
    try:
        bim_uuid = uuid.UUID(bim_id)
    except ValueError:
        return None

    # Get BIM metadata
    bim = bim_store.get_bim_by_id(bim_uuid)
    if not bim:
        return None

    # Get dataset metadata
    dataset_uuid = uuid.UUID(bim["dataset_id"])
    dataset = dataset_store.get_dataset_by_id(dataset_uuid)
    if not dataset:
        return None

    # Get object from MinIO
    response = minio_store.get_object_stream(dataset["object_key"])

    # Define streaming generator
    def file_iterator():
        try:
            for chunk in response.stream(32 * 1024):
                yield chunk
        finally:
            response.close()
            response.release_conn()

    return file_iterator(), dataset["content_type"], dataset["filename"]


def get_bim_metadata(bim_id: str):
    bim_store = BimStore()
    dataset_store = DatasetStore()

    try:
        bim_uuid = uuid.UUID(bim_id)
    except ValueError:
        return None

    bim = bim_store.get_bim_by_id(bim_uuid)
    if not bim:
        return None

    dataset_uuid = uuid.UUID(bim["dataset_id"])
    dataset = dataset_store.get_dataset_by_id(dataset_uuid)
    if not dataset:
        return None

    return {
        "id": bim["id"],
        "filename": bim["filename"],
        "upload_date": dataset["created_at"],
        "size": dataset["size_bytes"],
        "content_type": dataset["content_type"],
    }
