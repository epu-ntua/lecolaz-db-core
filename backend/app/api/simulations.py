import uuid

from fastapi import APIRouter, HTTPException

from app.schemas import (
    SimulationFileResponse,
    SimulationTimeseriesResponse,
    SimulationVariableResponse,
)
from app.storage.postgres.simulation_store import SimulationStore
from app.storage.postgres.simulation_timeseries_store import SimulationTimeseriesStore
from app.storage.postgres.simulation_variable_store import SimulationVariableStore


router = APIRouter(prefix="/simulations", tags=["Simulations"])


@router.get("", response_model=list[SimulationFileResponse])
def list_simulations(limit: int = 100):
    simulation_store = SimulationStore()
    return simulation_store.list_simulation_models(limit=limit)


@router.get("/by-dataset/{dataset_id}", response_model=SimulationFileResponse)
def get_simulation_by_dataset(dataset_id: str):
    simulation_store = SimulationStore()
    try:
        dataset_uuid = uuid.UUID(dataset_id)
    except ValueError:
        raise HTTPException(400, "Invalid dataset id")

    simulation = simulation_store.get_simulation_by_dataset_id(dataset_uuid)
    if not simulation:
        raise HTTPException(404, "Simulation not found")
    return simulation

@router.get(
    "/{simulation_id}/variables",
    response_model=list[SimulationVariableResponse],
)
def list_simulation_variables(simulation_id: str):
    variable_store = SimulationVariableStore()

    try:
        simulation_uuid = uuid.UUID(simulation_id)
    except ValueError:
        raise HTTPException(400, "Invalid simulation id")

    simulation_store = SimulationStore()
    simulation = simulation_store.get_simulation_by_id(simulation_uuid)
    if not simulation:
        raise HTTPException(404, "Simulation not found")

    return variable_store.list_by_simulation_dataset_id(simulation_uuid)


@router.get(
    "/{simulation_id}/timeseries",
    response_model=list[SimulationTimeseriesResponse],
)
def list_simulation_timeseries(
    simulation_id: str,
    variable_id: str,
    limit: int | None = None,
):
    timeseries_store = SimulationTimeseriesStore()

    try:
        simulation_uuid = uuid.UUID(simulation_id)
    except ValueError:
        raise HTTPException(400, "Invalid simulation id")

    try:
        variable_uuid = uuid.UUID(variable_id)
    except ValueError:
        raise HTTPException(400, "Invalid variable id")

    simulation_store = SimulationStore()
    simulation = simulation_store.get_simulation_by_id(simulation_uuid)
    if not simulation:
        raise HTTPException(404, "Simulation not found")

    return timeseries_store.list_by_simulation_dataset_and_variable_id(
        simulation_dataset_id=simulation_uuid,
        variable_id=variable_uuid,
        limit=limit,
    )
