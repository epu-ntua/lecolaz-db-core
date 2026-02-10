# app/api/bim.py

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.services.file_ingestion_service import ingest_upload, is_bim_filename
from app.storage.postgres.bim_store import BimStore

router = APIRouter(prefix="/bim", tags=["BIM"])


@router.post("/upload")
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


@router.get("")
def list_bim(limit: int = 100):
    bs = BimStore()
    return bs.list_bim_models(limit=limit)
