import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db.base import Base


class BimDataset(Base):
    __tablename__ = "bim_datasets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,
    )
    filename = Column(String, nullable=False)
    format = Column(String, nullable=False)
    schema = Column(String, nullable=True)
    stats = Column(JSONB, nullable=True)
    units = Column(JSONB, nullable=True)

    extra = Column(JSONB, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
