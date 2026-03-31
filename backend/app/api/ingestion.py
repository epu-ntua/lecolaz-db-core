from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from app.schemas import FileUploadResponse
from app.services.bim_processing_service import (
    BimConflictError,
    BimNotFoundError,
    BimProcessingError,
)
from app.services.simulation_processing_service import (
    SimulationConflictError,
    SimulationNotFoundError,
    SimulationProcessingError,
)
from app.services.upload_ingestion_service import (
    ingest_upload,
    is_bim_filename,
    is_energyplus_filename,
    UploadIngestionError,
)


router = APIRouter(prefix="/ingestion", tags=["Ingestion"])


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    data = await file.read()
    try:
        return ingest_upload(
            filename=file.filename,
            content_type=file.content_type,
            data=data,
            background_tasks=background_tasks,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except UploadIngestionError as exc:
        raise HTTPException(503, str(exc))
    except BimNotFoundError as exc:
        raise HTTPException(404, str(exc))
    except BimConflictError as exc:
        raise HTTPException(409, str(exc))
    except BimProcessingError as exc:
        raise HTTPException(500, str(exc))
    except SimulationNotFoundError as exc:
        raise HTTPException(404, str(exc))
    except SimulationConflictError as exc:
        raise HTTPException(409, str(exc))
    except SimulationProcessingError as exc:
        raise HTTPException(500, str(exc))


@router.post("/bim/upload", response_model=FileUploadResponse)
async def upload_bim(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not is_bim_filename(file.filename):
        raise HTTPException(400, "Only BIM files allowed")

    data = await file.read()
    try:
        return ingest_upload(
            filename=file.filename,
            content_type=file.content_type,
            data=data,
            type="bim",
            background_tasks=background_tasks,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except UploadIngestionError as exc:
        raise HTTPException(503, str(exc))
    except BimNotFoundError as exc:
        raise HTTPException(404, str(exc))
    except BimConflictError as exc:
        raise HTTPException(409, str(exc))
    except BimProcessingError as exc:
        raise HTTPException(500, str(exc))


@router.post("/simulations/upload", response_model=FileUploadResponse)
async def upload_simulation(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not is_energyplus_filename(file.filename):
        raise HTTPException(400, "Only simulation files allowed")

    data = await file.read()
    try:
        return ingest_upload(
            filename=file.filename,
            content_type=file.content_type,
            data=data,
            type="simulation",
            background_tasks=background_tasks,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except UploadIngestionError as exc:
        raise HTTPException(503, str(exc))
    except SimulationNotFoundError as exc:
        raise HTTPException(404, str(exc))
    except SimulationConflictError as exc:
        raise HTTPException(409, str(exc))
    except SimulationProcessingError as exc:
        raise HTTPException(500, str(exc))
