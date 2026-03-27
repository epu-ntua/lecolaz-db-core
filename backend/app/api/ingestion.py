from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas import FileUploadResponse
from app.services.bim_processing_service import (
    BimConflictError,
    BimNotFoundError,
    BimProcessingError,
    process_bim,
)
from app.services.upload_ingestion_service import (
    ingest_upload,
    is_bim_filename,
    is_energyplus_filename,
)
import uuid


router = APIRouter(prefix="/ingestion", tags=["Ingestion"])


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)):
    data = await file.read()
    try:
        return ingest_upload(
            filename=file.filename,
            content_type=file.content_type,
            data=data,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.post("/bim/upload", response_model=FileUploadResponse)
async def upload_bim(file: UploadFile = File(...)):
    if not is_bim_filename(file.filename):
        raise HTTPException(400, "Only BIM files allowed")

    data = await file.read()
    try:
        result = ingest_upload(
            filename=file.filename,
            content_type=file.content_type,
            data=data,
            type="bim",
        )
        process_bim(uuid.UUID(result["dataset_id"]))
        return result
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except BimNotFoundError as exc:
        raise HTTPException(404, str(exc))
    except BimConflictError as exc:
        raise HTTPException(409, str(exc))
    except BimProcessingError as exc:
        raise HTTPException(500, str(exc))


@router.post("/simulations/upload", response_model=FileUploadResponse)
async def upload_simulation(file: UploadFile = File(...)):
    if not is_energyplus_filename(file.filename):
        raise HTTPException(400, "Only simulation files allowed")

    data = await file.read()
    try:
        return ingest_upload(
            filename=file.filename,
            content_type=file.content_type,
            data=data,
            type="simulation",
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
