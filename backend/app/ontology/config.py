# app/ontology/config.py
"""
Configuration for the ontology sync service.

Kept separate from app/core/config.py so this subsystem stays independently
configurable (e.g. a different Fuseki host per environment) without touching
unrelated app settings.
"""

import os


class OntologySettings:
    LECO_NAMESPACE: str = os.getenv("LECO_NAMESPACE", "https://w3id.org/lecolaz/")
    FUSEKI_BASE_URL: str = os.getenv("FUSEKI_BASE_URL", "http://localhost:3030")
    FUSEKI_DATASET: str = os.getenv("FUSEKI_DATASET", "lecolaz")
    FUSEKI_TIMEOUT_SECONDS: float = float(os.getenv("FUSEKI_TIMEOUT_SECONDS", "30"))


ontology_settings = OntologySettings()


def build_graph_uri(bim_dataset_id) -> str:
    """https://w3id.org/lecolaz/graph/bim/{bim_dataset_id}"""
    return f"{ontology_settings.LECO_NAMESPACE}graph/bim/{bim_dataset_id}"
