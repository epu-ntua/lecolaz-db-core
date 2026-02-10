# app/services/file_ingestion.py

import uuid
from typing import Any, Dict, Optional

from app.storage.object.minio import MinioStore
from app.storage.postgres.file_store import FileStore
from app.storage.postgres.bim_store import BimStore


BIM_EXTENSIONS = (".ifc", ".ifczip", ".ifcxml")


def is_bim_filename(filename: str) -> bool:
    name = (filename or "").lower()
    return name.endswith(BIM_EXTENSIONS)


def ingest_upload(
    *,
    filename: str,
    content_type: Optional[str],
    data: bytes,
    extra: Optional[dict] = None,
    object_store: Optional[MinioStore] = None,
    file_store: Optional[FileStore] = None,
    bim_strict: bool = False,
) -> Dict[str, Any]:
    """
    Orchestrates upload + metadata persistence.
    Keeps endpoint clean; stores stay dumb.
    """
    object_store = MinioStore()
    file_store = FileStore()

    file_id = uuid.uuid4()
    object_key = f"uploads/{file_id}/{filename}"

    # 1) Upload to MinIO first
    object_store.put_object(
        object_key=object_key,
        data=data,
        content_type=content_type,
    )

    # 2) Persist generic metadata only if MinIO succeeded
    try:
        file_store.create_file_metadata(
            file_id=file_id,
            filename=filename,
            object_key=object_key,
            content_type=content_type,
            size_bytes=len(data),
            extra=extra,
        )
    except Exception:
        # rollback object if DB insert fails
        object_store.delete_object(object_key)
        raise

    # 3) Optional BIM specialization (placeholder)
    if is_bim_filename(filename):
        try:
            bim_store = BimStore()
            bim_store.create_bim_record(
                bim_id=uuid.uuid4(),
                file_id=file_id,
                format=filename.split(".")[-1],
                schema=None,
                extra=None,
            )
        except Exception:
            if bim_strict:
                object_store.delete_object(object_key)
                raise
            else:
                print(f"[WARN] BIM record insert failed for file_id={file_id}")

    return {
        "id": str(file_id),
        "filename": filename,
        "object_key": object_key,
    }
