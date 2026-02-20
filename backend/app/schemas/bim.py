from typing import Any

from pydantic import BaseModel


class BimFileResponse(BaseModel):
    id: str
    file_id: str
    filename: str
    format: str
    schema: str | None
    created_at: str | None
    extra: dict[str, Any] | None


class BimMetadataResponse(BaseModel):
    id: str
    filename: str
    upload_date: str | None
    size: int | None
    content_type: str | None
