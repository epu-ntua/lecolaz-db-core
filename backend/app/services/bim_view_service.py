import uuid

from app.storage.postgres.bim_store import BimStore
from app.storage.postgres.file_store import FileStore
from app.storage.object.minio import MinioStore


def get_bim_view_file(bim_id: str):
    bim_store = BimStore()
    file_store = FileStore()
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

    # Get file metadata
    file_uuid = uuid.UUID(bim["file_id"])
    file = file_store.get_file_by_id(file_uuid)
    if not file:
        return None

    # Get object from MinIO
    response = minio_store.client.get_object(
        minio_store.bucket,
        file["object_key"]
    )

    # Define streaming generator
    def file_iterator():
        try:
            for chunk in response.stream(32 * 1024):
                yield chunk
        finally:
            response.close()
            response.release_conn()

    return file_iterator(), file["content_type"], file["filename"]


def get_bim_metadata(bim_id: str):
    bim_store = BimStore()
    file_store = FileStore()

    try:
        bim_uuid = uuid.UUID(bim_id)
    except ValueError:
        return None

    bim = bim_store.get_bim_by_id(bim_uuid)
    if not bim:
        return None

    file_uuid = uuid.UUID(bim["file_id"])
    file = file_store.get_file_by_id(file_uuid)
    if not file:
        return None

    return {
        "id": bim["id"],
        "filename": bim["filename"],
        "upload_date": file["created_at"],
        "size": file["size_bytes"],
        "content_type": file["content_type"],
    }
