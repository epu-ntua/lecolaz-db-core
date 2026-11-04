import uuid
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.schemas import (
    ModularComponentBuildingUpdate,
    ModularComponentResponse,
    ModularComponentSensorsUpdate,
)
from app.schemas.sensors import RegisteredSensorResponse
from app.services.modular_component_service import (
    ComponentBuildingInvalid,
    ComponentNotFound,
    ComponentSensorsUnavailable,
    update_component_building,
    update_component_sensors,
)
from app.storage.object.minio import MinioStore
from app.storage.postgres.modular_component_store import ModularComponentStore


router = APIRouter(prefix="/components", tags=["Modular components"])


@router.get("", response_model=list[ModularComponentResponse])
def list_components(limit: int = Query(100, ge=1), offset: int = Query(0, ge=0)):
    return ModularComponentStore().list_components(limit=limit, offset=offset)


@router.get("/{component_id}", response_model=ModularComponentResponse)
def get_component(component_id: uuid.UUID):
    component = ModularComponentStore().get_by_id(component_id)
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")
    return component


@router.patch("/{component_id}/building", response_model=ModularComponentResponse)
def update_building(component_id: uuid.UUID, payload: ModularComponentBuildingUpdate):
    try:
        return update_component_building(component_id, payload.bim_dataset_id)
    except ComponentNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ComponentBuildingInvalid as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/{component_id}/sensors", response_model=list[RegisteredSensorResponse])
def update_sensors(component_id: uuid.UUID, payload: ModularComponentSensorsUpdate):
    try:
        return update_component_sensors(component_id, payload.add, payload.remove)
    except ComponentNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ComponentSensorsUnavailable as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{component_id}/files/{kind}")
def get_component_file(component_id: uuid.UUID, kind: Literal["photo", "qr", "ifc"]):
    component = ModularComponentStore().get_by_id(component_id)
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")
    object_key = component[f"{kind}_object_key"]
    if not object_key:
        raise HTTPException(status_code=404, detail=f"Component has no {kind} file")

    try:
        response = MinioStore().get_object_stream(object_key)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail="Failed to fetch file from object storage") from exc

    def file_iterator():
        try:
            for chunk in response.stream(32 * 1024):
                yield chunk
        finally:
            response.close()
            response.release_conn()

    return StreamingResponse(
        file_iterator(),
        media_type=response.headers.get("Content-Type", "application/octet-stream"),
    )
