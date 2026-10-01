"""Shared database access for discovery and ingestion."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import URL, Engine, create_engine

from dagster import ConfigurableResource


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
