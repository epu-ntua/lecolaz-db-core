import uuid

from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class SimulationVariable(Base):
    __tablename__ = "simulation_variables"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    simulation_dataset_id = Column(
        UUID(as_uuid=True),
        ForeignKey("simulation_datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    variable_id = Column(String, nullable=False)
    variable_name = Column(String, nullable=False)
    unit = Column(String, nullable=True)
    frequency = Column(String, nullable=True)

    key = Column(String, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
