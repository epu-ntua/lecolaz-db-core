"""Exercise production queries/mutations against real, isolated Dagster storage."""

import asyncio
import tempfile
import unittest
from unittest.mock import patch
from uuid import UUID

from dagster import AssetKey, AssetMaterialization, DagsterInstance, DagsterRunStatus
from dagster._core.remote_origin import InProcessCodeLocationOrigin
from dagster._core.types.loadable_target_origin import LoadableTargetOrigin
from dagster._core.workspace.context import WorkspaceProcessContext
from dagster._core.workspace.load_target import InProcessWorkspaceLoadTarget
from dagster_graphql import DagsterGraphQLClientError
from dagster_graphql.schema import create_schema
from graphql import parse, validate

from app.services import dagster_backfill_service as service
from infra.dagster.tests.backfill_fixtures import (
    DAYS, KEYS, MIXED_SENSOR_ID, OFFSET_SENSOR_ID, SENSOR_ID, STATIC_SENSOR_ID, UNPARTITIONED_SENSOR_ID,
    fixture_definitions,
)


class SensorBackfillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = create_schema()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.instance = DagsterInstance.local_temp(temporary.name)
        self.addCleanup(self.instance.dispose)
        origin = InProcessCodeLocationOrigin(
            LoadableTargetOrigin(module_name="infra.dagster.tests.backfill_fixtures", attribute="fixture_definitions"),
            location_name="lecolaz",
        )
        self.workspace = WorkspaceProcessContext(self.instance, InProcessWorkspaceLoadTarget(origin))
        self.addCleanup(self.workspace.__exit__, None, None, None)
        self.addCleanup(patch.stopall)
        patch.object(service.settings, "DAGSTER_CODE_LOCATION", "lecolaz").start()
        patch.object(service, "create_client", return_value=self).start()
        self.calls = []

    def _execute(self, query, variables=None):
        self.calls.append((query, variables))
        result = asyncio.run(self.schema.execute_async(
            query, variable_values=variables,
            context_value=self.workspace.create_request_context(),
        ))
        if result.errors:
            raise AssertionError(result.errors)
        return result.data

    def register(self, *ids):
        return service.launch_sensor_backfills([{"id": UUID(sensor_id)} for sensor_id in (ids or (SENSOR_ID,))])

    def materialized(self, key, *days):
        for day in days:
            self.instance.report_runless_asset_event(AssetMaterialization(key, partition=day))

    def active_run(self, key, day=None, *, status=DagsterRunStatus.QUEUED, tags=None, selection=True):
        job = self.workspace.create_request_context().get_code_location("lecolaz").get_repository(
            "__repository__"
        ).get_full_job("fixture_job")
        return self.instance.create_run_for_job(
            fixture_definitions().resolve_job_def("fixture_job"),
            asset_selection={key} if selection else None, status=status,
            tags=tags if tags is not None else {"dagster/partition": day},
            remote_job_origin=job.get_remote_origin(),
        )

    def target(self, result):
        backfill = self.instance.get_backfill(result["backfill_id"])
        graph = self.workspace.create_request_context().asset_graph
        data = backfill.get_asset_backfill_data(graph)
        return {key: set(subset.get_partition_keys())
                for key, subset in data.target_subset.partitions_subsets_by_asset_key.items()}

    def test_query_documents_match_installed_schema(self):
        for name in ("DISCOVER_ASSETS", "ASSET_STATE", "ACTIVE_BACKFILLS", "ACTIVE_RUNS",
                     "BACKFILL_TARGETS", "JOB_PARTITIONS", "JOB_ASSETS", "LAUNCH_BACKFILL"):
            with self.subTest(query=name):
                self.assertEqual(validate(self.schema.graphql_schema, parse(getattr(service, name))), [])

    def test_arbitrary_three_stage_sensor_launches_once_and_repeat_skips(self):
        first = self.register()[0]
        self.assertEqual(first["status"], "submitted")
        self.assertEqual(first["target_count"], 12)
        self.assertEqual(self.target(first), {key: set(DAYS) for key in KEYS})
        self.assertEqual(self.register()[0]["status"], "skipped")
        self.assertEqual(len(self.instance.get_backfills()), 1)

    def test_missing_downstream_reuses_materialized_upstream_and_excludes_runs(self):
        self.materialized(KEYS[0], DAYS[0])
        for key in KEYS:
            self.materialized(key, DAYS[1])
        self.active_run(KEYS[0], DAYS[2])
        self.active_run(KEYS[2], tags={"dagster/asset_partition_range_start": DAYS[3],
                                "dagster/asset_partition_range_end": DAYS[3]})
        result = self.register()[0]
        self.assertEqual(self.target(result), {key: {DAYS[0]} for key in KEYS[1:]})

    def test_completed_partitions_skip_even_after_a_failed_rerun(self):
        for key in KEYS:
            self.materialized(key, *DAYS)
        self.active_run(KEYS[0], DAYS[0], status=DagsterRunStatus.FAILURE)
        self.assertEqual(self.register()[0]["status"], "skipped")
        self.assertEqual(self.instance.get_backfills(), [])

    def test_terminal_failed_backfill_and_failed_run_do_not_block_retry(self):
        from dagster._core.execution.backfill import BulkActionStatus
        first = self.register()[0]
        backfill = self.instance.get_backfill(first["backfill_id"])
        self.instance.update_backfill(backfill.with_status(BulkActionStatus.COMPLETED_FAILED))
        self.active_run(KEYS[0], DAYS[0], status=DagsterRunStatus.FAILURE)
        second = self.register()[0]
        self.assertEqual(second["status"], "submitted")
        self.assertNotEqual(first["backfill_id"], second["backfill_id"])

    def test_partial_active_backfill_blocks_its_days_for_all_sensor_stages(self):
        self._execute(service.LAUNCH_BACKFILL, {"params": {"partitionsByAssets": [{
            "assetKey": {"path": KEYS[1].path},
            "partitions": {"ranges": [{"start": DAYS[1], "end": DAYS[2]}]},
        }]}})
        result = self.register()[0]
        self.assertEqual(self.target(result), {key: {DAYS[0], DAYS[3]} for key in KEYS})

    def test_pagination_reads_all_active_work(self):
        self.active_run(KEYS[0], DAYS[0])
        self.active_run(KEYS[0], DAYS[1])
        with patch.object(service, "PAGE_SIZE", 1):
            result = self.register()[0]
            self.assertEqual(self.target(result), {key: set(DAYS[2:]) for key in KEYS})
            self.assertEqual(self.register()[0]["status"], "skipped")

    def test_full_job_run_without_explicit_asset_selection_is_excluded(self):
        self.active_run(KEYS[0], DAYS[0], selection=False)
        self.assertEqual(self.target(self.register()[0]), {key: set(DAYS[1:]) for key in KEYS})

    def test_full_job_backfill_without_explicit_asset_selection_is_excluded(self):
        repository = self.workspace.create_request_context().get_code_location("lecolaz").get_repository(
            "__repository__"
        )
        partition_set = next(item for item in repository.get_partition_sets() if item.job_name == "fixture_job")
        launched = self._execute(service.LAUNCH_BACKFILL, {"params": {
            "selector": {
                "partitionSetName": partition_set.name,
                "repositorySelector": {"repositoryLocationName": "lecolaz", "repositoryName": "__repository__"},
            },
            "partitionNames": [DAYS[0]],
        }})["launchPartitionBackfill"]
        self.assertEqual(launched["__typename"], "LaunchBackfillSuccess")
        self.assertEqual(self.target(self.register()[0]), {key: set(DAYS[1:]) for key in KEYS})

    def test_canceling_backfill_remains_excluded_until_terminal(self):
        from dagster._core.execution.backfill import BulkActionStatus
        result = self.register()[0]
        backfill = self.instance.get_backfill(result["backfill_id"])
        self.instance.update_backfill(backfill.with_status(BulkActionStatus.CANCELING))
        self.assertEqual(self.register()[0]["status"], "skipped")
        self.instance.update_backfill(backfill.with_status(BulkActionStatus.CANCELED))
        self.assertEqual(self.register()[0]["status"], "submitted")

    def test_failed_active_work_query_does_not_launch(self):
        execute = self._execute

        def unavailable(query, variables=None):
            if query == service.ACTIVE_RUNS:
                return {"runsOrError": {"__typename": "PythonError", "message": "unavailable"}}
            return execute(query, variables)

        with patch.object(self, "_execute", side_effect=unavailable), self.assertLogs(service.LOGGER, level="ERROR"):
            self.assertEqual(self.register()[0]["status"], "failed")
        self.assertEqual(self.instance.get_backfills(), [])

    def test_active_run_without_partition_scope_defers_sensor(self):
        self.active_run(KEYS[0], tags={})
        self.assertEqual(self.register()[0]["status"], "skipped")

    def test_static_and_unpartitioned_assets_use_same_path(self):
        self.materialized(AssetKey("arbitrary_static"), "a")
        results = self.register(STATIC_SENSOR_ID, UNPARTITIONED_SENSOR_ID)
        self.assertEqual(self.target(results[0]), {AssetKey("arbitrary_static"): {"z", "b"}})
        self.assertEqual(results[1]["status"], "submitted")
        self.assertEqual(results[1]["target_count"], 1)
        self.assertEqual([result["status"] for result in self.register(STATIC_SENSOR_ID, UNPARTITIONED_SENSOR_ID)],
                         ["skipped", "skipped"])

    def test_mixed_definitions_defer_while_a_stage_is_running(self):
        self.instance.create_run_for_job(
            fixture_definitions().resolve_implicit_global_asset_job_def(),
            asset_selection={AssetKey("mixed_daily")}, status=DagsterRunStatus.STARTED,
            tags={"dagster/partition": DAYS[0]},
        )
        self.assertEqual(self.register(MIXED_SENSOR_ID)[0]["status"], "skipped")

    def test_custom_partition_mapping_defers_while_a_stage_is_running(self):
        self.instance.create_run_for_job(
            fixture_definitions().resolve_implicit_global_asset_job_def(),
            asset_selection={AssetKey("offset_source")}, status=DagsterRunStatus.STARTED,
            tags={"dagster/partition": DAYS[1]},
        )
        self.assertEqual(self.register(OFFSET_SENSOR_ID)[0]["status"], "skipped")

    def test_existing_ham_and_openmeteo_factories_are_discovered_without_special_cases(self):
        origin = InProcessCodeLocationOrigin(
            LoadableTargetOrigin(module_name="infra.dagster.tests.backfill_fixtures",
                                 attribute="registered_sensor_definitions"),
            location_name="lecolaz",
        )
        with WorkspaceProcessContext(self.instance, InProcessWorkspaceLoadTarget(origin)) as workspace:
            with patch.object(self, "workspace", workspace):
                results = self.register(SENSOR_ID, STATIC_SENSOR_ID)
                self.assertEqual([result["status"] for result in results], ["submitted", "submitted"])
                for result, family in zip(results, ("ham", "openmeteo")):
                    self.assertEqual(set(self.target(result)), {
                        AssetKey(["sensors", family, stage, result["sensor_id"]])
                        for stage in ("raw", "observation_values")
                    })
                self.assertEqual([result["status"] for result in self.register(SENSOR_ID, STATIC_SENSOR_ID)],
                                 ["skipped", "skipped"])

    def test_discovery_failure_does_not_launch(self):
        with patch.object(service, "create_client", side_effect=DagsterGraphQLClientError("unreachable")):
            with self.assertLogs(service.LOGGER, level="ERROR"):
                self.assertEqual(self.register()[0]["status"], "failed")
        self.assertEqual(self.instance.get_backfills(), [])

    def test_missing_sensor_assets_fail_independently_of_other_sensors(self):
        with self.assertLogs(service.LOGGER, level="ERROR"):
            results = self.register("00000000-0000-0000-0000-000000000099", SENSOR_ID)
        self.assertEqual([result["status"] for result in results], ["failed", "submitted"])

    def test_launch_timeout_is_not_retried_and_next_sensor_still_submits(self):
        execute = self._execute
        launches = 0

        def timed_out(query, variables=None):
            nonlocal launches
            if query == service.LAUNCH_BACKFILL:
                launches += 1
                if launches == 1:
                    # Dagster accepted it, but the HTTP response was lost.
                    execute(query, variables)
                    raise DagsterGraphQLClientError("timeout")
            return execute(query, variables)

        with patch.object(self, "_execute", side_effect=timed_out), self.assertLogs(service.LOGGER, level="ERROR"):
            results = self.register(SENSOR_ID, STATIC_SENSOR_ID)
        self.assertEqual([result["status"] for result in results], ["failed", "submitted"])
        self.assertEqual(launches, 2)
        self.assertEqual(self.register()[0]["status"], "skipped")


if __name__ == "__main__":
    unittest.main()
