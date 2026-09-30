"""OpenMeteo contracts from live 1334/564/232 responses captured 2026-09-30."""

import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch
from uuid import UUID

from app.db.models.observation_type import ObservationType
from app.db.models.observation_value import ObservationValue
from app.db.models.sensor import Sensor
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

import dagster as dg
from infra.dagster.object_storage import S3BytesIOManager
from infra.dagster.openmeteo import catalog, component, observations
from infra.dagster.openmeteo.client import OpenMeteoApi, parse_external_id
from infra.dagster.openmeteo.component import (
    REGISTRATION_KEYS,
    OpenMeteoComponent,
    RegistrationConfig,
    make_sensor_assets,
    observation_asset_key,
    raw_asset_key,
    registration_definitions,
)
from infra.dagster.tests.postgres import PostgresTestCase
from infra.dagster.tests.support import FakeDatabase, build_definitions

FIXTURES = Path(__file__).parent / "fixtures" / "openmeteo"
EXTERNAL_ID = "1334/564/232"
SENSOR_ID = "00000000-0000-0000-0000-000000000011"
TYPE_ID = UUID("00000000-0000-0000-0000-000000000012")
START = datetime(2026, 1, 1, tzinfo=timezone.utc)
DEVICE = {
    "id": SENSOR_ID,
    "external_id": EXTERNAL_ID,
    "name": "Temperature (from 1998)",
    "starting_date": START,
    "sensor_metadata": {"observation_type_key": "5683/14"},
}
CSV = (FIXTURES / "2026-01-01.csv").read_bytes()


def fixture_api():
    documents = {
        "stations/1334/": "station",
        "stations/1334/timeseriesgroups/564/": "group",
        "stations/1334/timeseriesgroups/564/timeseries/232/": "timeseries",
        "variables/5683/": "variable",
        "units/14/": "unit",
    }
    api = Mock()
    api.detail.side_effect = lambda path: json.loads(
        (FIXTURES / (documents[path] + ".json")).read_text()
    )
    api.readings.return_value = CSV
    return api


class MemoryStore:
    bucket = "fixture-bucket"

    def __init__(self):
        self.objects = {}

    def put_object(self, key, data, content_type, *, metadata=None):
        self.objects[key] = (data, metadata)

    def get_object_stream(self, key):
        data, metadata = self.objects[key]
        return Mock(
            headers={f"X-Amz-Meta-{name}": value for name, value in metadata.items()},
            read=Mock(return_value=data),
        )


class OpenMeteoMappingTests(unittest.TestCase):
    def test_registration_defaults_come_from_yaml_and_can_be_overridden(self):
        with patch.object(component, "REGISTRATION_DEFAULTS_PATH") as path:
            path.read_text.return_value = (
                f'external_ids: ["{EXTERNAL_ID}", "{EXTERNAL_ID}"]'
            )
            self.assertEqual(
                RegistrationConfig().external_ids, [EXTERNAL_ID, EXTERNAL_ID]
            )
            path.read_text.side_effect = AssertionError(
                "Explicit config must bypass defaults"
            )
            self.assertEqual(
                RegistrationConfig(external_ids=[EXTERNAL_ID]).external_ids,
                [EXTERNAL_ID],
            )

    def test_registration_yaml_rejects_invalid_lists_and_ids(self):
        for contents in (
            "",
            "external_ids: []",
            "external_ids: not-a-list",
            'external_ids: ["1334/564"]',
        ):
            with (
                self.subTest(contents=contents),
                patch.object(component, "REGISTRATION_DEFAULTS_PATH") as path,
            ):
                path.read_text.return_value = contents
                with self.assertRaises(ValueError):
                    component.load_registration_defaults()

    def test_registration_uses_each_api_level_and_preserves_metadata(self):
        api = fixture_api()
        sensors, types = catalog.prepare_registration(api, [EXTERNAL_ID, EXTERNAL_ID])
        self.assertEqual(len(sensors), 1)
        self.assertEqual(api.detail.call_count, 5)
        sensor, observation_type = sensors[0], types[0]
        self.assertEqual(sensor["name"], "Temperature (from 1998)")
        self.assertEqual(sensor["location"], "SRID=4326;POINT (23.78743 37.97385)")
        self.assertNotIn("starting_date", sensor)
        self.assertEqual(sensor["sensor_metadata"]["observation_type_key"], "5683/14")
        self.assertEqual(sensor["sensor_metadata"]["timeseries"]["time_step"], "10min")
        self.assertEqual(observation_type["label"], "Air temperature")
        self.assertEqual(observation_type["unit"], "°C")
        self.assertEqual(observation_type["key"], "5683/14")
        self.assertIn(
            "el", observation_type["type_metadata"]["variable"]["translations"]
        )

    def test_invalid_ids_and_entity_relationships(self):
        for value in (
            "",
            "1334/564",
            "1334/564/232/",
            "0/564/232",
            "1334/../232",
            "01334/564/232",
            None,
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_external_id(value)
        with self.assertRaises(ValueError):
            catalog.prepare_registration(fixture_api(), [])
        api = fixture_api()
        original = api.detail.side_effect
        api.detail.side_effect = lambda p: (
            {**original(p), "timeseries_group": 999}
            if p.endswith("232/")
            else original(p)
        )
        with self.assertRaisesRegex(ValueError, "parent"):
            catalog.prepare_registration(api, [EXTERNAL_ID])

    def test_live_sample_and_csv_boundary_missing_flag_duplicate_handling(self):
        rows, counts = observations.prepare_rows(
            CSV, SENSOR_ID, TYPE_ID, START, START + timedelta(days=1)
        )
        self.assertEqual(len(rows), 144)
        self.assertEqual(rows[0]["value"], 3)
        self.assertEqual(rows[-1]["value"], -0.1)
        self.assertEqual({r["observation_type_id"] for r in rows}, {TYPE_ID})
        sample = b"2026-01-01 00:00,1,SUSPECT\n2026-01-01 00:00,1,\n2026-01-01 01:00,,\n2026-01-02 00:00,9,\n"
        rows, counts = observations.prepare_rows(
            sample, SENSOR_ID, TYPE_ID, START, START + timedelta(days=1)
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(
            counts,
            {
                "returned_rows": 4,
                "missing_values": 1,
                "outside_interval": 1,
                "identical_duplicates": 1,
                "flagged_rows": 1,
            },
        )

    def test_malformed_csv_fails_before_writes(self):
        for data in (
            b"<html>Error</html>",
            b"2026-01-01 00:00,nan,",
            b"2026-01-01 00:00,inf,",
            b"2026-01-01 00:00,1,\n2026-01-01 00:00,2,",
            b"timestamp,value,flags",
        ):
            with self.subTest(data=data), self.assertRaises(ValueError):
                observations.prepare_rows(
                    data, SENSOR_ID, TYPE_ID, START, START + timedelta(days=1)
                )

    def test_http_configuration_and_utc_query(self):
        with patch("infra.dagster.openmeteo.client.urllib3.PoolManager") as manager:
            pool = manager.return_value.__enter__.return_value
            pool.request.return_value = Mock(status=200, data=CSV)
            self.assertEqual(
                OpenMeteoApi().readings(EXTERNAL_ID, START, START + timedelta(days=1)),
                CSV,
            )
            call = pool.request.call_args
            self.assertIn(
                "1334/timeseriesgroups/564/timeseries/232/data/", call.args[1]
            )
            self.assertEqual(call.kwargs["fields"]["timezone"], "UTC")
            retry = manager.call_args.kwargs["retries"]
            self.assertEqual(retry.total, 4)
            self.assertTrue(retry.is_retry("GET", 503))
            self.assertTrue(retry.is_retry("GET", 429))
            self.assertFalse(retry.is_retry("GET", 404))
            pool.request.return_value.status = 404
            with self.assertRaisesRegex(ValueError, "404"):
                OpenMeteoApi().detail("stations/1334/")


class OpenMeteoDagsterTests(unittest.TestCase):
    def setUp(self):
        self.api = fixture_api()
        self.memory = MemoryStore()
        self.io = S3BytesIOManager()
        self.instance = dg.DagsterInstance.ephemeral()
        self.addCleanup(self.instance.dispose)
        self.writes = []

    def execute(self, *, selected=None, device=DEVICE):
        def store(_):
            return self.memory

        def persist(engine, rows):
            self.writes.append(rows)
            return {"selected": len(rows), "inserted_or_updated": len(rows)}

        with (
            patch.object(S3BytesIOManager, "store", store),
            patch.object(catalog, "load_references", return_value=(device, TYPE_ID)),
            patch.object(observations, "persist_rows", persist),
            patch.object(dg.RetryPolicy, "calculate_delay", return_value=0),
        ):
            return dg.materialize(
                make_sensor_assets(device, 4),
                partition_key="2026-01-01",
                selection=selected,
                resources={
                    "database": FakeDatabase(),
                    "openmeteo_api": dg.ResourceDefinition.hardcoded_resource(self.api),
                    "raw_csv_io_manager": self.io,
                },
                instance=self.instance,
                raise_on_error=False,
            )

    def test_raw_then_load_and_separate_replay_without_api(self):
        result = self.execute()
        self.assertTrue(result.success)
        self.assertEqual(len(result.get_asset_materialization_events()), 2)
        self.assertEqual(len(self.writes[0]), 144)
        key = f"sensors/openmeteo/raw/{SENSOR_ID}/2026-01-01.csv"
        self.assertEqual(self.memory.objects[key][0], CSV)
        self.api.readings.reset_mock()
        self.api.readings.side_effect = AssertionError("Replay must not fetch")
        replay = self.execute(selected=[observation_asset_key(SENSOR_ID)])
        self.assertTrue(replay.success)
        self.api.readings.assert_not_called()
        self.assertEqual(len(self.writes), 2)

    def test_first_day_clips_and_empty_load_does_not_materialize(self):
        device = {**DEVICE, "starting_date": START + timedelta(hours=12)}
        self.assertTrue(self.execute(device=device).success)
        self.assertEqual(len(self.writes[0]), 72)
        self.assertEqual(self.api.readings.call_args.args[1], device["starting_date"])
        self.api.readings.return_value = b""
        result = self.execute()
        self.assertTrue(result.success)
        self.assertEqual(len(result.get_asset_materialization_events()), 1)
        self.assertEqual(len(self.writes), 1)

    def test_corrupt_or_stale_artifact_cannot_load(self):
        self.assertTrue(self.execute().success)
        key = next(iter(self.memory.objects))
        saved = self.memory.objects[key]
        self.memory.objects[key] = (b"corrupted", saved[1])
        self.assertFalse(
            self.execute(selected=[observation_asset_key(SENSOR_ID)]).success
        )
        self.memory.objects[key] = saved
        changed = {**DEVICE, "starting_date": START + timedelta(hours=1)}
        self.assertFalse(
            self.execute(
                selected=[observation_asset_key(SENSOR_ID)], device=changed
            ).success
        )
        self.assertEqual(len(self.writes), 1)

    def test_fetch_step_retries_transient_failure(self):
        self.api.readings.side_effect = [OSError("temporary"), CSV]
        self.assertTrue(self.execute().success)
        self.assertEqual(self.api.readings.call_count, 2)

    def test_failed_raw_step_never_runs_observation_load(self):
        self.api.readings.side_effect = OSError("API unavailable")
        result = self.execute()
        self.assertFalse(result.success)
        self.assertEqual(self.writes, [])
        self.assertEqual(self.memory.objects, {})
        self.assertEqual(result.get_asset_materialization_events(), [])

    def test_upstream_selection_materializes_both_partitions(self):
        selection = dg.AssetSelection.from_coercible(
            f'+key:"sensors/openmeteo/observation_values/{SENSOR_ID}"'
        )
        result = self.execute(selected=selection)
        self.assertTrue(result.success)
        self.assertEqual(
            [event.asset_key for event in result.get_asset_materialization_events()],
            [raw_asset_key(SENSOR_ID), observation_asset_key(SENSOR_ID)],
        )

    def test_registration_default_and_resource_scope(self):
        external_ids = component.load_registration_defaults()
        prepared = catalog.prepare_registration(self.api, [EXTERNAL_ID])
        job = build_definitions().resolve_job_def("register_openmeteo_sensors")
        self.assertEqual(
            set(job.resource_defs), {"database", "openmeteo_api", "io_manager"}
        )
        with (
            patch.object(catalog, "prepare_registration", return_value=prepared) as prepare,
            patch.object(catalog, "persist_registration", return_value={}) as persist,
        ):
            result = job.execute_in_process(
                resources={
                    "openmeteo_api": dg.ResourceDefinition.hardcoded_resource(self.api),
                }
            )
        self.assertTrue(result.success)
        self.assertEqual(prepare.call_args.args[1], external_ids)
        self.assertEqual(persist.call_args.args[1][0]["external_id"], EXTERNAL_ID)

    def test_registration_job_and_definitions(self):
        with patch.object(
            catalog, "persist_registration", return_value={"sensors": {"selected": 1}}
        ) as persist:
            job = registration_definitions(
                {"database": FakeDatabase(), "openmeteo_api": OpenMeteoApi()}
            ).resolve_job_def("register_openmeteo_sensors")
            result = job.execute_in_process(
                run_config={
                    "ops": {
                        "register_sensors": {"config": {"external_ids": [EXTERNAL_ID]}}
                    }
                },
                resources={
                    "database": FakeDatabase(),
                    "openmeteo_api": dg.ResourceDefinition.hardcoded_resource(self.api),
                },
            )
        self.assertTrue(result.success)
        persist.assert_called_once()
        defs = dg.Definitions.merge(
            OpenMeteoComponent([DEVICE]).build_defs(),
            dg.Definitions(
                resources={
                    "database": FakeDatabase(),
                    "openmeteo_api": OpenMeteoApi(),
                    "raw_csv_io_manager": self.io,
                }
            ),
        )
        dg.Definitions.validate_loadable(defs)
        registration, raw, values = list(defs.assets)
        self.assertEqual(registration.keys, set(REGISTRATION_KEYS))
        self.assertEqual(raw.asset_deps[raw.key], set(REGISTRATION_KEYS))
        self.assertEqual(values.asset_deps[values.key], {raw.key})
        self.assertEqual(
            values.group_names_by_key[values.key], "sensors/openmeteo/observation_values"
        )
        self.assertEqual(raw.backfill_policy.max_partitions_per_run, 1)
        self.assertEqual(raw.partitions_def, values.partitions_def)
        for asset in (raw, values):
            self.assertIn(DEVICE["name"], asset.descriptions_by_key[asset.key])
            self.assertIn(EXTERNAL_ID, asset.descriptions_by_key[asset.key])

    def test_downstream_automation_waits_for_missing_raw_partition(self):
        defs = dg.Definitions.merge(
            OpenMeteoComponent([DEVICE]).build_defs(),
            dg.Definitions(
                resources={
                    "database": FakeDatabase(),
                    "openmeteo_api": OpenMeteoApi(),
                    "raw_csv_io_manager": self.io,
                }
            ),
        )
        key = observation_asset_key(SENSOR_ID)
        cursor = None
        # Evaluate only the downstream asset, so the missing parent is not requested.
        for moment in ("2026-01-01T23:59", "2026-01-02T04:00"):
            result = dg.evaluate_automation_conditions(
                defs,
                instance=self.instance,
                cursor=cursor,
                asset_selection=dg.AssetSelection.assets(key),
                evaluation_time=datetime.fromisoformat(moment).replace(
                    tzinfo=timezone.utc
                ),
            )
            cursor = result.cursor
            self.assertEqual(result.get_requested_partitions(key), set())
        self.instance.report_runless_asset_event(
            dg.AssetMaterialization(raw_asset_key(SENSOR_ID), partition="2026-01-01")
        )
        result = dg.evaluate_automation_conditions(
            defs,
            instance=self.instance,
            cursor=cursor,
            asset_selection=dg.AssetSelection.assets(key),
            evaluation_time=datetime(2026, 1, 2, 5, tzinfo=timezone.utc),
        )
        self.assertEqual(result.get_requested_partitions(key), {"2026-01-01"})

    def test_automation_grace_and_downstream_readiness(self):
        for key in REGISTRATION_KEYS:
            self.instance.report_runless_asset_event(dg.AssetMaterialization(key))
        defs = dg.Definitions.merge(
            OpenMeteoComponent([DEVICE]).build_defs(),
            dg.Definitions(
                resources={
                    "database": FakeDatabase(),
                    "openmeteo_api": OpenMeteoApi(),
                    "raw_csv_io_manager": self.io,
                }
            ),
        )
        cursor = None
        for moment, expected in (
            ("2026-01-01T23:59", set()),
            ("2026-01-02T03:59", set()),
            ("2026-01-02T04:00", {"2026-01-01"}),
        ):
            result = dg.evaluate_automation_conditions(
                defs,
                instance=self.instance,
                cursor=cursor,
                evaluation_time=datetime.fromisoformat(moment).replace(
                    tzinfo=timezone.utc
                ),
            )
            cursor = result.cursor
            self.assertEqual(
                result.get_requested_partitions(raw_asset_key(SENSOR_ID)), expected
            )
            self.assertEqual(
                result.get_requested_partitions(observation_asset_key(SENSOR_ID)),
                expected,
            )


class OpenMeteoPostgresTests(PostgresTestCase):
    def test_registration_and_load_idempotence_preserve_local_fields(self):
        sensor_rows, type_rows = catalog.prepare_registration(
            fixture_api(), [EXTERNAL_ID]
        )
        catalog.persist_registration(self.engine, sensor_rows, type_rows)
        device = catalog.load_sensor_catalog(self.engine)[0]
        sensor, type_id = catalog.load_references(self.engine, device)
        self.assertEqual(device["starting_date"], START)
        local_start = START + timedelta(hours=1)
        with self.engine.begin() as conn:
            conn.execute(
                update(Sensor).values(starting_date=local_start, space="local")
            )
        summary = catalog.persist_registration(self.engine, sensor_rows, type_rows)
        self.assertEqual(summary["sensors"]["inserted_or_updated"], 0)
        self.assertEqual(summary["observation_types"]["inserted_or_updated"], 0)
        with self.engine.connect() as conn:
            stored = conn.execute(select(Sensor)).mappings().one()
        self.assertEqual(stored["id"], sensor["id"])
        self.assertEqual(stored["location"], sensor_rows[0]["location"])
        self.assertEqual(stored["space"], "local")
        self.assertEqual(stored["starting_date"], local_start)
        rows, _ = observations.prepare_rows(
            CSV, device["id"], type_id, local_start, START + timedelta(days=1)
        )
        self.assertEqual(
            observations.persist_rows(self.engine, rows)["inserted_or_updated"], 138
        )
        self.assertEqual(
            observations.persist_rows(self.engine, rows)["inserted_or_updated"], 0
        )
        with self.engine.connect() as conn:
            self.assertEqual(len(conn.execute(select(ObservationValue)).all()), 138)
        with self.assertRaisesRegex(ValueError, "starting_date changed"):
            catalog.load_references(self.engine, device)

    def test_registration_failure_rolls_back_both_tables(self):
        sensor_rows, type_rows = catalog.prepare_registration(
            fixture_api(), [EXTERNAL_ID]
        )
        sensor_rows[0]["name"] = None
        with self.assertRaises(IntegrityError):
            catalog.persist_registration(self.engine, sensor_rows, type_rows)
        with self.engine.connect() as conn:
            self.assertEqual(conn.execute(select(ObservationType)).all(), [])
            self.assertEqual(conn.execute(select(Sensor)).all(), [])
