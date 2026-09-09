"""Offline HAM responses for disposable deployment tests; never loaded by normal Compose."""

from dagster import definitions
from infra.dagster.definitions import build_definitions, configured_database
from infra.dagster.resources import HamApi


class FixtureHamApi(HamApi):
    def catalog(self, name: str) -> dict:
        if name == "models":
            return {"fixture": {"readings": ["T"]}}
        return {"T": {"label": "Temperature", "unit": "°C", "transform": "divide_by_100"}}

    def devices(self) -> dict:
        return {"devices": [{"name": f"Fixture {i}", "serialno": f"fixture:{i}"} for i in (1, 2)]}

    def readings(self, external_id, start, end) -> dict:
        if start.date().isoformat() == "2026-01-03":
            return {"timestamp": [], "T": []}
        return {"timestamp": [start.timestamp(), end.timestamp()], "T": [21.5, 99]}


@definitions
def defs():
    return build_definitions(configured_database(), FixtureHamApi())
