"""add unique constraint to simulation_datasets.dataset_id

Revision ID: c1a8e4d9b6f2
Revises: b3e9f6a1c2d4
Create Date: 2026-03-28
"""

from alembic import op


revision = "c1a8e4d9b6f2"
down_revision = "b3e9f6a1c2d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_simulation_datasets_dataset_id",
        "simulation_datasets",
        ["dataset_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_simulation_datasets_dataset_id",
        "simulation_datasets",
        type_="unique",
    )
