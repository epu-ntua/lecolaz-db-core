from dotenv import load_dotenv
import os

load_dotenv()

class Settings:
    # App
    APP_NAME: str = os.getenv("APP_NAME", "LeColaz")
    APP_ENV: str = os.getenv("APP_ENV", "dev")

    # Postgres
    POSTGRES_DSN: str = os.getenv("POSTGRES_DSN")

    # MinIO
    MINIO_INTERNAL_ENDPOINT: str = os.getenv("MINIO_INTERNAL_ENDPOINT")
    MINIO_PUBLIC_ENDPOINT: str = os.getenv("MINIO_PUBLIC_ENDPOINT")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY")
    MINIO_BUCKET: str = os.getenv("MINIO_BUCKET")

settings = Settings()
