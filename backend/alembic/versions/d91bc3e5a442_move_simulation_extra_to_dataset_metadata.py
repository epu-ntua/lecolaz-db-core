"""move simulation extra to dataset metadata

Revision ID: d91bc3e5a442
Revises: c7e8d2f41ab3
Create Date: 2026-04-08 21:10:00.000000

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "d91bc3e5a442"
down_revision = "c7e8d2f41ab3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE datasets AS d
        SET metadata = jsonb_strip_nulls(
            COALESCE(d.metadata, '{}'::jsonb) ||
            COALESCE(sd.extra, '{}'::jsonb)
        )
        FROM simulation_datasets AS sd
        WHERE sd.dataset_id = d.id
          AND sd.extra IS NOT NULL
        """
    )

    op.execute("UPDATE simulation_datasets SET extra = NULL WHERE extra IS NOT NULL")


def downgrade() -> None:
    op.execute(
        """
        UPDATE simulation_datasets AS sd
        SET extra = jsonb_strip_nulls(
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
