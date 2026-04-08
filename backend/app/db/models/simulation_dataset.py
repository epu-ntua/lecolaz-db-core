import uuid

from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db.base import Base


class SimulationDataset(Base):
    __tablename__ = "simulation_datasets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Link to the generic dataset row
    dataset_id = Column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,
    )
    filename = Column(String, nullable=False)  # Store original filename for reference

    format = Column(String, nullable=False)  # e.g. "eso"

    simulation_metadata = Column("metadata", JSONB, nullable=True)
    extra = Column(JSONB, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
