"""Compose registration and per-sensor raw/load assets from the stored catalog.

The host code location supplies its database snapshot, matching HAM's reload-based
catalog discovery. Building this component itself performs no external I/O.
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import yaml
from app.db.models.observation_type import ObservationType
from app.db.models.observation_value import ObservationValue
from app.db.models.sensor import Sensor
from pydantic import Field

import dagster as dg
from infra.dagster.metadata import table_metadata
from infra.dagster.openmeteo import (
    OBSERVATION_VALUES_PREFIX,
    RAW_PREFIX,
    REFERENCE_PREFIX,
    catalog,
    observations,
)
from infra.dagster.openmeteo.client import OpenMeteoApi, parse_external_id
from infra.dagster.resources import LeColazDatabase

RETRY_POLICY = dg.RetryPolicy(max_retries=3, delay=60, backoff=dg.Backoff.EXPONENTIAL)
REGISTRATION_DEFAULTS_PATH = Path(__file__).with_name("registration.yaml")
REGISTRATION_KEYS = tuple(
    dg.AssetKey([*REFERENCE_PREFIX, name]) for name in ("sensors", "observation_types")
)


def load_registration_defaults() -> list[str]:
    """Keep the editable sensor list beside the integration, not in instance config."""
    settings = yaml.safe_load(REGISTRATION_DEFAULTS_PATH.read_text(encoding="utf-8"))
    external_ids = settings.get("external_ids") if isinstance(settings, dict) else None
    if not isinstance(external_ids, list) or not external_ids:
        raise ValueError("registration.yaml must contain a nonempty external_ids list")
    for external_id in external_ids:
        parse_external_id(external_id)
    return external_ids


class RegistrationConfig(dg.Config):
    external_ids: list[str] = Field(
        default_factory=load_registration_defaults,
        description="OpenMeteo station/group/timeseries IDs to register. Replace or extend this list before launching.",
    )


@dg.multi_asset(
    specs=[
        dg.AssetSpec(
            key,
            group_name="/".join(REFERENCE_PREFIX),
            kinds={"python", "postgres"},
            description=f"OpenMeteo {model.__tablename__} registered from the configured timeseries list.",
            metadata=table_metadata(
                model.__table__,
                "sensor_family = 'openmeteo'",
                "Upsert selected source fields; preserve local fields and source-absent rows.",
            ),
        )
        for key, model in zip(REGISTRATION_KEYS, (Sensor, ObservationType))
    ],
    retry_policy=RETRY_POLICY,
)
def register_sensors(
    context: dg.AssetExecutionContext,
    config: RegistrationConfig,
    openmeteo_api: OpenMeteoApi,
    database: LeColazDatabase,
):
    """Validate the explicit selection, then commit both catalogs together."""
    sensors, types = catalog.prepare_registration(openmeteo_api, config.external_ids)
    with database.engine() as engine:
        summary = catalog.persist_registration(engine, sensors, types)
    # Both tables commit before either materialization is recorded.
    for key in REGISTRATION_KEYS:
        yield dg.MaterializeResult(
            asset_key=key,
            metadata={
                **summary.get(key.path[-1], {}),
                "external_ids": dg.MetadataValue.json(config.external_ids),
                "next_step": "Reload the lecolaz code location after manual registration.",
            },
        )


register_openmeteo_sensors = dg.define_asset_job(
    "register_openmeteo_sensors",
    selection=dg.AssetSelection.assets(register_sensors),
    description="Validate and register OpenMeteo sensors and observation types together.",
)


def registration_definitions(resources: dict | None = None) -> dg.Definitions:
    """Build registration independently of sensor discovery and other families."""
    return dg.Definitions(
        assets=[register_sensors],
        jobs=[register_openmeteo_sensors],
        resources=resources,
    )


def raw_asset_key(sensor_id: str) -> dg.AssetKey:
    return dg.AssetKey([*RAW_PREFIX, sensor_id])


def observation_asset_key(sensor_id: str) -> dg.AssetKey:
    return dg.AssetKey([*OBSERVATION_VALUES_PREFIX, sensor_id])


def make_sensor_assets(device: dict, delay_hours: int) -> list[dg.AssetsDefinition]:
    device = dict(device)
    sensor_id = str(device["id"])
    starting_date = catalog.utc_starting_date(device["starting_date"])
    type_key = catalog.observation_type_key(device)
    fingerprint = hashlib.sha256(
        json.dumps(
            [device["external_id"], starting_date.isoformat(), type_key],
        ).encode()
    ).hexdigest()
    partitions = dg.DailyPartitionsDefinition(
        start_date=starting_date.date().isoformat(), timezone="UTC"
    )
    common = {
        "partitions_def": partitions,
        "retry_policy": RETRY_POLICY,
        "backfill_policy": dg.BackfillPolicy.multi_run(max_partitions_per_run=1),
    }
    metadata = {
        "sensor_id": sensor_id,
        "sensor_name": device["name"],
        "sensor_external_id": device["external_id"],
        "observation_type_key": type_key,
        "starting_date": starting_date.isoformat(),
        "source_fingerprint": fingerprint,
        "partition_semantics": "UTC daily [start, end); first day clipped to starting_date.",
    }

    def references(database):
        with database.engine() as engine:
            try:
                return catalog.load_references(engine, device)
            except ValueError as exc:
                raise dg.Failure(str(exc), allow_retries=False) from exc

    @dg.asset(
        key=raw_asset_key(sensor_id),
        deps=REGISTRATION_KEYS,
        group_name="/".join(RAW_PREFIX),
        **common,
        io_manager_key="raw_csv_io_manager",
        kinds={"python", "s3"},
        metadata=metadata,
        automation_condition=(
            dg.AutomationCondition.on_missing()
            & dg.AutomationCondition.on_cron(
                f"0 {delay_hours} * * *", cron_timezone="UTC"
            ).ignore(dg.AssetSelection.groups("/".join(REFERENCE_PREFIX)))
            & ~dg.AutomationCondition.in_progress()
        ),
        description=(
            f"Daily raw CSV for {device['name']} ({sensor_id}); "
            f"fetched from OpenMeteo {device['external_id']} and stored unchanged "
            "in MinIO for replay."
        ),
    )
    def raw(
        context: dg.AssetExecutionContext,
        openmeteo_api: OpenMeteoApi,
        database: LeColazDatabase,
    ) -> bytes:
        sensor, _ = references(database)
        window = context.partition_time_window
        start = max(window.start, starting_date)
        data = openmeteo_api.readings(sensor["external_id"], start, window.end)
        context.add_output_metadata(
            {
                "interval_start": start.isoformat(),
                "interval_end": window.end.isoformat(),
            }
        )
        return data

    @dg.asset(
        key=observation_asset_key(sensor_id),
        group_name="/".join(OBSERVATION_VALUES_PREFIX),
        **common,
        ins={"raw_csv": dg.AssetIn(key=raw_asset_key(sensor_id))},
        kinds={"python", "postgres"},
        output_required=False,
        automation_condition=dg.AutomationCondition.eager(),
        metadata={
            **metadata,
            **table_metadata(
                ObservationValue.__table__,
                f"sensor_id = '{sensor_id}'",
                "Upsert sensor/type/timestamp values; preserve IDs and source-absent rows.",
            ),
        },
        description=(
            f"Daily observations for {device['name']} ({sensor_id}); owns only this sensor's rows. "
            f"Parses the stored OpenMeteo {device['external_id']} CSV for observation type {type_key}."
        ),
    )
    def values(
        context: dg.AssetExecutionContext, database: LeColazDatabase, raw_csv: bytes
    ):
        _, type_id = references(database)
        window = context.partition_time_window
        rows, counts = observations.prepare_rows(
            raw_csv, sensor_id, type_id, max(window.start, starting_date), window.end
        )
        if not rows:
            context.log_event(
                dg.AssetObservation(
                    asset_key=context.asset_key,
                    partition=context.partition_key,
                    metadata={**counts, "outcome": "empty"},
                )
            )
            return
        with database.engine() as engine:
            summary = observations.persist_rows(engine, rows)
        yield dg.MaterializeResult(
            metadata={
                **counts,
                **summary,
                "unchanged": summary["selected"] - summary["inserted_or_updated"],
            }
        )

    return [raw, values]


@dataclass
class OpenMeteoComponent(dg.Component):
    """Build composable definitions from the host's already-discovered sensor catalog."""

    sensors: list[dict]
    delay_hours: int = 4
    registration_resources: dict | None = None

    def build_defs(
        self, context: dg.ComponentLoadContext | None = None
    ) -> dg.Definitions:
        if type(self.delay_hours) is not int or not 0 <= self.delay_hours <= 23:
            raise ValueError(
                "OPENMETEO_INGESTION_DELAY_HOURS must be an integer from 0 to 23"
            )
        return dg.Definitions(
            assets=[
                register_sensors,
                *[
                    asset
                    for sensor in self.sensors
                    for asset in make_sensor_assets(sensor, self.delay_hours)
                ],
            ],
            jobs=[
                registration_definitions(self.registration_resources).resolve_job_def(
                    "register_openmeteo_sensors"
                )
                if self.registration_resources
                else register_openmeteo_sensors
            ],
            sensors=[
                dg.AutomationConditionSensorDefinition(
                    name="openmeteo_observation_automation",
                    target=dg.AssetSelection.groups(
                        "/".join(RAW_PREFIX), "/".join(OBSERVATION_VALUES_PREFIX)
                    ),
                    default_status=dg.DefaultSensorStatus.RUNNING,
                    minimum_interval_seconds=15 * 60,
                    run_tags={"lecolaz/workflow": "openmeteo_daily"},
                    description=(
                        "Fetch raw CSVs for new UTC day partitions after the configured "
                        "grace period and reference initialization, then load observation "
                        "values once their raw partitions are materialized; backfill "
                        "history explicitly."
                    ),
                )
            ],
        )
