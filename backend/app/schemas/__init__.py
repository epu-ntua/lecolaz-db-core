"""
Centralized API response schemas.

This package gathers the Pydantic models used by endpoint `response_model`
declarations so endpoint contracts are explicit,
validated, and easy to import from one place.
"""

from app.schemas.bim import (
    BimCategoryUpdate,
    BimFileResponse,
    BimMetadataResponse,
    BimSpaceResponse,
    BimStoreyResponse,
)
from app.schemas.components import (
    ModularComponentBuildingUpdate,
    ModularComponentResponse,
    ModularComponentSensorsUpdate,
)
from app.schemas.datasets import DatasetResponse, FileUploadResponse
from app.schemas.health import HealthResponse
from app.schemas.simulations import (
    SimulationFileResponse,
    SimulationTimeseriesResponse,
    SimulationVariableResponse,
)

__all__ = [
    "BimCategoryUpdate",
    "BimFileResponse",
    "BimMetadataResponse",
    "BimSpaceResponse",
    "BimStoreyResponse",
    "DatasetResponse",
    "FileUploadResponse",
    "HealthResponse",
    "ModularComponentBuildingUpdate",
    "ModularComponentResponse",
    "ModularComponentSensorsUpdate",
    "SimulationFileResponse",
    "SimulationTimeseriesResponse",
    "SimulationVariableResponse",
]
