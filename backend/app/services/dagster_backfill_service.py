"""Fill missing sensor-owned assets using only Dagster's existing execution state.

Ownership is the asset's sensor_id metadata, not its name, stage or sensor family.
The GraphQL SDK has no public backfill API; keep its version-pinned query interface
here and validate these documents against the deployed schema in tests.
"""

import logging

from dagster_graphql import DagsterGraphQLClient, DagsterGraphQLClientError

from app.core.config import settings
from app.services.dagster_service import create_client

LOGGER = logging.getLogger(__name__)
PAGE_SIZE = 100

DISCOVER_ASSETS = """query SensorAssets {
  assetNodes {
    assetKey { path }
    repository { location { name } }
    isMaterializable
    metadataEntries { label ... on TextMetadataEntry { text } }
  }
}"""

ASSET_STATE = """query SensorAssetState($keys: [AssetKeyInput!]!) {
  assetNodes(assetKeys: $keys) {
    assetKey { path }
    repository { location { name } }
    isPartitioned
    partitionDefinition { type description }
    dependencies { asset { assetKey { path } } partitionMapping { className } }
    partitionKeys
    latestMaterializationByPartition { partition }
    assetMaterializations(limit: 1) { timestamp }
  }
}"""

ACTIVE_BACKFILLS = """query ActiveSensorBackfills($cursor: String, $limit: Int!) {
  partitionBackfillsOrError(
    filters: {statuses: [REQUESTED, CANCELING, FAILING]}, cursor: $cursor, limit: $limit
  ) {
    __typename
    ... on PartitionBackfills {
      results {
        id isAssetBackfill assetSelection { path }
        partitionSet {
          pipelineName
          repositoryOrigin { repositoryLocationName repositoryName }
        }
      }
    }
    ... on PythonError { message }
  }
}"""

ACTIVE_RUNS = """query ActiveSensorRuns($cursor: String, $limit: Int!) {
  runsOrError(filter: {statuses: [NOT_STARTED, QUEUED, MANAGED, STARTING, STARTED, CANCELING]},
              cursor: $cursor, limit: $limit) {
    __typename
    ... on Runs {
      results {
        id assetSelection { path } assets { key { path } } tags { key value }
      }
    }
    ... on PythonError { message }
  }
}"""

BACKFILL_TARGETS = """query SensorBackfillTargets($id: String!, $key: AssetKeyInput!) {
  partitionBackfillOrError(backfillId: $id) {
    __typename
    ... on PartitionBackfill {
      isValidSerialization
      partitionsTargetedForAssetKey(assetKey: $key) {
        partitionKeys ranges { start end }
      }
    }
    ... on PythonError { message }
  }
}"""

JOB_PARTITIONS = """query SensorJobBackfillPartitions($id: String!) {
  partitionBackfillOrError(backfillId: $id) {
    __typename
    ... on PartitionBackfill { partitionNames }
    ... on PythonError { message }
  }
}"""

JOB_ASSETS = """query SensorJobAssets($selector: PipelineSelector!) {
  assetNodes(pipeline: $selector) { assetKey { path } }
}"""

LAUNCH_BACKFILL = """mutation SensorHistoryBackfill($params: LaunchBackfillParams!) {
  launchPartitionBackfill(backfillParams: $params) {
    __typename
    ... on LaunchBackfillSuccess { backfillId }
    ... on PythonError { message }
  }
}"""


def _expect(result: dict, typename: str) -> dict:
    if result["__typename"] != typename:
        raise ValueError(
            f"Dagster returned {result['__typename']} instead of {typename}: "
            f"{result.get('message', 'No details returned')}"
        )
    return result


def _pages(client: DagsterGraphQLClient, query: str, field: str, typename: str) -> list[dict]:
    rows = []
    cursor = None
    while True:
        page = _expect(client._execute(query, {"cursor": cursor, "limit": PAGE_SIZE})[field], typename)
        results = page["results"]
        rows.extend(results)
        if len(results) < PAGE_SIZE:
            return rows
        next_cursor = results[-1]["id"]
        if next_cursor == cursor:
            raise ValueError("Dagster pagination did not advance")
        cursor = next_cursor


def _discover(client: DagsterGraphQLClient, sensor_ids: set[str]) -> dict[str, list[tuple[str, ...]]]:
    owned = {sensor_id: [] for sensor_id in sensor_ids}
    for node in client._execute(DISCOVER_ASSETS)["assetNodes"]:
        if node["repository"]["location"]["name"] != settings.DAGSTER_CODE_LOCATION:
            continue
        metadata = {entry["label"]: entry.get("text") for entry in node["metadataEntries"]}
        sensor_id = metadata.get("sensor_id")
        if sensor_id in owned and node["isMaterializable"]:
            owned[sensor_id].append(tuple(node["assetKey"]["path"]))
    return owned


def _backfill_selections(client: DagsterGraphQLClient, backfills: list[dict]) -> list[dict]:
    """Resolve full-job backfills too, including ones with no explicit asset subset."""
    selected = []
    for backfill in backfills:
        selection = backfill["assetSelection"]
        if not backfill["isAssetBackfill"]:
            partition_set = backfill["partitionSet"]
            if partition_set is None:
                raise ValueError("Cannot resolve an active job backfill")
            origin = partition_set["repositoryOrigin"]
            if origin["repositoryLocationName"] != settings.DAGSTER_CODE_LOCATION:
                continue
            if selection is None:
                nodes = client._execute(JOB_ASSETS, {"selector": {
                    **origin, "pipelineName": partition_set["pipelineName"],
                }})["assetNodes"]
                selection = [node["assetKey"] for node in nodes]
        if selection is None:
            raise ValueError("Cannot resolve an active backfill's asset selection")
        selected.append({**backfill, "keys": {tuple(key["path"]) for key in selection}})
    return selected


def _range_keys(keys: list[str], start: str, end: str) -> set[str]:
    # Use Dagster's ordering, including for non-date/static partition keys.
    try:
        first, last = keys.index(start), keys.index(end)
    except ValueError as exc:
        raise ValueError("Active work references a changed partition definition") from exc
    if first > last:
        raise ValueError("Invalid active partition range")
    return set(keys[first:last + 1])


def _busy_partitions(
    client: DagsterGraphQLClient, key: tuple[str, ...], node: dict,
    backfills: list[dict], runs: list[dict],
) -> set[str | None]:
    keys = node["partitionKeys"]
    busy = set()
    for backfill in backfills:
        if key not in backfill["keys"]:
            continue
        if not node["isPartitioned"]:
            busy.add(None)
        elif backfill["isAssetBackfill"]:
            detail = _expect(client._execute(BACKFILL_TARGETS, {
                "id": backfill["id"], "key": {"path": list(key)},
            })["partitionBackfillOrError"], "PartitionBackfill")
            if not detail["isValidSerialization"]:
                raise ValueError("Active backfill cannot be read with the current definitions")
            target = detail["partitionsTargetedForAssetKey"]
            if target:
                busy.update(target["partitionKeys"] or [])
                for interval in target["ranges"] or []:
                    busy.update(_range_keys(keys, interval["start"], interval["end"]))
        else:
            detail = _expect(client._execute(JOB_PARTITIONS, {"id": backfill["id"]})[
                "partitionBackfillOrError"
            ], "PartitionBackfill")
            if detail["partitionNames"] is None:
                raise ValueError("Active job backfill has no partition selection")
            busy.update(detail["partitionNames"])
    for run in runs:
        selection = run["assetSelection"]
        if selection is None:
            selection = [asset["key"] for asset in run["assets"]]
        if key not in {tuple(asset["path"]) for asset in selection}:
            continue
        tags = {tag["key"]: tag["value"] for tag in run["tags"]}
        if not node["isPartitioned"]:
            busy.add(None)
        elif "dagster/partition" in tags:
            busy.add(tags["dagster/partition"])
        elif {"dagster/asset_partition_range_start", "dagster/asset_partition_range_end"} <= tags.keys():
            busy.update(_range_keys(keys, tags["dagster/asset_partition_range_start"],
                                    tags["dagster/asset_partition_range_end"]))
        else:
            # A selected asset with no readable partition scope is still active.
            busy.update(keys)
    return busy


def _partition_ranges(keys: list[str], selected: set[str]) -> list[dict]:
    ranges = []
    previous_selected = False
    for key in keys:
        if key in selected:
            if previous_selected:
                ranges[-1]["end"] = key
            else:
                ranges.append({"start": key, "end": key})
        previous_selected = key in selected
    return ranges


def _submit_sensor(
    client: DagsterGraphQLClient, sensor_id: str, paths: list[tuple[str, ...]],
    backfills: list[dict], runs: list[dict],
) -> dict:
    if not paths:
        raise ValueError("No materializable assets with sensor_id metadata were discovered")
    nodes = client._execute(ASSET_STATE, {"keys": [{"path": list(path)} for path in paths]})["assetNodes"]
    states = {tuple(node["assetKey"]["path"]): node for node in nodes
              if node["repository"]["location"]["name"] == settings.DAGSTER_CODE_LOCATION}
    if set(states) != set(paths):
        raise ValueError("Sensor assets changed after the code location reload")
    busy = set().union(*[
        _busy_partitions(client, key, node, backfills, runs) for key, node in states.items()
    ])
    # Same-partition stages can defer just the affected partitions. For mixed
    # definitions (including unpartitioned stages), defer the whole sensor while
    # active: the API must not guess custom upstream/downstream partition mappings.
    definitions = {
        (node["partitionDefinition"]["type"], node["partitionDefinition"]["description"],
         tuple(node["partitionKeys"])) if node["partitionDefinition"] else None
        for node in states.values()
    }
    custom_mapping = any(
        dependency["partitionMapping"]
        and dependency["partitionMapping"]["className"] != "IdentityPartitionMapping"
        for node in states.values() for dependency in node["dependencies"]
        if tuple(dependency["asset"]["assetKey"]["path"]) in states
    )
    defer_all = bool(busy) and (None in busy or len(definitions) > 1 or custom_mapping)
    selection = []
    target_count = 0
    for key, node in states.items():
        if defer_all:
            continue
        if node["isPartitioned"]:
            materialized = {event["partition"] for event in node["latestMaterializationByPartition"] if event}
            missing = set(node["partitionKeys"]) - materialized - busy
            if missing:
                selection.append({"assetKey": {"path": list(key)}, "partitions": {
                    "ranges": _partition_ranges(node["partitionKeys"], missing),
                }})
                target_count += len(missing)
        elif not node["assetMaterializations"]:
            selection.append({"assetKey": {"path": list(key)}})
            target_count += 1
    if not selection:
        return {"sensor_id": sensor_id, "status": "skipped", "target_count": 0,
                "message": "No missing assets or partitions are currently eligible for backfill."}
    result = _expect(client._execute(LAUNCH_BACKFILL, {"params": {
        "partitionsByAssets": selection,
    }})["launchPartitionBackfill"], "LaunchBackfillSuccess")
    return {"sensor_id": sensor_id, "status": "submitted", "backfill_id": result["backfillId"],
            "target_count": target_count}


def _failed(sensor_id: str) -> dict:
    return {"sensor_id": sensor_id, "status": "failed", "target_count": 0,
            "message": "Sensors were saved, but historical import could not be confirmed. "
                       "Re-register to check Dagster and retry missing work."}


def launch_sensor_backfills(sensors: list[dict]) -> list[dict]:
    """Submit at most one backfill per sensor; never retry an ambiguous launch.

    This is a snapshot check, not an atomic reservation. Concurrent registrations
    or Dagster launches can overlap, intentionally without locks or extra state.
    """
    sensor_ids = [str(sensor["id"]) for sensor in sensors]
    if not sensor_ids:
        return []
    errors = (DagsterGraphQLClientError, ValueError, KeyError, TypeError)
    try:
        client = create_client()
        owned = _discover(client, set(sensor_ids))
        backfills = _backfill_selections(client, _pages(
            client, ACTIVE_BACKFILLS, "partitionBackfillsOrError", "PartitionBackfills",
        ))
        runs = _pages(client, ACTIVE_RUNS, "runsOrError", "Runs")
    except errors:
        LOGGER.exception("Sensors saved, but Dagster backfill discovery failed")
        return [_failed(sensor_id) for sensor_id in sensor_ids]
    results = []
    for sensor_id in sensor_ids:
        try:
            results.append(_submit_sensor(client, sensor_id, owned[sensor_id], backfills, runs))
        except errors:
            LOGGER.exception("Sensor %s saved, but Dagster backfill submission failed", sensor_id)
            results.append(_failed(sensor_id))
    return results
