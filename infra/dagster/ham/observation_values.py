"""Import HAM time series for each run's data interval."""

import logging
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import Engine

from app.storage.postgres.observation_type_store import ObservationTypeStore
from app.storage.postgres.observation_value_store import ObservationValueStore
from app.storage.postgres.sensor_store import SensorStore
from infra.dagster.ham import SENSOR_FAMILY
from infra.dagster.ham.sensors import SensorUnavailable

LOGGER = logging.getLogger(__name__)


def load_references(engine: Engine, sensor_id: str) -> tuple[dict, dict[str, str]]:
    """Load one HAM sensor and its family's reading-type UUIDs for an import."""
    with engine.connect() as connection:
        sensor = SensorStore(connection).get_by_id_and_sensor_family(
            UUID(sensor_id), SENSOR_FAMILY
        )
        if sensor is None:
            raise SensorUnavailable(
                f"HAM sensor {sensor_id} not found or no longer HAM; reload the code location"
            )
        type_ids = ObservationTypeStore(connection).get_id_map_by_sensor_family(SENSOR_FAMILY)
        types = {key: str(type_id) for key, type_id in type_ids.items()}
    if not types:
        raise ValueError("No HAM observation types found; run their initialization first")
    if not isinstance(sensor["external_id"], str) or not sensor["external_id"].strip():
        raise ValueError(f"Sensor {sensor_id} has no external_id")
    return {**sensor, "id": str(sensor["id"])}, types


def validate_interval(start: datetime, end: datetime) -> None:
    """Require an explicit, positive, timezone-aware data interval."""
    if (
        not isinstance(start, datetime)
        or not isinstance(end, datetime)
        or start.utcoffset() is None
        or end.utcoffset() is None
        or start >= end
    ):
        raise ValueError("A nonempty timezone-aware data interval is required")


@dataclass
class PreparedObservations:
    """Validated rows and diagnostics about the transformed HAM response, before writes."""

    rows: list[dict]
    diagnostics: dict
    reading_summary: list[dict]


def prepare_observation_rows(
    response: dict, sensor: dict, types: dict, start: datetime, end: datetime
) -> PreparedObservations:
    """Zip series with timestamps and resolve both foreign keys; never transform twice."""
    validate_interval(start, end)
    if not isinstance(response, dict) or response.get("error"):
        raise ValueError("Invalid HAMAPI datalog response")
    timestamps = response.get("timestamp")
    if not isinstance(timestamps, list):
        raise ValueError("Datalog response requires a timestamp list")
    for key, values in response.items():
        if not isinstance(values, list) or len(values) != len(timestamps):
            raise ValueError(f"Datalog series {key!r} does not align with timestamps")
    selected_keys = sorted((response.keys() & types.keys()) - {"timestamp"})
    ignored = response.keys() - types.keys() - {"timestamp"}
    if ignored:
        LOGGER.info("Ignoring series without registered observation types: %s", sorted(ignored))
    if timestamps and not selected_keys:
        raise ValueError("No datalog series match registered observation types")

    diagnostics = {
        "returned_timestamp_count": len(timestamps),
        "returned_series_count": len(response) - 1,
        "selected_series_count": len(selected_keys),
        "ignored_series_keys": sorted(ignored),
        "out_of_interval_timestamp_count": 0,
        "null_value_count": 0,
        "identical_duplicate_count": 0,
    }
    type_ids = {key: UUID(types[key]) for key in selected_keys}
    reading_rows = {key: [] for key in selected_keys}
    null_counts = dict.fromkeys(selected_keys, 0)
    rows = {}
    sensor_id = UUID(sensor["id"])
    for index, seconds in enumerate(timestamps):
        if (
            isinstance(seconds, bool)
            or not isinstance(seconds, (int, float))
            or not math.isfinite(seconds)
        ):
            raise ValueError(f"Invalid timestamp at index {index}")
        timestamp = datetime.fromtimestamp(seconds, tz=timezone.utc)
        if not start <= timestamp < end:
            diagnostics["out_of_interval_timestamp_count"] += 1
            continue
        for key in selected_keys:
            value = response[key][index]
            if value is None:
                diagnostics["null_value_count"] += 1
                null_counts[key] += 1
                continue
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise ValueError(f"Invalid numeric value for {key!r} at index {index}")
            identity = (type_ids[key], timestamp)
            row = {
                "sensor_id": sensor_id,
                "observation_type_id": identity[0],
                "timestamp": timestamp,
                "value": float(value),
            }
            if identity in rows:
                if rows[identity]["value"] != row["value"]:
                    raise ValueError(f"Conflicting duplicate value for {key!r} at {timestamp}")
                diagnostics["identical_duplicate_count"] += 1
                continue
            rows[identity] = row
            reading_rows[key].append(row)

    valid_timestamps = {row["timestamp"] for row in rows.values()}
    diagnostics["distinct_timestamp_count"] = len(valid_timestamps)
    if rows:
        diagnostics["first_observation_at"] = min(valid_timestamps)
        diagnostics["last_observation_at"] = max(valid_timestamps)
    elif not timestamps:
        diagnostics["empty_reason"] = "no_timestamps"
    elif diagnostics["out_of_interval_timestamp_count"] == len(timestamps):
        diagnostics["empty_reason"] = "all_timestamps_outside_interval"
    else:
        diagnostics["empty_reason"] = "all_selected_values_null"
    return PreparedObservations(
        rows=list(rows.values()),
        diagnostics=diagnostics,
        reading_summary=[
            _summarize_reading(key, reading_rows[key], null_counts[key]) for key in selected_keys
        ],
    )


def _summarize_reading(key: str, rows: list[dict], null_count: int) -> dict:
    """Summarize validated, deduplicated rows; an empty channel still has a summary."""
    return {
        "reading_key": key,
        "selected_rows": len(rows),
        "null_values": null_count,
        "first_timestamp": min((row["timestamp"] for row in rows), default=None),
        "last_timestamp": max((row["timestamp"] for row in rows), default=None),
        "minimum": min((row["value"] for row in rows), default=None),
        "maximum": max((row["value"] for row in rows), default=None),
    }


def persist_observation_rows(engine: Engine, rows: list[dict]) -> dict:
    """Upsert bounded batches in one sensor transaction; reruns preserve row IDs."""
    if not rows:
        return {"selected": 0, "inserted_or_updated": 0}
    with engine.begin() as connection:
        summary = ObservationValueStore(connection).upsert_rows(rows)
    return summary
