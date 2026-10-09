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

    def test_fetch_preserves_bytes_and_uses_device_server_and_daily_bin(self):
        for server, expected in (("node2", "node2"), ("device0.hamsystems.eu", "node0"), (None, "node0")):
            with (
                self.subTest(server=server),
                patch.object(HamApi, "devices", return_value={"devices": [{"serialno": "e45:1", "device_server": server}]}),
                patch("infra.dagster.ham.client.requests.post") as post,
                patch("hamapi.hamapi", side_effect=AssertionError("SDK")),
            ):
                response = post.return_value.__enter__.return_value
                response.content = b"\xef\xbb\xbf1767225600;2150;4500;2500;0\r\n"
                actual = HamApi(api_key="test-key").readings("e45:1", self.start, self.start + timedelta(days=1))
                self.assertEqual(actual, response.content)
                post.assert_called_once_with(
                    f"https://{expected}.hamsystems.eu/datalogs.php",
                    params={"serialno": "e45:1", "id": f"0.{int(self.start.timestamp()) // 86400}"},
                    data={"api_key": "test-key"},
                    timeout=(10, 60),
                )
                response.raise_for_status.assert_called_once()

    def test_inaccessible_sensor_fails_without_fetch(self):
        with patch.object(HamApi, "devices", return_value={"devices": []}), patch("requests.post") as post:
            with self.assertRaisesRegex(ValueError, "cannot access"):
                HamApi(api_key="test-key").readings("e45:1", self.start, self.end)
            post.assert_not_called()

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

    def test_failed_device_request_propagates(self):
        with patch.object(HamApi, "devices", side_effect=OSError("Unavailable")):
            with self.assertRaisesRegex(OSError, "Unavailable"):
                HamApi(api_key="test-key").readings("e45:1", self.start, self.end)

    def test_invalid_device_response_server_and_multi_day_interval(self):
        for response in ({"error": "denied"}, {"devices": None}, {"devices": [{"serialno": "e45:1", "device_server": "evil.example"}]}):
            with patch.object(HamApi, "devices", return_value=response), patch("requests.post") as post:
                with self.assertRaises(ValueError):
                    HamApi(api_key="test").readings("e45:1", self.start, self.end)
                post.assert_not_called()
        with self.assertRaisesRegex(ValueError, "one UTC day"):
            HamApi().readings("e45:1", self.start, self.start + timedelta(days=2))

    def test_datalog_http_failure_closes_response(self):
        with patch.object(HamApi, "devices", return_value={"devices": [{"serialno": "e45:1"}]}), patch("requests.post") as post:
            response = post.return_value.__enter__.return_value
            response.raise_for_status.side_effect = requests.HTTPError("Unauthorized")
            with self.assertRaises(requests.HTTPError):
                HamApi(api_key="test").readings("e45:1", self.start, self.end)
            post.return_value.__exit__.assert_called_once()

    def test_missing_file_fails_without_returning_payload_or_retrying(self):
        with patch.object(HamApi, "devices", return_value={"devices": [{"serialno": "14:690"}]}), patch("requests.post") as post:
            response = post.return_value.__enter__.return_value
            response.content = b'{"messages":["File not found"]}'
            for status in (200, 404):
                response.status_code = status
                with self.assertRaisesRegex(Failure, "file not found") as raised:
                    HamApi(api_key="test").readings("14:690", self.start, self.end)
                self.assertFalse(raised.exception.allow_retries)
            response.raise_for_status.assert_not_called()
            response.raise_for_status.side_effect = requests.HTTPError("Not found")
            for status, body in ((404, b"<html>Not found</html>"), (403, b'{"messages":["File not found"]}'), (404, b'{"messages":["Access denied"]}')):
                response.status_code, response.content = status, body
                with self.assertRaises(requests.HTTPError):
                    HamApi(api_key="test").readings("14:690", self.start, self.end)

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
                patch("infra.dagster.ham.catalog.files") as files,
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
