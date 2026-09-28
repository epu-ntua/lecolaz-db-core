"""Assemble the code location from database-discovered HAM sensors."""

import os
from urllib.request import urlopen

from dagster import (
    AssetSelection,
    AutomationConditionSensorDefinition,
    DefaultSensorStatus,
    Definitions,
    EnvVar,
    OpExecutionContext,
    define_asset_job,
    definitions,
    job,
    multiprocess_executor,
    op,
)

# Keep the existing asset imports available to code-location consumers.
from infra.dagster.assets import (
    RETRY_POLICY,
    ObservationTypesConfig as ObservationTypesConfig,
    hamapi_observation_types,
    hamapi_sensors,
    make_observation_asset,
    observation_asset_key as observation_asset_key,
    observation_automation,
)
from infra.dagster.ham import sensors
from infra.dagster.resources import HamApi, LeColazDatabase

EXECUTOR = multiprocess_executor.configured({"max_concurrent": 4})


hamapi_initialize = define_asset_job(
    "hamapi_initialize",
    selection=AssetSelection.assets(hamapi_observation_types, hamapi_sensors),
    executor_def=EXECUTOR,
)


@op(config_schema={"url": str}, retry_policy=RETRY_POLICY)
def check_service(context: OpExecutionContext) -> dict:
    with urlopen(context.op_config["url"], timeout=10) as response:
        return {"status": response.status}


@job(executor_def=EXECUTOR)
def lecolaz_services_smoke_test():
    check_service.configured({"url": "http://backend:8000/health"}, name="check_backend")()
    check_service.configured({"url": "http://minio:9000/minio/health/live"}, name="check_minio")()


def configured_database() -> LeColazDatabase:
    return LeColazDatabase(
        host=EnvVar("LECOLAZ_POSTGRES_HOST"),
        port=EnvVar.int("LECOLAZ_POSTGRES_PORT"),
        database=EnvVar("LECOLAZ_POSTGRES_DB"),
        username=EnvVar("LECOLAZ_POSTGRES_USER"),
        password=EnvVar("LECOLAZ_POSTGRES_PASSWORD"),
    )


def build_definitions(
    database: LeColazDatabase, ham_api: HamApi, delay_hours: int = 4
) -> Definitions:
    # Read PostgreSQL at definition load, never at plain module import. Fail visibly on
    # connection/schema errors rather than silently publishing an empty asset catalog.
    observation_automation(delay_hours)  # Validate even when the catalog is empty.
    with database.process_config_and_initialize_cm() as resolved, resolved.engine() as engine:
        devices = sensors.load_sensor_catalog(engine)
    observation_assets = [make_observation_asset(device, delay_hours) for device in devices]
    return Definitions(
        assets=[hamapi_observation_types, hamapi_sensors, *observation_assets],
        jobs=[hamapi_initialize, lecolaz_services_smoke_test],
        sensors=[
            AutomationConditionSensorDefinition(
                name="hamapi_observation_automation",
                target=AssetSelection.groups("ham/observations"),
                default_status=DefaultSensorStatus.STOPPED,
                minimum_interval_seconds=15 * 60,
                run_tags={"lecolaz/workflow": "hamapi_daily"},
                description="Ingest new UTC day partitions after the configured grace period; backfill history explicitly.",
            )
        ],
        resources={"database": database, "ham_api": ham_api},
        executor=EXECUTOR,
    )


@definitions
def defs() -> Definitions:
    return build_definitions(
        configured_database(),
        HamApi(api_key=EnvVar("HAMAPI_API_KEY")),
        delay_hours=int(os.environ.get("HAMAPI_INGESTION_DELAY_HOURS", "4")),
    )
