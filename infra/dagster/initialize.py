"""Compose post-start initialization; exits after checking or registering catalogs."""

import logging
import time

import dagster as dg
from dagster._api.list_repositories import sync_list_repositories_grpc
from dagster._core.errors import DagsterUserCodeUnreachableError
from dagster._grpc.client import DagsterGrpcClient
from infra.dagster.definitions import configured_database
from infra.dagster.ham.definitions import (
    startup_registration_job as ham_registration_job,
)
from infra.dagster.openmeteo.definitions import (
    startup_registration_job as openmeteo_registration_job,
)

logger = logging.getLogger(__name__)


def initialize(instance: dg.DagsterInstance, job: dg.JobDefinition) -> bool:
    """Skip only when all job assets have materializations; failures remain retryable."""
    keys = job.asset_layer.executable_asset_keys
    if all(instance.get_latest_materialization_event(key) for key in keys):
        logger.info(
            "%s: reference assets are already materialized; skipping.", job.name
        )
        return False
    logger.info("Running %s with its default configuration.", job.name)
    result = job.execute_in_process(instance=instance)
    if not result.success:
        raise RuntimeError(f"{job.name} failed")
    return True


def reload_code_location() -> None:
    # Talk directly to this container's code server: the webserver/daemon may not
    # have started yet. This client is covered by our pinned Dagster version.
    client = DagsterGrpcClient(host="localhost", port=4000)
    for attempt in range(12):
        try:
            client.reload_code(timeout=180)
            sync_list_repositories_grpc(client)
            logger.info("Reloaded the code location to discover registered sensors.")
            return
        except DagsterUserCodeUnreachableError:
            if attempt == 11:
                raise
            logger.warning("Code server unavailable; retrying reload in 5 seconds.")
            time.sleep(5)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    database = configured_database()
    jobs = [ham_registration_job(database), openmeteo_registration_job(database)]
    with dg.DagsterInstance.get() as instance:
        registered = False
        failed = []
        for job in jobs:
            if job is None:
                continue
            try:
                registered = initialize(instance, job) or registered
            except Exception:
                # One family's failure must not prevent the other from initializing.
                logger.exception("%s failed", job.name)
                failed.append(job.name)
        if registered:
            reload_code_location()
        if failed:
            raise RuntimeError(f"Registration failed: {', '.join(failed)}")


if __name__ == "__main__":
    main()
