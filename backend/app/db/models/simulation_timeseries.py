import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class SimulationTimeseries(Base):
    __tablename__ = "simulation_timeseries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    simulation_dataset_id = Column(
        UUID(as_uuid=True),
        ForeignKey("simulation_datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    variable_id = Column(
        UUID(as_uuid=True),
        ForeignKey("simulation_variables.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    timestamp = Column(DateTime(timezone=True), primary_key=True, nullable=False, index=True)

    value = Column(Float, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
