"""Run with unittest; set HAMAPI_TEST_POSTGRES_DSN for temporary-table DB tests."""

import copy
import os
import unittest
from unittest.mock import patch

from infra.dagster.ham import observation_types as pipeline


class ReadingSelectionTests(unittest.TestCase):
    def test_union_includes_extra_readings_and_excludes_outputs(self):
        models = {
            "a": {"readings": ["T", "H"], "extra_readings": [{"key": "PMV"}], "output_names": ["out"]},
            "b": {"readings": ["T", "P"], "extra_readings": [{"key": "T"}]},
            "empty": {},
        }
        self.assertEqual(pipeline.collect_reading_keys(models), ["H", "P", "T"])
        self.assertEqual(pipeline.collect_reading_keys(models, include_extra_readings=True), ["H", "P", "PMV", "T"])

    def test_disabled_extra_readings_are_not_parsed_or_validated(self):
        for extra in (None, "invalid", [{}]):
            models = {"a": {"readings": ["T"], "extra_readings": extra}}
            with self.subTest(extra=extra):
                self.assertEqual(pipeline.collect_reading_keys(models), ["T"])
                with self.assertRaises(ValueError):
                    pipeline.collect_reading_keys(models, include_extra_readings=True)

    def test_metadata_preserved_and_required_columns_normalized(self):
        catalog = {
            "T": {"label": "Temperature", "unit": "°C", "transform": "divide_by_100"},
            "GI": {"label": "", "unit": None, "custom": {"values": [1, 2]}},
            "memory_free": {"label": "Memory", "unit": "MB"},
        }
        original = copy.deepcopy(catalog)
        rows = pipeline.prepare_rows(catalog, ["T", "GI", "T"])
        self.assertEqual([row["key"] for row in rows], ["GI", "T"])
        self.assertEqual(rows[0]["label"], "GI")
        self.assertEqual(rows[0]["unit"], "")
        self.assertEqual(rows[1]["type_metadata"], catalog["T"])
        self.assertEqual(catalog, original)

    def test_missing_catalog_reference_is_not_silently_dropped(self):
        with self.assertRaisesRegex(ValueError, "missing from catalog"):
            pipeline.prepare_rows({"T": {"label": "Temperature"}}, ["T", "unknown"])

    def test_malformed_or_empty_models_fail(self):
        for models in ({}, {"a": {}}, {"a": {"readings": "T"}}, {"a": {"extra_readings": [{}]}}, {"a": {"readings": [None]}}):
            with self.subTest(models=models), self.assertRaises(ValueError):
                pipeline.collect_reading_keys(models)

    def test_malformed_selected_metadata_fails(self):
        for metadata in (None, [], {"label": 123}, {"unit": []}):
            with self.subTest(metadata=metadata), self.assertRaises(ValueError):
                pipeline.prepare_rows({"T": metadata}, ["T"])




@unittest.skipUnless(os.environ.get("HAMAPI_TEST_POSTGRES_DSN"), "Set HAMAPI_TEST_POSTGRES_DSN to test PostgreSQL")
class PostgresTests(unittest.TestCase):
    def setUp(self):
        from sqlalchemy import create_engine
        from sqlalchemy.pool import StaticPool

        self.engine = create_engine(os.environ["HAMAPI_TEST_POSTGRES_DSN"], poolclass=StaticPool)
        self.addCleanup(self.engine.dispose)
        # A session-local table shadows the application table. No persistent data is changed.
        with self.engine.begin() as connection:
            connection.exec_driver_sql("CREATE TEMP TABLE observation_types (LIKE public.observation_types INCLUDING ALL)")
        self.rows = pipeline.prepare_rows({"T": {"label": "Temperature", "unit": "°C", "transform": "divide_by_100"}}, ["T"])

    def stored_rows(self):
        from sqlalchemy import select
        from app.db.models.observation_type import ObservationType

        with self.engine.connect() as connection:
            return connection.execute(select(ObservationType).order_by(
                ObservationType.sensor_family, ObservationType.key
            )).mappings().all()

    def test_retry_and_update_preserve_identity_and_other_namespaces(self):
        from sqlalchemy import insert
        from app.db.models.observation_type import ObservationType

        with self.engine.begin() as connection:
            connection.execute(insert(ObservationType).values(sensor_family="other", key="T", label="Untouched", unit=""))
        self.assertEqual(pipeline.persist_rows(self.engine, self.rows)["inserted_or_updated"], 1)
        original = self.stored_rows()
        self.assertEqual(original[0]["sensor_family"], "ham")
        self.assertEqual(pipeline.persist_rows(self.engine, self.rows)["inserted_or_updated"], 0)
        self.assertEqual(self.stored_rows(), original)
        updated = copy.deepcopy(self.rows)
        updated[0]["label"] = "Updated temperature"
        updated[0]["type_metadata"]["transform"] = "divide_by_10"
        self.assertEqual(pipeline.persist_rows(self.engine, updated)["inserted_or_updated"], 1)
        stored = self.stored_rows()
        self.assertEqual(stored[0]["id"], original[0]["id"])
        self.assertEqual(stored[0]["created_at"], original[0]["created_at"])
        self.assertEqual(stored[0]["label"], "Updated temperature")
        self.assertEqual(stored[0]["type_metadata"]["transform"], "divide_by_10")
        self.assertEqual(stored[1], original[1])

    def test_bad_batch_rolls_back_all_rows(self):
        from sqlalchemy.exc import IntegrityError

        bad_row = {"key": "bad", "label": None, "unit": "", "type_metadata": {}}
        with self.assertRaises(IntegrityError):
            pipeline.persist_rows(self.engine, self.rows + [bad_row])
        self.assertEqual(self.stored_rows(), [])


if __name__ == "__main__":
    unittest.main()
