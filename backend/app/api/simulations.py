import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.services.file_ingestion_service import ingest_upload, is_energyplus_filename
from app.schemas import (
    SimulationFileResponse,
    FileUploadResponse,
    SimulationProcessResponse,
)
from app.services.simulation_processing_service import (
    process_simulation,
    SimulationNotFoundError,
    SimulationConflictError,
    SimulationProcessingError,
)
from app.storage.postgres.simulation_store import SimulationStore


router = APIRouter(prefix="/simulations", tags=["Simulations"])


@router.post("/upload", response_model=FileUploadResponse)
async def upload_simulation(file: UploadFile = File(...)):
    if not is_energyplus_filename(file.filename):
        raise HTTPException(400, "Only simulation files allowed")

    data = await file.read()
    return ingest_upload(
        filename=file.filename,
        content_type=file.content_type,
        data=data,
        simulation_strict=True,
    )


@router.get("", response_model=list[SimulationFileResponse])
def list_simulations(limit: int = 100):
    simulation_store = SimulationStore()
    return simulation_store.list_simulation_models(limit=limit)


@router.post("/{simulation_id}/process", response_model=SimulationProcessResponse)
def process_simulation_endpoint(simulation_id: str, force: bool = False):
    try:
        simulation_uuid = uuid.UUID(simulation_id)
    except ValueError:
        raise HTTPException(400, "Invalid simulation id")

    try:
        result = process_simulation(simulation_uuid, allow_reprocess=force)
    except SimulationNotFoundError as exc:
        raise HTTPException(404, str(exc))
    except SimulationConflictError as exc:
        raise HTTPException(409, str(exc))
    except SimulationProcessingError as exc:
        raise HTTPException(500, str(exc))

    return {
        "id": result["id"],
        "status": result["status"],
        "message": "Simulation processing completed",
    }
