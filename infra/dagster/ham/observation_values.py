"""Import HAM time series for each run's data interval."""

import logging
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from infra.dagster.ham.sensors import SensorUnavailable

LOGGER = logging.getLogger(__name__)

SENSOR_FAMILY = "ham"

BATCH_SIZE = 1000


def load_references(engine, sensor_id: str | None = None) -> dict:
    """Select sensor identities and reading-type UUIDs from the same family."""
    from sqlalchemy import select
    from app.db.models.sensor import Sensor
    from app.db.models.observation_type import ObservationType

    sensor_query = select(Sensor.id, Sensor.external_id, Sensor.sensor_family, Sensor.starting_date).where(
        Sensor.sensor_family == SENSOR_FAMILY,
    ).order_by(Sensor.id)
    if sensor_id is not None:
        sensor_query = sensor_query.where(Sensor.id == UUID(sensor_id))
    with engine.connect() as connection:
        sensors = [dict(row) for row in connection.execute(
            sensor_query
        ).mappings()]
        types = {key: str(id_) for key, id_ in connection.execute(
            select(ObservationType.key, ObservationType.id)
            .where(ObservationType.sensor_family == SENSOR_FAMILY)
        )}
    if not sensors and sensor_id is not None:
        raise SensorUnavailable(f"HAM sensor {sensor_id} not found or no longer HAM; reload the code location")
    if not sensors:
        raise ValueError("No HAM sensors found; run the sensor initialization first")
    if not types:
        raise ValueError("No HAM observation types found; run their initialization first")
    for sensor in sensors:
        if not isinstance(sensor["external_id"], str) or not sensor["external_id"].strip():
            raise ValueError(f"Sensor {sensor['id']} has no external_id")
        sensor["id"] = str(sensor["id"])
    return {"sensors": sensors, "types": types}


def validate_interval(start, end):
    """Require an explicit, positive, timezone-aware data interval."""
    if (not isinstance(start, datetime) or not isinstance(end, datetime)
            or start.utcoffset() is None or end.utcoffset() is None or start >= end):
        raise ValueError("A nonempty timezone-aware data interval is required")


def fetch_readings(api_key: str, external_id: str, start: datetime, end: datetime) -> dict:
    """Fetch the library's transformed series using Unix seconds, not run wall time."""
    import hamapi

    validate_interval(start, end)
    client = hamapi.hamapi(api_key=api_key, cache_db_file=":memory:")
    try:
        # Check access explicitly: the library otherwise defaults to a server for unknown devices.
        devices = client.get_user_devices(force_refresh=True)
        if not isinstance(devices, dict) or devices.get("error") or not isinstance(devices.get("devices"), list):
            raise ValueError("HAMAPI returned an invalid device response")
        if not any(isinstance(device, dict) and device.get("serialno") == external_id
                   for device in devices["devices"]):
            raise ValueError("The configured API key cannot access the selected sensor")
        return client.get_datalog_data(external_id, start.timestamp(), end.timestamp())
    finally:
        client.cache_conn.close()


@dataclass
class PreparedObservations:
    """Validated rows and diagnostics about the transformed HAM response, before writes."""

    rows: list[dict]
    diagnostics: dict
    reading_summary: list[dict]


def prepare_observation_rows(response: dict, sensor: dict, types: dict,
                             start: datetime, end: datetime) -> PreparedObservations:
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
    reading_summary = {
        key: {"reading_key": key, "selected_rows": 0, "null_values": 0,
              "first_timestamp": None, "last_timestamp": None,
              "minimum": None, "maximum": None}
        for key in selected_keys
    }
    rows = {}
    sensor_id = UUID(sensor["id"])
    for index, seconds in enumerate(timestamps):
        if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(seconds):
            raise ValueError(f"Invalid timestamp at index {index}")
        timestamp = datetime.fromtimestamp(seconds, tz=timezone.utc)
        if not start <= timestamp < end:
            diagnostics["out_of_interval_timestamp_count"] += 1
            continue
        for key in selected_keys:
            value = response[key][index]
            if value is None:
                diagnostics["null_value_count"] += 1
                reading_summary[key]["null_values"] += 1
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"Invalid numeric value for {key!r} at index {index}")
            identity = (UUID(types[key]), timestamp)
            row = {"sensor_id": sensor_id, "observation_type_id": identity[0],
                   "timestamp": timestamp, "value": float(value)}
            if identity in rows:
                if rows[identity]["value"] != row["value"]:
                    raise ValueError(f"Conflicting duplicate value for {key!r} at {timestamp}")
                diagnostics["identical_duplicate_count"] += 1
                continue
            rows[identity] = row
            reading = reading_summary[key]
            reading["selected_rows"] += 1
            if reading["first_timestamp"] is None:
                reading.update(first_timestamp=timestamp, last_timestamp=timestamp,
                               minimum=row["value"], maximum=row["value"])
            else:
                reading["first_timestamp"] = min(reading["first_timestamp"], timestamp)
                reading["last_timestamp"] = max(reading["last_timestamp"], timestamp)
                reading["minimum"] = min(reading["minimum"], row["value"])
                reading["maximum"] = max(reading["maximum"], row["value"])

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
    return PreparedObservations(list(rows.values()), diagnostics, list(reading_summary.values()))


def persist_observation_rows(engine, rows: list[dict]) -> dict:
    """Upsert bounded batches in one sensor transaction; reruns preserve row IDs."""
    from sqlalchemy.dialects.postgresql import insert
    from app.db.models.observation_value import ObservationValue

    changed = 0
    if rows:
        with engine.begin() as connection:
            for offset in range(0, len(rows), BATCH_SIZE):
                statement = insert(ObservationValue).values(rows[offset:offset + BATCH_SIZE])
                statement = statement.on_conflict_do_update(
                    index_elements=[ObservationValue.sensor_id, ObservationValue.observation_type_id,
                                    ObservationValue.timestamp],
                    set_={"value": statement.excluded.value},
                    where=ObservationValue.value.is_distinct_from(statement.excluded.value),
                ).returning(ObservationValue.id)
                changed += len(connection.execute(statement).scalars().all())
    return {"selected": len(rows), "inserted_or_updated": changed}
