import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class BimSpace(Base):
    __tablename__ = "bim_spaces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bim_dataset_id = Column(
        UUID(as_uuid=True),
        ForeignKey("bim_datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    global_id = Column(String, nullable=False)
    name = Column(String, nullable=True)
    raw_name = Column(String, nullable=True)
    storey_id = Column(
        UUID(as_uuid=True),
        ForeignKey("bim_storeys.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    area = Column(Float, nullable=True)
    volume = Column(Float, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
