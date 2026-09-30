"""One-time registration uses persistent asset history and reloads after success."""

import tempfile
import unittest
from unittest.mock import patch

import dagster as dg
from dagster._core.errors import (
    DagsterMaxRetriesExceededError,
    DagsterUserCodeUnreachableError,
)
from infra.dagster import initialize
from infra.dagster.openmeteo import catalog
from infra.dagster.openmeteo.client import OpenMeteoApi
from infra.dagster.openmeteo.component import (
    REGISTRATION_KEYS,
    registration_definitions,
)
from infra.dagster.tests.support import FakeDatabase


class InitializationTests(unittest.TestCase):
    def setUp(self):
        self.job = registration_definitions(
            {"database": FakeDatabase(), "openmeteo_api": OpenMeteoApi()}
        ).resolve_job_def("register_openmeteo_sensors")
        self.prepare = self.enterContext(
            patch.object(catalog, "prepare_registration", return_value=([], []))
        )
        self.persist = self.enterContext(
            patch.object(catalog, "persist_registration", return_value={})
        )

    def test_registration_survives_process_restart_and_skips_second_run(self):
        with tempfile.TemporaryDirectory() as directory:
            with dg.DagsterInstance.local_temp(
                directory, overrides={"telemetry": {"enabled": False}}
            ) as instance:
                self.assertTrue(initialize.initialize(instance, self.job))
                self.assertEqual(instance.get_runs_count(), 1)
                for key in REGISTRATION_KEYS:
                    self.assertIsNotNone(instance.get_latest_materialization_event(key))
            with dg.DagsterInstance.local_temp(
                directory, overrides={"telemetry": {"enabled": False}}
            ) as instance:
                self.assertFalse(initialize.initialize(instance, self.job))
                self.assertEqual(instance.get_runs_count(), 1)
        self.persist.assert_called_once()

    def test_either_missing_asset_registers_both(self):
        for existing_key in REGISTRATION_KEYS:
            with (
                self.subTest(existing=existing_key),
                dg.DagsterInstance.ephemeral() as instance,
            ):
                instance.report_runless_asset_event(
                    dg.AssetMaterialization(existing_key)
                )
                self.assertTrue(initialize.initialize(instance, self.job))
                for key in REGISTRATION_KEYS:
                    self.assertIsNotNone(instance.get_latest_materialization_event(key))

    def test_failed_commit_does_not_materialize_and_can_retry(self):
        with (
            dg.DagsterInstance.ephemeral() as instance,
            patch.object(dg.RetryPolicy, "calculate_delay", return_value=0),
        ):
            self.persist.side_effect = RuntimeError("Commit failed")
            with self.assertRaises(DagsterMaxRetriesExceededError):
                initialize.initialize(instance, self.job)
            for key in REGISTRATION_KEYS:
                self.assertIsNone(instance.get_latest_materialization_event(key))
            self.persist.side_effect = None
            self.assertTrue(initialize.initialize(instance, self.job))

    def test_reload_retries_unavailable_code_server_and_is_bounded(self):
        with (
            patch.object(initialize, "DagsterGrpcClient") as client,
            patch.object(initialize, "sync_list_repositories_grpc") as check,
            patch.object(initialize.time, "sleep") as sleep,
        ):
            reload = client.return_value.reload_code
            reload.side_effect = [DagsterUserCodeUnreachableError("Starting"), None]
            initialize.reload_code_location()
            self.assertEqual(reload.call_count, 2)
            check.assert_called_once_with(client.return_value)
            sleep.assert_called_once_with(5)
            reload.reset_mock()
            sleep.reset_mock()
            reload.side_effect = DagsterUserCodeUnreachableError("Unavailable")
            with self.assertRaises(DagsterUserCodeUnreachableError):
                initialize.reload_code_location()
            self.assertEqual(reload.call_count, 12)
            self.assertEqual(sleep.call_count, 11)
