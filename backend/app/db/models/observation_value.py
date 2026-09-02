import uuid

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base

class ObservationValue(Base):
    __tablename__ = "observation_values"

    __table_args__ = (
        UniqueConstraint(
            "sensor_id",
            "observation_type_id",
            "timestamp",
            name="uq_observation_values_sensor_type_timestamp",
        ),
        Index(
            "ix_observation_values_sensor_timestamp",
            "sensor_id",
            "timestamp",
        ),
        Index(
            "ix_observation_values_sensor_type_timestamp",
            "sensor_id",
            "observation_type_id",
            "timestamp",
        ),
        Index(
            "ix_observation_values_type_timestamp",
            "observation_type_id",
            "timestamp",
        ),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    sensor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sensors.id", ondelete="CASCADE"),
        nullable=False,
    )

    observation_type_id = Column(
        UUID(as_uuid=True),
        ForeignKey("observation_types.id", ondelete="CASCADE"),
        nullable=False,
    )

    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
    )

    value = Column(
        Float,
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
