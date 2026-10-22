"""add bim dataset link to sensors

Revision ID: e71a88476008
Revises: b8431184fd5c
Create Date: 2026-10-21 14:03:11.892333

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'e71a88476008'
down_revision = 'b8431184fd5c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sensors",
        sa.Column("bim_dataset_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        op.f("ix_sensors_bim_dataset_id"),
        "sensors",
        ["bim_dataset_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_sensors_bim_dataset_id_bim_datasets",
        "sensors",
        "bim_datasets",
        ["bim_dataset_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_sensors_bim_dataset_id_bim_datasets",
        "sensors",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_sensors_bim_dataset_id"), table_name="sensors")
    op.drop_column("sensors", "bim_dataset_id")
