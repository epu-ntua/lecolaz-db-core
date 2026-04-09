from typing import Any

from pydantic import BaseModel


class SimulationFileResponse(BaseModel):
    id: str
    dataset_id: str
    bim_dataset_id: str | None
    filename: str
    format: str
    status: str | None
    created_at: str | None
    metadata: dict[str, Any] | None


class SimulationVariableResponse(BaseModel):
    id: str
    simulation_dataset_id: str
    bim_space_id: str | None
    variable_id: str
    variable_name: str
    unit: str | None
    frequency: str | None
    key: str | None
    created_at: str | None


class SimulationTimeseriesResponse(BaseModel):
    id: str
    simulation_dataset_id: str
    variable_id: str
    timestamp: str | None
    value: float
    created_at: str | None
