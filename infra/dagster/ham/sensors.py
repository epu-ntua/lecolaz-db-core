"""Synchronize the HAM devices accessible to the configured API key."""

import logging
from datetime import datetime, timezone

from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from app.storage.postgres.sensor_store import SensorStore
from infra.dagster.ham import SENSOR_FAMILY
from app.integrations.ham import prepare_sensor_rows  # noqa: F401

LOGGER = logging.getLogger(__name__)


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
