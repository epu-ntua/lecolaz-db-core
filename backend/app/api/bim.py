# app/api/bim.py

import uuid


from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.schemas import (
    BimCategoryUpdate,
    BimFileResponse,
    BimMetadataResponse,
    BimSpaceResponse,
    BimStoreyResponse,
    SimulationFileResponse,
)
from app.storage.postgres.bim_space_store import BimSpaceStore
from app.storage.postgres.bim_store import BimStore
from app.storage.postgres.bim_storey_store import BimStoreyStore
from app.storage.postgres.simulation_store import SimulationStore
from app.services.bim_view_service import get_bim_view_file, get_bim_metadata
from app.services.bim_image_service import (
    BimImageNotFound,
    BimImageStorageError,
    MAX_BIM_IMAGE_BYTES,
    get_bim_image_file,
    update_bim_image,
)


router = APIRouter(prefix="/bim", tags=["BIM"])


@router.put("/{bim_id}/image", response_model=BimFileResponse)
async def upload_bim_image(bim_id: uuid.UUID, image: UploadFile = File(...)):
    data = await image.read(MAX_BIM_IMAGE_BYTES + 1)
    try:
        return update_bim_image(bim_id, data, image.content_type)
    except ValueError as exc:
        if isinstance(exc, BimImageNotFound):
            raise HTTPException(404, str(exc)) from exc
        raise HTTPException(400, str(exc)) from exc
    except BimImageStorageError as exc:
        raise HTTPException(503, str(exc)) from exc


@router.get("/{bim_id}/image")
def get_bim_image(bim_id: uuid.UUID):
    try:
        chunks, content_type = get_bim_image_file(bim_id)
    except BimImageNotFound as exc:
        raise HTTPException(404, str(exc)) from exc
    except BimImageStorageError as exc:
        raise HTTPException(502, str(exc)) from exc
    return StreamingResponse(chunks, media_type=content_type)


@router.get("", response_model=list[BimFileResponse])
def list_bim(limit: int = 100):
    bs = BimStore()
    return bs.list_bim_models(limit=limit)


@router.get("/by-dataset/{dataset_id}", response_model=BimFileResponse)
def get_bim_by_dataset(dataset_id: str):
    bs = BimStore()
    try:
        dataset_uuid = uuid.UUID(dataset_id)
    except ValueError:
        raise HTTPException(400, "Invalid dataset id")

    bim = bs.get_bim_by_dataset_id(dataset_uuid)
    if not bim:
        raise HTTPException(404, "BIM not found")
    return bim


@router.patch("/{bim_id}/category", response_model=BimFileResponse)
def update_bim_category(bim_id: str, payload: BimCategoryUpdate):
    try:
        bim_uuid = uuid.UUID(bim_id)
    except ValueError:
        raise HTTPException(400, "Invalid BIM id")

    bim = BimStore().update_category(bim_uuid, payload.category)
    if not bim:
        raise HTTPException(404, "BIM not found")
    return bim


@router.get("/{bim_id}", response_model=BimFileResponse)
def get_bim(bim_id: str):
    bs = BimStore()
    try:
        bim_uuid = uuid.UUID(bim_id)
    except ValueError:
        raise HTTPException(400, "Invalid BIM id")

    bim = bs.get_bim_by_id(bim_uuid)
    if not bim:
        raise HTTPException(404, "BIM not found")
    return bim


@router.get(
    "/{bim_id}/storeys",
    response_model=list[BimStoreyResponse],
)
def list_bim_storeys(bim_id: str, limit: int = 500):
    storey_store = BimStoreyStore()

    try:
        bim_uuid = uuid.UUID(bim_id)
    except ValueError:
        raise HTTPException(400, "Invalid BIM id")

    bs = BimStore()
    bim = bs.get_bim_by_id(bim_uuid)
    if not bim:
        raise HTTPException(404, "BIM not found")

    return storey_store.list_by_bim_dataset_id(bim_uuid, limit=limit)


@router.get(
    "/{bim_id}/spaces",
    response_model=list[BimSpaceResponse],
)
def list_bim_spaces(bim_id: str, limit: int = 2000):
    space_store = BimSpaceStore()

    try:
        bim_uuid = uuid.UUID(bim_id)
    except ValueError:
        raise HTTPException(400, "Invalid BIM id")

    bs = BimStore()
    bim = bs.get_bim_by_id(bim_uuid)
    if not bim:
        raise HTTPException(404, "BIM not found")

    return space_store.list_by_bim_dataset_id(bim_uuid, limit=limit)


@router.get(
    "/{bim_id}/simulations",
    response_model=list[SimulationFileResponse],
)
def list_bim_simulations(bim_id: str, limit: int = 100):
    simulation_store = SimulationStore()

    try:
        bim_uuid = uuid.UUID(bim_id)
    except ValueError:
        raise HTTPException(400, "Invalid BIM id")

    bs = BimStore()
    bim = bs.get_bim_by_id(bim_uuid)
    if not bim:
        raise HTTPException(404, "BIM not found")

    return simulation_store.list_by_bim_dataset_id(bim_uuid, limit=limit)


@router.get("/{bim_id}/metadata", response_model=BimMetadataResponse)
def metadata_bim(bim_id: str):
    metadata = get_bim_metadata(bim_id)
    if not metadata:
        raise HTTPException(404, "BIM metadata not found")
    return metadata


@router.get("/{bim_id}/stream")
def stream_bim(bim_id: str):
    result = get_bim_view_file(bim_id)

    if not result:
        raise HTTPException(404, "BIM not found")

    file_stream, content_type, filename = result

    return StreamingResponse(
        file_stream,
        media_type=content_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"'
        },
    )
