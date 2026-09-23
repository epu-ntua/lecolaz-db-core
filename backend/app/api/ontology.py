# app/api/ontology.py

from fastapi import APIRouter, Depends

from app.ontology.service import OntologyService, get_ontology_service

router = APIRouter(prefix="/ontology", tags=["Ontology"])


@router.post("/resync")
def resync_ontology(service: OntologyService = Depends(get_ontology_service)):
    return service.resync_unsynced_datasets()
