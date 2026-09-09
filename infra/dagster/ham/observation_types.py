"""One-time HAMAPI reading-catalog import into LeColaz observation_types."""

import json
import logging

from urllib.request import urlopen

LOGGER = logging.getLogger(__name__)

BASE_URL = "https://api.hamsystems.eu/res/doc"

SENSOR_FAMILY = "ham"


def fetch_catalog(name: str) -> dict:
    """Fetch only at task execution time; HTTP/JSON failures remain retryable."""
    with urlopen(f"{BASE_URL}/{name}.json", timeout=30) as response:
        catalog = json.load(response)
    if not isinstance(catalog, dict) or not catalog:
        raise ValueError(f"{name}.json must be a nonempty object")
    return catalog


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
        rows.append({
            "key": key,
            "label": label if label and label.strip() else key,
            "unit": unit if unit is not None else "",
            "type_metadata": metadata,
        })

    excluded = sorted(catalog.keys() - set(reading_keys))
    LOGGER.info("Selected %d types; excluded %d catalog keys: %s", len(rows), len(excluded), excluded)
    return rows


def persist_rows(engine, rows: list[dict]) -> dict:
    """Upsert and verify in one transaction; failures roll back the entire batch."""
    from sqlalchemy import or_, select
    from sqlalchemy.dialects.postgresql import insert

    from app.db.models.observation_type import ObservationType

    if not rows:
        raise ValueError("Refusing to load an empty observation-type batch")
    keys = [row["key"] for row in rows]
    statement = insert(ObservationType).values([
        {**row, "sensor_family": SENSOR_FAMILY} for row in rows
    ])
    updated_fields = ("label", "unit", "type_metadata")
    statement = statement.on_conflict_do_update(
        index_elements=[ObservationType.sensor_family, ObservationType.key],
        set_={name: statement.excluded[name] for name in updated_fields},
        where=or_(*(
            getattr(ObservationType, name).is_distinct_from(statement.excluded[name])
            for name in updated_fields
        )),
    ).returning(ObservationType.key)
    with engine.begin() as connection:
        changed = len(connection.execute(statement).scalars().all())
        stored_keys = set(connection.execute(
            select(ObservationType.key).where(
                ObservationType.sensor_family == SENSOR_FAMILY,
                ObservationType.key.in_(keys),
            )
        ).scalars())
        if stored_keys != set(keys):
            raise ValueError("Observation-type verification failed; rolling back")
    summary = {"selected": len(keys), "inserted_or_updated": changed, "verified": len(stored_keys)}
    LOGGER.info("HAMAPI observation-type import committed: %s", summary)
    return summary
