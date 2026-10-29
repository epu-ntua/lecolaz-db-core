"""Read-only graph exploration, independent of Postgres and the publishing flow."""

import json
from threading import Lock

from pyparsing import ParseBaseException, ParseResults
from rdflib.plugins.sparql.parser import parseQuery
from rdflib.plugins.sparql.parserutils import CompValue

from app.core.config import settings
from app.ontology.exceptions import FusekiQueryError, InvalidOntologyQuery
from app.ontology.fuseki_client import FusekiClient

MAX_QUERY_LENGTH = 100_000
# RDFLib's shared pyparsing grammar mutates parse-action state. FastAPI runs
# these synchronous endpoints in parallel threads; only parsing is serialized.
_parse_lock = Lock()


def validate_query(query: str) -> str:
    """Parse SPARQL rather than guessing its operation from keywords in text."""
    if not query.strip() or len(query) > MAX_QUERY_LENGTH:
        raise InvalidOntologyQuery("A query of at most 100,000 characters is required.")
    try:
        with _parse_lock:
            parsed = parseQuery(query)
    except (ParseBaseException, ValueError, RecursionError) as exc:
        raise InvalidOntologyQuery("Invalid SPARQL query.") from exc

    kind = parsed[1].name
    if kind not in {"SelectQuery", "ConstructQuery"}:
        raise InvalidOntologyQuery("Only SELECT and CONSTRUCT queries are supported.")

    def check(node):
        if isinstance(node, CompValue):
            # SERVICE can make network requests even inside a SELECT. FROM can
            # load external graphs and would override the complete local graph.
            if node.name in {"ServiceGraphPattern", "DatasetClause"}:
                raise InvalidOntologyQuery("SERVICE and FROM are not allowed in explorer queries.")
            for value in node.values():
                check(value)
        elif isinstance(node, (list, tuple, ParseResults)):
            for value in node:
                check(value)

    check(parsed)
    return "text/turtle" if kind == "ConstructQuery" else "application/sparql-results+json"


def initial_instances_query() -> str:
    # Class IRIs are fixed by the ontology; instance IRIs are discovered afresh.
    # The path works without inference and across schema/data named graphs.
    return f"""PREFIX leco: <{settings.LECO_NAMESPACE}>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
SELECT DISTINCT ?inst WHERE {{
    VALUES ?root {{ leco:Building leco:ModularComponent leco:SimulationRun leco:EnergyModelDataset }}
    ?inst rdf:type/rdfs:subClassOf* ?root .
    FILTER(isIRI(?inst))
    FILTER NOT EXISTS {{ ?inst a owl:Class }}
    FILTER NOT EXISTS {{ ?inst a rdfs:Class }}
}}
ORDER BY ?inst
"""


class OntologyQueryService:
    def __init__(self, fuseki_client: FusekiClient | None = None):
        self._fuseki_client = fuseki_client or FusekiClient()

    def query(self, query: str) -> tuple[bytes, str]:
        media_type = validate_query(query)
        return self._fuseki_client.query(query=query, media_type=media_type), media_type

    def initial_instances(self) -> list[str]:
        content, _ = self.query(initial_instances_query())
        try:
            bindings = json.loads(content)["results"]["bindings"]
            return [row["inst"]["value"] for row in bindings if row["inst"]["type"] == "uri"]
        except (ValueError, KeyError, TypeError) as exc:
            raise FusekiQueryError("The knowledge graph returned an invalid response.") from exc


def get_ontology_query_service() -> OntologyQueryService:
    return OntologyQueryService()
