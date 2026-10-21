"""Refresh database-driven definitions through Dagster's GraphQL endpoint."""

import logging
from urllib.parse import urlsplit

from dagster_graphql import (
    DagsterGraphQLClient,
    DagsterGraphQLClientError,
    ReloadRepositoryLocationStatus,
)

from app.core.config import settings

LOGGER = logging.getLogger(__name__)


def reload_sensor_location() -> dict:
    """The DB has committed already; surface reload failure without losing that fact."""
    try:
        url = urlsplit(settings.DAGSTER_GRAPHQL_URL)
        path = url.path.rstrip("/")
        if (
            url.scheme not in ("http", "https") or not url.hostname
            or not path.endswith("/graphql")
            or url.query or url.fragment or url.username or url.password
        ):
            raise ValueError("DAGSTER_GRAPHQL_URL must be an HTTP(S) endpoint ending in /graphql")
        # The SDK appends /graphql itself. Preserve configured ports, HTTPS, and
        # reverse-proxy prefixes without changing the existing URL setting.
        client = DagsterGraphQLClient(
            hostname=f"[{url.hostname}]" if ":" in url.hostname else url.hostname,
            port_number=url.port,
            use_https=url.scheme == "https",
            path_prefix=path.removesuffix("/graphql"),
            timeout=60,
        )
        result = client.reload_repository_location(settings.DAGSTER_CODE_LOCATION)
        if result.status == ReloadRepositoryLocationStatus.SUCCESS:
            return {"status": "reloaded"}
        LOGGER.warning(
            "Sensor registration committed, but Dagster reload failed (%s): %s",
            result.failure_type, result.message,
        )
    except (DagsterGraphQLClientError, ValueError) as exc:
        LOGGER.warning("Sensor registration committed, but Dagster reload failed: %s", exc)
    return {
        "status": "failed",
        "message": (
            "Sensors were saved. Retry the same registration or reload the "
            f"{settings.DAGSTER_CODE_LOCATION} code location in Dagster."
        ),
    }
