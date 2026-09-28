"""Connections for catalog discovery at definition load and ingestion at execution."""

import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from urllib.request import urlopen

import hamapi
from dagster import ConfigurableResource, Failure
from sqlalchemy import URL, Engine, create_engine

from infra.dagster.ham.observation_values import validate_interval

HAM_CATALOG_URL = "https://api.hamsystems.eu/res/doc"


class LeColazDatabase(ConfigurableResource):
    host: str
    port: int = 5432
    database: str
    username: str
    password: str

    def connection_url(self) -> URL:
        return URL.create(
            "postgresql+psycopg",
            username=self.username,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database,
        )

    @contextmanager
    def engine(self) -> Iterator[Engine]:
        engine = create_engine(
            self.connection_url(), pool_pre_ping=True, connect_args={"connect_timeout": 10}
        )
        try:
            yield engine
        finally:
            engine.dispose()


class HamApi(ConfigurableResource):
    """Network access and lifetime of the HAM library's in-memory cache."""

    api_key: str = ""

    def require_key(self) -> str:
        if not self.api_key.strip():
            raise Failure(
                "Set HAMAPI_API_KEY in infra/.env and recreate Dagster services",
                allow_retries=False,
            )
        return self.api_key

    def catalog(self, name: str) -> dict:
        with urlopen(f"{HAM_CATALOG_URL}/{name}.json", timeout=30) as response:
            catalog = json.load(response)
        if not isinstance(catalog, dict) or not catalog:
            raise ValueError(f"{name}.json must be a nonempty object")
        return catalog

    @contextmanager
    def _client(self) -> Iterator[hamapi.hamapi]:
        client = hamapi.hamapi(api_key=self.require_key(), cache_db_file=":memory:")
        try:
            yield client
        finally:
            client.cache_conn.close()

    def devices(self) -> dict:
        with self._client() as client:
            return client.get_user_devices(force_refresh=True)

    def readings(self, external_id: str, start: datetime, end: datetime) -> dict:
        validate_interval(start, end)
        with self._client() as client:
            # The library otherwise chooses a default server for unknown devices.
            response = client.get_user_devices(force_refresh=True)
            if (
                not isinstance(response, dict)
                or response.get("error")
                or not isinstance(response.get("devices"), list)
            ):
                raise ValueError("HAMAPI returned an invalid device response")
            if not any(
                isinstance(device, dict) and device.get("serialno") == external_id
                for device in response["devices"]
            ):
                raise ValueError("The configured API key cannot access the selected sensor")
            return client.get_datalog_data(external_id, start.timestamp(), end.timestamp())
