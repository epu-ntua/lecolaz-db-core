"""OpenMeteo (Enhydris) catalog shared by the API and Dagster."""

import re
from pathlib import Path

import yaml

REGISTRATION_DEFAULTS_PATH = Path(__file__).with_name("openmeteo_registration.yaml")


def parse_external_id(value: str) -> tuple[int, int, int]:
    if not isinstance(value, str) or not re.fullmatch(
        r"[1-9][0-9]*/[1-9][0-9]*/[1-9][0-9]*", value
    ):
        raise ValueError(
            "Expected external_id as station_id/timeseries_group_id/timeseries_id (positive integers)"
        )
    return tuple(map(int, value.split("/")))


def timeseries_path(external_id: str) -> str:
    station, group, series = parse_external_id(external_id)
    return f"stations/{station}/timeseriesgroups/{group}/timeseries/{series}/"


def load_registration_defaults(path: Path = REGISTRATION_DEFAULTS_PATH) -> list[str]:
    """Keep the editable sensor list beside the integration, not in instance config."""
    settings = yaml.safe_load(path.read_text(encoding="utf-8"))
    external_ids = settings.get("external_ids") if isinstance(settings, dict) else None
    if not isinstance(external_ids, list) or not external_ids:
        raise ValueError("registration.yaml must contain a nonempty external_ids list")
    for external_id in external_ids:
        parse_external_id(external_id)
    return external_ids


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


