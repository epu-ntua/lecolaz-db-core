"""Link modular components to the building and the sensors they are placed in/with."""

import uuid

from app.storage.postgres.bim_store import BimStore
from app.storage.postgres.modular_component_store import ModularComponentStore
from app.storage.postgres.sensor_store import SensorStore


class ComponentNotFound(ValueError):
    pass


class ComponentBuildingInvalid(ValueError):
    pass


class ComponentSensorsUnavailable(ValueError):
    pass


def update_component_building(
    component_id: uuid.UUID, bim_dataset_id: uuid.UUID | None
) -> dict:
    """Link the component to a pilot building, or disconnect it with None."""
    if bim_dataset_id:
        bim = BimStore().get_bim_by_id(bim_dataset_id)
        if not bim:
            raise ComponentBuildingInvalid("Building not found")
        if bim["category"] == "archetype":
            raise ComponentBuildingInvalid("Components can only be linked to pilot buildings")

    component = ModularComponentStore().update_building(component_id, bim_dataset_id)
    if not component:
        raise ComponentNotFound("Component not found")
    return component


def update_component_sensors(
    component_id: uuid.UUID, add: list[uuid.UUID], remove: list[uuid.UUID]
) -> list[dict]:
    """Add/remove sensors on the component; only free sensors can be added."""
    if not ModularComponentStore().get_by_id(component_id):
        raise ComponentNotFound("Component not found")

    store = SensorStore()
    unavailable = store.update_modular_component_sensors(component_id, add, remove)
    if unavailable:
        raise ComponentSensorsUnavailable(
            "Sensors not found or already linked to a building or another component: "
            + ", ".join(str(sensor_id) for sensor_id in unavailable)
        )
    return store.list_registered(modular_component_id=component_id)
