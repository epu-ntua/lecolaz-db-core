"""add category to bim datasets

Revision ID: 4d2a7f91c6e8
Revises: b8431184fd5c
Create Date: 2026-10-21 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "4d2a7f91c6e8"
down_revision = "b8431184fd5c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bim_datasets",
        sa.Column("category", sa.String(), nullable=True),
    )
    op.create_check_constraint(
        "ck_bim_datasets_category",
        "bim_datasets",
        "category IS NULL OR category IN ('archetype', 'pilot')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_bim_datasets_category",
        "bim_datasets",
        type_="check",
    )
    op.drop_column("bim_datasets", "category")
