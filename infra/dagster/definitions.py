"""Assemble the code location from database-discovered sensors."""

import os
from urllib.request import urlopen

from dagster import (
    Backoff,
    Definitions,
    EnvVar,
    OpExecutionContext,
    RetryPolicy,
    definitions,
    job,
    multiprocess_executor,
    op,
)
from infra.dagster.ham.client import HamApi
from infra.dagster.ham.definitions import build_definitions as build_ham_definitions
from infra.dagster.object_storage import S3BytesIOManager
from infra.dagster.openmeteo.client import OpenMeteoApi
from infra.dagster.openmeteo.definitions import (
    build_definitions as build_openmeteo_definitions,
)
from infra.dagster.resources import LeColazDatabase

EXECUTOR = multiprocess_executor.configured({"max_concurrent": 4})


@op(
    config_schema={"url": str},
    retry_policy=RetryPolicy(max_retries=3, delay=60, backoff=Backoff.EXPONENTIAL),
)
def check_service(context: OpExecutionContext) -> dict:
    with urlopen(context.op_config["url"], timeout=10) as response:
        return {"status": response.status}


@job(executor_def=EXECUTOR)
def lecolaz_services_smoke_test():
    check_service.configured(
        {"url": "http://backend:8000/health"}, name="check_backend"
    )()
    check_service.configured(
        {"url": "http://minio:9000/minio/health/live"}, name="check_minio"
    )()


def configured_database() -> LeColazDatabase:
    return LeColazDatabase(
        host=EnvVar("LECOLAZ_POSTGRES_HOST"),
        port=EnvVar.int("LECOLAZ_POSTGRES_PORT"),
        database=EnvVar("LECOLAZ_POSTGRES_DB"),
        username=EnvVar("LECOLAZ_POSTGRES_USER"),
        password=EnvVar("LECOLAZ_POSTGRES_PASSWORD"),
    )


def build_definitions(
    database: LeColazDatabase,
    ham_api: HamApi,
    delay_hours: int = 4,
    *,
    openmeteo_api: OpenMeteoApi | None = None,
    raw_csv_io_manager: S3BytesIOManager | None = None,
    ham_raw_io_manager: S3BytesIOManager | None = None,
    openmeteo_delay_hours: int = 4,
) -> Definitions:
    # Family loaders discover their catalogs here, never at module import.
    # Discovery failures propagate instead of publishing an incomplete code location.
    return Definitions.merge(
        build_ham_definitions(
            database, ham_api, delay_hours,
            executor=EXECUTOR, raw_io_manager=ham_raw_io_manager,
        ),
        build_openmeteo_definitions(
            database,
            openmeteo_api or OpenMeteoApi(),
            raw_csv_io_manager or S3BytesIOManager(),
            openmeteo_delay_hours,
        ),
        Definitions(jobs=[lecolaz_services_smoke_test], executor=EXECUTOR),
    )


@definitions
def defs() -> Definitions:
    return build_definitions(
        configured_database(),
        HamApi(api_key=EnvVar("HAMAPI_API_KEY")),
        delay_hours=int(os.environ.get("HAMAPI_INGESTION_DELAY_HOURS", "4")),
        openmeteo_delay_hours=int(
            os.environ.get("OPENMETEO_INGESTION_DELAY_HOURS", "4")
        ),
    )
