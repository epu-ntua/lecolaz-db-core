# app/api/bim.py

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse

from app.services.file_ingestion_service import ingest_upload, is_bim_filename
from app.schemas import BimFileResponse, BimMetadataResponse, FileUploadResponse
from app.storage.postgres.bim_store import BimStore
from app.services.bim_view_service import get_bim_view_file, get_bim_metadata


router = APIRouter(prefix="/bim", tags=["BIM"])


@router.post("/upload", response_model=FileUploadResponse)
async def upload_bim(file: UploadFile = File(...)):
    if not is_bim_filename(file.filename):
        raise HTTPException(400, "Only BIM files allowed")

    data = await file.read()
    return ingest_upload(
        filename=file.filename,
        content_type=file.content_type,
        data=data,
        bim_strict=True,
    )


@router.get("", response_model=list[BimFileResponse])
def list_bim(limit: int = 100):
    bs = BimStore()
    return bs.list_bim_models(limit=limit)


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

