"""add bim context to simulations

Revision ID: f8c4d91ab213
Revises: e3a6f7c9b542
Create Date: 2026-04-09 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "f8c4d91ab213"
down_revision: Union[str, Sequence[str], None] = "e3a6f7c9b542"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "simulation_datasets",
        sa.Column("bim_dataset_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        op.f("ix_simulation_datasets_bim_dataset_id"),
        "simulation_datasets",
        ["bim_dataset_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_simulation_datasets_bim_dataset_id_bim_datasets",
        "simulation_datasets",
        "bim_datasets",
        ["bim_dataset_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "simulation_variables",
        sa.Column("bim_space_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        op.f("ix_simulation_variables_bim_space_id"),
        "simulation_variables",
        ["bim_space_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_simulation_variables_bim_space_id_bim_spaces",
        "simulation_variables",
        "bim_spaces",
        ["bim_space_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_simulation_variables_bim_space_id_bim_spaces",
        "simulation_variables",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_simulation_variables_bim_space_id"), table_name="simulation_variables")
    op.drop_column("simulation_variables", "bim_space_id")

    op.drop_constraint(
        "fk_simulation_datasets_bim_dataset_id_bim_datasets",
        "simulation_datasets",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_simulation_datasets_bim_dataset_id"), table_name="simulation_datasets")
    op.drop_column("simulation_datasets", "bim_dataset_id")
