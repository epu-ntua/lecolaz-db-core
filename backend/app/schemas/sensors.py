from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

SensorFamily = Literal["ham", "openmeteo"]


class SensorObservationTypeResponse(BaseModel):
    id: UUID
    unit: str
    label: str


class SensorTimestampBoundsResponse(BaseModel):
    start: datetime | None
    end: datetime | None


class SensorTimeseriesPointResponse(BaseModel):
    id: UUID
    timestamp: datetime
    value: float


class SensorListRequest(BaseModel):
    """Reserved for family-specific credentials/options in a future API version."""

    model_config = ConfigDict(extra="forbid")


class SensorSettings(BaseModel):
    """User-managed fields: omission preserves values; null clears nullable fields."""

    model_config = ConfigDict(extra="forbid")

    starting_date: AwareDatetime | None = None
    bim_dataset_id: UUID | None = None
    name: str | None = Field(default=None, description="Custom name; omit to preserve it. Null is not allowed.")
    location: str | None = None
    space: str | None = None

    @field_validator("name")
    @classmethod
    def nonnull_name(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Omit name to preserve it; null is not allowed")
        return value

    @field_validator("name", "location", "space")
    @classmethod
    def nonblank_text(cls, value: str | None) -> str | None:
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("Must not be blank")
        return value

    @field_validator("starting_date")
    @classmethod
    def normalize_start(cls, value: datetime | None) -> datetime:
        if value is None:
            raise ValueError("Omit starting_date to preserve the default; null is not allowed")
        return value.astimezone(timezone.utc)


class SensorSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    external_id: str = Field(min_length=1, max_length=255)
    settings: SensorSettings = Field(default_factory=SensorSettings)

    @field_validator("external_id")
    @classmethod
    def nonempty_id(cls, value: str) -> str:
        if not value.strip() or value != value.strip():
            raise ValueError("external_id must be nonempty and have no surrounding whitespace")
        return value


class SensorRegistrationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sensor_family: SensorFamily
    sensors: list[SensorSelection] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def unique_selection(self):
        ids = [sensor.external_id for sensor in self.sensors]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate external_ids are not allowed")
        return self


class EligibleSensorResponse(BaseModel):
    sensor_family: SensorFamily
    external_id: str
    name: str
    location: str | None = None
    space: str | None = None
    registered: bool
    id: UUID | None = None
    starting_date: datetime | None = None
    bim_dataset_id: UUID | None = None
    modular_component_id: UUID | None = None


class RegisteredSensorResponse(BaseModel):
    id: UUID
    sensor_family: SensorFamily
    external_id: str
    name: str
    location: str | None
    space: str | None = None
    starting_date: datetime
    bim_dataset_id: UUID | None
    modular_component_id: UUID | None


class DagsterReloadResponse(BaseModel):
    status: Literal["reloaded", "failed"]
    message: str | None = None


class SensorBackfillResponse(BaseModel):
    sensor_id: UUID
    status: Literal["submitted", "skipped", "failed"]
    backfill_id: str | None = None
    target_count: int = 0
    message: str | None = None


class SensorRegistrationResponse(BaseModel):
    sensors: list[RegisteredSensorResponse]
    dagster: DagsterReloadResponse
    backfills: list[SensorBackfillResponse] = Field(default_factory=list)
