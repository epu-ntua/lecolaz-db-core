from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import AwareDatetime

from app.schemas.sensors import (
    EligibleSensorResponse,
    RegisteredSensorResponse,
    SensorFamily,
    SensorListRequest,
    SensorRegistrationRequest,
    SensorRegistrationResponse,
    SensorObservationTypeResponse,
    SensorTimestampBoundsResponse,
    SensorTimeseriesPointResponse,
)
from app.services.sensor_catalog_service import (
    IneligibleSensors,
    SensorCatalogNotConfigured,
    SensorCatalogUnavailable,
)
from app.services.sensor_registration_service import (
    SensorBimNotFound,
    SensorComponentNotFound,
    list_eligible_sensors,
    register_sensors,
)
from app.storage.postgres.sensor_store import SensorStore
from app.storage.postgres.observation_value_store import ObservationValueStore

router = APIRouter(prefix="/sensors", tags=["Sensors"])


@router.get("/{sensor_id}/observation-types", response_model=list[SensorObservationTypeResponse])
def list_sensor_observation_types(sensor_id: UUID):
    return ObservationValueStore().list_observation_types(sensor_id)


@router.get("/{sensor_id}/timeseries/bounds", response_model=SensorTimestampBoundsResponse)
def get_sensor_timestamp_bounds(sensor_id: UUID, observation_type_id: UUID):
    return ObservationValueStore().get_timestamp_bounds(sensor_id, observation_type_id)


@router.get("/{sensor_id}/timeseries", response_model=list[SensorTimeseriesPointResponse])
def list_sensor_timeseries(
    sensor_id: UUID, observation_type_id: UUID, start: AwareDatetime, end: AwareDatetime
):
    if start > end:
        raise HTTPException(422, "Start must be at or before end")
    return ObservationValueStore().list_timeseries(sensor_id, observation_type_id, start, end)


@router.get("/registered", response_model=list[RegisteredSensorResponse])
def list_registered_sensors(
    sensor_family: SensorFamily | None = None,
    bim_dataset_id: UUID | None = None,
    modular_component_id: UUID | None = None,
    unassigned: bool = False,
):
    return SensorStore().list_registered(
        sensor_family=sensor_family,
        bim_dataset_id=bim_dataset_id,
        modular_component_id=modular_component_id,
        unassigned=unassigned,
    )


def _catalog_response(family: str):
    try:
        return list_eligible_sensors(family)
    except SensorCatalogNotConfigured as exc:
        raise HTTPException(503, str(exc)) from exc
    except SensorCatalogUnavailable as exc:
        raise HTTPException(502, str(exc)) from exc


@router.post("/list/ham", response_model=list[EligibleSensorResponse])
def list_ham_sensors(request: SensorListRequest | None = None):
    return _catalog_response("ham")


@router.post("/list/openmeteo", response_model=list[EligibleSensorResponse])
def list_openmeteo_sensors(request: SensorListRequest | None = None):
    return _catalog_response("openmeteo")


@router.post("/register", response_model=SensorRegistrationResponse)
def register(request: SensorRegistrationRequest):
    try:
        return register_sensors(request)
    except (SensorBimNotFound, SensorComponentNotFound) as exc:
        raise HTTPException(404, str(exc)) from exc
    except IneligibleSensors as exc:
        raise HTTPException(422, str(exc)) from exc
    except SensorCatalogNotConfigured as exc:
        raise HTTPException(503, str(exc)) from exc
    except SensorCatalogUnavailable as exc:
        raise HTTPException(502, str(exc)) from exc
