"""Typed metadata reflects model schemas and handles empty reading summaries."""

import unittest
from unittest.mock import patch

from sqlalchemy import Column, Integer, MetaData, String, Table

from infra.dagster.metadata import measure_duration, table_metadata
from infra.dagster.tests.support import build_definitions


class MetadataTests(unittest.TestCase):
    def test_schema_is_derived_from_model_columns(self):
        table = Table(
            "example",
            MetaData(),
            Column("id", Integer, primary_key=True),
            Column("label", String, nullable=True, comment="Human-readable label"),
            schema="custom",
        )
        metadata = table_metadata(table, "id = 1", "Upsert")
        self.assertEqual(metadata["dagster/table_name"], "custom.example")
        columns = metadata["dagster/column_schema"].schema.columns
        self.assertEqual([column.name for column in columns], ["id", "label"])
        self.assertEqual(columns[0].type, "INTEGER")
        self.assertFalse(columns[0].constraints.nullable)
        self.assertTrue(columns[1].constraints.nullable)
        self.assertEqual(columns[1].description, "Human-readable label")

    def test_all_assets_describe_table_scope_and_kinds(self):
        for asset in build_definitions().assets:
            with self.subTest(asset=asset.key):
                spec = asset.get_asset_spec(asset.key)
                self.assertEqual(spec.kinds, {"python", "postgres"})
                metadata = spec.metadata
                self.assertTrue(metadata["dagster/table_name"].startswith("public."))
                self.assertIsNotNone(metadata["dagster/column_schema"])
                self.assertIn("preserve", metadata["write_semantics"])
                if asset.key.path[0] == "observation_values":
                    self.assertIn(asset.key.path[1], metadata["row_scope"])
                    self.assertIn("UTC", metadata["partition_semantics"])
                else:
                    self.assertEqual(metadata["row_scope"], "sensor_family = 'ham'")

    def test_duration_uses_monotonic_clock_and_only_completed_phases(self):
        metadata = {}
        with patch("infra.dagster.metadata.perf_counter", side_effect=[10, 12.5, 20]):
            with measure_duration(metadata, "fetch_seconds"):
                pass
            with self.assertRaises(ValueError):
                with measure_duration(metadata, "persist_seconds"):
                    raise ValueError("rollback")
        self.assertEqual(metadata, {"fetch_seconds": 2.5})
