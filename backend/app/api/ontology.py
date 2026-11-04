# app/api/ontology.py

from fastapi import APIRouter, Body, Depends, HTTPException, Response

from app.ontology.exceptions import (
    FusekiPublishError,
    FusekiQueryError,
    InvalidOntologyQuery,
    OntologyValidationError,
    SchemaFileError,
)
from app.ontology.query_service import (
    MAX_QUERY_LENGTH,
    OntologyQueryService,
    get_ontology_query_service,
)
from app.ontology.service import OntologyService, get_ontology_service

router = APIRouter(prefix="/ontology", tags=["Ontology"])


@router.post("/query")
def query_ontology(
    query: str = Body(media_type="application/sparql-query", min_length=1, max_length=MAX_QUERY_LENGTH),
    service: OntologyQueryService = Depends(get_ontology_query_service),
):
    try:
        content, media_type = service.query(query)
    except InvalidOntologyQuery as exc:
        raise HTTPException(400, str(exc)) from exc
    except FusekiQueryError as exc:
        raise HTTPException(502, str(exc)) from exc
    return Response(content=content, media_type=media_type, headers={"Cache-Control": "no-store"})


@router.get("/instances", response_model=list[str])
def initial_ontology_instances(
    response: Response,
    service: OntologyQueryService = Depends(get_ontology_query_service),
):
    response.headers["Cache-Control"] = "no-store"
    try:
        return service.initial_instances()
    except FusekiQueryError as exc:
        raise HTTPException(502, str(exc)) from exc


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
