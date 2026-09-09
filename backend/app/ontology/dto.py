# app/ontology/dto.py
"""
Data transfer objects for the ontology sync pipeline.

These decouple RdfModelBuilder / TurtleSerializer / FusekiClient from the
SQLAlchemy ORM models - the builder only ever sees plain dataclasses.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class StoreyDTO:
    id: uuid.UUID
    global_id: str
    name: str | None
    elevation: float | None


@dataclass(frozen=True)
class SpaceDTO:
    id: uuid.UUID
    global_id: str
    name: str | None
    area: float | None
    volume: float | None
    storey_id: uuid.UUID | None


@dataclass(frozen=True)
class BimDatasetDTO:
    bim_dataset_id: uuid.UUID
    dataset_id: uuid.UUID
    filename: str
    format: str
    status: str | None
    created_at: datetime | None
    size_bytes: int | None
    storeys: list[StoreyDTO] = field(default_factory=list)
    spaces: list[SpaceDTO] = field(default_factory=list)


@dataclass(frozen=True)
class SyncResult:
    bim_dataset_id: uuid.UUID
    dataset_id: uuid.UUID
    graph_uri: str
    success: bool
    triple_count: int
    synced_at: datetime | None
    error: str | None
