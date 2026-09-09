# app/ontology/exceptions.py


class OntologyServiceError(Exception):
    """Base class for all ontology-sync failures."""


class BimDatasetNotFoundError(OntologyServiceError):
    """Raised when the referenced bim_dataset_id has no matching row."""


class OntologyValidationError(OntologyServiceError):
    """Raised when generated Turtle fails to parse back with rdflib."""


class FusekiPublishError(OntologyServiceError):
    """Raised when the Graph Store Protocol PUT to Fuseki fails."""
