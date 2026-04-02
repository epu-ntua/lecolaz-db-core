import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class SimulationTimeseries(Base):
    __tablename__ = "simulation_timeseries"
    __table_args__ = (
        Index(
            "ix_simulation_timeseries_dataset_timestamp",
            "simulation_dataset_id",
            "timestamp",
        ),
        Index(
            "ix_simulation_timeseries_dataset_variable_timestamp",
            "simulation_dataset_id",
            "variable_id",
            "timestamp",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    simulation_dataset_id = Column(
        UUID(as_uuid=True),
        ForeignKey("simulation_datasets.id", ondelete="CASCADE"),
        nullable=False,
    )

    variable_id = Column(
        UUID(as_uuid=True),
        ForeignKey("simulation_variables.id", ondelete="CASCADE"),
        nullable=False,
    )

    timestamp = Column(DateTime(timezone=True), primary_key=True, nullable=False)

    value = Column(Float, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
