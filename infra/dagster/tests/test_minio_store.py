"""Minimal upload extension and Dagster use of the existing MinIO stream API."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.storage.object.minio import MinioStore

from infra.dagster.object_storage import S3BytesIOManager


class MinioStoreTests(unittest.TestCase):
    def test_upload_metadata_preserves_existing_callers(self):
        settings = SimpleNamespace(
            MINIO_INTERNAL_ENDPOINT="http://minio:9000",
            MINIO_ACCESS_KEY="key",
            MINIO_SECRET_KEY="secret",
            MINIO_BUCKET="shared-bucket",
        )
        with (
            patch("app.storage.object.minio.settings", settings),
            patch("app.storage.object.minio.Minio") as factory,
        ):
            store = MinioStore()
            factory.assert_called_once_with(
                "minio:9000",
                access_key="key",
                secret_key="secret",
                secure=False,
            )
            factory.return_value.bucket_exists.assert_called_once_with("shared-bucket")
            store.put_object("upload.bin", b"old", "application/octet-stream")
            call = factory.return_value.put_object.call_args
            self.assertEqual(call.args[2].read(), b"old")
            self.assertIsNone(call.kwargs["metadata"])
            store.put_object("day.csv", b"csv", "text/csv", metadata={"sha256": "hash"})
            call = factory.return_value.put_object.call_args
            self.assertEqual(call.kwargs["metadata"], {"sha256": "hash"})
            self.assertEqual(call.kwargs["length"], 3)

    def test_io_manager_uses_unconfigured_shared_store(self):
        with patch("app.storage.object.minio.MinioStore") as factory:
            self.assertIs(S3BytesIOManager().store(), factory.return_value)
            factory.assert_called_once_with()

    def test_storage_namespace_is_asset_specific(self):
        store = Mock(bucket="shared-bucket")
        context = SimpleNamespace(
            asset_key=SimpleNamespace(path=["reports", "daily"]),
            asset_partition_key="2026-01-01",
            definition_metadata={},
            add_output_metadata=Mock(),
        )
        with patch.object(S3BytesIOManager, "store", return_value=store):
            S3BytesIOManager().handle_output(context, b"data")
        self.assertEqual(
            store.put_object.call_args.args[0], "reports/daily/2026-01-01.csv"
        )

    def test_io_manager_releases_stream_on_read_failure(self):
        response = Mock(headers={})
        response.read.side_effect = OSError("connection closed")
        store = Mock()
        store.get_object_stream.return_value = response
        context = SimpleNamespace(
            upstream_output=SimpleNamespace(
                asset_key=SimpleNamespace(path=["raw", "sensor"]),
                definition_metadata={},
            ),
            asset_partition_key="2026-01-01",
        )
        with (
            patch.object(S3BytesIOManager, "store", return_value=store),
            self.assertRaises(OSError),
        ):
            S3BytesIOManager().load_input(context)
        response.close.assert_called_once()
        response.release_conn.assert_called_once()
