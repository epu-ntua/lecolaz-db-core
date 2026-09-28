"""Sensor mapping, task wiring, and optional PostgreSQL integration tests."""

import copy
import unittest

from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError

from app.db.models.sensor import Sensor
from infra.dagster.ham import sensors as pipeline
from infra.dagster.tests.postgres import PostgresTestCase


class SensorTests(unittest.TestCase):
    def test_mapping_preserves_metadata_without_mutating_source(self):
        device = {
            "name": "Room sensor",
            "serialno": "e45:4",
            "location": "source location",
            "id": 42,
            "starting_date": "source date",
            "readings": {"T": 2150},
        }
        original = copy.deepcopy(device)
        row = pipeline.prepare_sensor_rows({"devices": [device]})[0]
        self.assertEqual(set(row), {"name", "external_id", "sensor_family", "sensor_metadata"})
        self.assertEqual(row["sensor_family"], "ham")
        self.assertEqual(row["external_id"], "e45:4")
        self.assertEqual(row["name"], "Room sensor")
        self.assertEqual(
            row["sensor_metadata"],
            {k: v for k, v in device.items() if k not in ("name", "serialno")},
        )
        self.assertEqual(device, original)

    def test_invalid_responses_fail(self):
        for response in (
            None,
            {},
            {"error": "unauthorized"},
            {"devices": {}},
            {"devices": [None]},
            {"devices": [{"name": "x"}]},
            {"devices": [{"name": "", "serialno": "x"}]},
        ):
            with self.subTest(response=response), self.assertRaises(ValueError):
                pipeline.prepare_sensor_rows(response)

    def test_duplicate_serials_fail(self):
        device = {"name": "Room", "serialno": "x"}
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            pipeline.prepare_sensor_rows({"devices": [device, device]})

    def test_empty_list_is_noop(self):
        self.assertEqual(pipeline.prepare_sensor_rows({"devices": []}), [])
        self.assertEqual(
            pipeline.persist_sensor_rows(None, []),
            {"selected": 0, "inserted_or_updated": 0, "verified": 0},
        )


class SensorPostgresTests(PostgresTestCase):
    def setUp(self):
        super().setUp()
        self.rows = pipeline.prepare_sensor_rows(
            {"devices": [{"name": "Room", "serialno": "e45:4", "reading": 1}]}
        )

    def stored(self):
        with self.engine.connect() as conn:
            return conn.execute(select(Sensor).order_by(Sensor.sensor_family)).mappings().all()

    def test_upsert_preserves_defaults_local_fields_and_other_families(self):
        self.assertEqual(
            pipeline.persist_sensor_rows(self.engine, self.rows)["inserted_or_updated"], 1
        )
        initial = self.stored()[0]
        self.assertIsNotNone(initial["id"])
        self.assertIsNone(initial["location"])
        self.assertIsNone(initial["space"])
        self.assertEqual(initial["starting_date"].year, 2026)
        with self.engine.begin() as conn:
            conn.execute(update(Sensor).values(location="Office", space="A"))
            conn.execute(
                insert(Sensor).values(sensor_family="other", external_id="e45:4", name="Other")
            )
        before = self.stored()
        self.assertEqual(
            pipeline.persist_sensor_rows(self.engine, self.rows)["inserted_or_updated"], 0
        )
        self.assertEqual(self.stored(), before)
        updated = pipeline.prepare_sensor_rows(
            {"devices": [{"name": "Renamed", "serialno": "e45:4", "reading": 2}]}
        )
        self.assertEqual(
            pipeline.persist_sensor_rows(self.engine, updated)["inserted_or_updated"], 1
        )
        after = self.stored()
        for field in ("id", "location", "space", "created_at", "starting_date"):
            self.assertEqual(after[0][field], before[0][field])
        self.assertEqual(after[0]["name"], "Renamed")
        self.assertEqual(after[0]["sensor_metadata"], {"reading": 2})
        self.assertEqual(after[1], before[1])

    def test_batch_failure_rolls_back(self):
        invalid = {**self.rows[0], "external_id": "bad", "name": None}
        with self.assertRaises(IntegrityError):
            pipeline.persist_sensor_rows(self.engine, self.rows + [invalid])
        self.assertEqual(self.stored(), [])

    def test_import_preserves_devices_absent_from_the_response(self):
        pipeline.persist_sensor_rows(self.engine, self.rows)
        original = self.stored()[0]
        pipeline.persist_sensor_rows(
            self.engine,
            pipeline.prepare_sensor_rows({"devices": [{"name": "New", "serialno": "e45:5"}]}),
        )
        stored = {row["external_id"]: row for row in self.stored()}
        self.assertEqual(set(stored), {"e45:4", "e45:5"})
        self.assertEqual(stored["e45:4"], original)
