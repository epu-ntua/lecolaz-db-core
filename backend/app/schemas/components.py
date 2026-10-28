import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


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


class ModularComponentSensorsUpdate(BaseModel):
    # Only the named sensors change, so concurrent edits by other users are kept.
    add: list[uuid.UUID] = Field(default_factory=list, max_length=500)
    remove: list[uuid.UUID] = Field(default_factory=list, max_length=500)

    @model_validator(mode="after")
    def disjoint(self):
        if set(self.add) & set(self.remove):
            raise ValueError("A sensor cannot be both added and removed")
        return self
