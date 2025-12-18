from minio import Minio
from core.config import settings
import io
from datetime import timedelta
from minio.error import S3Error


class MinioStore:
    def __init__(self):
        self.bucket = settings.MINIO_BUCKET

        # Single internal client (Docker networking)
        self.client = Minio(
            settings.MINIO_INTERNAL_ENDPOINT
            .replace("http://", "")
            .replace("https://", ""),
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=False,
        )

        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                print(f"[MinIO] Bucket '{self.bucket}' created")
        except S3Error as e:
            raise RuntimeError(f"MinIO bucket check failed: {e}")

    def put_object(self, object_key: str, data: bytes, content_type: str | None):
        self.client.put_object(
            self.bucket,
            object_key,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )

    def get_presigned_get_url(self, object_key: str, expires_seconds: int = 3600):
        return self.client.presigned_get_object(
            self.bucket,
            object_key,
            expires=timedelta(seconds=expires_seconds),
        )
