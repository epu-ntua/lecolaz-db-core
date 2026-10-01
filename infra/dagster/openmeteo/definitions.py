"""Discover OpenMeteo sensors and wire the family's component and resources."""

from dagster import Definitions, JobDefinition
from infra.dagster.object_storage import S3BytesIOManager
from infra.dagster.openmeteo import catalog
from infra.dagster.openmeteo.client import OpenMeteoApi
from infra.dagster.openmeteo.component import (
    OpenMeteoComponent,
    registration_definitions,
)
from infra.dagster.resources import LeColazDatabase


def startup_registration_job(database: LeColazDatabase) -> JobDefinition:
    return registration_definitions(
        {"database": database, "openmeteo_api": OpenMeteoApi()}
    ).resolve_job_def("register_openmeteo_sensors")


def build_definitions(
    database: LeColazDatabase,
    openmeteo_api: OpenMeteoApi,
    raw_csv_io_manager: S3BytesIOManager,
    delay_hours: int = 4,
) -> Definitions:
    with (
        database.process_config_and_initialize_cm() as resolved,
        resolved.engine() as engine,
    ):
        devices = catalog.load_sensor_catalog(engine)
    resources = {"database": database, "openmeteo_api": openmeteo_api}
    return Definitions.merge(
        OpenMeteoComponent(
            devices, delay_hours, registration_resources=resources
        ).build_defs(),
        Definitions(resources={**resources, "raw_csv_io_manager": raw_csv_io_manager}),
    )
