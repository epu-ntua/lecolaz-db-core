# app/ontology/fuseki_client.py
"""
Talks to Apache Fuseki via the SPARQL 1.1 Graph Store Protocol.

Uses HTTP PUT (not POST/SPARQL Update) so re-running a sync for the same
named graph replaces its triples wholesale instead of appending duplicates.
"""

import httpx

from app.ontology.config import ontology_settings
from app.ontology.exceptions import FusekiPublishError


class FusekiClient:
    def __init__(
        self,
        base_url: str | None = None,
        dataset: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self._base_url = (base_url or ontology_settings.FUSEKI_BASE_URL).rstrip("/")
        self._dataset = dataset or ontology_settings.FUSEKI_DATASET
        self._timeout = timeout or ontology_settings.FUSEKI_TIMEOUT_SECONDS

    async def put_graph(self, *, graph_uri: str, turtle: str) -> None:
        url = f"{self._base_url}/{self._dataset}/data"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.put(
                    url,
                    params={"graph": graph_uri},
                    content=turtle.encode("utf-8"),
                    headers={"Content-Type": "text/turtle; charset=utf-8"},
                )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:500]
            raise FusekiPublishError(
                f"Fuseki rejected PUT for graph {graph_uri} "
                f"({exc.response.status_code}): {body}"
            ) from exc
        except httpx.HTTPError as exc:
            raise FusekiPublishError(f"Failed to reach Fuseki at {url}: {exc}") from exc
