"""Decode headerless level-0 HAM datalogs using the model's ordered columns."""

import csv
import io
import json
import math
from collections.abc import Iterator
from datetime import datetime, timezone

from infra.dagster.ham.catalog import load_catalog

READING_MISSING = 2147483648
DIVISORS = {
    "divide_by_1": 1,
    "divide_by_10": 10,
    "divide_by_100": 100,
    "divide_by_1000": 1000,
    "divide_by_1000000": 1000000,
    "geocoordinates_translation": 1000000,
    "ws_to_kwh": 3600000,
}
CLAMPED_DIVISORS = {
    "divide_by_1000_max_1": (1000, 1),
    "divide_by_100_max_100": (100, 100),
    "divide_by_1000_max_100": (1000, 100),
}


class MissingDatalogError(ValueError):
    """A retained error response requires a new fetch, not a parser correction."""


def is_missing_datalog(payload: bytes) -> bool:
    """HAM uses this JSON body with HTTP 404 for a day without a datalog file."""
    if not payload.lstrip().startswith(b"{"):
        return False
    try:
        return json.loads(payload) == {"messages": ["File not found"]}
    except (ValueError, UnicodeDecodeError):
        return False


def transform_reading(value: float, transform: str | None) -> float:
    """Match hamapi's transform behavior while fixing bugs and rejecting unknown names."""
    if transform in (None, "transform", "absolute", "beaufort_scale"):
        # hamapi 0.1.15 falls back to float(x) for these cases, including the
        # unimplemented "absolute" and "beaufort_scale" names. Preserve signed values.
        return float(value)
    if transform in DIVISORS:
        return value / DIVISORS[transform]
    if transform in CLAMPED_DIVISORS:
        divisor, maximum = CLAMPED_DIVISORS[transform]
        return min(max(value / divisor, 0), maximum)
    if transform == "only_positive":
        return max(math.floor(value), 0)
    if transform == "binary_translation":
        return float(value > 0)
    if transform == "percent_translation":
        # hamapi 0.1.15 calls JavaScript's toFixed(1) on a Python number and raises.
        # Fix that bug with numeric rounding instead of a string-formatting method.
        return round(min(max(value * 100, 0), 100), 1)
    # Unlike hamapi's blanket float fallback, reject new names to avoid wrong units.
    raise ValueError(f"Unsupported HAM reading transform: {transform!r}")


def _datalog_columns(external_id: str, models: dict) -> tuple[list[str], list[str]]:
    model_id, separator, serial = external_id.partition(":")
    if not separator or not serial or model_id not in models:
        raise ValueError(f"Unknown HAM sensor model for {external_id!r}")
    model = models[model_id]
    keys = model.get("readings")
    outputs = model.get("output_names", [])
    if (
        not isinstance(keys, list)
        or not isinstance(outputs, list)
        or any(not isinstance(key, str) or not key for key in keys + outputs)
        or "timestamp" in keys
        or len(set(keys)) != len(keys)
    ):
        raise ValueError(f"Invalid datalog columns for model {model_id!r}")
    return keys, outputs


def _datalog_rows(
    payload: bytes, keys: list[str], outputs: list[str]
) -> Iterator[tuple[float, list[float | None]]]:
    """Validate the wire format without applying reading transforms."""
    if is_missing_datalog(payload):
        raise MissingDatalogError("HAM datalog file not found; rematerialize raw when source data is available")
    expected_columns = 1 + len(keys) + len(outputs)
    reader = csv.reader(io.StringIO(payload.decode("utf-8-sig")), delimiter=";", strict=True)
    try:
        for fields in reader:
            if not fields or (len(fields) == 1 and not fields[0].strip()):
                continue
            if len(fields) != expected_columns:
                raise ValueError(
                    f"expected {expected_columns} columns, got {len(fields)}"
                )
            timestamp = float(fields[0])
            if not math.isfinite(timestamp):
                raise ValueError("invalid timestamp")
            try:
                datetime.fromtimestamp(timestamp, tz=timezone.utc)
            except (ValueError, OverflowError, OSError) as exc:
                raise ValueError("timestamp outside supported range") from exc
            values = []
            for key, field in zip(keys, fields[1:]):
                if not field.strip():
                    values.append(None)
                    continue
                value = float(field)
                if not math.isfinite(value):
                    raise ValueError(f"nonfinite value for {key!r}")
                values.append(None if value == READING_MISSING else value)
            yield timestamp, values
    except (ValueError, csv.Error) as exc:
        raise ValueError(f"HAM datalog line {reader.line_num}: {exc}") from exc


def validate_datalog(payload: bytes, external_id: str) -> int:
    """Require a complete datalog containing measurements before persisting bytes."""
    keys, outputs = _datalog_columns(external_id, load_catalog("models"))
    row_count = 0
    has_measurement = False
    for _, values in _datalog_rows(payload, keys, outputs):
        row_count += 1
        has_measurement |= any(value is not None for value in values)
    if not has_measurement:
        raise ValueError("HAM datalog contains no measurements")
    return row_count


def parse_datalog(
    payload: bytes,
    external_id: str,
    *,
    models: dict | None = None,
    readings: dict | None = None,
) -> dict[str, list]:
    """Convert source samples, without forward filling or synthetic chart edges.

    Outputs occupy trailing columns but are not observation readings. Validate
    their presence without interpreting them (some outputs are nonnumeric).
    """
    models = load_catalog("models") if models is None else models
    readings = load_catalog("readings") if readings is None else readings
    keys, outputs = _datalog_columns(external_id, models)
    transforms = {}
    for key in keys:
        if not isinstance(readings.get(key), dict):
            raise ValueError(f"Missing reading catalog entry for {key!r}")
        transforms[key] = readings[key].get("transform")
        transform_reading(0, transforms[key])
    result = {key: [] for key in ["timestamp", *keys]}
    for timestamp, values in _datalog_rows(payload, keys, outputs):
        result["timestamp"].append(timestamp)
        for key, value in zip(keys, values):
            result[key].append(None if value is None else transform_reading(value, transforms[key]))
    return result
