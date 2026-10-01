"""Reusable Dagster IO manager for partitioned bytes in S3-compatible storage."""

import hashlib
from urllib.parse import quote

from dagster import ConfigurableIOManager, InputContext, OutputContext


def artifact_key(
    asset_path: list[str], partition: str, prefix: str, extension: str
) -> str:
    parts = [quote(part, safe="") for part in [*asset_path, partition]]
    return "/".join([prefix.strip("/"), *parts]).lstrip("/") + "." + extension


class S3BytesIOManager(ConfigurableIOManager):
    """Store raw bytes without pickling; load them across runs without refetching.

    Assets may set object_store_prefix for their own storage namespace and
    source_fingerprint to reject stale artifacts after a source mapping changes.
    """

    extension: str = "csv"
    content_type: str = "text/csv"

    def store(self):
        # Load backend settings and connect only when an asset executes.
        from app.storage.object.minio import MinioStore

        return MinioStore()

    def handle_output(self, context: OutputContext, obj: bytes) -> None:
        if not isinstance(obj, bytes):
            raise TypeError("S3BytesIOManager accepts bytes only")
        key = artifact_key(
            context.asset_key.path,
            context.asset_partition_key,
            (context.definition_metadata or {}).get("object_store_prefix", ""),
            self.extension,
        )
        checksum = hashlib.sha256(obj).hexdigest()
        metadata = {"sha256": checksum}
        fingerprint = (context.definition_metadata or {}).get("source_fingerprint")
        if fingerprint:
            metadata["source-fingerprint"] = fingerprint
        store = self.store()
        store.put_object(key, obj, self.content_type, metadata=metadata)
        context.add_output_metadata(
            {
                "uri": f"s3://{store.bucket}/{key}",
                "byte_count": len(obj),
                "sha256": checksum,
            }
        )

    def load_input(self, context: InputContext) -> bytes:
        upstream = context.upstream_output
        key = artifact_key(
            upstream.asset_key.path,
            context.asset_partition_key,
            (upstream.definition_metadata or {}).get("object_store_prefix", ""),
            self.extension,
        )
        response = self.store().get_object_stream(key)
        try:
            data = response.read()
            metadata = {
                name.lower().removeprefix("x-amz-meta-"): value
                for name, value in response.headers.items()
                if name.lower().startswith("x-amz-meta-")
            }
        finally:
            response.close()
            response.release_conn()
        expected = (upstream.definition_metadata or {}).get("source_fingerprint")
        if expected and metadata.get("source-fingerprint") != expected:
            raise ValueError(
                "Raw artifact source changed; rematerialize its upstream partition"
            )
        if metadata.get("sha256") != hashlib.sha256(data).hexdigest():
            raise ValueError("Raw artifact checksum mismatch")
        return data
