"""Shared PostgreSQL store contracts, independent of HAM mapping and Dagster."""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

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
            sensors = SensorStore(sessionmaker(bind=connection))
            types = ObservationTypeStore(sessionmaker(bind=connection))
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
            sensors = SensorStore(sessionmaker(bind=connection))
            types = ObservationTypeStore(sessionmaker(bind=connection))
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
                sensors = SensorStore(sessionmaker(bind=connection))
                types = ObservationTypeStore(sessionmaker(bind=connection))
                sensors.upsert_source_fields("other", self.sensor_rows)
                types.upsert_source_fields("other", self.type_rows)
                sensor = sensors.list_by_sensor_family("other")[0]
                type_id = types.get_id_map_by_sensor_family("other")["T"]
                summary = ObservationValueStore(sessionmaker(bind=connection)).upsert_rows([
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
                SensorStore(sessionmaker(bind=connection)).upsert_source_fields("other", []),
                {"selected": 0, "inserted_or_updated": 0, "verified": 0},
            )
            self.assertEqual(
                ObservationValueStore(sessionmaker(bind=connection)).upsert_rows([]),
                {"selected": 0, "inserted_or_updated": 0},
            )
            with self.assertRaisesRegex(ValueError, "empty observation-type"):
                ObservationTypeStore(sessionmaker(bind=connection)).upsert_source_fields("other", [])

    def test_session_factories_commit_and_preserve_records_and_ids(self):
        factory = sessionmaker(bind=self.engine)
        sensors = SensorStore(factory)
        types = ObservationTypeStore(session_factory=factory)
        values = ObservationValueStore(factory)
        sensors.upsert_source_fields("other", self.sensor_rows)
        types.upsert_source_fields("other", self.type_rows)
        sensor = sensors.list_by_sensor_family("other")[0]
        type_id = types.get_id_map_by_sensor_family("other")["T"]
        self.assertIsInstance(sensor["id"], UUID)
        self.assertIsInstance(type_id, UUID)
        self.assertIsNotNone(sensor["starting_date"].utcoffset())
        self.assertEqual(
            sensors.get_by_id_and_sensor_family(sensor["id"], "other")["external_id"],
            self.sensor_rows[0]["external_id"],
        )
        row = {
            "sensor_id": sensor["id"],
            "observation_type_id": type_id,
            "timestamp": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "value": 21.5,
        }
        self.assertEqual(values.upsert_rows([row])["inserted_or_updated"], 1)
        with self.engine.connect() as connection:
            observation_id = connection.execute(select(ObservationValue.id)).scalar_one()
        self.assertEqual(values.upsert_rows([row])["inserted_or_updated"], 0)
        self.assertEqual(
            values.upsert_rows([{**row, "value": 22.5}])["inserted_or_updated"], 1
        )
        self.assertEqual(
            sensors.upsert_source_fields("other", self.sensor_rows)["inserted_or_updated"], 0
        )
        self.assertEqual(
            types.upsert_source_fields("other", self.type_rows)["inserted_or_updated"], 0
        )
        with self.engine.connect() as connection:
            stored = connection.execute(select(ObservationValue)).mappings().one()
            self.assertEqual(stored["id"], observation_id)
            self.assertEqual(stored["value"], 22.5)
            self.assertEqual(connection.execute(select(Sensor.id)).scalar_one(), sensor["id"])
            self.assertEqual(connection.execute(select(ObservationType.id)).scalar_one(), type_id)

    def test_owned_session_rolls_back_all_batches_on_failure(self):
        factory = sessionmaker(bind=self.engine)
        sensors = SensorStore(factory)
        types = ObservationTypeStore(factory)
        sensors.upsert_source_fields("other", self.sensor_rows)
        types.upsert_source_fields("other", self.type_rows)
        row = {
            "sensor_id": sensors.list_by_sensor_family("other")[0]["id"],
            "observation_type_id": types.get_id_map_by_sensor_family("other")["T"],
            "timestamp": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "value": 21.5,
        }
        rows = [
            {**row, "timestamp": row["timestamp"] + timedelta(seconds=offset)}
            for offset in range(ObservationValueStore._BATCH_SIZE)
        ]
        rows.append({**row, "observation_type_id": uuid4()})
        values = ObservationValueStore(factory)
        with self.assertRaises(IntegrityError):
            values.upsert_rows(rows)
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(select(ObservationValue)).all(), [])
        # A failed call also releases its session, so the store can be reused.
        self.assertEqual(values.upsert_rows([row])["inserted_or_updated"], 1)
