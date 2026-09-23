# app/ontology/service.py
"""
OntologyService orchestrates the BIM -> RDF -> Fuseki sync flow:

    1. Read the newly persisted BIM entities (bim_datasets/bim_storeys/bim_spaces).
    2. Build an rdflib Graph from them (RdfModelBuilder).
    3. Serialize to Turtle and validate it parses (TurtleSerializer).
    4. PUT it to Fuseki as the dataset's named graph (FusekiClient).
    5. Record success/failure on datasets.kg_synced* in its own transaction.

RDF build/serialization and Fuseki failures are recorded on the dataset row
and returned as a failed SyncResult; DB errors and a missing BIM dataset
(BimDatasetNotFoundError) raise.
"""

import logging
import uuid
from datetime import datetime, timezone

from app.ontology.config import build_graph_uri
from app.ontology.dto import BimDatasetDTO, SpaceDTO, StoreyDTO, SyncResult
from app.ontology.exceptions import BimDatasetNotFoundError
from app.ontology.fuseki_client import FusekiClient
from app.ontology.rdf_model_builder import RdfModelBuilder
from app.ontology.turtle_serializer import TurtleSerializer
from app.storage.postgres.bim_space_store import BimSpaceStore
from app.storage.postgres.bim_store import BimStore
from app.storage.postgres.bim_storey_store import BimStoreyStore
from app.storage.postgres.dataset_store import DatasetStore

logger = logging.getLogger("uvicorn.error")


class OntologyService:
    def __init__(
        self,
        *,
        rdf_model_builder: RdfModelBuilder | None = None,
        turtle_serializer: TurtleSerializer | None = None,
        fuseki_client: FusekiClient | None = None,
        bim_store: BimStore | None = None,
        bim_storey_store: BimStoreyStore | None = None,
        bim_space_store: BimSpaceStore | None = None,
        dataset_store: DatasetStore | None = None,
    ) -> None:
        self._rdf_model_builder = rdf_model_builder or RdfModelBuilder()
        self._turtle_serializer = turtle_serializer or TurtleSerializer()
        self._fuseki_client = fuseki_client or FusekiClient()
        self._bim_store = bim_store or BimStore()
        self._bim_storey_store = bim_storey_store or BimStoreyStore()
        self._bim_space_store = bim_space_store or BimSpaceStore()
        self._dataset_store = dataset_store or DatasetStore()

    def sync_bim_dataset(self, *, bim_dataset_id: uuid.UUID) -> SyncResult:
        bim_data = self._load_bim_dataset(bim_dataset_id)
        return self._sync(bim_data)

    def resync_unsynced_datasets(self) -> dict:
        rows = self._bim_store.list_processed_kg_unsynced()

        total = len(rows)
        succeeded = 0
        failed = 0
        errors: list[dict] = []

        for row in rows:
            try:
                result = self.sync_bim_dataset(bim_dataset_id=uuid.UUID(row["id"]))
            except Exception as exc:
                logger.exception("Ontology resync failed to run for bim_dataset_id=%s", row["id"])
                failed += 1
                errors.append({"dataset_id": row["dataset_id"], "error": str(exc)})
                continue

            if result.success:
                succeeded += 1
            else:
                failed += 1
                errors.append({"dataset_id": row["dataset_id"], "error": result.error})

        return {
            "total": total,
            "succeeded": succeeded,
            "failed": failed,
            "errors": errors,
        }

    def _sync(self, bim_data: BimDatasetDTO) -> SyncResult:
        graph_uri = build_graph_uri(bim_data.bim_dataset_id)

        try:
            graph = self._rdf_model_builder.build(bim_data)
            turtle = self._turtle_serializer.serialize(graph)
            self._fuseki_client.put_graph(graph_uri=graph_uri, turtle=turtle)
        except Exception as exc:
            error_message = str(exc)
            logger.error(
                "Ontology sync failed for bim_dataset_id=%s dataset_id=%s graph=%s: %s",
                bim_data.bim_dataset_id,
                bim_data.dataset_id,
                graph_uri,
                error_message,
            )
            self._mark_sync_failed(bim_data.dataset_id, error_message)
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
        self._mark_sync_succeeded(bim_data.dataset_id, synced_at)
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

    def _load_bim_dataset(self, bim_dataset_id: uuid.UUID) -> BimDatasetDTO:
        bim_dataset = self._bim_store.get_bim_by_id(bim_dataset_id)
        if bim_dataset is None:
            raise BimDatasetNotFoundError(f"BIM dataset {bim_dataset_id} not found")

        dataset_id = uuid.UUID(bim_dataset["dataset_id"])
        dataset = self._dataset_store.get_dataset_by_id(dataset_id)
        if dataset is None:
            raise BimDatasetNotFoundError(f"Dataset {dataset_id} for BIM dataset {bim_dataset_id} not found")

        storeys = self._bim_storey_store.list_by_bim_dataset_id(bim_dataset_id)
        spaces = self._bim_space_store.list_by_bim_dataset_id(bim_dataset_id)

        return BimDatasetDTO(
            bim_dataset_id=bim_dataset_id,
            dataset_id=dataset_id,
            filename=dataset["filename"],
            format=bim_dataset["format"],
            status=dataset["status"],
            created_at=datetime.fromisoformat(dataset["created_at"]) if dataset["created_at"] else None,
            size_bytes=dataset["size_bytes"],
            storeys=[
                StoreyDTO(
                    id=uuid.UUID(s["id"]),
                    global_id=s["global_id"],
                    name=s["name"],
                    elevation=s["elevation"],
                )
                for s in storeys
            ],
            spaces=[
                SpaceDTO(
                    id=uuid.UUID(sp["id"]),
                    global_id=sp["global_id"],
                    name=sp["name"],
                    area=sp["area"],
                    volume=sp["volume"],
                    storey_id=uuid.UUID(sp["storey_id"]) if sp["storey_id"] else None,
                )
                for sp in spaces
            ],
        )

    def _mark_sync_succeeded(self, dataset_id: uuid.UUID, synced_at: datetime) -> None:
        self._dataset_store.mark_kg_synced(dataset_id, synced_at)

    def _mark_sync_failed(self, dataset_id: uuid.UUID, error_message: str) -> None:
        self._dataset_store.mark_kg_sync_failed(dataset_id, error_message)


# Default singleton for simple call sites (background tasks, other services).
# FastAPI endpoints should prefer `get_ontology_service` via Depends for testability.
ontology_service = OntologyService()


def get_ontology_service() -> OntologyService:
    return ontology_service
