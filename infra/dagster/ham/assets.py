"""HAM reference imports and daily raw/load asset pairs per physical sensor."""

import hashlib
import json
from collections.abc import Iterator
from dataclasses import dataclass
from importlib.metadata import version

from app.db.models.observation_type import ObservationType
from app.db.models.observation_value import ObservationValue
from app.db.models.sensor import Sensor

from dagster import (
    AssetExecutionContext,
    AssetIn,
    AssetKey,
    AssetObservation,
    AssetsDefinition,
    AssetSelection,
    AutomationCondition,
    BackfillPolicy,
    Backoff,
    Component,
    ComponentLoadContext,
    Config,
    DailyPartitionsDefinition,
    Definitions,
    Failure,
    MaterializeResult,
    MetadataValue,
    RetryPolicy,
    asset,
)
from infra.dagster.ham import (
    OBSERVATION_VALUES_PREFIX,
    RAW_PREFIX,
    REFERENCE_PREFIX,
    observation_types,
    observation_values,
    sensors,
)
from infra.dagster.ham.client import HamApi
from infra.dagster.ham.datalog import MissingDatalogError, parse_datalog, validate_datalog
from infra.dagster.ham.metadata import observation_metadata
from infra.dagster.metadata import (
    measure_duration,
    table_metadata,
)
from infra.dagster.resources import LeColazDatabase

RETRY_POLICY = RetryPolicy(max_retries=3, delay=60, backoff=Backoff.EXPONENTIAL)


def observation_asset_key(sensor_id: str) -> AssetKey:
    return AssetKey([*OBSERVATION_VALUES_PREFIX, sensor_id])


def raw_asset_key(sensor_id: str) -> AssetKey:
    return AssetKey([*RAW_PREFIX, sensor_id])


def observation_automation(delay_hours: int = 4) -> AutomationCondition:
    """Request new daily partitions once, after a UTC grace period and reference initialization."""
    if type(delay_hours) is not int or not 0 <= delay_hours <= 23:
        raise ValueError("HAMAPI_INGESTION_DELAY_HOURS must be an integer from 0 to 23")
    # on_missing tracks new partitions and waits for existing references. The cron
    # only adds a delay: reference assets do not need to refresh every morning.
    return (
        AutomationCondition.on_missing()
        & AutomationCondition.on_cron(f"0 {delay_hours} * * *", cron_timezone="UTC").ignore(
            AssetSelection.groups("/".join(REFERENCE_PREFIX))
        )
        & ~AutomationCondition.in_progress()
    ).with_label("new_daily_observations_after_grace_period")


class ObservationTypesConfig(Config):
    include_extra_readings: bool = False


@asset(
    key=AssetKey([*REFERENCE_PREFIX, "observation_types"]),
    group_name="/".join(REFERENCE_PREFIX),
    retry_policy=RETRY_POLICY,
    kinds={"python", "postgres"},
    metadata=table_metadata(
        ObservationType.__table__,
        "sensor_family = 'ham'",
        "Upsert model-referenced reading definitions; preserve IDs and rows absent from the response.",
    ),
    description="Register HAM reading definitions referenced by the bundled device models.",
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
            "readings_catalog": "hamapi/readings.json",
            "models_catalog": "hamapi/models.json",
            "hamapi_version": version("hamapi"),
        }
    )


@asset(
    key=AssetKey([*REFERENCE_PREFIX, "sensors"]),
    group_name="/".join(REFERENCE_PREFIX),
    retry_policy=RETRY_POLICY,
    kinds={"python", "postgres"},
    metadata=table_metadata(
        Sensor.__table__,
        "sensor_family = 'ham'",
        "Upsert source-owned device fields; preserve IDs, local fields, and source-absent devices.",
    ),
    description="Register devices accessible to HAMAPI_API_KEY; preserve locally managed fields.",
)
def hamapi_sensors(ham_api: HamApi, database: LeColazDatabase) -> MaterializeResult:
    timings = {}
    with measure_duration(timings, "fetch_seconds"):
        response = ham_api.devices()
    with measure_duration(timings, "prepare_seconds"):
        rows = sensors.prepare_sensor_rows(response)
    with database.engine() as engine, measure_duration(timings, "persist_seconds"):
        summary = sensors.persist_sensor_rows(engine, rows)
    return MaterializeResult(
        metadata={
            **summary,
            **timings,
            "unchanged": summary["selected"] - summary["inserted_or_updated"],
            "next_step": "Reload the lecolaz code location to discover new physical sensors.",
        }
    )


def make_sensor_assets(device: dict, delay_hours: int = 4) -> list[AssetsDefinition]:
    """Validate and persist source bytes before conversion; load-only runs never fetch."""
    device = dict(device)
    sensor_id = device["id"]
    starting_date = sensors.utc_starting_date(device["starting_date"])
    partitions = DailyPartitionsDefinition(
        start_date=starting_date.date().isoformat(),
        timezone="UTC",
    )
    metadata = {
        "sensor_id": sensor_id,
        "sensor_name": device["name"],
        "sensor_external_id": device["external_id"],
        "starting_date": starting_date.isoformat(),
        "source_fingerprint": hashlib.sha256(
            json.dumps([device["external_id"], starting_date.isoformat()]).encode()
        ).hexdigest(),
        "partition_semantics": "UTC daily [start, end); first interval clipped to sensor starting_date.",
    }

    @asset(
        key=raw_asset_key(sensor_id),
        group_name="/".join(RAW_PREFIX),
        partitions_def=partitions,
        retry_policy=RETRY_POLICY,
        kinds={"python", "s3"},
        io_manager_key="ham_raw_io_manager",
        automation_condition=observation_automation(delay_hours),
        deps=[hamapi_observation_types, hamapi_sensors],
        backfill_policy=BackfillPolicy.multi_run(max_partitions_per_run=1),
        metadata=metadata,
        description=f"Daily unparsed HAM datalog for {device['name']} ({sensor_id}), stored unchanged in MinIO for replay.",
    )
    def raw(
        context: AssetExecutionContext,
        ham_api: HamApi,
        database: LeColazDatabase,
    ) -> bytes:
        timings = {}
        with database.engine() as engine:
            selected, _ = _load_references(engine, device)
        window = context.partition_time_window
        start = max(window.start, starting_date)
        with measure_duration(timings, "fetch_seconds"):
            payload = ham_api.readings(selected["external_id"], start, window.end)
        with measure_duration(timings, "validation_seconds"):
            try:
                source_rows = validate_datalog(payload, selected["external_id"])
            except ValueError as exc:
                raise Failure(
                    f"Invalid HAM datalog response: {exc}. No raw payload was stored.",
                    allow_retries=False,
                ) from exc
        context.add_output_metadata(
            {
                **timings,
                "source_row_count": source_rows,
                "interval_start": start.isoformat(),
                "interval_end": window.end.isoformat(),
                "datalog_bin": f"0.{int(window.start.timestamp()) // 86400}",
            }
        )
        return payload

    @asset(
        key=observation_asset_key(sensor_id),
        group_name="/".join(OBSERVATION_VALUES_PREFIX),
        partitions_def=partitions,
        retry_policy=RETRY_POLICY,
        kinds={"python", "postgres"},
        output_required=False,
        automation_condition=AutomationCondition.eager(),
        ins={"raw_datalog": AssetIn(key=raw_asset_key(sensor_id))},
        backfill_policy=BackfillPolicy.multi_run(max_partitions_per_run=1),
        metadata={
            **metadata,
            **table_metadata(
                ObservationValue.__table__,
                f"sensor_id = '{sensor_id}'",
                "Upsert sensor/type/timestamp values; preserve IDs and rows absent from the response.",
            ),
            "physical_table": "observation_values",
        },
        description=f"Daily observations for {device['name']} ({sensor_id}); parses its stored HAM datalog using model column definitions.",
    )
    def observations(
        context: AssetExecutionContext,
        database: LeColazDatabase,
        raw_datalog: bytes,
    ) -> Iterator[MaterializeResult]:
        yield from _import_observations(context, database, device, raw_datalog)

    return [raw, observations]


def _load_references(engine, device: dict) -> tuple[dict, dict]:
    try:
        selected, types = observation_values.load_references(engine, device["id"])
    except sensors.SensorUnavailable as exc:
        raise Failure(str(exc), allow_retries=False) from exc
    for field in ("starting_date", "external_id"):
        if selected[field] != device[field]:
            raise Failure(
                f"Sensor {field} changed; reload the lecolaz code location before retrying",
                allow_retries=False,
            )
    return selected, types


def _import_observations(
    context: AssetExecutionContext,
    database: LeColazDatabase,
    device: dict,
    raw_datalog: bytes,
) -> Iterator[MaterializeResult]:
    """Synchronize one interval, then report it only after a successful commit."""
    day = str(context.partition_key)
    window = context.partition_time_window
    timings = {}
    sensor_id = device["id"]
    starting_date = sensors.utc_starting_date(device["starting_date"])
    with database.engine() as engine:
        with measure_duration(timings, "reference_lookup_seconds"):
            selected, types = _load_references(engine, device)
        start = max(window.start, starting_date)
        if start >= window.end:
            raise Failure(
                "Partition predates the physical sensor's starting_date", allow_retries=False
            )
        with measure_duration(timings, "prepare_seconds"):
            try:
                response = parse_datalog(raw_datalog, selected["external_id"])
                prepared = observation_values.prepare_observation_rows(
                    response, selected, types, start, window.end
                )
            except MissingDatalogError as exc:
                raise Failure(str(exc), allow_retries=False) from exc
            except ValueError as exc:
                raise Failure(
                    f"{exc}. Raw datalog is retained; correct the parser/schema and rematerialize only observation_values.",
                    allow_retries=False,
                ) from exc
        skipped = prepared.diagnostics["out_of_interval_timestamp_count"]
        if skipped:
            context.log.warning(
                "HAM out-of-window readings: sensor_id=%s external_id=%s day=%s "
                "interval=[%s, %s); skipped_source_rows=%s. Raw datalog is retained.",
                sensor_id, selected["external_id"], day,
                start.isoformat(), window.end.isoformat(), skipped,
            )
        for conflict in prepared.conflicts:
            context.log.warning(
                "HAM conflicting non-missing readings: sensor_id=%s external_id=%s day=%s "
                "timestamp=%s reading=%s values=%s selected_value=%s; "
                "the last non-missing source value wins. Raw datalog is retained; "
                "selection does not establish measurement accuracy.",
                sensor_id, selected["external_id"], day, conflict["timestamp"].isoformat(),
                conflict["reading_key"], conflict["values"], conflict["selected_value"],
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


@dataclass
class HamComponent(Component):
    """Build raw/load assets from the host's already-discovered HAM catalog."""

    sensors: list[dict]
    delay_hours: int = 4

    def build_defs(self, context: ComponentLoadContext | None = None) -> Definitions:
        observation_automation(self.delay_hours)
        return Definitions(
            assets=[
                hamapi_observation_types,
                hamapi_sensors,
                *[
                    asset
                    for device in self.sensors
                    for asset in make_sensor_assets(device, self.delay_hours)
                ],
            ]
        )
