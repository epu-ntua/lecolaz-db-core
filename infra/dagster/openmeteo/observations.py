"""Parse Enhydris CSV without coupling parsing to HTTP or object storage."""

import csv
import io
import math
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import sessionmaker

from app.storage.postgres.observation_value_store import ObservationValueStore


def prepare_rows(
    data: bytes, sensor_id: str, type_id: UUID, start: datetime, end: datetime
) -> tuple[list[dict], dict[str, int]]:
    if start.utcoffset() is None or end.utcoffset() is None or start >= end:
        raise ValueError("A nonempty timezone-aware interval is required")
    rows = {}
    counts = {
        "returned_rows": 0,
        "missing_values": 0,
        "outside_interval": 0,
        "identical_duplicates": 0,
        "flagged_rows": 0,
    }
    for line, fields in enumerate(
        csv.reader(io.StringIO(data.decode("utf-8-sig")), strict=True), 1
    ):
        if not fields:
            continue
        counts["returned_rows"] += 1
        if len(fields) != 3:
            raise ValueError(f"Expected timestamp,value,flags at CSV line {line}")
        timestamp = datetime.fromisoformat(fields[0].strip())
        if timestamp.utcoffset() is None:
            # The HTTP request explicitly asks for timezone=UTC.
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        timestamp = timestamp.astimezone(timezone.utc)
        if not start <= timestamp < end:
            counts["outside_interval"] += 1
            continue
        if fields[2].strip():
            # Keep flags in the raw CSV; the database has no quality column.
            counts["flagged_rows"] += 1
        if not fields[1].strip():
            counts["missing_values"] += 1
            continue  # observation_values.value is NOT NULL.
        value = float(fields[1])
        if not math.isfinite(value):
            raise ValueError(f"Nonfinite observation at CSV line {line}")
        if timestamp in rows:
            if rows[timestamp]["value"] != value:
                raise ValueError(f"Conflicting duplicate at {timestamp}")
            counts["identical_duplicates"] += 1
            continue
        rows[timestamp] = {
            "sensor_id": UUID(sensor_id),
            "observation_type_id": type_id,
            "timestamp": timestamp,
            "value": value,
        }
    return list(rows.values()), counts


def persist_rows(engine, rows: list[dict]) -> dict:
    with engine.begin() as connection:
        return ObservationValueStore(sessionmaker(bind=connection)).upsert_rows(rows)
