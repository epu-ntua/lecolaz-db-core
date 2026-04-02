"""optimize simulation_timeseries indexes

Revision ID: d6e7f8a9b0c1
Revises: c1a8e4d9b6f2
Create Date: 2026-04-02 12:00:00.000000

"""

from alembic import op


revision = "d6e7f8a9b0c1"
down_revision = "c1a8e4d9b6f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "DROP INDEX IF EXISTS ix_simulation_timeseries_simulation_dataset_id"
    )
    op.execute(
        "DROP INDEX IF EXISTS ix_simulation_timeseries_variable_id"
    )
    op.execute(
        "DROP INDEX IF EXISTS ix_simulation_timeseries_timestamp"
    )

    op.create_index(
        "ix_simulation_timeseries_dataset_timestamp",
        "simulation_timeseries",
        ["simulation_dataset_id", "timestamp"],
        unique=False,
    )
    op.create_index(
        "ix_simulation_timeseries_dataset_variable_timestamp",
        "simulation_timeseries",
        ["simulation_dataset_id", "variable_id", "timestamp"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_simulation_timeseries_dataset_variable_timestamp",
        table_name="simulation_timeseries",
    )
    op.drop_index(
        "ix_simulation_timeseries_dataset_timestamp",
        table_name="simulation_timeseries",
    )

    op.create_index(
        "ix_simulation_timeseries_timestamp",
        "simulation_timeseries",
        ["timestamp"],
        unique=False,
    )
    op.create_index(
        "ix_simulation_timeseries_variable_id",
        "simulation_timeseries",
        ["variable_id"],
        unique=False,
    )
    op.create_index(
        "ix_simulation_timeseries_simulation_dataset_id",
        "simulation_timeseries",
        ["simulation_dataset_id"],
        unique=False,
    )
