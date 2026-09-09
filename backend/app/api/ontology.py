# app/api/ontology.py

import uuid
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.async_session import AsyncSessionLocal
from app.ontology.dto import SyncResult
from app.ontology.exceptions import BimDatasetNotFoundError
from app.ontology.service import OntologyService, get_ontology_service

router = APIRouter(prefix="/ontology", tags=["Ontology"])


async def get_async_db() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


@router.post("/bim/{bim_id}/sync")
async def sync_bim_ontology(
    bim_id: str,
    db: AsyncSession = Depends(get_async_db),
    service: OntologyService = Depends(get_ontology_service),
):
    try:
        bim_uuid = uuid.UUID(bim_id)
    except ValueError:
        raise HTTPException(400, "Invalid BIM id")

    try:
        result = await service.sync_bim_dataset(db=db, bim_dataset_id=bim_uuid)
    except BimDatasetNotFoundError as exc:
        raise HTTPException(404, str(exc))

    if not result.success:
        raise HTTPException(502, result.error or "Ontology sync failed")
    return _to_response(result)


@router.post("/resync")
async def resync_ontology(
    db: AsyncSession = Depends(get_async_db),
    service: OntologyService = Depends(get_ontology_service),
):
    return await service.resync_unsynced_datasets(db)


def _to_response(result: SyncResult) -> dict:
    return {
        "bim_dataset_id": str(result.bim_dataset_id),
        "dataset_id": str(result.dataset_id),
        "graph_uri": result.graph_uri,
        "success": result.success,
        "triple_count": result.triple_count,
        "synced_at": result.synced_at.isoformat() if result.synced_at else None,
        "error": result.error,
    }
