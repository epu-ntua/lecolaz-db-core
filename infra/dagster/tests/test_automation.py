"""Daily ingestion eligibility, evaluated with Dagster's real automation cursor."""

import unittest
from datetime import datetime, timezone

from dagster import (
    AssetMaterialization,
    DagsterInstance,
    DefaultSensorStatus,
    evaluate_automation_conditions,
)

from infra.dagster import assets as pipeline
from infra.dagster.tests.support import DEVICE_IDS, build_definitions


class AutomationTests(unittest.TestCase):
    def setUp(self):
        self.instance = DagsterInstance.ephemeral()
        self.addCleanup(self.instance.dispose)
        self.defs = build_definitions()
        self.cursor = None
        self.keys = [pipeline.observation_asset_key(id_) for id_ in DEVICE_IDS]

    def evaluate(self, timestamp):
        result = evaluate_automation_conditions(
            self.defs,
            instance=self.instance,
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
        self.instance.report_runless_asset_event(
            AssetMaterialization(self.keys[0], partition="2026-09-08")
        )
        self.assertEqual(self.evaluate("2026-09-09T04:00"), [set(), {"2026-09-08"}])

    def test_zero_delay_and_sensor_start_date(self):
        self.defs = build_definitions(delay_hours=0)
        self.initialize_references()
        self.evaluate("2026-01-01T23:59")
        self.assertEqual(self.evaluate("2026-01-02T00:00"), [{"2026-01-01"}, set()])

    def test_configuration_and_no_generated_daily_jobs(self):
        for value in (-1, 24, 4.5, True):
            with self.assertRaises(ValueError):
                pipeline.observation_automation(value)
        self.assertEqual(
            {job.name for job in self.defs.jobs},
            {"hamapi_initialize", "lecolaz_services_smoke_test"},
        )
        sensor = self.defs.get_sensor_def("hamapi_observation_automation")
        self.assertEqual(sensor.default_status, DefaultSensorStatus.STOPPED)
