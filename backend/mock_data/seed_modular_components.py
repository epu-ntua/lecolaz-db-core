"""Seed mock modular components: uploads their files to MinIO and upserts the rows.

Safe to re-run: ids are fixed, files are overwritten and rows updated in place.

From the repository root:
    docker compose --env-file infra/.env -f infra/compose.yaml exec backend python -m mock_data.seed_modular_components
"""

import json
import logging
import uuid
from pathlib import Path

from app.storage.object.minio import MinioStore
from app.storage.postgres.modular_component_store import ModularComponentStore

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).with_name("modular_components")

# Fixed ids keep every environment's mock data identical.
COMPONENTS = [
    {
        "id": uuid.UUID("1af6798a-fd28-48c4-a56d-e88d90da3b02"),
        "name": "Modular partition panel",
        "component_class": "InteriorWall",
        "folder": "interior_wall",
    },
    {
        "id": uuid.UUID("de1f994c-18b9-43a9-9a74-7fe93847061a"),
        "name": "Facade cladding panel",
        "component_class": "FacadeElement",
        "folder": "facade_element",
    },
    {
        "id": uuid.UUID("9a2bdd8d-b5d4-4ae6-9e42-3f3d07d9622f"),
        "name": "Interlocking floor tile",
        "component_class": "FloorCovering",
        "folder": "floor_covering",
    },
]

# Column -> (file name in the component folder, content type). Missing files are skipped.
FILES = {
    "photo_object_key": ("photo.png", "image/png"),
    "qr_object_key": ("qr.png", "image/png"),
    "ifc_object_key": ("model.ifc", "application/octet-stream"),
}


def seed() -> None:
    minio_store = MinioStore()
    component_store = ModularComponentStore()

    for component in COMPONENTS:
        folder = DATA_DIR / component["folder"]
        record = {
            "id": component["id"],
            "name": component["name"],
            "component_class": component["component_class"],
            "dpp": json.loads((folder / "dpp.json").read_text(encoding="utf-8")),
        }
        for column, (filename, content_type) in FILES.items():
            path = folder / filename
            if not path.exists():
                record[column] = None
                continue
            object_key = f"modular_components/{component['id']}/{filename}"
            minio_store.put_object(object_key, path.read_bytes(), content_type)
            record[column] = object_key

        component_store.upsert(record)
        logger.info("Seeded modular component %s (%s)", record["name"], record["id"])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed()
