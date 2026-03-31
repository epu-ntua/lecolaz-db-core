# app/api/bim.py

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas import BimFileResponse, BimMetadataResponse
from app.storage.postgres.bim_store import BimStore
from app.services.bim_view_service import get_bim_view_file, get_bim_metadata


router = APIRouter(prefix="/bim", tags=["BIM"])


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

