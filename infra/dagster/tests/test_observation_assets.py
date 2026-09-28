"""Observation run outcomes: intervals, retries, commits, and Dagster history."""

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from dagster import (
    DagsterInstance,
    ResourceDefinition,
    RetryPolicy,
    TableMetadataValue,
    TimestampMetadataValue,
    materialize,
)

from infra.dagster import assets as pipeline
from infra.dagster.ham import observation_values, sensors
from infra.dagster.tests.support import CATALOG, DEVICE_IDS, FakeDatabase, StubHamApi


class ObservationExecutionTests(unittest.TestCase):
    def setUp(self):
        self.sensor_ids = DEVICE_IDS
        self.type_id = "00000000-0000-0000-0000-000000000003"
        self.sensors = [
            {
                "id": sensor_id,
                "external_id": f"device:{i}",
                "starting_date": CATALOG[i]["starting_date"],
            }
            for i, sensor_id in enumerate(DEVICE_IDS)
        ]
        self.types = {"T": self.type_id}
        self.start = CATALOG[0]["starting_date"]
        self.instance = DagsterInstance.ephemeral()
        self.addCleanup(self.instance.dispose)

    def execute(self, read, sensor_index=0, day="2026-01-01", instance=None, changed=None):
        asset = pipeline.make_observation_asset(CATALOG[sensor_index])
        references = (self.sensors[sensor_index], self.types)
        api = StubHamApi(readings=read)

        written_batches = []

        def persist_rows(engine, rows):
            written_batches.append(rows)
            return {
                "selected": len(rows),
                "inserted_or_updated": len(rows) if changed is None else changed,
            }

        with (
            patch.object(observation_values, "load_references", return_value=references),
            patch.object(observation_values, "persist_observation_rows", persist_rows),
            patch.object(RetryPolicy, "calculate_delay", return_value=0),
        ):
            result = materialize(
                [asset],
                partition_key=day,
                resources={
                    "ham_api": ResourceDefinition.hardcoded_resource(api),
                    "database": FakeDatabase(),
                },
                instance=instance or self.instance,
                raise_on_error=False,
            )
        return result, written_batches

    def test_partition_boundaries_and_only_selected_sensor(self):
        intervals = []

        def read(external_id, start, end):
            self.assertEqual(external_id, "device:0")
            intervals.append((start, end))
            return {"timestamp": [start.timestamp(), end.timestamp()], "T": [21, 22]}

        result, writes = self.execute(read)
        self.assertTrue(result.success)
        self.assertEqual(len(writes), 1)
        self.assertEqual(intervals[0][0], CATALOG[0]["starting_date"])
        self.assertEqual((intervals[0][1] - intervals[0][0]).total_seconds(), 10 * 3600)
        event = result.get_asset_materialization_events()[0].event_specific_data.materialization
        self.assertEqual(event.partition, "2026-01-01")
        self.assertEqual(event.metadata["selected"].value, 1)
        self.assertEqual(event.asset_key, pipeline.observation_asset_key(self.sensor_ids[0]))

    def test_targeted_days_and_failure_are_independent_partitions(self):
        for day in ("2026-01-01", "2026-01-02"):
            result, writes = self.execute(
                lambda external_id, start, end: {"timestamp": [start.timestamp()], "T": [21]},
                day=day,
                instance=self.instance,
            )
            self.assertTrue(result.success)
            self.assertEqual(len(writes), 1)

        def unavailable(*args):
            raise OSError("failed")

        failed, writes = self.execute(
            unavailable, sensor_index=1, day="2026-03-15", instance=self.instance
        )
        self.assertFalse(failed.success)
        self.assertEqual(writes, [])
        self.assertEqual(failed.get_asset_materialization_events(), [])
        keys = self.instance.get_materialized_partitions(
            pipeline.observation_asset_key(self.sensor_ids[0])
        )
        self.assertEqual(keys, {"2026-01-01", "2026-01-02"})

    def test_failed_sensor_retries_only_selected_sensor(self):
        attempts = []

        def read(external_id, start, end):
            attempts.append(external_id)
            if len(attempts) == 1:
                raise OSError("temporary fixture failure")
            return {"timestamp": [start.timestamp()], "T": [21]}

        result, writes = self.execute(read, sensor_index=1, day="2026-03-15")
        self.assertTrue(result.success)
        self.assertEqual(attempts, ["device:1", "device:1"])
        self.assertEqual(len(writes), 1)

    def test_exhausted_sensor_failure_prevents_materialization(self):
        attempts = []

        def read(external_id, start, end):
            attempts.append(external_id)
            raise OSError("persistent fixture failure")

        result, writes = self.execute(read, sensor_index=1, day="2026-03-15")
        self.assertFalse(result.success)
        self.assertEqual(attempts, ["device:1"] * (pipeline.RETRY_POLICY.max_retries + 1))
        self.assertEqual(writes, [])
        self.assertEqual(result.get_asset_materialization_events(), [])

    def test_deleted_sensor_fails_without_retries_or_api_calls(self):
        api = StubHamApi(readings=lambda *args: self.fail("Should not call HAM"))
        with patch.object(
            observation_values, "load_references", side_effect=sensors.SensorUnavailable("Deleted")
        ):
            result = materialize(
                [pipeline.make_observation_asset(CATALOG[0])],
                partition_key="2026-01-01",
                resources={
                    "ham_api": ResourceDefinition.hardcoded_resource(api),
                    "database": FakeDatabase(),
                },
                raise_on_error=False,
            )
        self.assertFalse(result.success)
        self.assertFalse(result.get_asset_materialization_events())
        self.assertFalse(any(event.is_step_up_for_retry for event in result.all_events))

    def test_changed_start_fails_without_retries(self):
        self.sensors[0]["starting_date"] = datetime(2026, 2, 1, tzinfo=timezone.utc)
        result, writes = self.execute(lambda *args: self.fail("Should not call API"))
        self.assertFalse(result.success)
        self.assertEqual(writes, [])
        self.assertFalse(result.get_asset_materialization_events())
        self.assertFalse(any(event.is_step_up_for_retry for event in result.all_events))

    def test_failed_database_write_does_not_materialize(self):
        api = StubHamApi(
            readings=lambda external_id, start, end: {"timestamp": [start.timestamp()], "T": [21]}
        )
        with (
            patch.object(
                observation_values, "load_references", return_value=(self.sensors[0], self.types)
            ),
            patch.object(
                observation_values, "persist_observation_rows", side_effect=OSError("commit failed")
            ),
            patch.object(RetryPolicy, "calculate_delay", return_value=0),
        ):
            result = materialize(
                [pipeline.make_observation_asset(CATALOG[0])],
                partition_key="2026-01-01",
                resources={
                    "ham_api": ResourceDefinition.hardcoded_resource(api),
                    "database": FakeDatabase(),
                },
                instance=self.instance,
                raise_on_error=False,
            )
        self.assertFalse(result.success)
        self.assertFalse(result.get_asset_materialization_events())
        self.assertFalse(result.get_asset_observation_events())

    def test_empty_observations_succeed_with_warning_and_no_materialization(self):
        for response in (
            {"timestamp": [], "T": []},
            {"timestamp": [self.start.timestamp()], "T": [None]},
        ):
            result, writes = self.execute(lambda *args: response, instance=self.instance)
            self.assertTrue(result.success)
            self.assertEqual(writes, [])
            self.assertFalse(result.get_asset_materialization_events())
            self.assertEqual(
                self.instance.get_materialized_partitions(
                    pipeline.observation_asset_key(self.sensor_ids[0])
                ),
                set(),
            )
            warnings = [
                entry for entry in self.instance.all_logs(result.run_id) if entry.level == 30
            ]
            self.assertTrue(
                any(
                    "No valid observations" in entry.user_message
                    and self.sensor_ids[0] in entry.user_message
                    for entry in warnings
                )
            )

    def test_empty_observation_metadata_and_reasons(self):
        t = CATALOG[0]["starting_date"].timestamp()
        cases = [
            ({"timestamp": []}, "no_timestamps"),
            ({"timestamp": [t - 1], "T": [None]}, "all_timestamps_outside_interval"),
            ({"timestamp": [t], "T": [None]}, "all_selected_values_null"),
        ]
        for response, reason in cases:
            with self.subTest(reason=reason):
                result, writes = self.execute(lambda *args: response)
                self.assertTrue(result.success)
                self.assertEqual(writes, [])
                events = result.get_asset_observation_events()
                self.assertEqual(len(events), 1)
                event = events[0].event_specific_data.asset_observation
                self.assertEqual(
                    event.asset_key, pipeline.observation_asset_key(self.sensor_ids[0])
                )
                self.assertEqual(event.partition, "2026-01-01")
                metadata = event.metadata
                self.assertEqual(metadata["outcome"].value, "empty")
                self.assertEqual(metadata["empty_reason"].value, reason)
                self.assertEqual(metadata["selected"].value, 0)
                self.assertEqual(metadata["interval_duration_seconds"].value, 36000)
                for field in (
                    "sensor_id",
                    "sensor_name",
                    "sensor_external_id",
                    "external_id",
                    "first_observation_at",
                    "last_observation_at",
                    "persist_seconds",
                    "dagster/last_updated_timestamp",
                    "dagster/partition_row_count",
                ):
                    self.assertNotIn(field, metadata)
                for field in ("fetch_seconds", "prepare_seconds", "reference_lookup_seconds"):
                    self.assertGreaterEqual(metadata[field].value, 0)
                self.assertFalse(result.get_asset_materialization_events())

    def test_materialization_has_typed_diagnostics(self):
        result, _ = self.execute(
            lambda external_id, start, end: {
                "timestamp": [start.timestamp(), start.timestamp()],
                "T": [21, 21],
                "OUT": [0, 0],
            }
        )
        self.assertTrue(result.success)
        self.assertFalse(result.get_asset_observation_events())
        event = result.get_asset_materialization_events()[0].event_specific_data.materialization
        metadata = event.metadata
        for field in ("sensor_id", "sensor_name", "sensor_external_id", "external_id"):
            self.assertNotIn(field, metadata)
        self.assertEqual(metadata["identical_duplicate_count"].value, 1)
        self.assertEqual(metadata["ignored_series_keys"].value, ["OUT"])
        self.assertIsInstance(metadata["first_observation_at"], TimestampMetadataValue)
        self.assertIsInstance(metadata["reading_summary"], TableMetadataValue)
        row = metadata["reading_summary"].records[0].data
        self.assertEqual(row["selected_rows"], 1)
        self.assertEqual(row["first_timestamp"], CATALOG[0]["starting_date"].isoformat())
        self.assertEqual(row["minimum"], 21)
        for field in (
            "fetch_seconds",
            "prepare_seconds",
            "persist_seconds",
            "reference_lookup_seconds",
        ):
            self.assertGreaterEqual(metadata[field].value, 0)
        self.assertNotIn("dagster/partition_row_count", metadata)

    def test_empty_rerun_preserves_previous_materialization(self):
        first, _ = self.execute(
            lambda external_id, start, end: {"timestamp": [start.timestamp()], "T": [21]},
            instance=self.instance,
        )
        self.assertTrue(first.success)
        result, writes = self.execute(
            lambda *args: {"timestamp": [], "T": []}, instance=self.instance
        )
        self.assertTrue(result.success)
        self.assertEqual(writes, [])
        self.assertFalse(result.get_asset_materialization_events())
        self.assertEqual(
            self.instance.get_materialized_partitions(
                pipeline.observation_asset_key(self.sensor_ids[0])
            ),
            {"2026-01-01"},
        )

    def test_nonempty_sync_counts_and_partition_tracking(self):
        # Cover full writes, partial overlap, and existing data without Dagster history.
        for changed in (2, 1, 0):
            with self.subTest(changed=changed), DagsterInstance.ephemeral() as instance:
                result, writes = self.execute(
                    lambda external_id, start, end: {
                        "timestamp": [start.timestamp(), start.timestamp() + 60],
                        "T": [21, 22],
                    },
                    instance=instance,
                    changed=changed,
                )
                self.assertTrue(result.success)
                self.assertEqual(len(writes), 1)
                events = result.get_asset_materialization_events()
                self.assertEqual(len(events), 1)
                metadata = events[0].event_specific_data.materialization.metadata
                self.assertEqual(metadata["selected"].value, 2)
                self.assertEqual(metadata["inserted_or_updated"].value, changed)
                self.assertEqual(metadata["unchanged"].value, 2 - changed)
                self.assertEqual(
                    instance.get_materialized_partitions(
                        pipeline.observation_asset_key(self.sensor_ids[0])
                    ),
                    {"2026-01-01"},
                )
                warnings = [
                    entry.user_message
                    for entry in instance.all_logs(result.run_id)
                    if entry.level == 30
                    and "already present with identical values" in entry.user_message
                ]
                self.assertEqual(len(warnings), int(changed < 2))
                if warnings:
                    self.assertIn(self.sensor_ids[0], warnings[0])
                    self.assertIn("day=2026-01-01", warnings[0])
                    self.assertIn(
                        f"selected=2 inserted_or_updated={changed} unchanged={2 - changed}",
                        warnings[0],
                    )

    def test_first_day_timezone_is_utc(self):
        device = {
            **CATALOG[0],
            "starting_date": datetime(2026, 1, 2, 1, tzinfo=timezone(timedelta(hours=3))),
        }
        asset = pipeline.make_observation_asset(device)
        self.assertEqual(asset.partitions_def.start.date().isoformat(), "2026-01-01")

    def test_later_days_use_full_utc_interval(self):
        def read(external_id, start, end):
            self.assertEqual((end - start).total_seconds(), 86400)
            return {"timestamp": [], "T": []}

        result, _ = self.execute(read, day="2026-01-02")
        self.assertTrue(result.success)
