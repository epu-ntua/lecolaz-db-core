# app/ontology/fuseki_client.py
"""
Talks to Apache Fuseki via its query endpoint and SPARQL 1.1 Graph Store Protocol.

Uses HTTP PUT (not POST/SPARQL Update) so re-running a sync for the same
named graph replaces its triples wholesale instead of appending duplicates.
"""

import httpx

from app.core.config import settings
from app.ontology.exceptions import FusekiPublishError, FusekiQueryError


class FusekiClient:
    def __init__(
        self,
        base_url: str | None = None,
        dataset: str | None = None,
        timeout: float | None = None,
        auth: tuple[str, str] | None = None,
    ) -> None:
        self._base_url = (base_url or settings.FUSEKI_BASE_URL).rstrip("/")
        self._dataset = dataset or settings.FUSEKI_DATASET
        self._timeout = timeout or settings.FUSEKI_TIMEOUT_SECONDS
        self._auth = auth or (
            settings.FUSEKI_ADMIN_USER,
            settings.FUSEKI_ADMIN_PASSWORD,
        )

    def query(self, *, query: str, media_type: str) -> bytes:
        """Query the merged default and named graphs, including the shared schema.

        The query endpoint is public; do not forward admin credentials. Callers
        must validate untrusted SPARQL before passing it here.
        """
        url = f"{self._base_url}/{self._dataset}/query"
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(
                    url,
                    params=[
                        ("default-graph-uri", "urn:x-arq:UnionGraph"),
                        ("default-graph-uri", "urn:x-arq:DefaultGraph"),
                        ("timeout", str(int(self._timeout * 1000))),
                    ],
                    content=query.encode("utf-8"),
                    headers={
                        "Content-Type": "application/sparql-query; charset=utf-8",
                        "Accept": media_type,
                    },
                )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise FusekiQueryError("The knowledge graph query timed out. Try a smaller selection.") from exc
        except httpx.HTTPError as exc:
            raise FusekiQueryError("The knowledge graph could not be queried. Please try again.") from exc
        return response.content

    def put_graph(self, *, graph_uri: str, turtle: str) -> None:
        url = f"{self._base_url}/{self._dataset}/data"
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.put(
                    url,
                    params={"graph": graph_uri},
                    content=turtle.encode("utf-8"),
                    headers={"Content-Type": "text/turtle; charset=utf-8"},
                    auth=self._auth,
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
