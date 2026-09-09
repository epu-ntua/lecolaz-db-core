"""Dagster wiring, partitions, runtime configuration, and failure behavior."""

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import importlib
import os
import unittest
from unittest.mock import patch

from dagster import (
    AssetKey, DagsterInstance, DefaultSensorStatus, Definitions, Failure, RetryPolicy,
    AssetMaterialization, evaluate_automation_conditions, materialize,
)

from infra.dagster import definitions as pipeline
from infra.dagster.resources import HamApi, LeColazDatabase


class FakeDatabase(LeColazDatabase):
    host: str = "fixture"
    database: str = "fixture"
    username: str = "fixture"
    password: str = "fixture"

    @contextmanager
    def engine(self):
        yield None


DEVICE_IDS = ["00000000-0000-0000-0000-000000000001", "00000000-0000-0000-0000-000000000002"]
CATALOG = [{"id": DEVICE_IDS[0], "name": "First", "starting_date": datetime(2026, 1, 1, 14, tzinfo=timezone.utc)},
           {"id": DEVICE_IDS[1], "name": "Second", "starting_date": datetime(2026, 3, 15, tzinfo=timezone.utc)}]


def build(catalog=CATALOG):
    with patch.object(pipeline.sensors, "load_sensor_catalog", return_value=catalog):
        return pipeline.build_definitions(FakeDatabase(), HamApi(api_key="fixture"))


class DefinitionTests(unittest.TestCase):
    def test_import_does_not_query_but_definition_load_does(self):
        with patch.dict(os.environ, {}, clear=True), \
             patch("sqlalchemy.create_engine", side_effect=AssertionError("DB at import")), \
             patch("urllib.request.urlopen", side_effect=AssertionError("HTTP at import")):
            importlib.reload(pipeline)
        with patch.object(pipeline.sensors, "load_sensor_catalog", return_value=CATALOG) as read:
            defs = pipeline.build_definitions(FakeDatabase(), HamApi())
            read.assert_called_once_with(None)
            Definitions.validate_loadable(defs)

    def test_database_failure_is_not_an_empty_catalog(self):
        with patch.object(pipeline.sensors, "load_sensor_catalog", side_effect=OSError("DB unavailable")):
            with self.assertRaises(OSError):
                pipeline.build_definitions(FakeDatabase(), HamApi())

    def test_lineage_distinct_start_dates_and_automation(self):
        defs = build()
        for device in CATALOG:
            key = pipeline.observation_asset_key(device["id"])
            asset = next(a for a in defs.assets if a.key == key)
            self.assertEqual(asset.asset_deps[key], {AssetKey("hamapi_sensors"), AssetKey("hamapi_observation_types")})
            self.assertEqual(asset.partitions_def.start.date(), device["starting_date"].date())
            self.assertEqual(asset.backfill_policy.max_partitions_per_run, 1)
        self.assertFalse(defs.schedules)

    def test_empty_catalog_still_loads_initialization_and_automation(self):
        defs = build([])
        Definitions.validate_loadable(defs)
        self.assertEqual(len(defs.assets), 2)
        self.assertEqual(len(defs.sensors), 1)

    def test_reload_add_delete_rename_and_start_date_changes(self):
        first = build()
        renamed = {**CATALOG[0], "name": "Renamed", "starting_date": datetime(2026, 2, 1, tzinfo=timezone.utc)}
        reloaded = build([renamed])
        key = pipeline.observation_asset_key(DEVICE_IDS[0])
        self.assertIn(pipeline.observation_asset_key(DEVICE_IDS[1]), first.resolve_all_asset_keys())
        self.assertNotIn(pipeline.observation_asset_key(DEVICE_IDS[1]), reloaded.resolve_all_asset_keys())
        asset = next(a for a in reloaded.assets if a.key == key)
        self.assertEqual(asset.partitions_def.start.date().isoformat(), "2026-02-01")
        self.assertEqual(asset.metadata_by_key[key]["sensor_name"], "Renamed")
        self.assertEqual(len(build().resolve_all_asset_keys()), 4)

    def test_runtime_extra_readings_option(self):
        from dagster import materialize
        catalog = {"T": {}, "PMV": {}}
        models = {"device": {"readings": ["T"], "extra_readings": [{"key": "PMV"}]}}
        for enabled, expected in ((False, ["T"]), (True, ["PMV", "T"])):
            with self.subTest(enabled=enabled), \
                 patch.object(HamApi, "catalog", side_effect=[catalog, models]), \
                 patch.object(pipeline.observation_types, "persist_rows", return_value={"selected": len(expected)}) as persist:
                result = materialize(
                    [pipeline.hamapi_observation_types],
                    resources={"ham_api": HamApi(), "database": FakeDatabase()},
                    run_config={"ops": {"hamapi_observation_types": {"config": {"include_extra_readings": enabled}}}},
                )
                self.assertTrue(result.success)
                self.assertEqual([row["key"] for row in persist.call_args.args[1]], expected)

    def test_missing_key_fails_without_retry_or_client_creation(self):
        with patch("hamapi.hamapi") as factory:
            with self.assertRaises(Failure) as raised:
                HamApi().devices()
            self.assertFalse(raised.exception.allow_retries)
            factory.assert_not_called()

    def test_database_url_preserves_special_characters(self):
        password = "p@ss:/?#% word"
        url = LeColazDatabase(host="postgres", database="fixture",
                             password=password, username="user@name").connection_url()
        from sqlalchemy.engine import make_url
        self.assertEqual(make_url(url.render_as_string(hide_password=False)).password, password)


class ObservationExecutionTests(unittest.TestCase):
    def setUp(self):
        self.sensor_ids = DEVICE_IDS
        self.type_id = "00000000-0000-0000-0000-000000000003"
        self.references = {
            "sensors": [{"id": id_, "external_id": f"device:{i}", "sensor_family": "ham", "starting_date": CATALOG[i]["starting_date"]}
                        for i, id_ in enumerate(self.sensor_ids)],
            "types": {"T": self.type_id},
        }
        self.start = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def execute(self, read, sensor_index=0, day="2026-01-01", instance=None, changed=None):
        sensor_id = self.sensor_ids[sensor_index]
        defs = build()
        refs = {**self.references, "sensors": [self.references["sensors"][sensor_index]]}
        with patch.object(pipeline.observation_values, "load_references", return_value=refs) as load, \
             patch.object(HamApi, "readings", side_effect=read), \
             patch.object(pipeline.observation_values, "persist_observation_rows",
                          side_effect=lambda engine, rows: {"selected": len(rows), "inserted_or_updated": len(rows) if changed is None else changed}) as persist, \
             patch.object(RetryPolicy, "calculate_delay", return_value=0):
            owned_instance = instance is None
            instance = instance or DagsterInstance.ephemeral()
            try:
                result = defs.resolve_implicit_job_def_def_for_assets([pipeline.observation_asset_key(sensor_id)]).execute_in_process(
                    partition_key=day, asset_selection=[pipeline.observation_asset_key(sensor_id)],
                    instance=instance, raise_on_error=False,
                )
                load.assert_called_with(None, sensor_id=sensor_id)
            finally:
                if owned_instance:
                    instance.dispose()
        return result, persist

    def test_partition_boundaries_and_only_selected_sensor(self):
        intervals = []
        def read(external_id, start, end):
            self.assertEqual(external_id, "device:0")
            intervals.append((start, end))
            return {"timestamp": [start.timestamp(), end.timestamp()], "T": [21, 22]}
        result, persist = self.execute(read)
        self.assertTrue(result.success)
        self.assertEqual(persist.call_count, 1)
        self.assertEqual(intervals[0][0], CATALOG[0]["starting_date"])
        self.assertEqual((intervals[0][1] - intervals[0][0]).total_seconds(), 10 * 3600)
        event = result.get_asset_materialization_events()[0].event_specific_data.materialization
        self.assertEqual(event.partition, "2026-01-01")
        self.assertEqual(event.metadata["selected"].value, 1)
        self.assertEqual(event.metadata["sensor_id"].value, self.sensor_ids[0])

    def test_targeted_days_and_failure_are_independent_partitions(self):
        with DagsterInstance.ephemeral() as instance:
            for day in ("2026-01-01", "2026-01-02"):
                result, persist = self.execute(
                    lambda external_id, start, end: {"timestamp": [start.timestamp()], "T": [21]},
                    day=day, instance=instance,
                )
                self.assertTrue(result.success)
                self.assertEqual(persist.call_count, 1)
            failed, persist = self.execute(lambda *args: (_ for _ in ()).throw(OSError("failed")),
                                          sensor_index=1, day="2026-03-15", instance=instance)
            self.assertFalse(failed.success)
            persist.assert_not_called()
            self.assertEqual(failed.get_asset_materialization_events(), [])
            keys = instance.get_materialized_partitions(pipeline.observation_asset_key(self.sensor_ids[0]))
            self.assertEqual(keys, {"2026-01-01", "2026-01-02"})

    def test_failed_sensor_retries_only_selected_sensor(self):
        attempts = []
        def read(external_id, start, end):
            attempts.append(external_id)
            if len(attempts) == 1:
                raise OSError("temporary fixture failure")
            return {"timestamp": [start.timestamp()], "T": [21]}
        result, persist = self.execute(read, sensor_index=1, day="2026-03-15")
        self.assertTrue(result.success)
        self.assertEqual(attempts, ["device:1", "device:1"])
        self.assertEqual(persist.call_count, 1)

    def test_exhausted_sensor_failure_prevents_materialization(self):
        attempts = []
        def read(external_id, start, end):
            attempts.append(external_id)
            raise OSError("persistent fixture failure")
        result, persist = self.execute(read, sensor_index=1, day="2026-03-15")
        self.assertFalse(result.success)
        self.assertEqual(attempts, ["device:1"] * (pipeline.RETRY_POLICY.max_retries + 1))
        persist.assert_not_called()
        self.assertEqual(result.get_asset_materialization_events(), [])

    def test_deleted_sensor_fails_without_retries_or_api_calls(self):
        defs = build()
        with patch.object(pipeline.observation_values, "load_references", side_effect=pipeline.sensors.SensorUnavailable("Deleted")) as read, \
             patch.object(HamApi, "readings") as api:
            result = defs.resolve_implicit_job_def_def_for_assets([pipeline.observation_asset_key(DEVICE_IDS[0])]).execute_in_process(
                partition_key="2026-01-01", asset_selection=[pipeline.observation_asset_key(DEVICE_IDS[0])], raise_on_error=False)
            self.assertFalse(result.success)
            self.assertEqual(read.call_count, 1)
            api.assert_not_called()
            self.assertEqual(result.get_asset_materialization_events(), [])

    def test_changed_start_fails_without_retries(self):
        self.references["sensors"][0]["starting_date"] = datetime(2026, 2, 1, tzinfo=timezone.utc)
        result, persist = self.execute(lambda *args: self.fail("Should not call API"))
        self.assertFalse(result.success)
        persist.assert_not_called()
        self.assertFalse(result.get_asset_materialization_events())

    def test_empty_observations_succeed_with_warning_and_no_materialization(self):
        with DagsterInstance.ephemeral() as instance:
            for response in ({"timestamp": [], "T": []},
                             {"timestamp": [self.start.timestamp()], "T": [None]}):
                result, persist = self.execute(lambda *args: response, instance=instance)
                self.assertTrue(result.success)
                persist.assert_not_called()
                self.assertFalse(result.get_asset_materialization_events())
                self.assertEqual(instance.get_materialized_partitions(pipeline.observation_asset_key(self.sensor_ids[0])), set())
                warnings = [entry for entry in instance.all_logs(result.run_id) if entry.level == 30]
                self.assertTrue(any("No valid observations" in entry.user_message
                                    and self.sensor_ids[0] in entry.user_message for entry in warnings))

    def test_empty_rerun_preserves_previous_materialization(self):
        with DagsterInstance.ephemeral() as instance:
            first, _ = self.execute(
                lambda external_id, start, end: {"timestamp": [start.timestamp()], "T": [21]},
                instance=instance,
            )
            self.assertTrue(first.success)
            result, persist = self.execute(lambda *args: {"timestamp": [], "T": []}, instance=instance)
            self.assertTrue(result.success)
            persist.assert_not_called()
            self.assertFalse(result.get_asset_materialization_events())
            self.assertEqual(instance.get_materialized_partitions(pipeline.observation_asset_key(self.sensor_ids[0])),
                             {"2026-01-01"})

    def test_nonempty_sync_counts_and_partition_tracking(self):
        # Cover full writes, partial overlap, and existing data without Dagster history.
        for changed in (2, 1, 0):
            with self.subTest(changed=changed), DagsterInstance.ephemeral() as instance:
                result, persist = self.execute(
                    lambda external_id, start, end: {
                        "timestamp": [start.timestamp(), start.timestamp() + 60], "T": [21, 22],
                    }, instance=instance, changed=changed,
                )
                self.assertTrue(result.success)
                self.assertEqual(persist.call_count, 1)
                events = result.get_asset_materialization_events()
                self.assertEqual(len(events), 1)
                metadata = events[0].event_specific_data.materialization.metadata
                self.assertEqual(metadata["selected"].value, 2)
                self.assertEqual(metadata["inserted_or_updated"].value, changed)
                self.assertEqual(metadata["unchanged"].value, 2 - changed)
                self.assertEqual(instance.get_materialized_partitions(
                    pipeline.observation_asset_key(self.sensor_ids[0])), {"2026-01-01"})
                warnings = [entry.user_message for entry in instance.all_logs(result.run_id)
                            if entry.level == 30 and "already present with identical values" in entry.user_message]
                self.assertEqual(len(warnings), int(changed < 2))
                if warnings:
                    self.assertIn(self.sensor_ids[0], warnings[0])
                    self.assertIn("day=2026-01-01", warnings[0])
                    self.assertIn(f"selected=2 inserted_or_updated={changed} unchanged={2 - changed}", warnings[0])

    def test_first_day_timezone_is_utc_and_later_days_are_full(self):
        device = {**CATALOG[0], "starting_date": datetime(2026, 1, 2, 1, tzinfo=timezone(timedelta(hours=3)))}
        asset = pipeline.make_observation_asset(device)
        self.assertEqual(asset.partitions_def.start.date().isoformat(), "2026-01-01")
        def read(external_id, start, end):
            self.assertEqual((end-start).total_seconds(), 86400)
            return {"timestamp": [], "T": []}
        result, _ = self.execute(read, day="2026-01-02")
        self.assertTrue(result.success)


class AutomationTests(unittest.TestCase):
    def setUp(self):
        self.instance = DagsterInstance.ephemeral()
        self.addCleanup(self.instance.dispose)
        self.defs = build()
        self.cursor = None
        self.keys = [pipeline.observation_asset_key(id_) for id_ in DEVICE_IDS]

    def evaluate(self, timestamp):
        result = evaluate_automation_conditions(
            self.defs, instance=self.instance,
            evaluation_time=datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc),
            cursor=self.cursor,
        )
        self.cursor = result.cursor
        return [result.get_requested_partitions(key) for key in self.keys]

    def initialize_references(self):
        for name in ("hamapi_sensors", "hamapi_observation_types"):
            self.instance.report_runless_asset_event(AssetMaterialization(name))

    def test_default_delay_and_one_request_per_new_day(self):
        self.initialize_references()
        self.assertEqual(self.evaluate("2026-09-08T23:59"), [set(), set()])
        for time in ("00:00", "03:59"):
            self.assertEqual(self.evaluate("2026-09-09T" + time), [set(), set()])
        self.assertEqual(self.evaluate("2026-09-09T04:00"), [{"2026-09-08"}] * 2)
        self.assertEqual(self.evaluate("2026-09-09T05:00"), [set(), set()])
        self.assertEqual(self.evaluate("2026-09-10T00:00"), [set(), set()])
        self.assertEqual(self.evaluate("2026-09-10T04:00"), [{"2026-09-09"}] * 2)

    def test_waits_for_references_without_requiring_daily_refresh(self):
        self.evaluate("2026-09-08T23:59")
        self.assertEqual(self.evaluate("2026-09-09T04:00"), [set(), set()])
        self.initialize_references()
        self.assertEqual(self.evaluate("2026-09-09T06:00"), [{"2026-09-08"}] * 2)

    def test_initial_enable_does_not_backfill_and_manual_materialization_is_respected(self):
        self.initialize_references()
        self.assertEqual(self.evaluate("2026-09-08T12:00"), [set(), set()])
        self.evaluate("2026-09-09T00:00")
        self.instance.report_runless_asset_event(AssetMaterialization(self.keys[0], partition="2026-09-08"))
        self.assertEqual(self.evaluate("2026-09-09T04:00"), [set(), {"2026-09-08"}])

    def test_zero_delay_and_sensor_start_date(self):
        with patch.object(pipeline.sensors, "load_sensor_catalog", return_value=CATALOG):
            self.defs = pipeline.build_definitions(FakeDatabase(), HamApi(), delay_hours=0)
        self.initialize_references()
        self.evaluate("2026-01-01T23:59")
        self.assertEqual(self.evaluate("2026-01-02T00:00"), [{"2026-01-01"}, set()])

    def test_configuration_and_no_generated_daily_jobs(self):
        for value in (-1, 24, 4.5, True):
            with self.assertRaises(ValueError):
                pipeline.observation_automation(value)
        self.assertEqual({job.name for job in self.defs.jobs},
                         {"hamapi_initialize", "lecolaz_services_smoke_test"})
        sensor = self.defs.get_sensor_def("hamapi_observation_automation")
        self.assertEqual(sensor.default_status, DefaultSensorStatus.STOPPED)
