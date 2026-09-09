# app/ontology/service.py
"""
OntologyService orchestrates the BIM -> RDF -> Fuseki sync flow:

    1. Read the newly persisted BIM entities (bim_datasets/bim_storeys/bim_spaces).
    2. Build an rdflib Graph from them (RdfModelBuilder).
    3. Serialize to Turtle and validate it parses (TurtleSerializer).
    4. PUT it to Fuseki as the dataset's named graph (FusekiClient).
    5. Record success/failure on datasets.kg_synced* in its own transaction,
       separate from whatever transaction persisted the BIM data.

A Fuseki failure never raises past this service in a way that could roll
back the caller's transaction - it is recorded on the dataset row and
returned as a failed SyncResult.
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.async_session import AsyncSessionLocal
from app.db.models.bim_dataset import BimDataset
from app.db.models.bim_space import BimSpace
from app.db.models.bim_storey import BimStorey
from app.db.models.dataset import Dataset
from app.ontology.config import build_graph_uri
from app.ontology.dto import BimDatasetDTO, SpaceDTO, StoreyDTO, SyncResult
from app.ontology.exceptions import BimDatasetNotFoundError
from app.ontology.fuseki_client import FusekiClient
from app.ontology.rdf_model_builder import RdfModelBuilder
from app.ontology.turtle_serializer import TurtleSerializer

logger = logging.getLogger("uvicorn.error")


class OntologyService:
    def __init__(
        self,
        *,
        rdf_model_builder: RdfModelBuilder | None = None,
        turtle_serializer: TurtleSerializer | None = None,
        fuseki_client: FusekiClient | None = None,
        session_factory: async_sessionmaker[AsyncSession] = AsyncSessionLocal,
    ) -> None:
        self._rdf_model_builder = rdf_model_builder or RdfModelBuilder()
        self._turtle_serializer = turtle_serializer or TurtleSerializer()
        self._fuseki_client = fuseki_client or FusekiClient()
        self._session_factory = session_factory

    async def sync_bim_dataset(
        self,
        *,
        bim_dataset_id: uuid.UUID,
        db: AsyncSession | None = None,
    ) -> SyncResult:
        if db is not None:
            bim_data = await self._load_bim_dataset(db, bim_dataset_id)
        else:
            async with self._session_factory() as session:
                bim_data = await self._load_bim_dataset(session, bim_dataset_id)

        return await self._sync(bim_data)

    async def resync_unsynced_datasets(self, db: AsyncSession) -> dict:
        stmt = (
            select(Dataset.id, BimDataset.id)
            .join(BimDataset, BimDataset.dataset_id == Dataset.id)
            .where(Dataset.kg_synced.is_(False))
        )
        rows = (await db.execute(stmt)).all()

        total = len(rows)
        succeeded = 0
        failed = 0
        errors: list[dict] = []

        for dataset_id, bim_dataset_id in rows:
            result = await self.sync_bim_dataset(bim_dataset_id=bim_dataset_id)
            if result.success:
                succeeded += 1
            else:
                failed += 1
                errors.append({"dataset_id": str(dataset_id), "error": result.error})

        return {
            "total": total,
            "succeeded": succeeded,
            "failed": failed,
            "errors": errors,
        }

    async def _sync(self, bim_data: BimDatasetDTO) -> SyncResult:
        graph_uri = build_graph_uri(bim_data.bim_dataset_id)

        try:
            graph = self._rdf_model_builder.build(bim_data)
            turtle = self._turtle_serializer.serialize(graph)
            await self._fuseki_client.put_graph(graph_uri=graph_uri, turtle=turtle)
        except Exception as exc:
            error_message = str(exc)
            logger.error(
                "Ontology sync failed for bim_dataset_id=%s dataset_id=%s graph=%s: %s",
                bim_data.bim_dataset_id,
                bim_data.dataset_id,
                graph_uri,
                error_message,
            )
            await self._mark_sync_failed(bim_data.dataset_id, error_message)
            return SyncResult(
                bim_dataset_id=bim_data.bim_dataset_id,
                dataset_id=bim_data.dataset_id,
                graph_uri=graph_uri,
                success=False,
                triple_count=0,
                synced_at=None,
                error=error_message,
            )

        synced_at = datetime.now(timezone.utc)
        await self._mark_sync_succeeded(bim_data.dataset_id, synced_at)
        logger.info(
            "Ontology sync succeeded for bim_dataset_id=%s dataset_id=%s graph=%s triples=%d",
            bim_data.bim_dataset_id,
            bim_data.dataset_id,
            graph_uri,
            len(graph),
        )
        return SyncResult(
            bim_dataset_id=bim_data.bim_dataset_id,
            dataset_id=bim_data.dataset_id,
            graph_uri=graph_uri,
            success=True,
            triple_count=len(graph),
            synced_at=synced_at,
            error=None,
        )

    async def _load_bim_dataset(self, session: AsyncSession, bim_dataset_id: uuid.UUID) -> BimDatasetDTO:
        stmt = (
            select(BimDataset, Dataset)
            .join(Dataset, Dataset.id == BimDataset.dataset_id)
            .where(BimDataset.id == bim_dataset_id)
        )
        row = (await session.execute(stmt)).first()
        if row is None:
            raise BimDatasetNotFoundError(f"BIM dataset {bim_dataset_id} not found")
        bim_dataset, dataset = row

        storeys_stmt = select(BimStorey).where(BimStorey.bim_dataset_id == bim_dataset.id)
        storeys = (await session.execute(storeys_stmt)).scalars().all()

        spaces_stmt = select(BimSpace).where(BimSpace.bim_dataset_id == bim_dataset.id)
        spaces = (await session.execute(spaces_stmt)).scalars().all()

        return BimDatasetDTO(
            bim_dataset_id=bim_dataset.id,
            dataset_id=dataset.id,
            filename=dataset.filename,
            format=bim_dataset.format,
            status=dataset.status,
            created_at=dataset.created_at,
            size_bytes=dataset.size_bytes,
            storeys=[
                StoreyDTO(
                    id=s.id,
                    global_id=s.global_id,
                    name=s.name,
                    elevation=s.elevation,
                )
                for s in storeys
            ],
            spaces=[
                SpaceDTO(
                    id=sp.id,
                    global_id=sp.global_id,
                    name=sp.name,
                    area=sp.area,
                    volume=sp.volume,
                    storey_id=sp.storey_id,
                )
                for sp in spaces
            ],
        )

    async def _mark_sync_succeeded(self, dataset_id: uuid.UUID, synced_at: datetime) -> None:
        async with self._session_factory() as session:
            await session.execute(
                update(Dataset)
                .where(Dataset.id == dataset_id)
                .values(kg_synced=True, kg_synced_at=synced_at, kg_error=None)
            )
            await session.commit()

    async def _mark_sync_failed(self, dataset_id: uuid.UUID, error_message: str) -> None:
        async with self._session_factory() as session:
            await session.execute(
                update(Dataset)
                .where(Dataset.id == dataset_id)
                .values(kg_synced=False, kg_synced_at=None, kg_error=error_message)
            )
            await session.commit()


# Default singleton for simple call sites (background tasks, other services).
# FastAPI endpoints should prefer `get_ontology_service` via Depends for testability.
ontology_service = OntologyService()


def get_ontology_service() -> OntologyService:
    return ontology_service


async def resync_unsynced_datasets(db: AsyncSession) -> dict:
    """Module-level convenience wrapper around OntologyService.resync_unsynced_datasets."""
    return await ontology_service.resync_unsynced_datasets(db)
