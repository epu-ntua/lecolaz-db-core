"""Discover HAM sensors and assemble the family's assets, job, and automation."""

import logging
import os

from dagster import (
    AssetSelection,
    AutomationConditionSensorDefinition,
    DefaultSensorStatus,
    Definitions,
    ExecutorDefinition,
    JobDefinition,
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


def registration_definitions(
    database: LeColazDatabase,
    ham_api: HamApi,
    executor: ExecutorDefinition | None = None,
) -> Definitions:
    """Registration is independent of database-driven observation asset discovery."""
    return Definitions(
        assets=[hamapi_observation_types, hamapi_sensors],
        jobs=[
            define_asset_job(
                "register_hamapi_sensors",
                selection=AssetSelection.assets(
                    hamapi_observation_types, hamapi_sensors
                ),
                executor_def=executor,
                description="Register accessible HAM devices and bundled model-referenced observation types.",
            )
        ],
        resources={"database": database, "ham_api": ham_api},
    )


def startup_registration_job(database: LeColazDatabase) -> JobDefinition | None:
    api_key = os.environ.get("HAMAPI_API_KEY", "")
    if not api_key.strip():
        logging.getLogger(__name__).info(
            "HAMAPI_API_KEY is missing; skipping HAM registration."
        )
        return None
    return registration_definitions(database, HamApi(api_key=api_key)).resolve_job_def(
        "register_hamapi_sensors"
    )


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
            registration_definitions(database, ham_api, executor).resolve_job_def(
                "register_hamapi_sensors"
            )
        ],
        sensors=[
            AutomationConditionSensorDefinition(
                name="hamapi_observation_automation",
                target=AssetSelection.groups("/".join(OBSERVATION_VALUES_PREFIX)),
                default_status=DefaultSensorStatus.RUNNING,
                minimum_interval_seconds=15 * 60,
                run_tags={"lecolaz/workflow": "hamapi_daily"},
                description="Ingest new UTC day partitions after the configured grace period; backfill history explicitly.",
            )
        ],
        resources={"database": database, "ham_api": ham_api},
    )
