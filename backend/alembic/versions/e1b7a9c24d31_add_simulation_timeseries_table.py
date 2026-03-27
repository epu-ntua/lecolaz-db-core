"""add simulation_timeseries table

Revision ID: e1b7a9c24d31
Revises: c4f0f8dd9b6b
Create Date: 2026-03-27 17:20:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e1b7a9c24d31"
down_revision = "c4f0f8dd9b6b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "simulation_timeseries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("simulation_dataset_id", sa.UUID(), nullable=False),
        sa.Column("variable_id", sa.UUID(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["variable_id"],
            ["simulation_variables.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", "timestamp"),
    )
    op.create_index(
        op.f("ix_simulation_timeseries_simulation_dataset_id"),
        "simulation_timeseries",
        ["simulation_dataset_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_simulation_timeseries_variable_id"),
        "simulation_timeseries",
        ["variable_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_simulation_timeseries_timestamp"),
        "simulation_timeseries",
        ["timestamp"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_simulation_timeseries_timestamp"),
        table_name="simulation_timeseries",
    )
    op.drop_index(
        op.f("ix_simulation_timeseries_variable_id"),
        table_name="simulation_timeseries",
    )
    op.drop_index(
        op.f("ix_simulation_timeseries_simulation_dataset_id"),
        table_name="simulation_timeseries",
    )
    op.drop_table("simulation_timeseries")
