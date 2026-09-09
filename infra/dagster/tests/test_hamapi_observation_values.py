"""Reading conversion, library contract, and optional PostgreSQL upsert checks."""

import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

from infra.dagster.ham import observation_values as pipeline


class ReadingTests(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.end = self.start + timedelta(hours=1)
        self.sensor = {"id": str(uuid4()), "external_id": "e45:1", "sensor_family": "ham"}
        self.types = {"T": str(uuid4())}

    def rows(self, response):
        return pipeline.prepare_observation_rows(response, self.sensor, self.types, self.start, self.end)

    def test_mapping_and_half_open_interval(self):
        t = self.start.timestamp()
        rows = self.rows({"timestamp": [t - 0.01, t, t + 0.99, self.end.timestamp()],
                          "T": [1, 21.5, 22, 3], "OUT": [0, 0, 0, 0]})
        self.assertEqual([r["value"] for r in rows], [21.5, 22])
        self.assertEqual(str(rows[0]["sensor_id"]), self.sensor["id"])
        self.assertEqual(str(rows[0]["observation_type_id"]), self.types["T"])
        self.assertEqual(rows[1]["timestamp"].microsecond, 990000)
        self.assertEqual(set(rows[0]), {"sensor_id", "observation_type_id", "timestamp", "value"})

    def test_invalid_series_and_values(self):
        t = self.start.timestamp()
        for response in ({}, {"error": "denied"}, {"timestamp": [t], "T": []},
                         {"timestamp": [float("nan")], "T": [1]},
                         {"timestamp": [t], "T": [float("inf")]},
                         {"timestamp": [t], "T": ["last"]},
                         {"timestamp": [t], "unknown": [1]}):
            with self.subTest(response=response), self.assertRaises(ValueError):
                self.rows(response)

    def test_empty_null_and_duplicates(self):
        t = self.start.timestamp()
        self.assertEqual(self.rows({"timestamp": [], "T": []}), [])
        self.assertEqual(self.rows({"timestamp": [t], "T": [None]}), [])
        self.assertEqual(len(self.rows({"timestamp": [t, t], "T": [1, 1]})), 1)
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            self.rows({"timestamp": [t, t], "T": [1, 2]})
        self.assertEqual(pipeline.persist_observation_rows(None, []),
                         {"selected": 0, "inserted_or_updated": 0})

    def test_invalid_interval(self):
        for start, end in ((None, None), (self.start, self.start), (self.end, self.start),
                           (self.start.replace(tzinfo=None), self.end)):
            with self.assertRaises(ValueError):
                pipeline.validate_interval(start, end)

    def test_fetch_passes_key_and_epoch_interval_and_closes_cache(self):
        with patch("hamapi.hamapi") as factory:
            client = factory.return_value
            client.get_user_devices.return_value = {"devices": [{"serialno": "e45:1"}]}
            client.get_datalog_data.return_value = {"timestamp": [], "T": []}
            pipeline.fetch_readings("test-key", "e45:1", self.start, self.end)
            factory.assert_called_once_with(api_key="test-key", cache_db_file=":memory:")
            client.get_datalog_data.assert_called_once_with("e45:1", self.start.timestamp(), self.end.timestamp())
            client.cache_conn.close.assert_called_once()

    def test_inaccessible_sensor_fails_and_closes_cache(self):
        with patch("hamapi.hamapi") as factory:
            factory.return_value.get_user_devices.return_value = {"devices": []}
            with self.assertRaisesRegex(ValueError, "cannot access"):
                pipeline.fetch_readings("test-key", "e45:1", self.start, self.end)
            factory.return_value.get_datalog_data.assert_not_called()
            factory.return_value.cache_conn.close.assert_called_once()

    def test_actual_library_parser_contract(self):
        import hamapi
        client = hamapi.hamapi(cache_db_file=":memory:")
        self.addCleanup(client.cache_conn.close)
        client.family_info_map = {"test": {"readings": ["T"], "output_names": ["OUT"]}}
        client.reading_info_map_load({"T": {"transform": "divide_by_100"}})
        t = self.start.timestamp()
        response = client.parse_datalog_data("test:1", {"0.1": f"{t};2150;0\n{t + 60};2200;1"}, t, t + 3600)
        rows = self.rows(response)
        self.assertEqual([r["value"] for r in rows], [21.5, 21.5, 22])
        self.assertEqual(rows[1]["timestamp"], self.start + timedelta(seconds=59.99))



@unittest.skipUnless(os.environ.get("HAMAPI_TEST_POSTGRES_DSN"), "Set HAMAPI_TEST_POSTGRES_DSN to test PostgreSQL")
class ReadingPostgresTests(unittest.TestCase):
    def setUp(self):
        from sqlalchemy import create_engine, insert
        from sqlalchemy.pool import StaticPool
        from app.db.models.sensor import Sensor
        from app.db.models.observation_type import ObservationType
        self.engine = create_engine(os.environ["HAMAPI_TEST_POSTGRES_DSN"], poolclass=StaticPool)
        self.addCleanup(self.engine.dispose)
        self.sensor_id, self.type_id = uuid4(), uuid4()
        with self.engine.begin() as conn:
            for table in ("sensors", "observation_types", "observation_values"):
                conn.exec_driver_sql(f"CREATE TEMP TABLE {table} (LIKE public.{table} INCLUDING ALL)")
            conn.exec_driver_sql("ALTER TABLE observation_values ADD FOREIGN KEY (sensor_id) REFERENCES sensors(id)")
            conn.exec_driver_sql("ALTER TABLE observation_values ADD FOREIGN KEY (observation_type_id) REFERENCES observation_types(id)")
            for family in ("ham", "other"):
                conn.execute(insert(Sensor).values(id=self.sensor_id if family == "ham" else uuid4(),
                             name="Test", external_id="test:1", sensor_family=family))
                conn.execute(insert(ObservationType).values(id=self.type_id if family == "ham" else uuid4(),
                             key="T", label="Temperature", unit="C", sensor_family=family))
        self.row = {"sensor_id": self.sensor_id, "observation_type_id": self.type_id,
                    "timestamp": datetime(2026, 1, 1, tzinfo=timezone.utc), "value": 21.5}

    def stored(self):
        from sqlalchemy import select
        from app.db.models.observation_value import ObservationValue
        with self.engine.connect() as conn:
            return conn.execute(select(ObservationValue)).mappings().all()

    def test_family_resolution_and_idempotent_update(self):
        refs = pipeline.load_references(self.engine)
        self.assertEqual(len(refs["sensors"]), 1)
        self.assertEqual(refs["types"], {"T": str(self.type_id)})
        self.assertEqual(pipeline.persist_observation_rows(self.engine, [self.row])["inserted_or_updated"], 1)
        original = self.stored()[0]
        self.assertEqual(pipeline.persist_observation_rows(self.engine, [self.row])["inserted_or_updated"], 0)
        self.assertEqual(pipeline.persist_observation_rows(self.engine, [{**self.row, "value": 22}])["inserted_or_updated"], 1)
        updated = self.stored()[0]
        self.assertEqual(updated["value"], 22)
        for key in ("id", "created_at", "sensor_id", "observation_type_id", "timestamp"):
            self.assertEqual(updated[key], original[key])

    def test_selected_sensor_lookup_and_discovery_are_family_scoped(self):
        from sqlalchemy import insert
        from app.db.models.sensor import Sensor
        from infra.dagster.ham.sensors import load_sensor_catalog
        other_id = uuid4()
        with self.engine.begin() as conn:
            conn.execute(insert(Sensor).values(id=other_id, name="Second", external_id="test:2", sensor_family="ham"))
        refs = pipeline.load_references(self.engine, sensor_id=str(self.sensor_id))
        self.assertEqual([row["id"] for row in refs["sensors"]], [str(self.sensor_id)])
        self.assertEqual({row["id"] for row in load_sensor_catalog(self.engine)}, {str(self.sensor_id), str(other_id)})
        with self.assertRaisesRegex(ValueError, "not found"):
            pipeline.load_references(self.engine, sensor_id=str(uuid4()))
        with self.engine.connect() as conn:
            non_ham_id = conn.execute(Sensor.__table__.select().where(Sensor.sensor_family == "other")).mappings().one()["id"]
        with self.assertRaisesRegex(ValueError, "not found"):
            pipeline.load_references(self.engine, sensor_id=str(non_ham_id))

    def test_later_batch_fk_failure_rolls_back_every_batch(self):
        from sqlalchemy.exc import IntegrityError
        with patch.object(pipeline, "BATCH_SIZE", 1), self.assertRaises(IntegrityError):
            pipeline.persist_observation_rows(self.engine, [self.row, {**self.row, "observation_type_id": uuid4()}])
        self.assertEqual(self.stored(), [])
