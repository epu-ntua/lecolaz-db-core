"""HAM table assets and local service checks for the LeColaz Dagster instance."""

import os
from urllib.request import urlopen

from dagster import (
    AssetExecutionContext, AssetKey, AssetObservation, AssetSelection, AutomationCondition,
    AutomationConditionSensorDefinition, BackfillPolicy, Backoff,
    Config, DailyPartitionsDefinition, DefaultSensorStatus, Definitions, EnvVar,
    Failure, MaterializeResult, MetadataValue, OpExecutionContext, RetryPolicy,
    asset, define_asset_job, definitions, job, multiprocess_executor, op,
)

from app.db.models.observation_type import ObservationType
from app.db.models.observation_value import ObservationValue
from app.db.models.sensor import Sensor

from infra.dagster.ham import observation_types, observation_values, sensors
from infra.dagster.metadata import measure_duration, observation_metadata, table_metadata
from infra.dagster.resources import HamApi, LeColazDatabase

RETRY_POLICY = RetryPolicy(max_retries=3, delay=60, backoff=Backoff.EXPONENTIAL)
EXECUTOR = multiprocess_executor.configured({"max_concurrent": 4})


def observation_asset_key(sensor_id: str) -> AssetKey:
    return AssetKey(["observation_values", sensor_id])


def observation_automation(delay_hours: int = 4):
    """Request new daily partitions once, after a UTC grace period and reference initialization."""
    if type(delay_hours) is not int or not 0 <= delay_hours <= 23:
        raise ValueError("HAMAPI_INGESTION_DELAY_HOURS must be an integer from 0 to 23")
    # on_missing tracks new partitions and waits for existing references. The cron
    # only adds a delay: reference assets do not need to refresh every morning.
    return (
        AutomationCondition.on_missing()
        & AutomationCondition.on_cron(f"0 {delay_hours} * * *", cron_timezone="UTC").ignore(
            AssetSelection.groups("ham/reference")
        )
        & ~AutomationCondition.in_progress()
    ).with_label("new_daily_observations_after_grace_period")


class ObservationTypesConfig(Config):
    include_extra_readings: bool = False


@asset(group_name="ham/reference", retry_policy=RETRY_POLICY, kinds={"python", "postgres"},
       metadata=table_metadata(
           ObservationType.__table__, "sensor_family = 'ham'",
           "Upsert model-referenced reading definitions; preserve IDs and rows absent from the response.",
       ),
       description="Manually synchronize HAM reading definitions referenced by device models.")
def hamapi_observation_types(config: ObservationTypesConfig, ham_api: HamApi,
                             database: LeColazDatabase):
    catalog = ham_api.catalog("readings")
    models = ham_api.catalog("models")
    keys = observation_types.collect_reading_keys(models, config.include_extra_readings)
    rows = observation_types.prepare_rows(catalog, keys)
    with database.engine() as engine:
        summary = observation_types.persist_rows(engine, rows)
    excluded = sorted(catalog.keys() - set(keys))
    return MaterializeResult(metadata={
        **summary,
        "unchanged": summary["selected"] - summary["inserted_or_updated"],
        "model_count": len(models), "catalog_reading_count": len(catalog),
        "excluded_reading_count": len(excluded),
        "excluded_reading_keys": MetadataValue.json(excluded),
        "include_extra_readings": config.include_extra_readings,
        "readings_catalog_url": MetadataValue.url(f"{observation_types.BASE_URL}/readings.json"),
        "models_catalog_url": MetadataValue.url(f"{observation_types.BASE_URL}/models.json"),
    })


@asset(group_name="ham/reference", retry_policy=RETRY_POLICY, kinds={"python", "postgres"},
       metadata=table_metadata(
           Sensor.__table__, "sensor_family = 'ham'",
           "Upsert source-owned device fields; preserve IDs, local fields, and source-absent devices.",
       ),
       description="Manually synchronize devices accessible to HAMAPI_API_KEY.")
def hamapi_sensors(context: AssetExecutionContext, ham_api: HamApi, database: LeColazDatabase):
    timings = {}
    with measure_duration(timings, "fetch_seconds"):
        response = ham_api.devices()
    with measure_duration(timings, "prepare_seconds"):
        rows = sensors.prepare_sensor_rows(response)
    with database.engine() as engine:
        with measure_duration(timings, "persist_seconds"):
            summary = sensors.persist_sensor_rows(engine, rows)
    return MaterializeResult(metadata={
        **summary, **timings,
        "unchanged": summary["selected"] - summary["inserted_or_updated"],
        "next_step": "Reload the lecolaz code location to discover new physical sensors.",
    })


def make_observation_asset(device: dict, delay_hours: int = 4):
    """One stable logical table subset per physical sensor; no generated Python files."""
    sensor_id = device["id"]
    starting_date = sensors.utc_starting_date(device["starting_date"])
    partitions = DailyPartitionsDefinition(
        start_date=starting_date.date().isoformat(), timezone="UTC",
    )

    @asset(
        key=observation_asset_key(sensor_id), group_name="ham/observations",
        partitions_def=partitions, retry_policy=RETRY_POLICY, kinds={"python", "postgres"},
        output_required=False,
        automation_condition=observation_automation(delay_hours),
        deps=[hamapi_observation_types, hamapi_sensors],
        backfill_policy=BackfillPolicy.multi_run(max_partitions_per_run=1),
        metadata={
            **table_metadata(
                ObservationValue.__table__, f"sensor_id = '{sensor_id}'",
                "Upsert sensor/type/timestamp values; preserve IDs and rows absent from the response.",
            ),
            "partition_semantics": "UTC daily [start, end); first interval clipped to sensor starting_date.",
            "sensor_id": sensor_id, "sensor_name": device["name"],
            "starting_date": starting_date.isoformat(), "physical_table": "observation_values",
        },
        description=f"Daily observations for {device['name']} ({sensor_id}); owns only this sensor's rows.",
    )
    def observations(context: AssetExecutionContext, ham_api: HamApi, database: LeColazDatabase):
        day = str(context.partition_key)
        window = partitions.time_window_for_partition_key(day)
        timings = {}
        with database.engine() as engine:
            try:
                with measure_duration(timings, "reference_lookup_seconds"):
                    references = observation_values.load_references(engine, sensor_id=sensor_id)
            except sensors.SensorUnavailable as exc:
                raise Failure(str(exc), allow_retries=False) from exc
            selected = references["sensors"][0]
            if sensors.utc_starting_date(selected["starting_date"]) != starting_date:
                raise Failure("Sensor starting_date changed; reload the lecolaz code location before retrying",
                              allow_retries=False)
            start = max(window.start, starting_date)
            if start >= window.end:
                raise Failure("Partition predates the physical sensor's starting_date", allow_retries=False)
            with measure_duration(timings, "fetch_seconds"):
                response = ham_api.readings(selected["external_id"], start, window.end)
            with measure_duration(timings, "prepare_seconds"):
                prepared = observation_values.prepare_observation_rows(
                    response, selected, references["types"], start, window.end,
                )
            metadata = {
                **observation_metadata(prepared),
                "day": day, "sensor_id": sensor_id, "external_id": selected["external_id"],
                "interval_start": start.isoformat(), "interval_end": window.end.isoformat(),
                "interval_duration_seconds": (window.end - start).total_seconds(),
            }
            if not prepared.rows:
                context.log.warning(
                    "No valid observations for sensor_id=%s day=%s interval=[%s, %s); "
                    "no materialization emitted. Existing data and history are unchanged.",
                    sensor_id, day, start.isoformat(), window.end.isoformat(),
                )
                context.log_event(AssetObservation(
                    asset_key=context.asset_key, partition=day,
                    metadata={**metadata, **timings, "outcome": "empty", "selected": 0},
                ))
                return
            with measure_duration(timings, "persist_seconds"):
                summary = observation_values.persist_observation_rows(engine, prepared.rows)
        unchanged = summary["selected"] - summary["inserted_or_updated"]
        if unchanged:
            context.log.warning(
                "Observations already present with identical values for sensor_id=%s day=%s "
                "interval=[%s, %s): selected=%s inserted_or_updated=%s unchanged=%s. "
                "Synchronization completed; emitting a materialization to record the populated partition.",
                sensor_id, day, start.isoformat(), window.end.isoformat(),
                summary["selected"], summary["inserted_or_updated"], unchanged,
            )
        yield MaterializeResult(metadata={
            **metadata, **timings, **summary, "unchanged": unchanged,
        })

    return observations


hamapi_initialize = define_asset_job(
    "hamapi_initialize", selection=AssetSelection.assets(hamapi_observation_types, hamapi_sensors),
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


def configured_database():
    return LeColazDatabase(
        host=EnvVar("LECOLAZ_POSTGRES_HOST"), port=EnvVar.int("LECOLAZ_POSTGRES_PORT"),
        database=EnvVar("LECOLAZ_POSTGRES_DB"), username=EnvVar("LECOLAZ_POSTGRES_USER"),
        password=EnvVar("LECOLAZ_POSTGRES_PASSWORD"),
    )


def build_definitions(database: LeColazDatabase, ham_api: HamApi, delay_hours: int = 4) -> Definitions:
    # Read PostgreSQL at definition load, never at plain module import. Fail visibly on
    # connection/schema errors rather than silently publishing an empty asset catalog.
    with database.process_config_and_initialize_cm() as resolved, resolved.engine() as engine:
        devices = sensors.load_sensor_catalog(engine)
    observation_automation(delay_hours)  # Validate configuration even with an empty catalog.
    observation_assets = [make_observation_asset(device, delay_hours) for device in devices]
    return Definitions(
        assets=[hamapi_observation_types, hamapi_sensors, *observation_assets],
        jobs=[hamapi_initialize, lecolaz_services_smoke_test],
        sensors=[AutomationConditionSensorDefinition(
            name="hamapi_observation_automation",
            target=AssetSelection.groups("ham/observations"),
            default_status=DefaultSensorStatus.STOPPED,
            minimum_interval_seconds=15 * 60,
            run_tags={"lecolaz/workflow": "hamapi_daily"},
            description="Ingest new UTC day partitions after the configured grace period; backfill history explicitly.",
        )],
        resources={"database": database, "ham_api": ham_api}, executor=EXECUTOR,
    )


@definitions
def defs():
    return build_definitions(
        configured_database(), HamApi(api_key=EnvVar("HAMAPI_API_KEY")),
        delay_hours=int(os.environ.get("HAMAPI_INGESTION_DELAY_HOURS", "4")),
    )
