from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()

class Settings:
    # App
    APP_NAME: str = os.getenv("APP_NAME", "LeColaz")
    APP_ENV: str = os.getenv("APP_ENV", "dev")
    # Externally reachable base URL of this API, written into links stored in
    # Fuseki (for example, leco:timeSeriesRef). Use the public reverse-proxy
    # URL in production, including its /api prefix; never a Docker-internal URL.
    API_PUBLIC_BASE_URL: str = os.getenv("API_PUBLIC_BASE_URL", "http://localhost:8000")

    # Postgres
    POSTGRES_DSN: str = os.getenv("POSTGRES_DSN")

    # Sensor catalogs and post-registration asset discovery.
    HAMAPI_API_KEY: str = os.getenv("HAMAPI_API_KEY", "")
    DAGSTER_GRAPHQL_URL: str = os.getenv("DAGSTER_GRAPHQL_URL", "http://localhost:3000/graphql")
    DAGSTER_CODE_LOCATION: str = os.getenv("DAGSTER_CODE_LOCATION", "lecolaz")

    # MinIO
    MINIO_INTERNAL_ENDPOINT: str = os.getenv("MINIO_INTERNAL_ENDPOINT")
    MINIO_PUBLIC_ENDPOINT: str = os.getenv("MINIO_PUBLIC_ENDPOINT")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY")
    MINIO_BUCKET: str = os.getenv("MINIO_BUCKET")

    # Ontology / Fuseki
    LECO_NAMESPACE: str = os.getenv("LECO_NAMESPACE", "https://w3id.org/lecolaz/")
    FUSEKI_BASE_URL: str = os.getenv("FUSEKI_BASE_URL", "http://localhost:3030")
    FUSEKI_DATASET: str = os.getenv("FUSEKI_DATASET", "lecolaz")
    FUSEKI_TIMEOUT_SECONDS: float = float(os.getenv("FUSEKI_TIMEOUT_SECONDS", "30"))
    # The dataset's update/data endpoints require Basic Auth (see
    # infra/compose.yaml's fuseki service).
    FUSEKI_ADMIN_USER: str = os.getenv("FUSEKI_ADMIN_USER", "admin")
    FUSEKI_ADMIN_PASSWORD: str = os.getenv("FUSEKI_ADMIN_PASSWORD", "")
    # Ontology schema loaded by POST /ontology/schema/reload. Defaults to its
    # repo location; in the backend container that resolves to
    # /resources/ontology/, where infra/compose*.yaml mounts it.
    LECO_SCHEMA_PATH: str = os.getenv(
        "LECO_SCHEMA_PATH",
        str(Path(__file__).resolve().parents[3] / "resources" / "ontology" / "le_colaz_ontology_schema.ttl"),
    )

settings = Settings()
