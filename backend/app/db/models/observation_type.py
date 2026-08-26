import uuid

from sqlalchemy import (
  Column,
  DateTime,
  String,
  Text,
  func,
  text,
  UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base

class ObservationType(Base):
    __tablename__ = "observation_types"

    __table_args__ = (
      UniqueConstraint(
        "sensor_family",
        "key",
        name="uq_observation_types_sensor_family_key",
      ),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    label = Column(
        String,
        nullable=False,
        comment="Describes the content of the value (e.g. Power, Voltage, Luminosity).",
    )

    unit = Column(
        String,
        nullable=False,
        comment="Describes the unit of the value (e.g. kWh, V, mA).",
    )

    key = Column(
        String,
        nullable=False,
        comment="Identifier used to extract the value from an observation record. Could be a JSON dict key or a column name.",
    )

    sensor_family = Column(
        Text,
        nullable=True,
        comment="Contains the brand/model family of the sensor observations of this type are extracted from, if applicable.",
    )

    type_metadata = Column(
        JSONB,
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
