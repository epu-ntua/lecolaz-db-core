"""Resource configuration, HAM client contracts, and connection cleanup."""

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import requests
from sqlalchemy.engine import make_url

from dagster import Failure
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
        self.assertEqual(
            make_url(url.render_as_string(hide_password=False)).password, password
        )

    def test_fetch_passes_key_and_epoch_interval_and_closes_cache(self):
        with patch("hamapi.hamapi") as factory:
            client = factory.return_value
            client.get_user_devices.return_value = {"devices": [{"serialno": "e45:1"}]}
            client.get_datalog_data.return_value = {"timestamp": [], "T": []}
            HamApi(api_key="test-key").readings("e45:1", self.start, self.end)
            factory.assert_called_once_with(
                api_key="test-key", cache_db_file=":memory:"
            )
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

    def test_device_fetch_has_timeouts_and_checks_http_status(self):
        with patch("infra.dagster.ham.client.requests.post") as post:
            response = post.return_value.__enter__.return_value
            response.json.return_value = {"devices": []}
            self.assertEqual(HamApi(api_key="test-key").devices(), {"devices": []})
            post.assert_called_once_with(
                "https://api.hamsystems.eu/get_user_devices.php",
                data={"api_key": "test-key"},
                timeout=(10, 30),
            )
            response.raise_for_status.assert_called_once()
            response.raise_for_status.side_effect = requests.HTTPError("Unauthorized")
            with self.assertRaises(requests.HTTPError):
                HamApi(api_key="test-key").devices()

    def test_failed_library_request_closes_cache(self):
        with patch("hamapi.hamapi") as factory:
            client = factory.return_value
            client.get_user_devices.side_effect = OSError("Unavailable")
            with self.assertRaisesRegex(OSError, "Unavailable"):
                HamApi(api_key="test-key").readings("e45:1", self.start, self.end)
            client.cache_conn.close.assert_called_once()

    def test_catalogs_load_from_installed_package_without_key_or_network(self):
        with (
            patch(
                "requests.sessions.Session.request", side_effect=AssertionError("HTTP")
            ),
            patch("urllib.request.urlopen", side_effect=AssertionError("HTTP")),
            patch("hamapi.hamapi", side_effect=AssertionError("SDK client")),
        ):
            self.assertIn("T", HamApi().catalog("readings"))
            models = HamApi().catalog("models")
            self.assertTrue(models)
            self.assertTrue(any("readings" in model for model in models.values()))

    def test_catalog_rejects_empty_or_non_object_files(self):
        for body in ("{}", "[]", "null"):
            with (
                self.subTest(body=body),
                patch("infra.dagster.ham.client.files") as files,
            ):
                files.return_value.joinpath.return_value.read_text.return_value = body
                with self.assertRaisesRegex(ValueError, "nonempty object"):
                    HamApi().catalog("models")

    def test_database_engine_is_disposed_after_failure(self):
        with patch("infra.dagster.resources.create_engine") as create_engine:
            database = LeColazDatabase(
                host="postgres",
                database="fixture",
                username="fixture",
                password="fixture",
            )
            with self.assertRaisesRegex(OSError, "failed import"):
                with database.engine():
                    raise OSError("failed import")
            create_engine.return_value.dispose.assert_called_once()
