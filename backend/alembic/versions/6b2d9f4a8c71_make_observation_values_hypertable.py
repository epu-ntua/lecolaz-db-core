"""make observation_values a hypertable

Revision ID: 6b2d9f4a8c71
Revises: 23e8a4b2e393
Create Date: 2026-09-29

"""

from alembic import op


revision = "6b2d9f4a8c71"
down_revision = "23e8a4b2e393"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Lock referenced tables first to avoid foreign-key deadlocks during conversion.
    op.execute("LOCK TABLE sensors, observation_types IN SHARE ROW EXCLUSIVE MODE")
    # Every unique constraint on a hypertable must include its partitioning column.
    op.drop_constraint("observation_values_pkey", "observation_values", type_="primary")
    op.create_primary_key("observation_values_pkey", "observation_values", ["id", "timestamp"])
    op.execute(
        """
        SELECT create_hypertable(
            'observation_values',
            'timestamp',
            if_not_exists => TRUE,
            migrate_data => TRUE
        );
        """
    )


def downgrade() -> None:
    raise NotImplementedError(
        "Downgrading observation_values from hypertable to a regular table is not supported."
    )
