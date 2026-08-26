import uuid

from sqlalchemy import (
    Column,
    DateTime,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base

class Sensor(Base):
    __tablename__ = "sensors"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    name = Column(
        String,
        nullable=False,
    )

    external_id = Column(
        String,
        nullable=True,
        unique=True,
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
