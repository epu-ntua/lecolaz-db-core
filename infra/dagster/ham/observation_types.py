"""One-time HAMAPI reading-catalog import into LeColaz observation_types."""

import logging

from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from app.storage.postgres.observation_type_store import ObservationTypeStore
from infra.dagster.ham import SENSOR_FAMILY
from app.integrations.ham import collect_reading_keys, prepare_rows  # noqa: F401

LOGGER = logging.getLogger(__name__)


def persist_rows(engine: Engine, rows: list[dict]) -> dict:
    """Upsert and verify in one transaction; failures roll back the entire batch."""
    if not rows:
        raise ValueError("Refusing to load an empty observation-type batch")
    with engine.begin() as connection:
        summary = ObservationTypeStore(sessionmaker(bind=connection)).upsert_source_fields(SENSOR_FAMILY, rows)
    LOGGER.info("HAMAPI observation-type import committed: %s", summary)
    return summary
