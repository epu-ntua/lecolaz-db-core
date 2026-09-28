"""HAM assets: reference imports and one daily observation asset per physical sensor."""

from collections.abc import Iterator
from datetime import datetime

from dagster import (
    AssetExecutionContext,
    AssetKey,
    AssetObservation,
    AssetsDefinition,
    AssetSelection,
    AutomationCondition,
    BackfillPolicy,
    Backoff,
    Config,
    DailyPartitionsDefinition,
    Failure,
    MaterializeResult,
    MetadataValue,
    RetryPolicy,
    asset,
)

from app.db.models.observation_type import ObservationType
from app.db.models.observation_value import ObservationValue
from app.db.models.sensor import Sensor
from infra.dagster.ham import observation_types, observation_values, sensors
from infra.dagster.metadata import (
    measure_duration,
    observation_metadata,
    table_metadata,
)
from infra.dagster.resources import HAM_CATALOG_URL, HamApi, LeColazDatabase

RETRY_POLICY = RetryPolicy(max_retries=3, delay=60, backoff=Backoff.EXPONENTIAL)


def observation_asset_key(sensor_id: str) -> AssetKey:
    return AssetKey(["observation_values", sensor_id])


def observation_automation(delay_hours: int = 4) -> AutomationCondition:
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


@asset(
    group_name="ham/reference",
    retry_policy=RETRY_POLICY,
    kinds={"python", "postgres"},
    metadata=table_metadata(
        ObservationType.__table__,
        "sensor_family = 'ham'",
        "Upsert model-referenced reading definitions; preserve IDs and rows absent from the response.",
    ),
    description="Manually synchronize HAM reading definitions referenced by device models.",
)
def hamapi_observation_types(
    config: ObservationTypesConfig, ham_api: HamApi, database: LeColazDatabase
) -> MaterializeResult:
    catalog = ham_api.catalog("readings")
    models = ham_api.catalog("models")
    keys = observation_types.collect_reading_keys(models, config.include_extra_readings)
    rows = observation_types.prepare_rows(catalog, keys)
    with database.engine() as engine:
        summary = observation_types.persist_rows(engine, rows)
    excluded = sorted(catalog.keys() - set(keys))
    return MaterializeResult(
        metadata={
            **summary,
            "unchanged": summary["selected"] - summary["inserted_or_updated"],
            "model_count": len(models),
            "catalog_reading_count": len(catalog),
            "excluded_reading_count": len(excluded),
            "excluded_reading_keys": MetadataValue.json(excluded),
            "include_extra_readings": config.include_extra_readings,
            "readings_catalog_url": MetadataValue.url(f"{HAM_CATALOG_URL}/readings.json"),
            "models_catalog_url": MetadataValue.url(f"{HAM_CATALOG_URL}/models.json"),
        }
    )


@asset(
    group_name="ham/reference",
    retry_policy=RETRY_POLICY,
    kinds={"python", "postgres"},
    metadata=table_metadata(
        Sensor.__table__,
        "sensor_family = 'ham'",
        "Upsert source-owned device fields; preserve IDs, local fields, and source-absent devices.",
    ),
    description="Manually synchronize devices accessible to HAMAPI_API_KEY.",
)
def hamapi_sensors(ham_api: HamApi, database: LeColazDatabase) -> MaterializeResult:
    timings = {}
    with measure_duration(timings, "fetch_seconds"):
        response = ham_api.devices()
    with measure_duration(timings, "prepare_seconds"):
        rows = sensors.prepare_sensor_rows(response)
    with database.engine() as engine:
        with measure_duration(timings, "persist_seconds"):
            summary = sensors.persist_sensor_rows(engine, rows)
    return MaterializeResult(
        metadata={
            **summary,
            **timings,
            "unchanged": summary["selected"] - summary["inserted_or_updated"],
            "next_step": "Reload the lecolaz code location to discover new physical sensors.",
        }
    )


def make_observation_asset(device: dict, delay_hours: int = 4) -> AssetsDefinition:
    """One stable logical table subset per physical sensor; no generated Python files."""
    sensor_id = device["id"]
    starting_date = sensors.utc_starting_date(device["starting_date"])
    partitions = DailyPartitionsDefinition(
        start_date=starting_date.date().isoformat(),
        timezone="UTC",
    )

    @asset(
        key=observation_asset_key(sensor_id),
        group_name="ham/observations",
        partitions_def=partitions,
        retry_policy=RETRY_POLICY,
        kinds={"python", "postgres"},
        output_required=False,
        automation_condition=observation_automation(delay_hours),
        deps=[hamapi_observation_types, hamapi_sensors],
        backfill_policy=BackfillPolicy.multi_run(max_partitions_per_run=1),
        metadata={
            **table_metadata(
                ObservationValue.__table__,
                f"sensor_id = '{sensor_id}'",
                "Upsert sensor/type/timestamp values; preserve IDs and rows absent from the response.",
            ),
            "partition_semantics": "UTC daily [start, end); first interval clipped to sensor starting_date.",
            "sensor_id": sensor_id,
            "sensor_name": device["name"],
            "sensor_external_id": device["external_id"],
            "starting_date": starting_date.isoformat(),
            "physical_table": "observation_values",
        },
        description=f"Daily observations for {device['name']} ({sensor_id}); owns only this sensor's rows.",
    )
    def observations(
        context: AssetExecutionContext,
        ham_api: HamApi,
        database: LeColazDatabase,
    ) -> Iterator[MaterializeResult]:
        yield from _import_observations(context, ham_api, database, sensor_id, starting_date)

    return observations


def _import_observations(
    context: AssetExecutionContext,
    ham_api: HamApi,
    database: LeColazDatabase,
    sensor_id: str,
    starting_date: datetime,
) -> Iterator[MaterializeResult]:
    """Synchronize one interval, then report it only after a successful commit."""
    day = str(context.partition_key)
    window = context.partition_time_window
    timings = {}
    with database.engine() as engine:
        try:
            with measure_duration(timings, "reference_lookup_seconds"):
                selected, types = observation_values.load_references(engine, sensor_id)
        except sensors.SensorUnavailable as exc:
            raise Failure(str(exc), allow_retries=False) from exc
        if sensors.utc_starting_date(selected["starting_date"]) != starting_date:
            raise Failure(
                "Sensor starting_date changed; reload the lecolaz code location before retrying",
                allow_retries=False,
            )
        start = max(window.start, starting_date)
        if start >= window.end:
            raise Failure(
                "Partition predates the physical sensor's starting_date", allow_retries=False
            )
        with measure_duration(timings, "fetch_seconds"):
            response = ham_api.readings(selected["external_id"], start, window.end)
        with measure_duration(timings, "prepare_seconds"):
            prepared = observation_values.prepare_observation_rows(
                response,
                selected,
                types,
                start,
                window.end,
            )
        metadata = {
            **observation_metadata(prepared),
            "day": day,
            "interval_start": start.isoformat(),
            "interval_end": window.end.isoformat(),
            "interval_duration_seconds": (window.end - start).total_seconds(),
        }
        if not prepared.rows:
            context.log.warning(
                "No valid observations for sensor_id=%s day=%s interval=[%s, %s); "
                "no materialization emitted. Existing data and history are unchanged.",
                sensor_id,
                day,
                start.isoformat(),
                window.end.isoformat(),
            )
            context.log_event(
                AssetObservation(
                    asset_key=context.asset_key,
                    partition=day,
                    metadata={**metadata, **timings, "outcome": "empty", "selected": 0},
                )
            )
            return
        with measure_duration(timings, "persist_seconds"):
            summary = observation_values.persist_observation_rows(engine, prepared.rows)
    unchanged = summary["selected"] - summary["inserted_or_updated"]
    if unchanged:
        context.log.warning(
            "Observations already present with identical values for sensor_id=%s day=%s "
            "interval=[%s, %s): selected=%s inserted_or_updated=%s unchanged=%s. "
            "Synchronization completed; emitting a materialization to record the populated partition.",
            sensor_id,
            day,
            start.isoformat(),
            window.end.isoformat(),
            summary["selected"],
            summary["inserted_or_updated"],
            unchanged,
        )
    yield MaterializeResult(
        metadata={
            **metadata,
            **timings,
            **summary,
            "unchanged": unchanged,
        }
    )
