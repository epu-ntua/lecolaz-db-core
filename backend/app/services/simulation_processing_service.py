import uuid
import csv
import io
import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable

from app.storage.object.minio import MinioStore
from app.storage.postgres.dataset_store import DatasetStore
from app.storage.postgres.simulation_store import SimulationStore
from app.storage.postgres.simulation_timeseries_store import SimulationTimeseriesStore
from app.storage.postgres.simulation_variable_store import SimulationVariableStore

ENVIRONMENT_RECORD_ID = 1
TIMESTAMP_KEYS = {
    "year": ["calendar year of simulation"],
    "month": ["month"],
    "day": ["day of month", "day"],
    "hour": ["hour"],
    "minute": ["end minute", "endminute", "start minute", "startminute"],
}


class SimulationProcessingError(Exception):
    pass


class SimulationNotFoundError(SimulationProcessingError):
    pass


class SimulationConflictError(SimulationProcessingError):
    pass


def _normalize_label(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _split_variable_descriptor(value: str) -> tuple[str, str | None, str | None]:
    descriptor, _, frequency = value.partition("!")
    descriptor = descriptor.strip()
    frequency = frequency.strip() or None

    unit_match = re.search(r"\[(.*?)\]", descriptor)
    units = unit_match.group(1).strip() if unit_match else None
    variable = re.sub(r"\s*\[.*?\]\s*", "", descriptor).strip()
    return variable, units, frequency


def _to_number(value: str) -> int | float | str:
    raw = value.strip()
    if raw == "":
        return raw
    try:
        numeric = float(raw)
    except ValueError:
        return raw
    if numeric.is_integer():
        return int(numeric)
    return numeric


def _is_timestamp_dictionary_row(fields: Iterable[str]) -> bool:
    normalized = [_normalize_label(field) for field in fields]
    has_month = any("month" in field for field in normalized)
    has_day = any("day of month" in field or field == "day" for field in normalized)
    has_hour = any("hour" in field for field in normalized)
    has_year = any("calendar year of simulation" in field for field in normalized)
    return (has_month and has_day) or has_hour or has_year


def _resolve_timestamp_value(parsed: Dict[str, Any], key: str) -> Any:
    for label in TIMESTAMP_KEYS[key]:
        normalized = _normalize_label(label)
        if normalized in parsed:
            return parsed[normalized]
    return None


def _build_timestamp_value(parsed: Dict[str, Any]) -> str | None:
    year = _resolve_timestamp_value(parsed, "year")
    month = _resolve_timestamp_value(parsed, "month")
    day = _resolve_timestamp_value(parsed, "day")
    hour = _resolve_timestamp_value(parsed, "hour")
    minute = _resolve_timestamp_value(parsed, "minute")

    if all(isinstance(value, int) for value in (year, month, day, hour)):
        minute_value = minute if isinstance(minute, int) else 0
        return datetime(year, month, day, hour, minute_value).isoformat()

    date_parts: list[str] = []
    if isinstance(year, int):
        date_parts.append(f"{year:04d}")
    if isinstance(month, int):
        date_parts.append(f"{month:02d}")
    if isinstance(day, int):
        date_parts.append(f"{day:02d}")

    timestamp = "-".join(date_parts) if date_parts else None
    if isinstance(hour, int):
        minute_value = minute if isinstance(minute, int) else 0
        time_part = f"{hour:02d}:{minute_value:02d}"
        return f"{timestamp} {time_part}" if timestamp else time_part

    return timestamp


def _parse_iso_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _build_timestamp(fields: list[str], labels: list[str]) -> Dict[str, Any]:
    parsed: Dict[str, Any] = {}
    for label, value in zip(labels, fields):
        normalized = _normalize_label(label)
        parsed[normalized] = _to_number(value)

    return {
        "timestamp": _build_timestamp_value(parsed),
        "fields": parsed,
    }


def _extract_variable_definition(field_labels: list[str], value_count: int | None) -> Dict[str, Any]:
    descriptor = field_labels[-1]
    context_fields = field_labels[:-1]
    context = context_fields[0] if context_fields else None
    variable_name, units, frequency = _split_variable_descriptor(descriptor)

    return {
        "zone": context,
        "context": context_fields,
        "variable": variable_name,
        "units": units,
        "frequency": frequency,
        "value_count": value_count,
    }


def _parse_variable_value(value_cells: list[str], value_count: int | None) -> Any:
    expected_count = value_count if isinstance(value_count, int) and value_count > 0 else len(value_cells)
    cells = value_cells[:expected_count]
    parsed_cells = [_to_number(value) for value in cells]
    if expected_count == 1 and parsed_cells:
        return parsed_cells[0]
    return parsed_cells


def _parse_eso_bytes(data: bytes) -> Dict[str, Any]:
    if not data:
        raise ValueError("Simulation file is empty")

    try:
        text = data.decode("utf-8")
        encoding = "utf-8"
    except UnicodeDecodeError:
        text = data.decode("latin-1")
        encoding = "latin-1"

    rows = [
        [cell.strip() for cell in row]
        for row in csv.reader(io.StringIO(text))
        if any(cell.strip() for cell in row)
    ]
    if not rows:
        raise ValueError("Simulation file does not contain readable records")

    dictionary_rows: list[list[str]] = []
    data_rows: list[list[str]] = []
    in_data = False
    for row in rows:
        if row[0].strip() == "End of Data Dictionary":
            in_data = True
            continue
        if in_data:
            data_rows.append(row)
        else:
            dictionary_rows.append(row)

    variables: Dict[str, Any] = {}
    dictionary_info: Dict[str, Any] = {}
    timestamp_record_definitions: Dict[int, list[str]] = {}

    for row in dictionary_rows:
        if not row or not row[0].isdigit():
            continue

        record_id = int(row[0])
        value_count = int(row[1]) if len(row) > 1 and row[1].isdigit() else None
        field_labels = row[2:]
        if not field_labels:
            continue

        if record_id == ENVIRONMENT_RECORD_ID:
            dictionary_info["environment_fields"] = field_labels
            dictionary_info["environment_value_count"] = value_count
            continue

        if _is_timestamp_dictionary_row(field_labels):
            timestamp_record_definitions[record_id] = field_labels
            continue

        variables[str(record_id)] = _extract_variable_definition(field_labels, value_count)

    if not variables:
        raise ValueError("No simulation variables found in ESO dictionary")

    timesteps: list[Dict[str, Any]] = []
    values: Dict[str, list[Any]] = {}
    used_variable_ids: set[str] = set()
    current_timestep_index = -1

    for row in data_rows:
        if not row or not row[0].isdigit():
            continue

        record_id = int(row[0])
        if record_id in timestamp_record_definitions:
            timesteps.append(_build_timestamp(row[1:], timestamp_record_definitions[record_id]))
            current_timestep_index += 1
            continue

        variable_id = str(record_id)
        if variable_id not in variables:
            continue
        if current_timestep_index < 0:
            continue

        variable_values = values.setdefault(variable_id, [])
        if len(variable_values) <= current_timestep_index:
            variable_values.extend([None] * (current_timestep_index + 1 - len(variable_values)))
        variable_values[current_timestep_index] = _parse_variable_value(
            row[1:],
            variables[variable_id].get("value_count"),
        )
        used_variable_ids.add(variable_id)

    timestep_count = len(timesteps)
    valid_variable_ids = used_variable_ids - {str(record_id) for record_id in timestamp_record_definitions}

    filtered_variables = {
        variable_id: variable_info
        for variable_id, variable_info in variables.items()
        if variable_id in valid_variable_ids
    }

    filtered_values: Dict[str, list[Any]] = {}
    for variable_id in filtered_variables:
        variable_values = values.setdefault(variable_id, [])
        if len(variable_values) < timestep_count:
            variable_values.extend([None] * (timestep_count - len(variable_values)))
        filtered_values[variable_id] = variable_values

    if not filtered_variables:
        raise ValueError("No simulation variables produced timestep values")

    return {
        "parser": "structured_eso_text",
        "encoding": encoding,
        "line_count": len(rows),
        "variable_count": len(filtered_variables),
        "timestep_count": len(timesteps),
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "dictionary_info": dictionary_info,
        "variables": filtered_variables,
        "timesteps": timesteps,
        "values": filtered_values,
    }


def _build_variable_rows(summary: Dict[str, Any]) -> list[Dict[str, Any]]:
    rows: list[Dict[str, Any]] = []
    for variable_id, variable_info in summary.get("variables", {}).items():
        context_fields = variable_info.get("context") or []
        key = context_fields[0] if context_fields else variable_info.get("zone")
        rows.append(
            {
                "variable_id": variable_id,
                "variable_name": variable_info.get("variable"),
                "unit": variable_info.get("units"),
                "frequency": variable_info.get("frequency"),
                "key": key,
            }
        )
    return rows


def _build_timeseries_rows(
    summary: Dict[str, Any],
    variable_id_map: Dict[str, str],
) -> tuple[list[Dict[str, Any]], int]:
    timesteps = summary.get("timesteps", [])
    values_map = summary.get("values", {})
    rows: list[Dict[str, Any]] = []
    skipped_values_count = 0

    for eso_variable_id, db_variable_id in variable_id_map.items():
        variable_values = values_map.get(eso_variable_id, [])
        for timestep_index, timestep in enumerate(timesteps):
            if timestep_index >= len(variable_values):
                continue

            timestamp = _parse_iso_timestamp(timestep.get("timestamp"))
            if timestamp is None:
                skipped_values_count += 1
                continue

            value = variable_values[timestep_index]
            if not isinstance(value, (int, float)):
                skipped_values_count += 1
                continue

            rows.append(
                {
                    "variable_id": db_variable_id,
                    "timestamp": timestamp,
                    "value": float(value),
                }
            )

    return rows, skipped_values_count


def process_simulation(dataset_id: uuid.UUID, *, allow_reprocess: bool = False) -> Dict[str, Any]:
    simulation_store = SimulationStore()
    dataset_store = DatasetStore()
    simulation_variable_store = SimulationVariableStore()
    simulation_timeseries_store = SimulationTimeseriesStore()
    minio_store = MinioStore()

    dataset_record = dataset_store.get_dataset_by_id(dataset_id)
    if not dataset_record:
        raise SimulationNotFoundError("Dataset not found")
    if dataset_record.get("type") != "simulation":
        raise SimulationProcessingError("Dataset is not a simulation dataset")

    simulation = simulation_store.get_simulation_by_dataset_id(dataset_id)
    if not simulation:
        raise SimulationNotFoundError("Simulation dataset not found")

    current_status = dataset_record.get("status")
    if current_status == "processing":
        raise SimulationConflictError("Simulation is already processing")
    if current_status == "processed" and not allow_reprocess:
        raise SimulationConflictError("Simulation is already processed")

    dataset_store.update_dataset_status(
        dataset_id,
        "processing",
        metadata_patch={"processing_error": None},
    )

    try:
        data = minio_store.get_object_bytes(dataset_record["object_key"])
        summary = _parse_eso_bytes(data)

        simulation_dataset_id = uuid.UUID(simulation["id"])
        simulation_timeseries_store.delete_by_simulation_dataset_id(simulation_dataset_id)
        simulation_variable_store.delete_by_simulation_dataset_id(simulation_dataset_id)

        variable_rows = _build_variable_rows(summary)
        variable_id_map = simulation_variable_store.replace_variables(
            simulation_dataset_id,
            variable_rows,
        )

        timeseries_rows, skipped_values_count = _build_timeseries_rows(summary, variable_id_map)
        simulation_timeseries_store.replace_timeseries(
            simulation_dataset_id,
            timeseries_rows,
        )

        updated = dataset_store.update_dataset_status(
            dataset_id,
            "processed",
            metadata_patch={
                "processing_error": None,
                "variable_count": len(variable_rows),
                "timestep_count": len(summary.get("timesteps", [])),
                "skipped_values": skipped_values_count,
                "processed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        if not updated:
            raise SimulationNotFoundError("Dataset not found during status update")
        return {
            "id": simulation["id"],
            "status": updated["status"],
        }
    except Exception as exc:
        dataset_store.update_dataset_status(
            dataset_id,
            "failed",
            metadata_patch={"processing_error": str(exc)},
        )
        raise SimulationProcessingError(str(exc)) from exc
