"""Exercise queued runs through the webserver in the disposable fixture stack.

Run inside dagster-code, then restart services and run with --after-restart.
"""

import json
import os
from pathlib import Path
import sys
import time

import psycopg
from urllib.request import Request, urlopen

from dagster import AssetKey, DagsterInstance, RunsFilter
from infra.dagster.definitions import observation_asset_key
from infra.dagster.ham.sensors import load_sensor_catalog
from sqlalchemy import select, update, delete
from app.db.models.sensor import Sensor
from datetime import datetime, timezone
from uuid import UUID

from app.db.models.observation_value import ObservationValue
from infra.dagster.resources import LeColazDatabase

STATE_FILE = Path("/opt/dagster/storage/deployment-test.json")


def graphql(query, variables=None):
    request = Request("http://dagster-webserver:3000/graphql",
                      data=json.dumps({"query": query, "variables": variables or {}}).encode(),
                      headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=15) as response:
        body = json.load(response)
    if body.get("errors"):
        raise AssertionError(body["errors"])
    return body["data"]


def launch(job_name, partition=None, sensor_id=None):
    selector = {"repositoryLocationName": "lecolaz", "repositoryName": "__repository__",
                "pipelineName": job_name}
    if sensor_id:
        selector["assetSelection"] = [{"path": ["observation_values", sensor_id]}]
    params = {"selector": selector, "runConfigData": {}}
    if partition:
        params["executionMetadata"] = {"tags": [{"key": "dagster/partition", "value": partition}]}
    data = graphql('''mutation($params: ExecutionParams!) {
      launchPipelineExecution(executionParams: $params) {
        __typename ... on LaunchRunSuccess { run { runId } }
        ... on PythonError { message } ... on RunConfigValidationInvalid { errors { message } }
      }
    }''', {"params": params})["launchPipelineExecution"]
    assert data["__typename"] == "LaunchRunSuccess", data
    run_id = data["run"]["runId"]
    with DagsterInstance.get() as instance:
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            run = instance.get_run_by_id(run_id)
            if run.is_finished:
                assert run.is_success, f"{job_name}: {run.status} ({run_id})"
                print(f"{job_name}: SUCCESS ({run_id})", flush=True)
                return run_id
            time.sleep(1)
    raise AssertionError(f"Run did not complete within 120 seconds: {run_id}")


def backfill(sensor_id, partition_keys, expect_empty=False):
    result = graphql('''mutation($params: LaunchBackfillParams!) {
      launchPartitionBackfill(backfillParams: $params) {
        __typename ... on LaunchBackfillSuccess { backfillId }
        ... on PythonError { message }
      }
    }''', {"params": {"assetSelection": [{"path": ["observation_values", sensor_id]}],
                    "partitionNames": partition_keys}})["launchPartitionBackfill"]
    assert result["__typename"] == "LaunchBackfillSuccess", result
    backfill_id = result["backfillId"]
    with DagsterInstance.get() as instance:
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            runs = instance.get_runs(filters=RunsFilter(tags={"dagster/backfill": backfill_id}))
            assert not any(run.is_finished and not run.is_success for run in runs), runs
            if len(runs) == len(partition_keys) and all(run.is_success for run in runs):
                # Asset backfills use range tags even for one-partition runs.
                assert all(run.tags["dagster/asset_partition_range_start"] ==
                           run.tags["dagster/asset_partition_range_end"] for run in runs)
                assert {run.tags["dagster/asset_partition_range_start"] for run in runs} == set(partition_keys)
                if expect_empty:
                    state = instance.get_backfill(backfill_id)
                    if state.status.value in ("REQUESTED", "IN_PROGRESS"):
                        time.sleep(1)
                        continue
                    assert state.status.value == "COMPLETED_FAILED", state.status
                    assert not set(partition_keys) & instance.get_materialized_partitions(observation_asset_key(sensor_id))
                    print(f"Empty backfill: successful runs, missing partitions, {state.status.value}", flush=True)
                print(f"Targeted asset backfill runs: SUCCESS ({backfill_id})", flush=True)
                return [run.run_id for run in runs]
            time.sleep(1)
    raise AssertionError(f"Backfill did not complete: {backfill_id}")


def fixture_database():
    return LeColazDatabase(host="postgres", database="dagster_fixture", username="fixture", password="fixture")


def stored_observations():
    with fixture_database().engine() as engine, engine.connect() as connection:
        return [dict(row) for row in connection.execute(
            select(ObservationValue).order_by(ObservationValue.id),
        ).mappings()]


def loaded_keys():
    data = graphql('''query {
      repositoryOrError(repositorySelector: {repositoryLocationName: "lecolaz", repositoryName: "__repository__"}) {
        __typename ... on Repository { assetNodes { assetKey { path } } }
        ... on PythonError { message }
      }
    }''')["repositoryOrError"]
    assert data["__typename"] == "Repository", data
    return {tuple(node["assetKey"]["path"]) for node in data["assetNodes"]}


def reload_location():
    data = graphql('''mutation { reloadRepositoryLocation(repositoryLocationName: "lecolaz") {
      __typename ... on PythonError { message }
    }}''')["reloadRepositoryLocation"]
    assert data["__typename"] == "WorkspaceLocationEntry", data


def verify_metadata_database():
    """Metadata uses the shared server but a dedicated unprivileged database owner."""
    username = os.environ["DAGSTER_POSTGRES_USER"]
    with psycopg.connect(host="postgres", dbname=os.environ["DAGSTER_POSTGRES_DB"],
                        user=username, password=os.environ["DAGSTER_POSTGRES_PASSWORD"]) as connection:
        assert connection.execute("SELECT current_database()").fetchone()[0] != "dagster_fixture"
        privileges = connection.execute(
            "SELECT rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls "
            "FROM pg_roles WHERE rolname = current_user"
        ).fetchone()
        assert not any(privileges), privileges
        assert connection.execute("SELECT to_regclass('public.runs')").fetchone()[0]
        assert connection.execute("SELECT to_regclass('public.sensors')").fetchone()[0] is None
        assert connection.execute("SELECT count(*) FROM pg_extension WHERE extname='timescaledb'").fetchone()[0] == 0
    with psycopg.connect(host="postgres", dbname="dagster_fixture", user=username,
                        password=os.environ["DAGSTER_POSTGRES_PASSWORD"]) as connection:
        assert not connection.execute("SELECT has_table_privilege(current_user, 'public.sensors', 'SELECT')").fetchone()[0]
    print("Shared PostgreSQL: separate metadata database and non-superuser role verified.", flush=True)


def main():
    assert os.environ.get("LECOLAZ_POSTGRES_DB") == "dagster_fixture", "Use only the disposable fixture stack"
    verify_metadata_database()
    if "--after-restart" in sys.argv:
        state = json.loads(STATE_FILE.read_text())
        with DagsterInstance.get() as instance:
            for run_id in state["runs"]:
                assert instance.get_run_by_id(run_id).is_success
                assert instance.all_logs(run_id)
            assert instance.get_materialized_partitions(observation_asset_key(state["deleted_id"])) == {"2026-03-15"}
        assert list(Path("/opt/dagster/storage/compute_logs").rglob("*.out")), "Compute logs lost"
        assert ("observation_values", state["deleted_id"]) not in loaded_keys()
        assert ("observation_values", state["sensor_ids"][0]) in loaded_keys()
        print("Run history, retained deleted-asset history, current definitions, and logs survived restart.")
        return

    run_ids = [launch("lecolaz_services_smoke_test"), launch("hamapi_initialize")]
    with fixture_database().engine() as engine:
        sensor_ids = [row["id"] for row in load_sensor_catalog(engine)]
        assert len(sensor_ids) == 2, sensor_ids
        with engine.begin() as connection:
            for sensor_id, start in zip(sensor_ids, [datetime(2026,1,1,14,tzinfo=timezone.utc),
                                                    datetime(2026,3,15,tzinfo=timezone.utc)]):
                connection.execute(update(Sensor).where(Sensor.id == UUID(sensor_id)).values(starting_date=start))
    reload_location()
    assert all(("observation_values", sensor_id) in loaded_keys() for sensor_id in sensor_ids)
    keys = ["2026-01-01", "2026-01-02"]
    run_ids.extend(backfill(sensor_ids[0], keys))
    run_ids.extend(backfill(sensor_ids[0], ["2026-01-03"], expect_empty=True))
    before = stored_observations()
    assert len(before) == 2, before
    assert {str(row["sensor_id"]) for row in before} == {sensor_ids[0]}
    assert {row["timestamp"].isoformat() for row in before} == {"2026-01-01T14:00:00+00:00", "2026-01-02T00:00:00+00:00"}
    assert all(row["value"] == 21.5 for row in before), before
    run_ids.append(launch("__ASSET_JOB", keys[0], sensor_ids[0]))
    assert stored_observations() == before, "Rerun changed existing observation identities"
    with DagsterInstance.get() as instance:
        assert instance.get_materialized_partitions(observation_asset_key(sensor_ids[0])) == set(keys)

    # Exercise physical deletion only in the disposable application database.
    deleted_id = sensor_ids[1]
    run_ids.append(launch("__ASSET_JOB", "2026-03-15", deleted_id))
    with fixture_database().engine() as engine, engine.begin() as connection:
        connection.execute(delete(Sensor).where(Sensor.id == UUID(deleted_id)))
    reload_location()
    assert ("observation_values", deleted_id) not in loaded_keys()
    assert stored_observations() == before, "Application FK should cascade only the deleted sensor's readings"
    with DagsterInstance.get() as instance:
        assert instance.get_materialized_partitions(observation_asset_key(deleted_id)) == {"2026-03-15"}
    STATE_FILE.write_text(json.dumps({"runs": run_ids, "sensor_ids": sensor_ids, "deleted_id": deleted_id}))
    print("Factory reload, partial day, native backfill, rerun, and physical deletion passed; ready for restart check.")


if __name__ == "__main__":
    main()
