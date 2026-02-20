from typing import Any

from pydantic import BaseModel


class FileUploadResponse(BaseModel):
    id: str
    filename: str
    object_key: str


class FileMetadataResponse(BaseModel):
    id: str
    filename: str
    object_key: str
    content_type: str | None
    size_bytes: int | None
    created_at: str | None
    extra: dict[str, Any] | None
