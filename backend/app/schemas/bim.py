from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BimFileResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    dataset_id: str
    filename: str
    format: str
    status: str | None
    bim_schema: str | None = Field(
        default=None,
        validation_alias="schema",
        serialization_alias="schema",
    )
    stats: dict[str, Any] | None
    units: list[dict[str, Any]] | None
    created_at: str | None
    extra: dict[str, Any] | None


class BimMetadataResponse(BaseModel):
    id: str
    filename: str
    upload_date: str | None
    size: int | None
    content_type: str | None


class BimStoreyResponse(BaseModel):
    id: str
    bim_dataset_id: str
    global_id: str
    name: str | None
    elevation: float | None
    created_at: str | None


class BimSpaceResponse(BaseModel):
    id: str
    bim_dataset_id: str
    global_id: str
    name: str | None
    raw_name: str | None
    storey_id: str | None
    area: float | None
    volume: float | None
    created_at: str | None
