"""Connections for catalog discovery at definition load and ingestion at execution."""

from contextlib import contextmanager

from dagster import ConfigurableResource, Failure
from sqlalchemy import URL, create_engine

from infra.dagster.ham import observation_types, observation_values, sensors


class LeColazDatabase(ConfigurableResource):
    host: str
    port: int = 5432
    database: str
    username: str
    password: str

    def connection_url(self) -> URL:
        return URL.create(
            "postgresql+psycopg", username=self.username, password=self.password,
            host=self.host, port=self.port, database=self.database,
        )

    @contextmanager
    def engine(self):
        engine = create_engine(self.connection_url(), pool_pre_ping=True,
                               connect_args={"connect_timeout": 10})
        try:
            yield engine
        finally:
            engine.dispose()


class HamApi(ConfigurableResource):
    api_key: str = ""

    def require_key(self) -> str:
        if not self.api_key.strip():
            raise Failure("Set HAMAPI_API_KEY in infra/.env and recreate Dagster services",
                          allow_retries=False)
        return self.api_key

    def catalog(self, name: str) -> dict:
        return observation_types.fetch_catalog(name)

    def devices(self) -> dict:
        return sensors.fetch_devices(self.require_key())

    def readings(self, external_id, start, end) -> dict:
        return observation_values.fetch_readings(self.require_key(), external_id, start, end)
