import uuid

from sqlalchemy import CheckConstraint, Column, DateTime, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base


class ModularComponent(Base):
    __tablename__ = "modular_components"
    __table_args__ = (
        CheckConstraint(
            "component_class IN ('FacadeElement', 'InteriorWall', 'FloorCovering')",
            name="ck_modular_components_component_class",
        ),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name = Column(String, nullable=False)
    component_class = Column(String, nullable=False)

    # Draft Digital Product Passport; expected to move to its own table later.
    dpp = Column(JSONB, nullable=True)

    # MinIO object keys
    photo_object_key = Column(String, nullable=True)
    qr_object_key = Column(String, nullable=True)
    ifc_object_key = Column(String, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
