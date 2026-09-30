"""Shared startup orchestration and HAM's independent reference materializations."""

import unittest
from unittest.mock import Mock, patch

import dagster as dg
from dagster._core.errors import DagsterMaxRetriesExceededError
from infra.dagster import initialize
from infra.dagster.ham import observation_types, sensors
from infra.dagster.ham.assets import hamapi_observation_types, hamapi_sensors
from infra.dagster.ham.client import HamApi
from infra.dagster.ham.definitions import startup_registration_job
from infra.dagster.tests.support import FakeDatabase


class SharedInitializationTests(unittest.TestCase):
    def test_main_checks_families_independently_and_reloads_once(self):
        ham = Mock(name="ham job")
        ham.name = "register_hamapi_sensors"
        openmeteo = Mock(name="openmeteo job")
        openmeteo.name = "register_openmeteo_sensors"
        for outcomes, expected_reload, failed in (
            ([False, False], 0, False),
            ([True, True], 1, False),
            ([RuntimeError("HAM failed"), True], 1, True),
            ([True, RuntimeError("OpenMeteo failed")], 1, True),
            ([RuntimeError("HAM failed"), False], 0, True),
        ):
            with (
                self.subTest(outcomes=outcomes),
                patch.object(
                    initialize, "configured_database", return_value=FakeDatabase()
                ),
                patch.object(initialize, "ham_registration_job", return_value=ham),
                patch.object(
                    initialize, "openmeteo_registration_job", return_value=openmeteo
                ),
                patch.object(initialize.dg.DagsterInstance, "get"),
                patch.object(initialize, "initialize", side_effect=outcomes) as run,
                patch.object(initialize, "reload_code_location") as reload,
            ):
                if failed:
                    with self.assertRaisesRegex(RuntimeError, "Registration failed"):
                        initialize.main()
                else:
                    initialize.main()
                self.assertEqual(
                    [call.args[1] for call in run.call_args_list], [ham, openmeteo]
                )
                self.assertEqual(reload.call_count, expected_reload)

    def test_missing_ham_key_skips_only_ham(self):
        with (
            patch.dict("os.environ", {"HAMAPI_API_KEY": "  "}),
            patch.object(
                initialize, "configured_database", return_value=FakeDatabase()
            ),
            patch.object(initialize, "openmeteo_registration_job") as openmeteo,
            patch.object(initialize.dg.DagsterInstance, "get"),
            patch.object(initialize, "initialize", return_value=True) as run,
            patch.object(initialize, "reload_code_location") as reload,
        ):
            initialize.main()
            run.assert_called_once()
            self.assertIs(run.call_args.args[1], openmeteo.return_value)
            reload.assert_called_once()

    def test_ham_partial_failure_retries_then_skips_materialized_assets(self):
        with patch.dict("os.environ", {"HAMAPI_API_KEY": "fixture"}):
            job = startup_registration_job(FakeDatabase())
        self.assertEqual(set(job.resource_defs), {"ham_api", "database", "io_manager"})
        with (
            dg.DagsterInstance.ephemeral() as instance,
            patch.object(
                HamApi, "devices", return_value={"error": "Invalid API key"}
            ) as devices,
            patch.object(
                observation_types,
                "persist_rows",
                return_value={"selected": 1, "inserted_or_updated": 1},
            ),
            patch.object(
                sensors,
                "persist_sensor_rows",
                return_value={"selected": 1, "inserted_or_updated": 1},
            ) as persist,
            patch.object(dg.RetryPolicy, "calculate_delay", return_value=0),
        ):
            with self.assertRaises(DagsterMaxRetriesExceededError):
                initialize.initialize(instance, job)
            self.assertIsNotNone(
                instance.get_latest_materialization_event(hamapi_observation_types.key)
            )
            self.assertIsNone(
                instance.get_latest_materialization_event(hamapi_sensors.key)
            )
            persist.assert_not_called()
            devices.return_value = {
                "devices": [{"name": "Fixture", "serialno": "fixture:1"}]
            }
            self.assertTrue(initialize.initialize(instance, job))
            self.assertIsNotNone(
                instance.get_latest_materialization_event(hamapi_sensors.key)
            )
            self.assertFalse(initialize.initialize(instance, job))
            self.assertEqual(instance.get_runs_count(), 2)
