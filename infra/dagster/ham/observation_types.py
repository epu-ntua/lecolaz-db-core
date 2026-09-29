"""One-time HAMAPI reading-catalog import into LeColaz observation_types."""

import logging

from sqlalchemy import Engine

from app.storage.postgres.observation_type_store import ObservationTypeStore
from infra.dagster.ham import SENSOR_FAMILY

LOGGER = logging.getLogger(__name__)


def collect_reading_keys(models: dict, include_extra_readings: bool = False) -> list[str]:
    """Collect readings across all models, optionally including extra readings."""
    if not isinstance(models, dict) or not models:
        raise ValueError("Models must be a nonempty object")
    keys = set()
    for model_id, model in models.items():
        if not isinstance(model, dict):
            raise ValueError(f"Model {model_id!r} must be an object")
        readings = model.get("readings", [])
        extra_readings = model.get("extra_readings", []) if include_extra_readings else []
        if not isinstance(readings, list) or not isinstance(extra_readings, list):
            raise ValueError(f"Model {model_id!r} reading collections must be lists")
        for key in readings:
            if not isinstance(key, str) or not key.strip():
                raise ValueError(f"Model {model_id!r} has an invalid reading key")
            keys.add(key)
        for entry in extra_readings:
            if not isinstance(entry, dict):
                raise ValueError(f"Model {model_id!r} has an invalid extra reading")
            key = entry.get("key")
            if not isinstance(key, str) or not key.strip():
                raise ValueError(f"Model {model_id!r} has an invalid extra reading key")
            keys.add(key)
    if not keys:
        raise ValueError("No reading keys were found in the models")
    return sorted(keys)


def prepare_rows(catalog: dict, reading_keys: list[str]) -> list[dict]:
    """Validate the complete selection before allowing any database writes."""
    if not isinstance(catalog, dict) or not catalog or not reading_keys:
        raise ValueError("Reading catalog and selected keys must be nonempty")
    missing = set(reading_keys) - catalog.keys()
    if missing:
        raise ValueError(f"Model reading keys missing from catalog: {sorted(missing)}")

    rows = []
    for key in sorted(set(reading_keys)):
        metadata = catalog[key]
        if not isinstance(metadata, dict):
            raise ValueError(f"Metadata for {key!r} must be an object")
        label = metadata.get("label")
        unit = metadata.get("unit")
        if label is not None and not isinstance(label, str):
            raise ValueError(f"Label for {key!r} must be a string or null")
        if unit is not None and not isinstance(unit, str):
            raise ValueError(f"Unit for {key!r} must be a string or null")
        rows.append(
            {
                "key": key,
                "label": label if label and label.strip() else key,
                "unit": unit if unit is not None else "",
                "type_metadata": metadata,
            }
        )

    excluded = sorted(catalog.keys() - set(reading_keys))
    LOGGER.info(
        "Selected %d types; excluded %d catalog keys: %s", len(rows), len(excluded), excluded
    )
    return rows


def persist_rows(engine: Engine, rows: list[dict]) -> dict:
    """Upsert and verify in one transaction; failures roll back the entire batch."""
    if not rows:
        raise ValueError("Refusing to load an empty observation-type batch")
    with engine.begin() as connection:
        summary = ObservationTypeStore(connection).upsert_source_fields(SENSOR_FAMILY, rows)
    LOGGER.info("HAMAPI observation-type import committed: %s", summary)
    return summary
