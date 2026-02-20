"""
Centralized API response schemas.

This package gathers the Pydantic models used by endpoint `response_model`
declarations so endpoint contracts are explicit,
validated, and easy to import from one place.
"""

from app.schemas.bim import BimFileResponse, BimMetadataResponse
from app.schemas.files import FileMetadataResponse, FileUploadResponse
from app.schemas.health import HealthResponse

__all__ = [
    "BimFileResponse",
    "BimMetadataResponse",
    "FileMetadataResponse",
    "FileUploadResponse",
    "HealthResponse",
]
