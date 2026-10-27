import uuid
from typing import Any, Literal

from pydantic import BaseModel


class ModularComponentResponse(BaseModel):
    id: str
    name: str
    component_class: Literal["FacadeElement", "InteriorWall", "FloorCovering"]
    bim_dataset_id: str | None
    dpp: dict[str, Any] | None
    photo_object_key: str | None
    qr_object_key: str | None
    ifc_object_key: str | None
    created_at: str | None


class ModularComponentBuildingUpdate(BaseModel):
    # None disconnects the component from its building.
    bim_dataset_id: uuid.UUID | None
