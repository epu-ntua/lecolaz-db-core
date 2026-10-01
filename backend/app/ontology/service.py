# app/ontology/service.py
"""
OntologyService orchestrates the Postgres -> RDF -> Fuseki sync flow for BIM
and simulation datasets:

    1. Read the newly persisted entities (bim_datasets/bim_storeys/bim_spaces,
       or simulation_datasets/simulation_variables).
    2. Build an rdflib Graph from them (RdfModelBuilder).
    3. Serialize to Turtle and validate it parses (TurtleSerializer).
    4. PUT it to Fuseki as the dataset's named graph (FusekiClient).
    5. Record success/failure on datasets.kg_synced* in its own transaction.

RDF build/serialization and Fuseki failures are recorded on the dataset row
and returned as a failed SyncResult; DB errors and a missing dataset
(BimDatasetNotFoundError / SimulationDatasetNotFoundError) raise.

It also reloads the ontology schema from its file in the repo into Fuseki's
schema graph (reload_schema); failures there raise.
"""

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from rdflib import Graph

from app.core.config import settings
from app.ontology.config import build_graph_uri, build_schema_graph_uri, build_simulation_graph_uri
from app.ontology.dto import (
    BimDatasetDTO,
    SimulationDatasetDTO,
    SimulationVariableDTO,
    SpaceDTO,
    StoreyDTO,
    SyncResult,
)
from app.ontology.exceptions import (
    BimDatasetNotFoundError,
    OntologyServiceError,
    OntologyValidationError,
    SchemaFileError,
    SimulationDatasetNotFoundError,
)
from app.ontology.fuseki_client import FusekiClient
from app.ontology.rdf_model_builder import RdfModelBuilder
from app.ontology.turtle_serializer import TurtleSerializer
from app.storage.postgres.bim_space_store import BimSpaceStore
from app.storage.postgres.bim_store import BimStore
from app.storage.postgres.bim_storey_store import BimStoreyStore
from app.storage.postgres.dataset_store import DatasetStore
from app.storage.postgres.simulation_store import SimulationStore
from app.storage.postgres.simulation_variable_store import SimulationVariableStore

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
        simulation_store: SimulationStore | None = None,
        simulation_variable_store: SimulationVariableStore | None = None,
        schema_path: str | None = None,
    ) -> None:
        self._rdf_model_builder = rdf_model_builder or RdfModelBuilder()
        self._turtle_serializer = turtle_serializer or TurtleSerializer()
        self._fuseki_client = fuseki_client or FusekiClient()
        self._bim_store = bim_store or BimStore()
        self._bim_storey_store = bim_storey_store or BimStoreyStore()
        self._bim_space_store = bim_space_store or BimSpaceStore()
        self._dataset_store = dataset_store or DatasetStore()
        self._simulation_store = simulation_store or SimulationStore()
        self._simulation_variable_store = simulation_variable_store or SimulationVariableStore()
        self._schema_path = Path(schema_path or settings.LECO_SCHEMA_PATH)

    def sync_bim_dataset(self, *, bim_dataset_id: uuid.UUID) -> SyncResult:
        bim_data = self._load_bim_dataset(bim_dataset_id)
        return self._sync(
            source_id=bim_data.bim_dataset_id,
            dataset_id=bim_data.dataset_id,
            graph_uri=build_graph_uri(bim_data.bim_dataset_id),
            build_graph=lambda: self._rdf_model_builder.build(bim_data),
        )

    def sync_simulation_dataset(self, *, simulation_dataset_id: uuid.UUID) -> SyncResult:
        simulation_data = self._load_simulation_dataset(simulation_dataset_id)
        return self._sync(
            source_id=simulation_data.simulation_dataset_id,
            dataset_id=simulation_data.dataset_id,
            graph_uri=build_simulation_graph_uri(simulation_data.simulation_dataset_id),
            build_graph=lambda: self._rdf_model_builder.build_simulation(simulation_data),
        )

    def resync_unsynced_datasets(self) -> dict:
        jobs = [
            (row, self.sync_bim_dataset, "bim_dataset_id")
            for row in self._bim_store.list_processed_kg_unsynced()
        ] + [
            (row, self.sync_simulation_dataset, "simulation_dataset_id")
            for row in self._simulation_store.list_processed_kg_unsynced()
        ]

        total = len(jobs)
        succeeded = 0
        failed = 0
        errors: list[dict] = []

        for row, sync, id_kwarg in jobs:
            try:
                result = sync(**{id_kwarg: uuid.UUID(row["id"])})
            except Exception as exc:
                logger.exception("Ontology resync failed to run for %s=%s", id_kwarg, row["id"])
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

    def reload_schema(self) -> dict:
        """Loads the schema file into the schema graph, replacing its triples."""
        graph_uri = build_schema_graph_uri()

        try:
            turtle = self._read_schema_file()
            triple_count = self._count_schema_triples(turtle)
            self._fuseki_client.put_graph(graph_uri=graph_uri, turtle=turtle)
        except OntologyServiceError as exc:
            logger.error(
                "Ontology schema reload failed for graph=%s file=%s: %s",
                graph_uri,
                self._schema_path,
                exc,
            )
            raise

        logger.info(
            "Ontology schema reloaded into graph=%s file=%s triples=%d",
            graph_uri,
            self._schema_path,
            triple_count,
        )
        return {"graph_uri": graph_uri, "triple_count": triple_count}

    def _read_schema_file(self) -> str:
        if not self._schema_path.is_file():
            raise SchemaFileError(f"Schema file not found: {self._schema_path}")
        # utf-8-sig drops a BOM that Windows editors may add; rdflib rejects it.
        turtle = self._schema_path.read_text(encoding="utf-8-sig")
        # An empty file is valid Turtle: PUT would silently wipe the schema graph.
        if not turtle.strip():
            raise SchemaFileError(f"Schema file is empty: {self._schema_path}")
        return turtle

    @staticmethod
    def _count_schema_triples(turtle: str) -> int:
        try:
            return len(Graph().parse(data=turtle, format="turtle"))
        except Exception as exc:
            raise OntologyValidationError(f"Schema file failed to parse: {exc}") from exc

    def _sync(
        self,
        *,
        source_id: uuid.UUID,
        dataset_id: uuid.UUID,
        graph_uri: str,
        build_graph: Callable[[], Graph],
    ) -> SyncResult:
        try:
            graph = build_graph()
            turtle = self._turtle_serializer.serialize(graph)
            self._fuseki_client.put_graph(graph_uri=graph_uri, turtle=turtle)
        except Exception as exc:
            error_message = str(exc)
            logger.error(
                "Ontology sync failed for source_id=%s dataset_id=%s graph=%s: %s",
                source_id,
                dataset_id,
                graph_uri,
                error_message,
            )
            self._mark_sync_failed(dataset_id, error_message)
            return SyncResult(
                source_id=source_id,
                dataset_id=dataset_id,
                graph_uri=graph_uri,
                success=False,
                triple_count=0,
                synced_at=None,
                error=error_message,
            )

        synced_at = datetime.now(timezone.utc)
        self._mark_sync_succeeded(dataset_id, synced_at)
        logger.info(
            "Ontology sync succeeded for source_id=%s dataset_id=%s graph=%s triples=%d",
            source_id,
            dataset_id,
            graph_uri,
            len(graph),
        )
        return SyncResult(
            source_id=source_id,
            dataset_id=dataset_id,
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

    def _load_simulation_dataset(self, simulation_dataset_id: uuid.UUID) -> SimulationDatasetDTO:
        simulation = self._simulation_store.get_simulation_by_id(simulation_dataset_id)
        if simulation is None:
            raise SimulationDatasetNotFoundError(
                f"Simulation dataset {simulation_dataset_id} not found"
            )

        dataset_id = uuid.UUID(simulation["dataset_id"])
        dataset = self._dataset_store.get_dataset_by_id(dataset_id)
        if dataset is None:
            raise SimulationDatasetNotFoundError(
                f"Dataset {dataset_id} for simulation dataset {simulation_dataset_id} not found"
            )

        variables = self._simulation_variable_store.list_by_simulation_dataset_id(simulation_dataset_id)

        # simulation_variables.bim_space_id -> IFC GlobalId, so observations point
        # at the same space URIs the BIM graph mints.
        space_global_id_by_id: dict[str, str] = {}
        if simulation["bim_dataset_id"]:
            spaces = self._bim_space_store.list_by_bim_dataset_id(uuid.UUID(simulation["bim_dataset_id"]))
            space_global_id_by_id = {sp["id"]: sp["global_id"] for sp in spaces}

        return SimulationDatasetDTO(
            simulation_dataset_id=simulation_dataset_id,
            dataset_id=dataset_id,
            filename=dataset["filename"],
            format=simulation["format"],
            status=dataset["status"],
            created_at=datetime.fromisoformat(dataset["created_at"]) if dataset["created_at"] else None,
            size_bytes=dataset["size_bytes"],
            variables=[
                SimulationVariableDTO(
                    id=uuid.UUID(v["id"]),
                    variable_id=v["variable_id"],
                    variable_name=v["variable_name"],
                    unit=v["unit"],
                    frequency=v["frequency"],
                    key=v["key"],
                    space_global_id=space_global_id_by_id.get(v["bim_space_id"]),
                )
                for v in variables
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
