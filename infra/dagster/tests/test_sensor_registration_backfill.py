"""Registration commit/reload/backfill orchestration without external services."""

import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

from app.schemas.sensors import SensorRegistrationRequest, SensorRegistrationResponse
from app.services import sensor_registration_service as service

START = datetime(2026, 1, 1, tzinfo=timezone.utc)
SENSOR_ROWS = [{"external_id": "room-1", "name": "Room"}]
TYPE_ROWS = [{"key": "T", "label": "Temperature", "unit": "C"}]


def registration():
    return {"sensor_family": "ham", "sensors": [{"external_id": "room-1"}]}


class RegistrationBackfillTests(unittest.TestCase):
    """Check orchestration even when a PostgreSQL test database is unavailable."""

    def setUp(self):
        self.addCleanup(patch.stopall)
        self.saved = {"id": uuid4(), "sensor_family": "ham", "external_id": "room-1",
                      "name": "Room", "location": None, "starting_date": START,
                      "bim_dataset_id": None, "modular_component_id": None}
        self.events = []
        transaction = patch.object(service, "engine").start().begin.return_value
        transaction.__exit__.side_effect = lambda *args: self.events.append("commit") or False
        patch.object(service, "sessionmaker").start()
        patch.object(service, "prepare_catalog", return_value=(SENSOR_ROWS, TYPE_ROWS)).start()
        patch.object(service, "ObservationTypeStore").start()
        self.store = patch.object(service, "SensorStore").start().return_value
        self.store.list_registration_fields.return_value = [self.saved]

        def reload():
            self.events.append("reload")
            return {"status": "reloaded"}

        def backfill(rows):
            self.events.append("backfill")
            self.assertEqual(rows, [self.saved])
            return [{"sensor_id": self.saved["id"], "status": "submitted", "backfill_id": "fixture"}]

        self.reload = patch.object(service, "reload_sensor_location", side_effect=reload).start()
        self.backfill = patch.object(service, "launch_sensor_backfills", side_effect=backfill).start()

    def register(self):
        return service.register_sensors(SensorRegistrationRequest.model_validate(registration()))

    def test_commit_reload_backfill_order_and_response_contract(self):
        result = SensorRegistrationResponse.model_validate(self.register())
        self.assertEqual(self.events, ["commit", "reload", "backfill"])
        self.assertEqual(result.backfills[0].backfill_id, "fixture")
        self.assertEqual(result.sensors[0].id, self.saved["id"])

    def test_reregistration_follows_the_same_path(self):
        self.register()
        self.register()
        self.assertEqual(self.events, ["commit", "reload", "backfill"] * 2)

    def test_reload_failure_keeps_saved_sensors_and_does_not_backfill(self):
        self.reload.side_effect = None
        self.reload.return_value = {"status": "failed"}
        result = self.register()
        self.assertEqual(result["sensors"], [self.saved])
        self.assertEqual(result["backfills"], [])
        self.backfill.assert_not_called()

    def test_write_failure_neither_reloads_nor_backfills(self):
        self.store.update_registration_fields.side_effect = RuntimeError("write failed")
        with self.assertRaises(RuntimeError):
            self.register()
        self.reload.assert_not_called()
        self.backfill.assert_not_called()

    def test_backfill_failure_preserves_reload_success_and_saved_sensors(self):
        self.backfill.side_effect = None
        self.backfill.return_value = [{"sensor_id": self.saved["id"], "status": "failed"}]
        result = SensorRegistrationResponse.model_validate(self.register())
        self.assertEqual(result.dagster.status, "reloaded")
        self.assertEqual(result.sensors[0].id, self.saved["id"])
        self.assertEqual(result.backfills[0].status, "failed")


