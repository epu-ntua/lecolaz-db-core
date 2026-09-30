import uuid

from sqlalchemy import Boolean, Column, String, Integer, DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db.base import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    type = Column(String, nullable=False)
    subtype = Column(String, nullable=True)

    filename = Column(String, nullable=False)
    object_key = Column(String, nullable=False)
    content_type = Column(String, nullable=True)
    size_bytes = Column(Integer, nullable=False)

    status = Column(String, nullable=False, default="raw", server_default="raw")
    source = Column(String, nullable=True)
    dataset_metadata = Column("metadata", JSONB, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Ontology / knowledge-graph sync tracking
    kg_synced = Column(Boolean, nullable=False, default=False, server_default="false")
    kg_synced_at = Column(DateTime(timezone=True), nullable=True)
    kg_error = Column(Text, nullable=True)
