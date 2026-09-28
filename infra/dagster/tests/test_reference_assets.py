"""Reference asset configuration and materialization metadata."""

import unittest
from unittest.mock import patch

from dagster import ResourceDefinition, materialize

from infra.dagster import assets as pipeline
from infra.dagster.ham import observation_types, sensors
from infra.dagster.tests.support import FakeDatabase, StubHamApi


class ReferenceAssetTests(unittest.TestCase):
    def test_runtime_extra_readings_option(self):
        catalog = {"T": {}, "PMV": {}}
        models = {"device": {"readings": ["T"], "extra_readings": [{"key": "PMV"}]}}
        for enabled, expected in ((False, ["T"]), (True, ["PMV", "T"])):
            with (
                self.subTest(enabled=enabled),
                patch.object(
                    observation_types,
                    "persist_rows",
                    return_value={"selected": len(expected), "inserted_or_updated": len(expected)},
                ) as persist,
            ):
                result = materialize(
                    [pipeline.hamapi_observation_types],
                    resources={
                        "ham_api": ResourceDefinition.hardcoded_resource(
                            StubHamApi(catalogs={"readings": catalog, "models": models})
                        ),
                        "database": FakeDatabase(),
                    },
                    run_config={
                        "ops": {
                            "hamapi_observation_types": {
                                "config": {"include_extra_readings": enabled}
                            }
                        }
                    },
                )
                self.assertTrue(result.success)
                self.assertEqual([row["key"] for row in persist.call_args.args[1]], expected)
                event = result.get_asset_materialization_events()[
                    0
                ].event_specific_data.materialization
                metadata = event.metadata
                self.assertEqual(metadata["include_extra_readings"].value, enabled)
                self.assertEqual(metadata["model_count"].value, 1)
                self.assertEqual(metadata["catalog_reading_count"].value, 2)
                self.assertEqual(
                    metadata["excluded_reading_keys"].value, [] if enabled else ["PMV"]
                )
                self.assertEqual(metadata["excluded_reading_count"].value, 0 if enabled else 1)
                self.assertEqual(metadata["unchanged"].value, 0)
                self.assertTrue(metadata["models_catalog_url"].value.endswith("/models.json"))

    def test_sensor_import_metadata_including_empty_catalog(self):
        for devices in ([], [{"name": "Example", "serialno": "device:0"}]):
            with (
                self.subTest(devices=devices),
                patch.object(
                    sensors,
                    "persist_sensor_rows",
                    return_value={
                        "selected": len(devices),
                        "inserted_or_updated": 0,
                        "verified": len(devices),
                    },
                ),
            ):
                result = materialize(
                    [pipeline.hamapi_sensors],
                    resources={
                        "ham_api": ResourceDefinition.hardcoded_resource(
                            StubHamApi(devices=devices)
                        ),
                        "database": FakeDatabase(),
                    },
                )
                self.assertTrue(result.success)
                event = result.get_asset_materialization_events()[
                    0
                ].event_specific_data.materialization
                metadata = event.metadata
                self.assertEqual(metadata["unchanged"].value, len(devices))
                for field in ("fetch_seconds", "prepare_seconds", "persist_seconds"):
                    self.assertGreaterEqual(metadata[field].value, 0)
                self.assertIn("Reload", metadata["next_step"].value)
