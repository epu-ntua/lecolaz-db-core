"""Synchronize the HAM devices accessible to the configured API key."""

import logging
from datetime import datetime, timezone

from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from app.storage.postgres.sensor_store import SensorStore
from infra.dagster.ham import SENSOR_FAMILY

LOGGER = logging.getLogger(__name__)


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


def persist_sensor_rows(engine: Engine, rows: list[dict]) -> dict:
    """Atomically upsert source-owned fields, preserving locally managed fields."""
    if not rows:
        return {"selected": 0, "inserted_or_updated": 0, "verified": 0}

    with engine.begin() as connection:
        summary = SensorStore(sessionmaker(bind=connection)).upsert_source_fields(SENSOR_FAMILY, rows)
    LOGGER.info("HAM sensor import committed: %s", summary)
    return summary


class SensorUnavailable(ValueError):
    """A requested physical sensor was deleted or moved out of the HAM family."""


def utc_starting_date(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError("Physical sensor starting_date must be a timezone-aware timestamp")
    return value.astimezone(timezone.utc)


def load_sensor_catalog(engine: Engine) -> list[dict]:
    """Read the stored HAM catalog and validate definition inputs."""
    with engine.connect() as connection:
        rows = SensorStore(sessionmaker(bind=connection)).list_by_sensor_family(SENSOR_FAMILY)
    for row in rows:
        row["id"] = str(row["id"])
        row["starting_date"] = utc_starting_date(row["starting_date"])
    return rows
