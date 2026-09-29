"""Shared PostgreSQL store contracts, independent of HAM mapping and Dagster."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select

from app.db.models.observation_type import ObservationType
from app.db.models.observation_value import ObservationValue
from app.db.models.sensor import Sensor
from app.storage.postgres.observation_type_store import ObservationTypeStore
from app.storage.postgres.observation_value_store import ObservationValueStore
from app.storage.postgres.sensor_store import SensorStore
from infra.dagster.tests.postgres import PostgresTestCase


class PostgresStoreTests(PostgresTestCase):
    sensor_rows = [{"name": "Room", "external_id": "shared:1", "sensor_metadata": {}}]
    type_rows = [{"key": "T", "label": "Temperature", "unit": "C", "type_metadata": {}}]

    def test_catalog_operations_are_family_scoped_and_return_native_records(self):
        with self.engine.begin() as connection:
            sensors = SensorStore(connection)
            types = ObservationTypeStore(connection)
            for family in ("ham", "other"):
                sensors.upsert_source_fields(family, self.sensor_rows)
                types.upsert_source_fields(family, self.type_rows)
            sensors.upsert_source_fields(
                "other", [{**self.sensor_rows[0], "external_id": "shared:2"}]
            )
            catalog = sensors.list_by_sensor_family("other")
            self.assertEqual(len(catalog), 2)
            self.assertEqual([row["id"] for row in catalog], sorted(row["id"] for row in catalog))
            for row in catalog:
                self.assertIsInstance(row["id"], UUID)
                self.assertIsNotNone(row["starting_date"].utcoffset())
                selected = sensors.get_by_id_and_sensor_family(row["id"], "other")
                self.assertEqual(selected["external_id"], row["external_id"])
                self.assertIsNone(sensors.get_by_id_and_sensor_family(row["id"], "ham"))
            self.assertIsNone(sensors.get_by_id_and_sensor_family(uuid4(), "other"))
            ham_types = types.get_id_map_by_sensor_family("ham")
            other_types = types.get_id_map_by_sensor_family("other")
            self.assertEqual(set(other_types), {"T"})
            self.assertIsInstance(other_types["T"], UUID)
            self.assertNotEqual(ham_types["T"], other_types["T"])
            self.assertEqual(sensors.list_by_sensor_family("missing"), [])
            self.assertEqual(types.get_id_map_by_sensor_family("missing"), {})

    def test_source_upserts_cannot_override_local_fields_or_family(self):
        with self.engine.begin() as connection:
            sensors = SensorStore(connection)
            types = ObservationTypeStore(connection)
            sensors.upsert_source_fields(
                "other",
                [{
                    **self.sensor_rows[0],
                    "sensor_family": "ham",
                    "location": "Source",
                    "space": "Source",
                    "starting_date": datetime(2000, 1, 1, tzinfo=timezone.utc),
                }],
            )
            types.upsert_source_fields(
                "other", [{**self.type_rows[0], "sensor_family": "ham"}]
            )
            self.assertEqual(sensors.list_by_sensor_family("ham"), [])
            self.assertEqual(types.get_id_map_by_sensor_family("ham"), {})
            sensor = connection.execute(select(Sensor)).mappings().one()
            self.assertIsNone(sensor["location"])
            self.assertIsNone(sensor["space"])
            self.assertEqual(sensor["starting_date"].year, 2026)

    def test_all_stores_participate_in_the_callers_transaction(self):
        with self.assertRaisesRegex(RuntimeError, "abort workflow"):
            with self.engine.begin() as connection:
                sensors = SensorStore(connection)
                types = ObservationTypeStore(connection)
                sensors.upsert_source_fields("other", self.sensor_rows)
                types.upsert_source_fields("other", self.type_rows)
                sensor = sensors.list_by_sensor_family("other")[0]
                type_id = types.get_id_map_by_sensor_family("other")["T"]
                summary = ObservationValueStore(connection).upsert_rows([
                    {
                        "sensor_id": sensor["id"],
                        "observation_type_id": type_id,
                        "timestamp": datetime(2026, 1, 1, tzinfo=timezone.utc),
                        "value": 21.5,
                    }
                ])
                self.assertEqual(summary, {"selected": 1, "inserted_or_updated": 1})
                raise RuntimeError("abort workflow")
        with self.engine.connect() as connection:
            for model in (Sensor, ObservationType, ObservationValue):
                self.assertEqual(connection.execute(select(model)).all(), [])

    def test_empty_store_operations_preserve_their_contracts(self):
        with self.engine.begin() as connection:
            self.assertEqual(
                SensorStore(connection).upsert_source_fields("other", []),
                {"selected": 0, "inserted_or_updated": 0, "verified": 0},
            )
            self.assertEqual(
                ObservationValueStore(connection).upsert_rows([]),
                {"selected": 0, "inserted_or_updated": 0},
            )
            with self.assertRaisesRegex(ValueError, "empty observation-type"):
                ObservationTypeStore(connection).upsert_source_fields("other", [])
