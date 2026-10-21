"""Discover authoritative catalogs without importing Dagster into the API."""

import httpx

from app.core.config import settings
from app.integrations import ham, openmeteo


class SensorCatalogUnavailable(Exception):
    """A provider could not supply a valid catalog."""


class SensorCatalogNotConfigured(Exception):
    """Required server-side credentials are absent."""


class IneligibleSensors(ValueError):
    pass


class OpenMeteoDetails:
    def __init__(self, client: httpx.Client):
        self.client = client

    def detail(self, path: str) -> dict:
        response = self.client.get("https://openmeteo.org/api/" + path)
        response.raise_for_status()
        value = response.json()
        if not isinstance(value, dict) or not isinstance(value.get("id"), int):
            raise ValueError("Invalid OpenMeteo detail")
        return value


def prepare_catalog(sensor_family: str, external_ids: list[str] | None = None):
    """Return validated sensor/type rows; a selection is reverified on every call."""
    if sensor_family == "ham" and not settings.HAMAPI_API_KEY.strip():
        raise SensorCatalogNotConfigured("HAMAPI_API_KEY is not configured")
    try:
        with httpx.Client(timeout=httpx.Timeout(30, connect=10)) as client:
            if sensor_family == "ham":
                response = client.post(
                    "https://api.hamsystems.eu/get_user_devices.php",
                    data={"api_key": settings.HAMAPI_API_KEY},
                )
                response.raise_for_status()
                rows = ham.prepare_sensor_rows(response.json())
                if external_ids is None:
                    return rows, []
                by_id = {row["external_id"]: row for row in rows}
                if set(external_ids) - by_id.keys():
                    raise IneligibleSensors("Selection includes sensors unavailable to the configured HAM account")
                keys = ham.collect_reading_keys(ham.load_catalog("models"))
                types = ham.prepare_rows(ham.load_catalog("readings"), keys)
                return [by_id[key] for key in external_ids], types
            if sensor_family == "openmeteo":
                eligible = openmeteo.load_registration_defaults()
                if external_ids is not None and set(external_ids) - set(eligible):
                    raise IneligibleSensors("Selection includes sensors outside the OpenMeteo catalog")
                return openmeteo.prepare_registration(
                    OpenMeteoDetails(client), eligible if external_ids is None else external_ids
                )
            raise IneligibleSensors("Unsupported sensor family")
    except IneligibleSensors:
        raise
    except (httpx.HTTPError, ValueError, TypeError, KeyError, OSError) as exc:
        # Provider bodies and exception strings may contain account data.
        raise SensorCatalogUnavailable(f"Unable to retrieve a valid {sensor_family} sensor catalog") from exc
