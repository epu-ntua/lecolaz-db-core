import uuid
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas import ModularComponentBuildingUpdate, ModularComponentResponse
from app.storage.object.minio import MinioStore
from app.storage.postgres.bim_store import BimStore
from app.storage.postgres.modular_component_store import ModularComponentStore


router = APIRouter(prefix="/components", tags=["Modular components"])


@router.get("", response_model=list[ModularComponentResponse])
def list_components(limit: int = 100):
    return ModularComponentStore().list_components(limit=limit)


@router.get("/{component_id}", response_model=ModularComponentResponse)
def get_component(component_id: uuid.UUID):
    component = ModularComponentStore().get_by_id(component_id)
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")
    return component


@router.patch("/{component_id}/building", response_model=ModularComponentResponse)
def update_component_building(component_id: uuid.UUID, payload: ModularComponentBuildingUpdate):
    # TODO: the pilot-only rule is business logic and belongs in a service. It lives
    # here while it is the only rule; move it once linking gains more logic (e.g. KG sync).
    if payload.bim_dataset_id:
        bim = BimStore().get_bim_by_id(payload.bim_dataset_id)
        if not bim:
            raise HTTPException(status_code=400, detail="Building not found")
        if bim["category"] == "archetype":
            raise HTTPException(status_code=400, detail="Components can only be linked to pilot buildings")

    component = ModularComponentStore().update_building(component_id, payload.bim_dataset_id)
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")
    return component


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
