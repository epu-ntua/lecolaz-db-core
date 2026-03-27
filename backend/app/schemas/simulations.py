from typing import Any

from pydantic import BaseModel


class SimulationFileResponse(BaseModel):
    id: str
    dataset_id: str
    filename: str
    format: str
    status: str | None
    created_at: str | None
    extra: dict[str, Any] | None


class SimulationProcessResponse(BaseModel):
    id: str
    status: str
    message: str
