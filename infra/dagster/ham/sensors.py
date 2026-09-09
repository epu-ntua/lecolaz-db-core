"""Synchronize the HAM devices accessible to the configured API key."""

import logging

LOGGER = logging.getLogger(__name__)

SENSOR_FAMILY = "ham"


def fetch_devices(api_key: str) -> dict:
    """Fetch devices for the supplied key without a shared on-disk cache."""
    import hamapi

    client = hamapi.hamapi(api_key=api_key, cache_db_file=":memory:")
    try:
        return client.get_user_devices(force_refresh=True)
    finally:
        client.cache_conn.close()


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
        rows.append({
            "sensor_family": SENSOR_FAMILY,
            "name": name,
            "external_id": serialno,
            "sensor_metadata": metadata,
        })
    LOGGER.info("Validated %d HAM sensors", len(rows))
    return rows


def persist_sensor_rows(engine, rows: list[dict]) -> dict:
    """Atomically upsert source-owned fields, preserving locally managed fields."""
    from sqlalchemy import or_, select
    from sqlalchemy.dialects.postgresql import insert

    from app.db.models.sensor import Sensor

    if not rows:
        return {"selected": 0, "inserted_or_updated": 0, "verified": 0}

    statement = insert(Sensor).values(rows)
    statement = statement.on_conflict_do_update(
        index_elements=[Sensor.sensor_family, Sensor.external_id],
        set_={
            "name": statement.excluded.name,
            "sensor_metadata": statement.excluded.sensor_metadata,
        },
        where=or_(
            Sensor.name.is_distinct_from(statement.excluded.name),
            Sensor.sensor_metadata.is_distinct_from(statement.excluded.sensor_metadata),
        ),
    ).returning(Sensor.external_id)
    serials = {row["external_id"] for row in rows}
    with engine.begin() as connection:
        changed = len(connection.execute(statement).scalars().all())
        stored = set(connection.execute(select(Sensor.external_id).where(
            Sensor.sensor_family == SENSOR_FAMILY,
            Sensor.external_id.in_(serials),
        )).scalars())
        if stored != serials:
            raise ValueError("Sensor verification failed; rolling back")
    summary = {"selected": len(rows), "inserted_or_updated": changed, "verified": len(stored)}
    LOGGER.info("HAM sensor import committed: %s", summary)
    return summary


class SensorUnavailable(ValueError):
    """A requested physical sensor was deleted or moved out of the HAM family."""


def utc_starting_date(value):
    from datetime import datetime, timezone

    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError("Physical sensor starting_date must be a timezone-aware timestamp")
    return value.astimezone(timezone.utc)


def load_sensor_catalog(engine) -> list[dict]:
    """Read definition inputs directly from PostgreSQL in stable UUID order."""
    from sqlalchemy import select
    from app.db.models.sensor import Sensor

    with engine.connect() as connection:
        rows = [dict(row) for row in connection.execute(
            select(Sensor.id, Sensor.name, Sensor.starting_date)
            .where(Sensor.sensor_family == SENSOR_FAMILY).order_by(Sensor.id)
        ).mappings()]
    for row in rows:
        row["id"] = str(row["id"])
        row["starting_date"] = utc_starting_date(row["starting_date"])
    return rows
