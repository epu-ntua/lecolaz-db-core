"""Map and atomically register explicitly selected Enhydris timeseries."""

from datetime import datetime, timezone
from uuid import UUID

from app.storage.postgres.observation_type_store import ObservationTypeStore
from app.storage.postgres.sensor_store import SensorStore

from infra.dagster.openmeteo import SENSOR_FAMILY
from infra.dagster.openmeteo.client import parse_external_id, timeseries_path


def utc_starting_date(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError("Sensor starting_date must be timezone-aware")
    return value.astimezone(timezone.utc)


def observation_type_key(sensor: dict) -> str:
    key = (sensor.get("sensor_metadata") or {}).get("observation_type_key")
    # Reuse the strict positive ID grammar for the two-part type identity.
    parse_external_id(f"1/{key}")
    return key


def prepare_registration(api, external_ids: list[str]) -> tuple[list[dict], list[dict]]:
    if not external_ids:
        raise ValueError("Provide at least one OpenMeteo external_id")
    for external_id in external_ids:
        parse_external_id(external_id)
    cache = {}

    def detail(path, expected):
        if path not in cache:
            cache[path] = api.detail(path)
        value = cache[path]
        if value.get("id") != expected:
            raise ValueError(f"Unexpected entity ID at {path}")
        return value

    sensors, types = [], {}
    for external_id in dict.fromkeys(external_ids):
        station_id, group_id, series_id = parse_external_id(external_id)
        station = detail(f"stations/{station_id}/", station_id)
        group = detail(f"stations/{station_id}/timeseriesgroups/{group_id}/", group_id)
        series = detail(timeseries_path(external_id), series_id)
        if (
            group.get("gentity") != station_id
            or series.get("timeseries_group") != group_id
        ):
            raise ValueError(f"Inconsistent parent relationships for {external_id}")
        if series.get("publicly_available") is False:
            raise ValueError(f"Timeseries {external_id} is not publicly available")
        variable_id, unit_id = group.get("variable"), group.get("unit_of_measurement")
        key = f"{variable_id}/{unit_id}"
        parse_external_id(f"1/{key}")
        variable = detail(f"variables/{variable_id}/", variable_id)
        unit = detail(f"units/{unit_id}/", unit_id)
        label = variable.get("descr") or variable.get("translations", {}).get(
            "en", {}
        ).get("descr")
        name, symbol = group.get("name"), unit.get("symbol")
        if not all(isinstance(v, str) and v.strip() for v in (name, label, symbol)):
            raise ValueError(
                f"Missing group name, variable description, or unit symbol for {external_id}"
            )
        location = station.get("geom")
        if location is not None and not isinstance(location, str):
            raise ValueError("Station geom must be an EWKT string or null")
        sensors.append(
            {
                "external_id": external_id,
                "name": name,
                "location": location,
                "sensor_metadata": {
                    "observation_type_key": key,
                    "station": {k: v for k, v in station.items() if k != "geom"},
                    "timeseries_group": {k: v for k, v in group.items() if k != "name"},
                    "timeseries": series,
                },
            }
        )
        types[key] = {
            "key": key,
            "label": label,
            "unit": symbol,
            "type_metadata": {"variable": variable, "unit_of_measurement": unit},
        }
    return sensors, list(types.values())


def persist_registration(
    engine, sensor_rows: list[dict], type_rows: list[dict]
) -> dict:
    with engine.begin() as connection:
        types = ObservationTypeStore(connection).upsert_source_fields(
            SENSOR_FAMILY, type_rows
        )
        sensors = SensorStore(connection).upsert_source_fields(
            SENSOR_FAMILY,
            sensor_rows,
            # The station's geom is authoritative for OpenMeteo sensors.
            source_location=True,
        )
    return {"sensors": sensors, "observation_types": types}


def load_sensor_catalog(engine) -> list[dict]:
    with engine.connect() as connection:
        rows = SensorStore(connection).list_by_sensor_family(SENSOR_FAMILY)
    for row in rows:
        row["id"] = str(row["id"])
        row["starting_date"] = utc_starting_date(row["starting_date"])
        parse_external_id(row["external_id"])
        observation_type_key(row)
    return rows


def load_references(engine, expected: dict) -> tuple[dict, UUID]:
    with engine.connect() as connection:
        sensor = SensorStore(connection).get_by_id_and_sensor_family(
            UUID(expected["id"]), SENSOR_FAMILY
        )
        if sensor is None:
            raise ValueError(
                "OpenMeteo sensor is unavailable; reload the code location"
            )
        for field in ("external_id", "starting_date"):
            if sensor[field] != expected[field]:
                raise ValueError(f"Sensor {field} changed; reload the code location")
        key = observation_type_key(sensor)
        if key != observation_type_key(expected):
            raise ValueError(
                "Sensor observation type changed; reload the code location"
            )
        types = ObservationTypeStore(connection).get_id_map_by_sensor_family(
            SENSOR_FAMILY
        )
        if key not in types:
            raise ValueError(
                f"Missing OpenMeteo observation type {key}; register the sensor again"
            )
    return sensor, types[key]
