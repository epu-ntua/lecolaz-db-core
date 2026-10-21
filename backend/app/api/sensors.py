from fastapi import APIRouter, HTTPException

from app.schemas.sensors import (
    EligibleSensorResponse,
    SensorListRequest,
    SensorRegistrationRequest,
    SensorRegistrationResponse,
)
from app.services.sensor_catalog_service import (
    IneligibleSensors,
    SensorCatalogNotConfigured,
    SensorCatalogUnavailable,
)
from app.services.sensor_registration_service import (
    SensorBimNotFound,
    list_eligible_sensors,
    register_sensors,
)

router = APIRouter(prefix="/sensors", tags=["Sensors"])


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
    except SensorBimNotFound as exc:
        raise HTTPException(404, str(exc)) from exc
    except IneligibleSensors as exc:
        raise HTTPException(422, str(exc)) from exc
    except SensorCatalogNotConfigured as exc:
        raise HTTPException(503, str(exc)) from exc
    except SensorCatalogUnavailable as exc:
        raise HTTPException(502, str(exc)) from exc
