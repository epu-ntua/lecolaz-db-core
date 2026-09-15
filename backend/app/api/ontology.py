# app/api/ontology.py

from typing import AsyncIterator

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.async_session import AsyncSessionLocal
from app.ontology.service import OntologyService, get_ontology_service

router = APIRouter(prefix="/ontology", tags=["Ontology"])


async def get_async_db() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


@router.post("/resync")
async def resync_ontology(
    db: AsyncSession = Depends(get_async_db),
    service: OntologyService = Depends(get_ontology_service),
):
    return await service.resync_unsynced_datasets(db)
