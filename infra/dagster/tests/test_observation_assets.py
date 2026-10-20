"""HAM raw persistence, offline replay, partition boundaries and failure isolation."""

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from dagster import (
    DagsterInstance, Failure, ResourceDefinition, RetryPolicy, TableMetadataValue,
    TimestampMetadataValue, materialize,
)

from infra.dagster.ham import assets as pipeline
from infra.dagster.ham import observation_values, sensors
from infra.dagster.object_storage import S3BytesIOManager
from infra.dagster.tests.support import CATALOG, FakeDatabase
from infra.dagster.tests.test_openmeteo import MemoryStore


class ObservationExecutionTests(unittest.TestCase):
    def setUp(self):
        self.device = {**CATALOG[0], "external_id": "e45:1"}
        self.types = {"T": "00000000-0000-0000-0000-000000000003"}
        self.start = self.device["starting_date"]
        self.api = Mock()
        self.api.readings.side_effect = lambda external_id, start, end: (
            f"{start.timestamp()};2150;4500;2500;123\r\n"
            f"{end.timestamp()};9900;4500;2500;123\r\n"
        ).encode()
        self.memory = MemoryStore()
        self.io = S3BytesIOManager(extension="hal", content_type="text/plain")
        self.instance = DagsterInstance.ephemeral()
        self.addCleanup(self.instance.dispose)
        self.writes = []

    def execute(self, *, selection=None, device=None, current=None, day="2026-01-01", changed=None, failure=None, reference_failure=None):
        device = device or self.device

        def persist(engine, rows):
            if failure:
                raise failure
            self.writes.append(rows)
            return {"selected": len(rows), "inserted_or_updated": len(rows) if changed is None else changed}

        with (
            patch.object(S3BytesIOManager, "store", return_value=self.memory),
            patch.object(observation_values, "load_references", return_value=(current or device, self.types), side_effect=reference_failure),
            patch.object(observation_values, "persist_observation_rows", persist),
            patch.object(RetryPolicy, "calculate_delay", return_value=0),
        ):
            return materialize(
                pipeline.make_sensor_assets(device),
                selection=selection,
                partition_key=day,
                resources={
                    "ham_api": ResourceDefinition.hardcoded_resource(self.api),
                    "database": FakeDatabase(),
                    "ham_raw_io_manager": self.io,
                },
                instance=self.instance,
                raise_on_error=False,
            )

    def values_events(self, result):
        return [event for event in result.get_asset_materialization_events() if event.asset_key == pipeline.observation_asset_key(self.device["id"])]

    def replay(self, **kwargs):
        return self.execute(selection=[pipeline.observation_asset_key(self.device["id"])], **kwargs)

    def test_exact_bytes_partition_boundaries_and_offline_replay(self):
        result = self.execute()
        self.assertTrue(result.success)
        self.assertEqual(len(result.get_asset_materialization_events()), 2)
        self.assertEqual(len(self.writes[0]), 1)
        self.assertEqual(self.writes[0][0]["timestamp"], self.start)
        self.assertEqual(self.writes[0][0]["value"], 21.5)
        call = self.api.readings.call_args.args
        self.assertEqual(call[:2], ("e45:1", self.start))
        self.assertEqual((call[2] - call[1]).total_seconds(), 36000)
        key = f"sensors/ham/raw/{self.device['id']}/2026-01-01.hal"
        self.assertEqual(self.memory.objects[key][0], self.api.readings.side_effect(*call))
        raw_meta = result.get_asset_materialization_events()[0].event_specific_data.materialization.metadata
        self.assertTrue(raw_meta["uri"].value.endswith(key))
        self.assertEqual(raw_meta["byte_count"].value, len(self.memory.objects[key][0]))
        self.api.readings.side_effect = AssertionError("Replay must not fetch")
        self.api.readings.reset_mock()
        self.assertTrue(self.replay().success)
        self.api.readings.assert_not_called()
        self.assertEqual(self.writes[0], self.writes[1])

    def test_conversion_failure_retains_valid_payload_for_offline_replay(self):
        payload = self.api.readings.side_effect("e45:1", self.start, self.start + timedelta(hours=10))
        with patch.object(pipeline, "parse_datalog", side_effect=ValueError("conversion bug")):
            result = self.execute()
        self.assertFalse(result.success)
        self.assertEqual(len(result.get_asset_materialization_events()), 1)
        self.assertFalse(any(event.is_step_up_for_retry for event in result.all_events))
        self.assertEqual(next(iter(self.memory.objects.values()))[0], payload)
        self.assertEqual(self.writes, [])
        self.api.readings.side_effect = AssertionError("Must not fetch after parser correction")
        self.assertTrue(self.replay().success)
        self.assertEqual(self.writes[0][0]["value"], 21.5)
        self.assertEqual(self.api.readings.call_count, 1)

    def test_invalid_or_empty_payload_never_reaches_storage_or_conversion(self):
        self.api.readings.side_effect = None
        valid = f"{self.start.timestamp()};2150;4500;2500;123\n".encode()
        for payload in (
            b"", b" \r\n", b"\xef\xbb\xbf", b"\xff", b'<html>server error</html>',
            b'{"error":"denied"}', b'{"messages":["File not found"]}',
            valid + b"1767276000;2150\n", valid + b"bad;2150;4500;2500;0\n",
            valid + b"1767276000;inf;4500;2500;0\n",
            b"1767276000;;2147483648;;\n",
        ):
            with self.subTest(payload=payload), patch.object(pipeline, "parse_datalog") as parse:
                self.api.readings.return_value = payload
                result = self.execute()
                self.assertFalse(result.success)
                self.assertFalse(result.get_asset_materialization_events())
                self.assertFalse(any(event.is_step_up_for_retry for event in result.all_events))
                self.assertEqual(self.memory.objects, {})
                self.assertEqual(self.writes, [])
                parse.assert_not_called()

    def test_failed_db_load_can_replay_without_refetch(self):
        result = self.execute(failure=OSError("commit failed"))
        self.assertFalse(result.success)
        self.assertFalse(self.values_events(result))
        self.assertEqual(len(self.memory.objects), 1)
        self.assertEqual(self.api.readings.call_count, 1)
        self.api.readings.side_effect = AssertionError("Must use retained raw data")
        self.assertTrue(self.replay().success)

    def test_missing_source_file_fails_raw_without_storage_or_downstream_writes(self):
        self.api.readings.side_effect = Failure("HAM datalog file not found", allow_retries=False)
        result = self.execute()
        self.assertFalse(result.success)
        self.assertFalse(result.get_asset_materialization_events())
        self.assertFalse(any(event.is_step_up_for_retry for event in result.all_events))
        self.assertEqual(self.memory.objects, {})
        self.assertEqual(self.writes, [])

    def test_legacy_missing_file_object_fails_load_only_replay(self):
        self.api.readings.side_effect = None
        self.api.readings.return_value = b'{"messages":["File not found"]}'
        # Seed the object as the previous fetch policy did, without parsing it.
        with patch.object(pipeline, "validate_datalog", return_value=0):
            self.assertTrue(self.execute(selection=[pipeline.raw_asset_key(self.device["id"])]).success)
        self.api.readings.side_effect = AssertionError("Replay must not fetch")
        result = self.replay()
        self.assertFalse(result.success)
        self.assertFalse(result.get_asset_materialization_events())
        self.assertFalse(result.get_asset_observation_events())
        self.assertFalse(any(event.is_step_up_for_retry for event in result.all_events))
        message = result.get_step_failure_events()[0].event_specific_data.error.message
        self.assertIn("rematerialize raw", message)
        self.assertNotIn("rematerialize only observation_values", message)
        self.assertEqual(self.writes, [])

    def test_storage_failure_never_runs_parser_or_database_load(self):
        with patch.object(self.memory, "put_object", side_effect=OSError("storage unavailable")), patch.object(pipeline, "parse_datalog") as parse:
            result = self.execute()
        self.assertFalse(result.success)
        self.assertFalse(result.get_asset_materialization_events())
        parse.assert_not_called()
        self.assertEqual(self.writes, [])

    def test_valid_data_with_no_selected_values_materializes_only_raw(self):
        self.api.readings.side_effect = None
        self.api.readings.return_value = f"{self.start.timestamp()};;4500;;\n".encode()
        result = self.execute()
        self.assertTrue(result.success)
        self.assertEqual(len(result.get_asset_materialization_events()), 1)
        self.assertFalse(self.values_events(result))
        observation = result.get_asset_observation_events()[0].event_specific_data.asset_observation
        self.assertEqual(observation.metadata["empty_reason"].value, "all_selected_values_null")
        self.assertEqual(self.writes, [])

    def test_empty_rerun_preserves_previous_materialization(self):
        self.assertTrue(self.execute().success)
        objects = dict(self.memory.objects)
        self.api.readings.side_effect = None
        self.api.readings.return_value = b""
        result = self.execute()
        self.assertFalse(result.success)
        self.assertFalse(result.get_asset_materialization_events())
        self.assertEqual(self.memory.objects, objects)
        self.assertEqual(self.instance.get_materialized_partitions(pipeline.observation_asset_key(self.device["id"])), {"2026-01-01"})

    def test_corrupt_and_stale_artifacts_fail_before_writes(self):
        self.assertTrue(self.execute().success)
        key = next(iter(self.memory.objects))
        saved = self.memory.objects[key]
        self.memory.objects[key] = (b"corrupted", saved[1])
        self.assertFalse(self.replay().success)
        self.memory.objects[key] = saved
        for field, value in (("external_id", "e45:2"), ("starting_date", self.start + timedelta(hours=1))):
            self.assertFalse(self.replay(device={**self.device, field: value}).success)
        self.assertEqual(len(self.writes), 1)

    def test_deleted_or_changed_sensor_fails_without_fetch_or_retry(self):
        cases = [
            {"reference_failure": sensors.SensorUnavailable("Deleted")},
            {"current": {**self.device, "starting_date": self.start + timedelta(days=1)}},
            {"current": {**self.device, "external_id": "e45:2"}},
        ]
        for kwargs in cases:
            result = self.execute(**kwargs)
            self.assertFalse(result.success)
            self.assertFalse(any(event.is_step_up_for_retry for event in result.all_events))
        self.api.readings.assert_not_called()
        self.assertEqual(self.memory.objects, {})

    def test_fetch_retries_only_selected_sensor_and_never_loads_on_failure(self):
        self.api.readings.side_effect = [OSError("temporary"), b"1767225600;2150;;;\n"]
        device = {**CATALOG[1], "external_id": "e45:2"}
        self.assertTrue(self.execute(device=device, day="2026-03-15").success)
        self.assertEqual([call.args[0] for call in self.api.readings.call_args_list], ["e45:2"] * 2)
        self.api.readings.side_effect = OSError("persistent")
        result = self.execute()
        self.assertFalse(result.success)
        self.assertFalse(result.get_asset_materialization_events())
        self.assertEqual(self.writes, [])

    def test_typed_metadata_duplicates_and_unchanged_counts(self):
        self.api.readings.side_effect = None
        self.api.readings.return_value = f"{self.start.timestamp()};2150;4500;2500;123\n".encode() * 2
        result = self.execute(changed=0)
        self.assertTrue(result.success)
        metadata = self.values_events(result)[0].event_specific_data.materialization.metadata
        self.assertEqual(metadata["selected"].value, 1)
        self.assertEqual(metadata["unchanged"].value, 1)
        self.assertEqual(metadata["identical_duplicate_count"].value, 1)
        self.assertIsInstance(metadata["first_observation_at"], TimestampMetadataValue)
        self.assertIsInstance(metadata["reading_summary"], TableMetadataValue)
        self.assertNotIn("fetch_seconds", metadata)

    def test_first_day_timezone_and_later_day_interval(self):
        device = {**self.device, "starting_date": datetime(2026, 1, 2, 1, tzinfo=timezone(timedelta(hours=3)))}
        raw, values = pipeline.make_sensor_assets(device)
        self.assertEqual(raw.partitions_def.start.date().isoformat(), "2026-01-01")
        self.assertEqual(raw.partitions_def, values.partitions_def)
        self.assertTrue(self.execute(day="2026-01-02").success)
        _, start, end = self.api.readings.call_args.args
        self.assertEqual((end - start).total_seconds(), 86400)

    def test_out_of_window_rows_emit_warning_and_preserve_in_window_values(self):
        day_start = self.start.replace(hour=0)
        end = day_start + timedelta(days=1)
        self.api.readings.side_effect = None
        self.api.readings.return_value = "".join(
            f"{timestamp.timestamp()};2150;4500;2500;123\n"
            for timestamp in (day_start - timedelta(seconds=1), self.start - timedelta(seconds=1), self.start, end)
        ).encode()
        result = self.execute()
        self.assertTrue(result.success)
        self.assertEqual(len(self.writes[0]), 1)
        self.assertEqual(self.writes[0][0]["timestamp"], self.start)
        metadata = self.values_events(result)[0].event_specific_data.materialization.metadata
        self.assertEqual(metadata["out_of_interval_timestamp_count"].value, 3)
        warnings = [
            entry.user_message for entry in self.instance.all_logs(result.run_id)
            if entry.level == 30 and "HAM out-of-window readings" in entry.user_message
        ]
        self.assertEqual(len(warnings), 1)
        for detail in (
            f"sensor_id={self.device['id']}", "external_id=e45:1", "day=2026-01-01",
            f"interval=[{self.start.isoformat()}, {end.isoformat()})",
            "skipped_source_rows=3", "Raw datalog is retained",
        ):
            self.assertIn(detail, warnings[0])

    def test_all_out_of_window_rows_warn_before_empty_result(self):
        self.api.readings.side_effect = None
        self.api.readings.return_value = f"{self.start.timestamp() - 1};2150;4500;2500;123\n".encode()
        result = self.execute()
        self.assertTrue(result.success)
        self.assertFalse(self.values_events(result))
        self.assertEqual(self.writes, [])
        self.assertTrue(any(
            entry.level == 30 and "HAM out-of-window readings" in entry.user_message
            and "skipped_source_rows=1" in entry.user_message
            for entry in self.instance.all_logs(result.run_id)
        ))

    def test_in_window_rows_do_not_emit_out_of_window_warning(self):
        self.api.readings.side_effect = None
        self.api.readings.return_value = f"{self.start.timestamp()};2150;4500;2500;123\n".encode()
        result = self.execute()
        self.assertTrue(result.success)
        self.assertFalse(any(
            entry.level == 30 and "HAM out-of-window readings" in entry.user_message
            for entry in self.instance.all_logs(result.run_id)
        ))

    def test_conflicting_source_rows_emit_detailed_warning_and_last_non_missing_value(self):
        self.api.readings.side_effect = None
        self.api.readings.return_value = (
            f"{self.start.timestamp()};2150;4500;2500;123\n"
            f"{self.start.timestamp()};2200;4500;2500;123\n"
            f"{self.start.timestamp()};;4500;2500;123\n"
        ).encode()
        result = self.execute()
        self.assertTrue(result.success)
        self.assertEqual(self.writes[0][0]["value"], 22)
        metadata = self.values_events(result)[0].event_specific_data.materialization.metadata
        self.assertEqual(metadata["conflicting_duplicate_count"].value, 1)
        warnings = [
            entry.user_message
            for entry in self.instance.all_logs(result.run_id)
            if entry.level == 30 and "HAM conflicting" in entry.user_message
        ]
        self.assertEqual(len(warnings), 1)
        for detail in (
            f"sensor_id={self.device['id']}", "external_id=e45:1", "day=2026-01-01",
            f"timestamp={self.start.isoformat()}", "reading=T", "values=[21.5, 22.0]",
            "selected_value=22.0", "last non-missing source value wins",
        ):
            self.assertIn(detail, warnings[0])

    def test_missing_and_identical_source_values_do_not_emit_conflict_warning(self):
        self.api.readings.side_effect = None
        self.api.readings.return_value = (
            f"{self.start.timestamp()};;4500;2500;123\n"
            f"{self.start.timestamp()};2150;4500;2500;123\n"
            f"{self.start.timestamp()};2150;4500;2500;123\n"
            f"{self.start.timestamp()};;4500;2500;123\n"
        ).encode()
        result = self.execute()
        self.assertTrue(result.success)
        self.assertEqual(self.writes[0][0]["value"], 21.5)
        metadata = self.values_events(result)[0].event_specific_data.materialization.metadata
        self.assertEqual(metadata["conflicting_duplicate_count"].value, 0)
        self.assertEqual(metadata["identical_duplicate_count"].value, 1)
        self.assertFalse(any(
            entry.level == 30 and "HAM conflicting" in entry.user_message
            for entry in self.instance.all_logs(result.run_id)
        ))
