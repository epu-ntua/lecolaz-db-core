# app/ontology/config.py

from app.core.config import settings


def build_graph_uri(bim_dataset_id) -> str:
    """https://w3id.org/lecolaz/graph/bim/{bim_dataset_id}"""
    return f"{settings.LECO_NAMESPACE}graph/bim/{bim_dataset_id}"


def build_schema_graph_uri() -> str:
    """https://w3id.org/lecolaz/graph/schema (same graph as SCHEMA_GRAPH in infra/compose*.yaml)"""
    return f"{settings.LECO_NAMESPACE}graph/schema"
