"""add modular component link to sensors

Revision ID: c8cc320edf1d
Revises: d2d7e37ecfe1
Create Date: 2026-10-27 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'c8cc320edf1d'
down_revision = 'd2d7e37ecfe1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sensors",
        sa.Column("modular_component_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        op.f("ix_sensors_modular_component_id"),
        "sensors",
        ["modular_component_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_sensors_modular_component_id_modular_components",
        "sensors",
        "modular_components",
        ["modular_component_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "ck_sensors_single_link",
        "sensors",
        "bim_dataset_id IS NULL OR modular_component_id IS NULL",
    )


def downgrade() -> None:
    op.drop_constraint("ck_sensors_single_link", "sensors", type_="check")
    op.drop_constraint(
        "fk_sensors_modular_component_id_modular_components",
        "sensors",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_sensors_modular_component_id"), table_name="sensors")
    op.drop_column("sensors", "modular_component_id")
