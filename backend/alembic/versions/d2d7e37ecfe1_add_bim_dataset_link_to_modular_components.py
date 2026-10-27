"""add bim dataset link to modular components

Revision ID: d2d7e37ecfe1
Revises: 6247258f6f50
Create Date: 2026-10-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'd2d7e37ecfe1'
down_revision = '6247258f6f50'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "modular_components",
        sa.Column("bim_dataset_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        op.f("ix_modular_components_bim_dataset_id"),
        "modular_components",
        ["bim_dataset_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_modular_components_bim_dataset_id_bim_datasets",
        "modular_components",
        "bim_datasets",
        ["bim_dataset_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_modular_components_bim_dataset_id_bim_datasets",
        "modular_components",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_modular_components_bim_dataset_id"), table_name="modular_components")
    op.drop_column("modular_components", "bim_dataset_id")
