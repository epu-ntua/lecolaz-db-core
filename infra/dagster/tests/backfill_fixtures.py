"""Offline definitions with arbitrary names and stage counts for GraphQL tests."""

from dagster import (
    AssetDep, AssetKey, BackfillPolicy, DailyPartitionsDefinition, Definitions,
    StaticPartitionsDefinition, TimeWindowPartitionMapping, asset, define_asset_job,
)

SENSOR_ID = "00000000-0000-0000-0000-000000000001"
STATIC_SENSOR_ID = "00000000-0000-0000-0000-000000000002"
UNPARTITIONED_SENSOR_ID = "00000000-0000-0000-0000-000000000003"
MIXED_SENSOR_ID = "00000000-0000-0000-0000-000000000004"
OFFSET_SENSOR_ID = "00000000-0000-0000-0000-000000000005"
KEYS = [AssetKey(["custom", stage]) for stage in ("source", "clean", "summary")]
DAYS = ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"]
DAILY = DailyPartitionsDefinition(start_date=DAYS[0], end_date="2026-01-05", timezone="UTC")


def fixture_definitions():
    assets = []
    for index, key in enumerate(KEYS):
        @asset(key=key, deps=KEYS[index - 1:index] if index else [],
               partitions_def=DAILY, metadata={"sensor_id": SENSOR_ID},
               backfill_policy=BackfillPolicy.multi_run(max_partitions_per_run=1))
        def stage():
            return 1
        assets.append(stage)

    @asset(key="arbitrary_static", partitions_def=StaticPartitionsDefinition(["z", "a", "b"]),
           metadata={"sensor_id": STATIC_SENSOR_ID})
    def static_stage():
        return 1

    @asset(key="arbitrary_unpartitioned", metadata={"sensor_id": UNPARTITIONED_SENSOR_ID})
    def unpartitioned_stage():
        return 1

    @asset(key="mixed_daily", partitions_def=DAILY, metadata={"sensor_id": MIXED_SENSOR_ID})
    def mixed_daily():
        return 1

    @asset(key="mixed_summary", deps=[mixed_daily], metadata={"sensor_id": MIXED_SENSOR_ID})
    def mixed_summary():
        return 1

    @asset(key="offset_source", partitions_def=DAILY, metadata={"sensor_id": OFFSET_SENSOR_ID})
    def offset_source():
        return 1

    @asset(key="offset_summary", partitions_def=DAILY, metadata={"sensor_id": OFFSET_SENSOR_ID},
           deps=[AssetDep(offset_source, partition_mapping=TimeWindowPartitionMapping(-1, -1))])
    def offset_summary():
        return 1

    @asset(key="unrelated_reference")
    def unrelated():
        return 1

    return Definitions(
        assets=[*assets, static_stage, unpartitioned_stage, mixed_daily, mixed_summary,
                offset_source, offset_summary, unrelated],
        jobs=[define_asset_job("fixture_job", selection=KEYS)],
    )


def registered_sensor_definitions():
    """Use both production factories; replace only their database discovery."""
    from unittest.mock import patch
    from infra.dagster.definitions import build_definitions
    from infra.dagster.ham.client import HamApi
    from infra.dagster.tests.support import CATALOG, FakeDatabase

    openmeteo = {"id": STATIC_SENSOR_ID, "name": "Weather", "external_id": "1334/564/232",
                "starting_date": CATALOG[0]["starting_date"],
                "sensor_metadata": {"observation_type_key": "5683/14"}}
    with (
        patch("infra.dagster.ham.sensors.load_sensor_catalog", return_value=CATALOG[:1]),
        patch("infra.dagster.openmeteo.catalog.load_sensor_catalog", return_value=[openmeteo]),
    ):
        return build_definitions(FakeDatabase(), HamApi())
