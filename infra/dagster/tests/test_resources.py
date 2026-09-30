"""Resource configuration, HAM client contracts, and connection cleanup."""

import io
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from dagster import Failure
from sqlalchemy.engine import make_url

from infra.dagster.ham.client import HamApi
from infra.dagster.resources import LeColazDatabase


class ResourceTests(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.end = self.start + timedelta(hours=1)

    def test_missing_key_fails_without_retry_or_client_creation(self):
        with patch("hamapi.hamapi") as factory:
            with self.assertRaises(Failure) as raised:
                HamApi().devices()
            self.assertFalse(raised.exception.allow_retries)
            factory.assert_not_called()

    def test_database_url_preserves_special_characters(self):
        password = "p@ss:/?#% word"
        url = LeColazDatabase(
            host="postgres", database="fixture", password=password, username="user@name"
        ).connection_url()
        self.assertEqual(make_url(url.render_as_string(hide_password=False)).password, password)

    def test_fetch_passes_key_and_epoch_interval_and_closes_cache(self):
        with patch("hamapi.hamapi") as factory:
            client = factory.return_value
            client.get_user_devices.return_value = {"devices": [{"serialno": "e45:1"}]}
            client.get_datalog_data.return_value = {"timestamp": [], "T": []}
            HamApi(api_key="test-key").readings("e45:1", self.start, self.end)
            factory.assert_called_once_with(api_key="test-key", cache_db_file=":memory:")
            client.get_datalog_data.assert_called_once_with(
                "e45:1", self.start.timestamp(), self.end.timestamp()
            )
            client.cache_conn.close.assert_called_once()

    def test_inaccessible_sensor_fails_and_closes_cache(self):
        with patch("hamapi.hamapi") as factory:
            factory.return_value.get_user_devices.return_value = {"devices": []}
            with self.assertRaisesRegex(ValueError, "cannot access"):
                HamApi(api_key="test-key").readings("e45:1", self.start, self.end)
            factory.return_value.get_datalog_data.assert_not_called()
            factory.return_value.cache_conn.close.assert_called_once()

    def test_device_fetch_uses_configured_key_and_closes_cache(self):
        with patch("hamapi.hamapi") as factory:
            client = factory.return_value
            client.get_user_devices.return_value = {"devices": []}
            self.assertEqual(HamApi(api_key="test-key").devices(), {"devices": []})
            factory.assert_called_once_with(api_key="test-key", cache_db_file=":memory:")
            client.get_user_devices.assert_called_once_with(force_refresh=True)
            client.cache_conn.close.assert_called_once()

    def test_failed_library_request_closes_cache(self):
        with patch("hamapi.hamapi") as factory:
            client = factory.return_value
            client.get_user_devices.side_effect = OSError("Unavailable")
            with self.assertRaisesRegex(OSError, "Unavailable"):
                HamApi(api_key="test-key").devices()
            client.cache_conn.close.assert_called_once()

    def test_catalog_is_public_and_has_a_timeout(self):
        with patch(
            "infra.dagster.ham.client.urlopen", return_value=io.BytesIO(b'{"T": {}}')
        ) as fetch:
            self.assertEqual(HamApi().catalog("readings"), {"T": {}})
        fetch.assert_called_once_with("https://api.hamsystems.eu/res/doc/readings.json", timeout=30)

    def test_catalog_rejects_empty_or_non_object_responses(self):
        for body in (b"{}", b"[]", b"null"):
            with (
                self.subTest(body=body),
                patch("infra.dagster.ham.client.urlopen", return_value=io.BytesIO(body)),
            ):
                with self.assertRaisesRegex(ValueError, "nonempty object"):
                    HamApi().catalog("models")

    def test_database_engine_is_disposed_after_failure(self):
        with patch("infra.dagster.resources.create_engine") as create_engine:
            database = LeColazDatabase(
                host="postgres", database="fixture", username="fixture", password="fixture"
            )
            with self.assertRaisesRegex(OSError, "failed import"):
                with database.engine():
                    raise OSError("failed import")
            create_engine.return_value.dispose.assert_called_once()
