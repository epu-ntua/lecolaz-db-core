"""HAM catalog validation shared by HTTP registration and Dagster."""

import logging
import json
from importlib.resources import files

SENSOR_FAMILY = "ham"
LOGGER = logging.getLogger(__name__)


def load_catalog(name: str) -> dict:
    if name not in ("readings", "models"):
        raise ValueError(f"Unknown HAM catalog: {name}")
    catalog = json.loads(
        files("hamapi").joinpath(f"{name}.json").read_text(encoding="utf-8")
    )
    if not isinstance(catalog, dict) or not catalog:
        raise ValueError(f"{name}.json must be a nonempty object")
    return catalog


def prepare_sensor_rows(response: dict) -> list[dict]:
    """Map device identities to columns and preserve all remaining device data."""
    if not isinstance(response, dict) or response.get("error"):
        raise ValueError("HAMAPI returned an invalid or error response")
    devices = response.get("devices")
    if not isinstance(devices, list):
        raise ValueError("HAMAPI response must contain a devices list")

    rows = []
    seen_serials = set()
    for index, device in enumerate(devices):
        if not isinstance(device, dict):
            raise ValueError(f"Device at index {index} must be an object")
        metadata = device.copy()
        name = metadata.pop("name", None)
        serialno = metadata.pop("serialno", None)
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Device at index {index} requires a nonempty name")
        if not isinstance(serialno, str) or not serialno.strip():
            raise ValueError(f"Device at index {index} requires a nonempty serialno")
        if serialno in seen_serials:
            raise ValueError(f"Duplicate serialno at device index {index}")
        seen_serials.add(serialno)
        rows.append(
            {
                "sensor_family": SENSOR_FAMILY,
                "name": name,
                "external_id": serialno,
                "sensor_metadata": metadata,
            }
        )
    LOGGER.info("Validated %d HAM sensors", len(rows))
    return rows


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


