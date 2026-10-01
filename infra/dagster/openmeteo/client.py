"""Public Enhydris API access with bounded transient-error retries."""

import json
import re
from datetime import datetime, timezone

import urllib3
from pydantic import Field
from urllib3.util import Retry, Timeout

from dagster import ConfigurableResource


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


class OpenMeteoApi(ConfigurableResource):
    base_url: str = "https://openmeteo.org/api/"
    timeout_seconds: float = Field(default=90, gt=0)
    max_retries: int = Field(default=4, ge=0)

    def _get(self, path: str, params: dict | None = None) -> bytes:
        # A fresh, bounded pool per request; no sockets or clients at definition load.
        with urllib3.PoolManager(
            timeout=Timeout(connect=15, read=self.timeout_seconds),
            retries=Retry(
                total=self.max_retries,
                backoff_factor=2,
                allowed_methods={"GET"},
                status_forcelist=[408, 429, 500, 502, 503, 504],
                respect_retry_after_header=True,
            ),
        ) as pool:
            response = pool.request(
                "GET", self.base_url.rstrip("/") + "/" + path, fields=params
            )
            if response.status != 200:
                raise ValueError(
                    f"OpenMeteo GET {path} returned HTTP {response.status}"
                )
            return response.data

    def detail(self, path: str) -> dict:
        value = json.loads(self._get(path))
        if not isinstance(value, dict) or not isinstance(value.get("id"), int):
            raise TypeError(f"Invalid OpenMeteo detail at {path}")
        return value

    def readings(self, external_id: str, start: datetime, end: datetime) -> bytes:
        if start.utcoffset() is None or end.utcoffset() is None or start >= end:
            raise ValueError("A nonempty timezone-aware interval is required")
        return self._get(
            timeseries_path(external_id) + "data/",
            {
                "start_date": start.astimezone(timezone.utc).isoformat(),
                "end_date": end.astimezone(timezone.utc).isoformat(),
                "timezone": "UTC",
            },
        )
