import uuid

from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db.base import Base


class SimulationModel(Base):
    __tablename__ = "simulation_models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Link to the generic file row
    file_id = Column(
        UUID(as_uuid=True),
        ForeignKey("file_metadata.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=False,  # 1 simulation record per file (remove if multiple needed)
    )
    filename = Column(String, nullable=False)  # Store original filename for reference

    # Minimal simulation-specific fields (extend later)
    format = Column(String, nullable=False)  # e.g. "eso"
    schema = Column(String, nullable=True)
    status = Column(String, nullable=False, server_default="uploaded", index=True)

    extra = Column(JSONB, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
