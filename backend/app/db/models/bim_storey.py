import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Float, String, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class BimStorey(Base):
    __tablename__ = "bim_storeys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bim_dataset_id = Column(
        UUID(as_uuid=True),
        ForeignKey("bim_datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    global_id = Column(String, nullable=False)
    name = Column(String, nullable=True)
    elevation = Column(Float, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
