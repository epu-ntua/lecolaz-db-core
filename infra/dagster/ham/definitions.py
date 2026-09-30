"""Discover HAM sensors and assemble the family's assets, job, and automation."""

from dagster import (
    AssetSelection,
    AutomationConditionSensorDefinition,
    DefaultSensorStatus,
    Definitions,
    ExecutorDefinition,
    define_asset_job,
)
from infra.dagster.ham import OBSERVATION_VALUES_PREFIX, sensors
from infra.dagster.ham.assets import (
    hamapi_observation_types,
    hamapi_sensors,
    make_observation_asset,
    observation_automation,
)
from infra.dagster.ham.client import HamApi
from infra.dagster.resources import LeColazDatabase


def build_definitions(
    database: LeColazDatabase,
    ham_api: HamApi,
    delay_hours: int = 4,
    *,
    executor: ExecutorDefinition,
) -> Definitions:
    observation_automation(delay_hours)  # Validate even when the catalog is empty.
    with (
        database.process_config_and_initialize_cm() as resolved,
        resolved.engine() as engine,
    ):
        devices = sensors.load_sensor_catalog(engine)
    return Definitions(
        assets=[
            hamapi_observation_types,
            hamapi_sensors,
            *[make_observation_asset(device, delay_hours) for device in devices],
        ],
        jobs=[
            define_asset_job(
                "hamapi_initialize",
                selection=AssetSelection.assets(hamapi_observation_types, hamapi_sensors),
                executor_def=executor,
            )
        ],
        sensors=[
            AutomationConditionSensorDefinition(
                name="hamapi_observation_automation",
                target=AssetSelection.groups("/".join(OBSERVATION_VALUES_PREFIX)),
                default_status=DefaultSensorStatus.STOPPED,
                minimum_interval_seconds=15 * 60,
                run_tags={"lecolaz/workflow": "hamapi_daily"},
                description="Ingest new UTC day partitions after the configured grace period; backfill history explicitly.",
            )
        ],
        resources={"database": database, "ham_api": ham_api},
    )
