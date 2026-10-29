# app/ontology/exceptions.py


class OntologyServiceError(Exception):
    """Base class for all ontology-sync failures."""


class BimDatasetNotFoundError(OntologyServiceError):
    """Raised when the referenced bim_dataset_id has no matching row."""


class SimulationDatasetNotFoundError(OntologyServiceError):
    """Raised when the referenced simulation_dataset_id has no matching row."""


class OntologyValidationError(OntologyServiceError):
    """Raised when generated Turtle fails to parse back with rdflib."""


class FusekiPublishError(OntologyServiceError):
    """Raised when the Graph Store Protocol PUT to Fuseki fails."""


class FusekiQueryError(OntologyServiceError):
    """Raised when a read-only query to Fuseki fails."""


class InvalidOntologyQuery(ValueError):
    """Raised when an explorer query is invalid or outside the local read scope."""


class SchemaFileError(OntologyServiceError):
    """Raised when the ontology schema file is missing or empty."""
