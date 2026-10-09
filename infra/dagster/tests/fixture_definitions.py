"""Offline HAM responses for disposable deployment tests; never loaded by normal Compose."""

from dagster import definitions

from infra.dagster.definitions import build_definitions, configured_database
from infra.dagster.ham.client import HamApi


class FixtureHamApi(HamApi):
    def devices(self) -> dict:
        return {"devices": [{"name": f"Fixture {i}", "serialno": f"e45:{i}"} for i in (1, 2)]}

    def readings(self, external_id, start, end) -> bytes:
        if start.date().isoformat() == "2026-01-03":
            # Valid source data, but no measurements inside the requested interval.
            return f"{start.timestamp() - 60};2150;;;\n".encode()
        return f"{start.timestamp()};2150;;;\n{end.timestamp()};9900;;;\n".encode()


@definitions
def defs():
    return build_definitions(configured_database(), FixtureHamApi())
