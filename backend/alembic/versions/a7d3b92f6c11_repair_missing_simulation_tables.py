"""repair missing simulation tables

Revision ID: a7d3b92f6c11
Revises: f2a1c6b7d4ee
Create Date: 2026-03-27 18:05:00.000000

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "a7d3b92f6c11"
down_revision = "f2a1c6b7d4ee"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS simulation_datasets (
            id UUID PRIMARY KEY,
            dataset_id UUID NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
            filename VARCHAR NOT NULL,
            format VARCHAR NOT NULL,
            extra JSONB NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_simulation_datasets_created_at
        ON simulation_datasets (created_at);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_simulation_datasets_dataset_id
        ON simulation_datasets (dataset_id);
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS simulation_variables (
            id UUID PRIMARY KEY,
            simulation_dataset_id UUID NOT NULL REFERENCES simulation_datasets(id) ON DELETE CASCADE,
            variable_id VARCHAR NOT NULL,
            variable_name VARCHAR NOT NULL,
            unit VARCHAR NULL,
            frequency VARCHAR NULL,
            key VARCHAR NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_simulation_variables_simulation_dataset_id
        ON simulation_variables (simulation_dataset_id);
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS simulation_timeseries (
            id UUID NOT NULL,
            simulation_dataset_id UUID NOT NULL REFERENCES simulation_datasets(id) ON DELETE CASCADE,
            variable_id UUID NOT NULL REFERENCES simulation_variables(id) ON DELETE CASCADE,
            timestamp TIMESTAMPTZ NOT NULL,
            value DOUBLE PRECISION NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (id, timestamp)
        );
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_simulation_timeseries_simulation_dataset_id
        ON simulation_timeseries (simulation_dataset_id);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_simulation_timeseries_variable_id
        ON simulation_timeseries (variable_id);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_simulation_timeseries_timestamp
        ON simulation_timeseries (timestamp);
        """
    )

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
        "Downgrading repaired simulation tables is not supported."
    )
