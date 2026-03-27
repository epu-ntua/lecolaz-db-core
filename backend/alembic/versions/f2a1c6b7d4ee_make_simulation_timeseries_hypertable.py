"""make simulation_timeseries a hypertable

Revision ID: f2a1c6b7d4ee
Revises: e1b7a9c24d31
Create Date: 2026-03-27 17:35:00.000000

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "f2a1c6b7d4ee"
down_revision = "e1b7a9c24d31"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        SELECT create_hypertable(
            'simulation_timeseries',
            'timestamp',
            if_not_exists => TRUE,
            migrate_data => TRUE
        );
        """
    )


def downgrade() -> None:
    raise NotImplementedError(
        "Downgrading simulation_timeseries from hypertable to a regular table is not supported."
    )
