from typing import Any

from pydantic import BaseModel


class FileUploadResponse(BaseModel):
    dataset_id: str


class DatasetResponse(BaseModel):
    id: str
    type: str
    subtype: str | None
    filename: str
    object_key: str
    content_type: str | None
    size_bytes: int | None
    status: str
    source: str | None
    created_at: str | None
    updated_at: str | None
    metadata: dict[str, Any] | None
