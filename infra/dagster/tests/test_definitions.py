"""Code-location assembly and physical sensor discovery."""

import subprocess
import sys
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from dagster import AssetKey, Definitions

from infra.dagster import definitions as pipeline
from infra.dagster.ham import sensors
from infra.dagster.resources import HamApi
from infra.dagster.tests.support import (
    CATALOG,
    DEVICE_IDS,
    FakeDatabase,
    build_definitions,
)


class DefinitionTests(unittest.TestCase):
    def test_import_does_not_access_database_or_network(self):
        # Use a fresh interpreter: reloading an imported module misses cached dependencies.
        script = """
from unittest.mock import patch
with patch('sqlalchemy.create_engine', side_effect=AssertionError('DB at import')), \
     patch('urllib.request.urlopen', side_effect=AssertionError('HTTP at import')), \
     patch('hamapi.hamapi', side_effect=AssertionError('HAM at import')):
    import infra.dagster.definitions
    import sys
    assert 'app.db.session' not in sys.modules
    assert 'app.core.config' not in sys.modules
"""
        result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_definition_load_discovers_sensors(self):
        with patch.object(sensors, "load_sensor_catalog", return_value=CATALOG) as read, patch.object(
            pipeline.openmeteo_catalog, "load_sensor_catalog", return_value=[]
        ):
            definitions = pipeline.build_definitions(FakeDatabase(), HamApi())
        read.assert_called_once()
        Definitions.validate_loadable(definitions)

    def test_database_failure_is_not_an_empty_catalog(self):
        with patch.object(sensors, "load_sensor_catalog", side_effect=OSError("DB unavailable")):
            with self.assertRaises(OSError):
                pipeline.build_definitions(FakeDatabase(), HamApi())

    def test_lineage_distinct_start_dates_and_automation(self):
        defs = build_definitions()
        for device in CATALOG:
            key = pipeline.observation_asset_key(device["id"])
            asset = next(a for a in defs.assets if a.key == key)
            self.assertEqual(
                asset.asset_deps[key],
                {AssetKey("hamapi_sensors"), AssetKey("hamapi_observation_types")},
            )
            self.assertEqual(asset.partitions_def.start.date(), device["starting_date"].date())
            self.assertEqual(asset.backfill_policy.max_partitions_per_run, 1)
            metadata = asset.metadata_by_key[key]
            self.assertEqual(metadata["sensor_id"], device["id"])
            self.assertEqual(metadata["sensor_name"], device["name"])
            self.assertEqual(metadata["sensor_external_id"], device["external_id"])
        self.assertFalse(defs.schedules)

    def test_empty_catalog_still_loads_initialization_and_automation(self):
        defs = build_definitions([])
        Definitions.validate_loadable(defs)
        self.assertEqual(len(defs.assets), 2)
        self.assertEqual(len(defs.sensors), 2)

    def test_reload_add_delete_rename_and_start_date_changes(self):
        first = build_definitions()
        renamed = {
            **CATALOG[0],
            "name": "Renamed",
            "starting_date": datetime(2026, 2, 1, tzinfo=timezone.utc),
        }
        reloaded = build_definitions([renamed])
        key = pipeline.observation_asset_key(DEVICE_IDS[0])
        self.assertIn(pipeline.observation_asset_key(DEVICE_IDS[1]), first.resolve_all_asset_keys())
        self.assertNotIn(
            pipeline.observation_asset_key(DEVICE_IDS[1]), reloaded.resolve_all_asset_keys()
        )
        asset = next(a for a in reloaded.assets if a.key == key)
        self.assertEqual(asset.partitions_def.start.date().isoformat(), "2026-02-01")
        self.assertEqual(asset.metadata_by_key[key]["sensor_name"], "Renamed")
        self.assertEqual(len(build_definitions().resolve_all_asset_keys()), 4)

    def test_invalid_delay_is_rejected_even_with_empty_catalog(self):
        for delay in (-1, 24, 4.5, True):
            with self.subTest(delay=delay), self.assertRaisesRegex(ValueError, "0 to 23"):
                build_definitions([], delay_hours=delay)

    def test_invalid_start_date_fails_definition_loading(self):
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            build_definitions([{**CATALOG[0], "starting_date": datetime(2026, 1, 1)}])
