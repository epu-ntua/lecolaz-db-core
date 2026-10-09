"""Bounded HAM HTTP requests, preserving datalog response bodies for replay."""

import math
import re
from datetime import datetime

import requests

from dagster import ConfigurableResource, Failure
from infra.dagster.ham.catalog import load_catalog
from infra.dagster.ham.datalog import is_missing_datalog
from infra.dagster.ham.observation_values import validate_interval


class HamApi(ConfigurableResource):
    """Fetch source bytes without invoking the HAM library's parser or cache."""

    api_key: str = ""

    def require_key(self) -> str:
        if not self.api_key.strip():
            raise Failure(
                "Set HAMAPI_API_KEY in infra/.env and recreate Dagster services",
                allow_retries=False,
            )
        return self.api_key

    def catalog(self, name: str) -> dict:
        return load_catalog(name)

    def devices(self) -> dict:
        # The SDK's get_user_devices() omits a timeout. Registration runs in the
        # Compose startup hook, so bound this request and let Dagster retry failures.
        with requests.post(
            "https://api.hamsystems.eu/get_user_devices.php",
            data={"api_key": self.require_key()},
            timeout=(10, 30),
        ) as response:
            response.raise_for_status()
            return response.json()

    def readings(self, external_id: str, start: datetime, end: datetime) -> bytes:
        """Fetch the level-0 bin containing this UTC daily partition, unchanged."""
        validate_interval(start, end)
        bin_id = math.floor(start.timestamp() / 86400)
        if end.timestamp() > (bin_id + 1) * 86400:
            raise ValueError("HAM raw requests must fit within one UTC day")
        response = self.devices()
        if (
            not isinstance(response, dict)
            or response.get("error")
            or not isinstance(response.get("devices"), list)
        ):
            raise ValueError("HAMAPI returned an invalid device response")
        device = next(
            (
                item for item in response["devices"]
                if isinstance(item, dict) and item.get("serialno") == external_id
            ),
            None,
        )
        if device is None:
            raise ValueError("The configured API key cannot access the selected sensor")
        server = device.get("device_server") or "node0.hamsystems.eu"
        if not isinstance(server, str):
            raise ValueError("Invalid HAM device server")
        if "." not in server:
            server += ".hamsystems.eu"
        if server in ("device0.hamsystems.eu", "hamsystems.eu"):
            server = "node0.hamsystems.eu"
        if not re.fullmatch(r"[a-zA-Z0-9-]+\.hamsystems\.eu", server):
            raise ValueError("Invalid HAM device server")
        with requests.post(
            f"https://{server}/datalogs.php",
            params={"serialno": external_id, "id": f"0.{bin_id}"},
            data={"api_key": self.require_key()},
            timeout=(10, 60),
        ) as response:
            if response.status_code in (200, 404) and is_missing_datalog(response.content):
                raise Failure(
                    f"HAM datalog file not found for {external_id}, bin 0.{bin_id}; "
                    "no raw payload was stored. Retry the partition when source data is available.",
                    allow_retries=False,
                )
            response.raise_for_status()
            return response.content
