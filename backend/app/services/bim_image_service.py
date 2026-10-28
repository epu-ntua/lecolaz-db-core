"""Validate and store the optional image associated with a BIM model."""

import uuid

from app.storage.object.minio import MinioStore
from app.storage.postgres.bim_store import BimStore


MAX_BIM_IMAGE_BYTES = 10 * 1024 * 1024
IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


class BimImageNotFound(ValueError):
    pass


class BimImageStorageError(RuntimeError):
    pass


def validate_bim_image(data: bytes, content_type: str | None) -> None:
    if content_type not in IMAGE_CONTENT_TYPES:
        raise ValueError("Image must be JPEG, PNG, or WebP")
    if not data or len(data) > MAX_BIM_IMAGE_BYTES:
        raise ValueError("Image must be between 1 byte and 10 MB")
    valid_signature = {
        "image/jpeg": data.startswith(b"\xff\xd8\xff"),
        "image/png": data.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/webp": data.startswith(b"RIFF") and data[8:12] == b"WEBP",
    }
    if not valid_signature[content_type]:
        raise ValueError("Image content does not match its format")


def update_bim_image(bim_id: uuid.UUID, data: bytes, content_type: str | None) -> dict:
    validate_bim_image(data, content_type)
    bim_store = BimStore()
    old = bim_store.get_bim_by_id(bim_id)
    if not old:
        raise BimImageNotFound("BIM not found")

    key = f"bim/{old['dataset_id']}/image/{uuid.uuid4()}"
    object_store = None
    try:
        object_store = MinioStore()
        object_store.put_object(key, data, content_type)
        updated = bim_store.update_image(bim_id, key)
        if not updated:
            raise BimImageNotFound("BIM not found")
    except Exception as exc:
        if object_store is not None:
            try:
                object_store.delete_object(key)
            except Exception:
                pass
        if isinstance(exc, BimImageNotFound):
            raise
        raise BimImageStorageError("Building image could not be saved") from exc

    if old["image_object_key"]:
        try:
            object_store.delete_object(old["image_object_key"])
        except Exception:
            pass
    return updated


def get_bim_image_file(bim_id: uuid.UUID):
    bim = BimStore().get_bim_by_id(bim_id)
    if not bim or not bim["image_object_key"]:
        raise BimImageNotFound("Building image not found")
    try:
        response = MinioStore().get_object_stream(bim["image_object_key"])
    except RuntimeError as exc:
        raise BimImageStorageError("Building image could not be loaded") from exc

    def chunks():
        try:
            yield from response.stream(32 * 1024)
        finally:
            response.close()
            response.release_conn()

    return chunks(), response.headers.get("Content-Type", "image/jpeg")
