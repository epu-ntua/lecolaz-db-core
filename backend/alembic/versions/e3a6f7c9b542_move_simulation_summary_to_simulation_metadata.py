"""move simulation summary to simulation metadata

Revision ID: e3a6f7c9b542
Revises: d91bc3e5a442
Create Date: 2026-04-08 21:30:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "e3a6f7c9b542"
down_revision = "d91bc3e5a442"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "simulation_datasets",
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    op.execute(
        """
        UPDATE simulation_datasets AS sd
        SET metadata = jsonb_strip_nulls(
            jsonb_build_object(
                'variable_count', d.metadata->'variable_count',
                'timestep_count', d.metadata->'timestep_count',
                'skipped_values', d.metadata->'skipped_values'
            )
        )
        FROM datasets AS d
        WHERE sd.dataset_id = d.id
        """
    )

    op.execute(
        """
        UPDATE datasets
        SET metadata = metadata - 'variable_count' - 'timestep_count' - 'skipped_values'
        WHERE metadata IS NOT NULL
          AND jsonb_typeof(metadata) = 'object'
        """
    )

    op.execute("UPDATE simulation_datasets SET extra = NULL")


def downgrade() -> None:
    op.execute(
        """
        UPDATE datasets AS d
        SET metadata = jsonb_strip_nulls(
            COALESCE(d.metadata, '{}'::jsonb) ||
            COALESCE(sd.metadata, '{}'::jsonb)
        )
        FROM simulation_datasets AS sd
        WHERE sd.dataset_id = d.id
          AND sd.metadata IS NOT NULL
        """
    )

    op.drop_column("simulation_datasets", "metadata")
