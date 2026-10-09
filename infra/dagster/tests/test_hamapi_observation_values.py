"""Reading conversion and optional PostgreSQL upsert checks."""

import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError

from app.db.models.observation_type import ObservationType
from app.db.models.observation_value import ObservationValue
from app.db.models.sensor import Sensor
from app.storage.postgres.observation_value_store import ObservationValueStore
from infra.dagster.ham import observation_values as pipeline
from infra.dagster.ham.sensors import load_sensor_catalog
from infra.dagster.tests.postgres import PostgresTestCase


class ReadingTests(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.end = self.start + timedelta(hours=1)
        self.sensor = {"id": str(uuid4()), "external_id": "e45:1", "sensor_family": "ham"}
        self.types = {"T": str(uuid4())}

    def rows(self, response):
        return pipeline.prepare_observation_rows(
            response, self.sensor, self.types, self.start, self.end
        ).rows

    def test_mapping_and_half_open_interval(self):
        t = self.start.timestamp()
        rows = self.rows(
            {
                "timestamp": [t - 0.01, t, t + 0.99, self.end.timestamp()],
                "T": [1, 21.5, 22, 3],
                "OUT": [0, 0, 0, 0],
            }
        )
        self.assertEqual([r["value"] for r in rows], [21.5, 22])
        self.assertEqual(str(rows[0]["sensor_id"]), self.sensor["id"])
        self.assertEqual(str(rows[0]["observation_type_id"]), self.types["T"])
        self.assertEqual(rows[1]["timestamp"].microsecond, 990000)
        self.assertEqual(set(rows[0]), {"sensor_id", "observation_type_id", "timestamp", "value"})

    def test_invalid_series_and_values(self):
        t = self.start.timestamp()
        for response in (
            {},
            {"error": "denied"},
            {"timestamp": [t], "T": []},
            {"timestamp": [float("nan")], "T": [1]},
            {"timestamp": [t], "T": [float("inf")]},
            {"timestamp": [t], "T": ["last"]},
            {"timestamp": [True], "T": [1]},
            {"timestamp": [t], "T": [True]},
            {"timestamp": [t], "unknown": [1]},
        ):
            with self.subTest(response=response), self.assertRaises(ValueError):
                self.rows(response)

    def test_empty_null_and_duplicates(self):
        t = self.start.timestamp()
        self.assertEqual(self.rows({"timestamp": [], "T": []}), [])
        self.assertEqual(self.rows({"timestamp": [t], "T": [None]}), [])
        self.assertEqual(len(self.rows({"timestamp": [t, t], "T": [1, 1]})), 1)
        self.assertEqual(self.rows({"timestamp": [t, t], "T": [1, 2]})[0]["value"], 2)
        self.assertEqual(
            pipeline.persist_observation_rows(None, []), {"selected": 0, "inserted_or_updated": 0}
        )

    def test_conflicts_use_last_non_missing_value_per_reading_and_summary(self):
        t = self.start.timestamp()
        types = {**self.types, "H": str(uuid4())}
        prepared = pipeline.prepare_observation_rows(
            {"timestamp": [t, t, t], "T": [1, 2, None], "H": [40, 50, 45]},
            self.sensor, types, self.start, self.end,
        )
        values = {str(row["observation_type_id"]): row["value"] for row in prepared.rows}
        self.assertEqual(values, {types["T"]: 2, types["H"]: 45})
        self.assertEqual(prepared.diagnostics["conflicting_duplicate_count"], 2)
        self.assertEqual(prepared.conflicts, [
            {"reading_key": "H", "timestamp": self.start, "values": [40, 50, 45], "selected_value": 45},
            {"reading_key": "T", "timestamp": self.start, "values": [1, 2], "selected_value": 2},
        ])
        humidity, temperature = prepared.reading_summary
        self.assertEqual(humidity["minimum"], 45)
        self.assertEqual(humidity["maximum"], 45)
        self.assertEqual(temperature["selected_rows"], 1)
        self.assertEqual(temperature["minimum"], 2)

    def test_missing_and_matching_values_are_not_conflicts(self):
        for values, expected in (
            ([None, None], []),
            ([None, 0, None], [0]),
            ([1, None], [1]),
            ([None, 1], [1]),
            ([None, 1, None, 1, None], [1]),
        ):
            with self.subTest(values=values):
                prepared = pipeline.prepare_observation_rows(
                    {"timestamp": [self.start.timestamp()] * len(values), "T": values},
                    self.sensor, self.types, self.start, self.end,
                )
                self.assertEqual([row["value"] for row in prepared.rows], expected)
                self.assertEqual(prepared.conflicts, [])
                self.assertEqual(prepared.diagnostics["conflicting_duplicate_count"], 0)
                self.assertEqual(prepared.diagnostics["null_value_count"], values.count(None))

    def test_conflict_group_keeps_final_choice_even_when_it_returns_to_first_value(self):
        t = self.start.timestamp()
        prepared = pipeline.prepare_observation_rows(
            {"timestamp": [t, t, t + 1, t, t, t, t], "T": [1, None, 9, 2, 1, 1, None]},
            self.sensor, self.types, self.start, self.end,
        )
        self.assertEqual([row["value"] for row in prepared.rows], [1, 9])
        self.assertEqual(prepared.diagnostics["conflicting_duplicate_count"], 1)
        self.assertEqual(prepared.diagnostics["identical_duplicate_count"], 1)
        self.assertEqual(prepared.conflicts, [
            {"reading_key": "T", "timestamp": self.start, "values": [1, 2], "selected_value": 1},
        ])

    def test_complementary_readings_merge_in_either_source_order(self):
        types = {**self.types, "H": str(uuid4())}
        for temperatures, humidities in (([21, None], [None, 50]), ([None, 21], [50, None])):
            with self.subTest(temperatures=temperatures):
                prepared = pipeline.prepare_observation_rows(
                    {"timestamp": [self.start.timestamp()] * 2, "T": temperatures, "H": humidities},
                    self.sensor, types, self.start, self.end,
                )
                self.assertEqual(
                    {str(row["observation_type_id"]): row["value"] for row in prepared.rows},
                    {types["T"]: 21, types["H"]: 50},
                )
                self.assertEqual(prepared.conflicts, [])

    def test_out_of_window_conflicts_are_not_reported(self):
        t = self.start.timestamp()
        prepared = pipeline.prepare_observation_rows(
            {"timestamp": [t - 1, t - 1, t, self.end.timestamp(), self.end.timestamp()], "T": [1, 2, 3, 4, 5]},
            self.sensor, self.types, self.start, self.end,
        )
        self.assertEqual([row["value"] for row in prepared.rows], [3])
        self.assertEqual(prepared.conflicts, [])

    def test_channels_at_the_same_timestamp_remain_distinct(self):
        self.types["H"] = str(uuid4())
        prepared = pipeline.prepare_observation_rows(
            {"timestamp": [self.start.timestamp()] * 2, "T": [21, 21], "H": [50, 50]},
            self.sensor,
            self.types,
            self.start,
            self.end,
        )
        values = {str(row["observation_type_id"]): row["value"] for row in prepared.rows}
        self.assertEqual(values, {self.types["T"]: 21, self.types["H"]: 50})
        self.assertEqual(prepared.diagnostics["identical_duplicate_count"], 2)
        self.assertEqual(prepared.diagnostics["distinct_timestamp_count"], 1)

    def test_diagnostics_and_reading_summary(self):
        t = self.start.timestamp()
        types = {**self.types, "H": str(uuid4())}
        prepared = pipeline.prepare_observation_rows(
            {
                "timestamp": [t + 60, t, t, t - 1, self.end.timestamp()],
                "T": [22, 21, 21, None, 999],
                "H": [None] * 5,
                "OUT": [0] * 5,
            },
            self.sensor,
            types,
            self.start,
            self.end,
        )
        self.assertEqual(len(prepared.rows), 2)
        diagnostics = prepared.diagnostics
        self.assertEqual(diagnostics["returned_timestamp_count"], 5)
        self.assertEqual(diagnostics["returned_series_count"], 3)
        self.assertEqual(diagnostics["selected_series_count"], 2)
        self.assertEqual(diagnostics["ignored_series_keys"], ["OUT"])
        self.assertEqual(diagnostics["out_of_interval_timestamp_count"], 2)
        self.assertEqual(diagnostics["null_value_count"], 3)
        self.assertEqual(diagnostics["identical_duplicate_count"], 1)
        self.assertEqual(diagnostics["distinct_timestamp_count"], 2)
        self.assertEqual(diagnostics["first_observation_at"], self.start)
        self.assertEqual(diagnostics["last_observation_at"], self.start + timedelta(seconds=60))
        self.assertNotIn("empty_reason", diagnostics)
        humidity, temperature = prepared.reading_summary
        self.assertEqual(humidity["selected_rows"], 0)
        self.assertEqual(humidity["null_values"], 3)
        self.assertIsNone(humidity["minimum"])
        self.assertIsNone(humidity["first_timestamp"])
        self.assertEqual(temperature["selected_rows"], 2)
        self.assertEqual((temperature["minimum"], temperature["maximum"]), (21, 22))

    def test_invalid_interval(self):
        for start, end in (
            (None, None),
            (self.start, self.start),
            (self.end, self.start),
            (self.start.replace(tzinfo=None), self.end),
        ):
            with self.assertRaises(ValueError):
                pipeline.validate_interval(start, end)

class ReadingPostgresTests(PostgresTestCase):
    def setUp(self):
        super().setUp()
        self.sensor_id, self.type_id = uuid4(), uuid4()
        with self.engine.begin() as conn:
            for family in ("ham", "other"):
                conn.execute(
                    insert(Sensor).values(
                        id=self.sensor_id if family == "ham" else uuid4(),
                        name="Test",
                        external_id="test:1",
                        sensor_family=family,
                    )
                )
                conn.execute(
                    insert(ObservationType).values(
                        id=self.type_id if family == "ham" else uuid4(),
                        key="T",
                        label="Temperature",
                        unit="C",
                        sensor_family=family,
                    )
                )
        self.row = {
            "sensor_id": self.sensor_id,
            "observation_type_id": self.type_id,
            "timestamp": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "value": 21.5,
        }

    def stored(self):
        with self.engine.connect() as conn:
            return conn.execute(select(ObservationValue)).mappings().all()

    def test_family_resolution_and_idempotent_update(self):
        sensor, types = pipeline.load_references(self.engine, str(self.sensor_id))
        self.assertEqual(sensor["id"], str(self.sensor_id))
        self.assertEqual(types, {"T": str(self.type_id)})
        self.assertEqual(
            pipeline.persist_observation_rows(self.engine, [self.row])["inserted_or_updated"], 1
        )
        original = self.stored()[0]
        self.assertEqual(
            pipeline.persist_observation_rows(self.engine, [self.row])["inserted_or_updated"], 0
        )
        self.assertEqual(
            pipeline.persist_observation_rows(self.engine, [{**self.row, "value": 22}])[
                "inserted_or_updated"
            ],
            1,
        )
        updated = self.stored()[0]
        self.assertEqual(updated["value"], 22)
        for key in ("id", "created_at", "sensor_id", "observation_type_id", "timestamp"):
            self.assertEqual(updated[key], original[key])

    def test_selected_sensor_lookup_and_discovery_are_family_scoped(self):
        other_id = uuid4()
        with self.engine.begin() as conn:
            conn.execute(
                insert(Sensor).values(
                    id=other_id, name="Second", external_id="test:2", sensor_family="ham"
                )
            )
        sensor, _ = pipeline.load_references(self.engine, str(self.sensor_id))
        self.assertEqual(sensor["id"], str(self.sensor_id))
        self.assertEqual(
            {row["id"]: row["external_id"] for row in load_sensor_catalog(self.engine)},
            {str(self.sensor_id): "test:1", str(other_id): "test:2"},
        )
        with self.assertRaisesRegex(ValueError, "not found"):
            pipeline.load_references(self.engine, sensor_id=str(uuid4()))
        with self.engine.connect() as conn:
            non_ham_id = (
                conn.execute(Sensor.__table__.select().where(Sensor.sensor_family == "other"))
                .mappings()
                .one()["id"]
            )
        with self.assertRaisesRegex(ValueError, "not found"):
            pipeline.load_references(self.engine, sensor_id=str(non_ham_id))

    def test_last_non_missing_replay_preserves_value_and_row_identity(self):
        start = self.row["timestamp"]
        prepared = pipeline.prepare_observation_rows(
            {"timestamp": [start.timestamp()] * 4, "T": [21, None, 22, None]},
            {"id": str(self.sensor_id)}, {"T": str(self.type_id)},
            start, start + timedelta(days=1),
        )
        self.assertEqual(pipeline.persist_observation_rows(self.engine, prepared.rows)["inserted_or_updated"], 1)
        original = self.stored()[0]
        self.assertEqual(original["value"], 22)
        self.assertEqual(pipeline.persist_observation_rows(self.engine, prepared.rows)["inserted_or_updated"], 0)
        self.assertEqual(self.stored()[0], original)

    def test_later_batch_fk_failure_rolls_back_every_batch(self):
        rows = [
            {**self.row, "timestamp": self.row["timestamp"] + timedelta(seconds=offset)}
            for offset in range(ObservationValueStore._BATCH_SIZE)
        ]
        rows.append({**self.row, "observation_type_id": uuid4()})
        with self.assertRaises(IntegrityError):
            pipeline.persist_observation_rows(self.engine, rows)
        self.assertEqual(self.stored(), [])
