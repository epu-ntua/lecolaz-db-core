"""Small fixtures shared by definition and asset execution tests."""

from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import patch

from infra.dagster.definitions import build_definitions as _build_definitions
from infra.dagster.ham import sensors
from infra.dagster.openmeteo import catalog as openmeteo_catalog
from infra.dagster.resources import HamApi, LeColazDatabase

DEVICE_IDS = [
    "00000000-0000-0000-0000-000000000001",
    "00000000-0000-0000-0000-000000000002",
]
CATALOG = [
    {
        "id": DEVICE_IDS[0],
        "name": "First",
        "external_id": "device:0",
        "starting_date": datetime(2026, 1, 1, 14, tzinfo=timezone.utc),
    },
    {
        "id": DEVICE_IDS[1],
        "name": "Second",
        "external_id": "device:1",
        "starting_date": datetime(2026, 3, 15, tzinfo=timezone.utc),
    },
]


class FakeDatabase(LeColazDatabase):
    """Use only when the tested workflow's database functions are patched."""

    host: str = "fixture"
    database: str = "fixture"
    username: str = "fixture"
    password: str = "fixture"

    @contextmanager
    def engine(self):
        yield None


class StubHamApi:
    """Supply explicit responses without replacing methods on the real resource."""

    def __init__(self, *, catalogs=None, devices=None, readings=None):
        self._catalogs = catalogs
        self._devices = devices
        self._readings = readings

    def catalog(self, name):
        return self._catalogs[name]

    def devices(self):
        return {"devices": self._devices}

    def readings(self, external_id, start, end):
        return self._readings(external_id, start, end)


def build_definitions(catalog=CATALOG, *, delay_hours=4):
    with (
        patch.object(sensors, "load_sensor_catalog", return_value=catalog),
        patch.object(openmeteo_catalog, "load_sensor_catalog", return_value=[]),
    ):
        return _build_definitions(FakeDatabase(), HamApi(), delay_hours=delay_hours)
