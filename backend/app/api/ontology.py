# app/api/ontology.py

from fastapi import APIRouter, Depends, HTTPException

from app.ontology.exceptions import FusekiPublishError, OntologyValidationError, SchemaFileError
from app.ontology.service import OntologyService, get_ontology_service

router = APIRouter(prefix="/ontology", tags=["Ontology"])


@router.post("/resync")
def resync_ontology(service: OntologyService = Depends(get_ontology_service)):
    return service.resync_unsynced_datasets()


@router.post("/schema/reload")
def reload_ontology_schema(service: OntologyService = Depends(get_ontology_service)):
    try:
        return service.reload_schema()
    except (SchemaFileError, OntologyValidationError) as exc:
        raise HTTPException(500, str(exc))
    except FusekiPublishError as exc:
        raise HTTPException(502, str(exc))
