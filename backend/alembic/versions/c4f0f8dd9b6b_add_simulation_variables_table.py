"""add simulation_variables table

Revision ID: c4f0f8dd9b6b
Revises: 9c6d8f41b2aa
Create Date: 2026-03-27 17:05:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c4f0f8dd9b6b"
down_revision = "9c6d8f41b2aa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "simulation_variables",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("simulation_dataset_id", sa.UUID(), nullable=False),
        sa.Column("variable_id", sa.String(), nullable=False),
        sa.Column("variable_name", sa.String(), nullable=False),
        sa.Column("unit", sa.String(), nullable=True),
        sa.Column("frequency", sa.String(), nullable=True),
        sa.Column("key", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["simulation_dataset_id"],
            ["simulation_datasets.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_simulation_variables_simulation_dataset_id"),
        "simulation_variables",
        ["simulation_dataset_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_simulation_variables_simulation_dataset_id"),
        table_name="simulation_variables",
    )
    op.drop_table("simulation_variables")
