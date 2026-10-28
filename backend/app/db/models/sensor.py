import uuid

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base

class Sensor(Base):
    __tablename__ = "sensors"

    __table_args__ = (
        UniqueConstraint(
            "sensor_family",
            "external_id",
            name="uq_sensors_sensor_family_external_id",
        ),
        # A sensor is placed on a building or on a modular component, never both.
        CheckConstraint(
            "bim_dataset_id IS NULL OR modular_component_id IS NULL",
            name="ck_sensors_single_link",
        ),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    bim_dataset_id = Column(
        UUID(as_uuid=True),
        ForeignKey("bim_datasets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    modular_component_id = Column(
        UUID(as_uuid=True),
        ForeignKey("modular_components.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    name = Column(
        String,
        nullable=False,
    )

    external_id = Column(
        String,
        nullable=True,
    )

    sensor_family = Column(
        Text,
        nullable=True,
        comment="Contains the brand/model family of the sensor, if applicable.",
    )

    sensor_metadata = Column(
        JSONB,
        nullable=True,
    )

    location = Column(
        Text,
        nullable=True,
    )

    space = Column(
        Text,
        nullable=True,
    )

    starting_date = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("TIMESTAMPTZ '2026-01-01 00:00:00 UTC'"),
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
