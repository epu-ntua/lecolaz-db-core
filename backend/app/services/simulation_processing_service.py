import uuid
import csv
import io
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable

from app.storage.object.minio import MinioStore
from app.storage.postgres.bim_space_store import BimSpaceStore
from app.storage.postgres.dataset_store import DatasetStore
from app.storage.postgres.simulation_store import SimulationStore
from app.storage.postgres.simulation_timeseries_store import SimulationTimeseriesStore
from app.storage.postgres.simulation_variable_store import SimulationVariableStore

ENVIRONMENT_RECORD_ID = 1
TIMESTAMP_RECORD_IDS = {2, 3, 4, 5, 6}
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


logger = logging.getLogger("uvicorn.error")


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

    # EnergyPlus ESO timestamp records frequently omit the year and may encode
    # midnight as hour 24. Normalize those cases so timeseries rows are not
    # dropped just because they are not ISO-ready on first parse.
    if isinstance(month, int) and isinstance(day, int) and isinstance(hour, int):
        normalized_year = year if isinstance(year, int) else 2001
        minute_value = minute if isinstance(minute, int) else 0

        try:
            base = datetime(normalized_year, month, day, 0, 0)
        except ValueError:
            return None

        normalized = base + timedelta(hours=hour, minutes=minute_value)
        return normalized.isoformat()

    date_parts: list[str] = []
    normalized_year = year if isinstance(year, int) else 2001
    if isinstance(month, int) and isinstance(day, int):
        date_parts.append(f"{normalized_year:04d}")
    if isinstance(month, int):
        date_parts.append(f"{month:02d}")
    if isinstance(day, int):
        date_parts.append(f"{day:02d}")

    timestamp = "-".join(date_parts) if date_parts else None
    if isinstance(hour, int):
        minute_value = minute if isinstance(minute, int) else 0
        if timestamp:
            try:
                base = datetime.fromisoformat(timestamp)
            except ValueError:
                return None
            normalized = base + timedelta(hours=hour, minutes=minute_value)
            return normalized.isoformat()

        time_part = f"{hour:02d}:{minute_value:02d}"
        return time_part

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

        if record_id in TIMESTAMP_RECORD_IDS:
            timestamp_record_definitions[record_id] = field_labels
            continue

        variables[str(record_id)] = _extract_variable_definition(field_labels, value_count)

    if not variables:
        raise ValueError("No simulation variables found in ESO dictionary")

    events: list[Dict[str, Any]] = []
    event_variable_ids: set[str] = set()
    timestep_values_seen: set[str] = set()
    skipped_values_count = 0
    current_timestamp: datetime | None = None

    for row in data_rows:
        if not row or not row[0].isdigit():
            continue

        record_id = int(row[0])
        if record_id in timestamp_record_definitions:
            timestamp_info = _build_timestamp(row[1:], timestamp_record_definitions[record_id])
            current_timestamp = _parse_iso_timestamp(timestamp_info.get("timestamp"))
            continue

        variable_id = str(record_id)
        if variable_id not in variables:
            continue

        value = _parse_variable_value(
            row[1:],
            variables[variable_id].get("value_count"),
        )
        if current_timestamp is None:
            skipped_values_count += 1
            continue

        if not isinstance(value, (int, float)):
            skipped_values_count += 1
            continue

        events.append(
            {
                "eso_variable_id": variable_id,
                "timestamp": current_timestamp,
                "value": float(value),
            }
        )
        event_variable_ids.add(variable_id)
        timestep_values_seen.add(current_timestamp.isoformat())

    filtered_variables = {
        variable_id: variable_info
        for variable_id, variable_info in variables.items()
        if variable_id in event_variable_ids
    }

    if not filtered_variables:
        raise ValueError("No simulation values produced valid timestamped events")

    return {
        "parser": "structured_eso_text",
        "encoding": encoding,
        "line_count": len(rows),
        "variable_count": len(filtered_variables),
        "timestep_count": len(timestep_values_seen),
        "skipped_values": skipped_values_count,
        "dictionary_info": dictionary_info,
        "variables": filtered_variables,
        "events": events,
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


def _enrich_variable_rows_with_bim_links(
    variable_rows: list[Dict[str, Any]],
    bim_space_id_map: Dict[str, uuid.UUID],
) -> list[Dict[str, Any]]:
    for row in variable_rows:
        key = row.get("key")
        normalized_key = key.casefold() if isinstance(key, str) else None
        matched_space_id = None
        if normalized_key:
            matched_space_id = bim_space_id_map.get(normalized_key)
            if matched_space_id is None:
                for global_id, space_id in bim_space_id_map.items():
                    if global_id in normalized_key:
                        matched_space_id = space_id
                        break

        row["bim_space_id"] = matched_space_id
    return variable_rows


def _build_timeseries_rows(
    summary: Dict[str, Any],
    variable_id_map: Dict[str, str],
) -> tuple[list[Dict[str, Any]], int]:
    events = summary.get("events", [])
    rows: list[Dict[str, Any]] = []
    skipped_values_count = 0

    for event in events:
        db_variable_id = variable_id_map.get(event["eso_variable_id"])
        if not db_variable_id:
            skipped_values_count += 1
            continue

        rows.append(
            {
                "variable_id": db_variable_id,
                "timestamp": event["timestamp"],
                "value": event["value"],
            }
        )

    return rows, skipped_values_count + int(summary.get("skipped_values", 0))


def process_simulation(dataset_id: uuid.UUID, *, allow_reprocess: bool = False) -> Dict[str, Any]:
    simulation_store = SimulationStore()
    dataset_store = DatasetStore()
    simulation_variable_store = SimulationVariableStore()
    simulation_timeseries_store = SimulationTimeseriesStore()
    bim_space_store = BimSpaceStore()
    minio_store = MinioStore()

    dataset_record = dataset_store.get_dataset_by_id(dataset_id)
    if not dataset_record:
        raise SimulationNotFoundError("Dataset not found")
    if dataset_record.get("type") != "simulation":
        raise SimulationProcessingError("Dataset is not a simulation dataset")

    logger.info(
        "simulation_processing_started dataset_id=%s allow_reprocess=%s current_status=%s",
        dataset_id,
        allow_reprocess,
        dataset_record.get("status"),
    )

    simulation = simulation_store.get_simulation_by_dataset_id(dataset_id)
    if not simulation:
        raise SimulationNotFoundError("Simulation dataset not found")

    logger.info(
        "simulation_processing_validated dataset_id=%s simulation_dataset_id=%s",
        dataset_id,
        simulation["id"],
    )

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
        logger.info(
            "simulation_processing_fetch_object dataset_id=%s object_key=%s",
            dataset_id,
            dataset_record["object_key"],
        )
        data = minio_store.get_object_bytes(dataset_record["object_key"])
        logger.info(
            "simulation_processing_object_loaded dataset_id=%s bytes=%s",
            dataset_id,
            len(data),
        )
        summary = _parse_eso_bytes(data)
        logger.info(
            "simulation_processing_parsed dataset_id=%s variable_count=%s timestep_count=%s event_count=%s skipped_values=%s",
            dataset_id,
            summary.get("variable_count", 0),
            summary.get("timestep_count", 0),
            len(summary.get("events", [])),
            summary.get("skipped_values", 0),
        )

        simulation_dataset_id = uuid.UUID(simulation["id"])
        logger.info(
            "simulation_processing_reset_existing_rows dataset_id=%s simulation_dataset_id=%s",
            dataset_id,
            simulation_dataset_id,
        )
        simulation_timeseries_store.delete_by_simulation_dataset_id(simulation_dataset_id)
        simulation_variable_store.delete_by_simulation_dataset_id(simulation_dataset_id)

        variable_rows = _build_variable_rows(summary)
        bim_dataset_id = simulation.get("bim_dataset_id")
        if bim_dataset_id:
            logger.info(
                "simulation_processing_link_bim_spaces dataset_id=%s simulation_dataset_id=%s bim_dataset_id=%s",
                dataset_id,
                simulation_dataset_id,
                bim_dataset_id,
            )
            bim_space_id_map = bim_space_store.get_space_id_map_by_bim_dataset_id(
                uuid.UUID(bim_dataset_id)
            )
            variable_rows = _enrich_variable_rows_with_bim_links(
                variable_rows,
                bim_space_id_map,
            )
        logger.info(
            "simulation_processing_insert_variables dataset_id=%s variable_rows=%s",
            dataset_id,
            len(variable_rows),
        )
        variable_id_map = simulation_variable_store.replace_variables(
            simulation_dataset_id,
            variable_rows,
        )
        logger.info(
            "simulation_processing_variables_inserted dataset_id=%s inserted_variables=%s",
            dataset_id,
            len(variable_id_map),
        )

        timeseries_rows, skipped_values_count = _build_timeseries_rows(summary, variable_id_map)
        logger.info(
            "simulation_processing_insert_timeseries dataset_id=%s timeseries_rows=%s skipped_values=%s",
            dataset_id,
            len(timeseries_rows),
            skipped_values_count,
        )
        simulation_timeseries_store.replace_timeseries(
            simulation_dataset_id,
            timeseries_rows,
        )
        logger.info(
            "simulation_processing_timeseries_inserted dataset_id=%s inserted_timeseries=%s",
            dataset_id,
            len(timeseries_rows),
        )

        updated = dataset_store.update_dataset_status(
            dataset_id,
            "processed",
            metadata_patch={
                "processing_error": None,
                "processed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        if not updated:
            raise SimulationNotFoundError("Dataset not found during status update")
        simulation_store.update_simulation_metadata(
            dataset_id,
            {
                "variable_count": len(variable_rows),
                "timestep_count": int(summary.get("timestep_count", 0)),
                "skipped_values": skipped_values_count,
            },
        )
        logger.info(
            "simulation_processing_completed dataset_id=%s status=%s variable_count=%s timestep_count=%s timeseries_rows=%s skipped_values=%s",
            dataset_id,
            updated["status"],
            len(variable_rows),
            int(summary.get("timestep_count", 0)),
            len(timeseries_rows),
            skipped_values_count,
        )
        return {
            "id": simulation["id"],
            "status": updated["status"],
        }
    except Exception as exc:
        logger.exception(
            "simulation_processing_failed dataset_id=%s error=%s",
            dataset_id,
            exc,
        )
        dataset_store.update_dataset_status(
            dataset_id,
            "failed",
            metadata_patch={"processing_error": str(exc)},
        )
        raise SimulationProcessingError(str(exc)) from exc
