import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db.base import Base


class BimModel(Base):
    __tablename__ = "bim_models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Link to the generic file row
    file_id = Column(
        UUID(as_uuid=True),
        ForeignKey("file_metadata.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,  # 1 BIM record per file (remove if multiple needed)
    )

    # Minimal BIM-specific fields (extend later)
    format = Column(String, nullable=False)          # e.g. "ifc"
    schema = Column(String, nullable=True)           # e.g. "IFC4", "IFC2X3" (optional)

    extra = Column(JSONB, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
