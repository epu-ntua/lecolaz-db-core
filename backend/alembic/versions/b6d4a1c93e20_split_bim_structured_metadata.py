"""split bim structured metadata

Revision ID: b6d4a1c93e20
Revises: a12f6d4e9b21
Create Date: 2026-04-08 20:35:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "b6d4a1c93e20"
down_revision = "a12f6d4e9b21"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bim_datasets",
        sa.Column("stats", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "bim_datasets",
        sa.Column("units", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "bim_datasets",
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "simulation_datasets",
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.execute(
        """
        UPDATE bim_datasets
        SET
            stats = extra->'stats',
            units = extra->'units',
            processed_at = CASE
                WHEN EXISTS (
                    SELECT 1
                    FROM datasets d
                    WHERE d.id = bim_datasets.dataset_id
                      AND d.status = 'processed'
                ) THEN created_at
                ELSE NULL
            END,
            extra = NULL
        """
    )

    op.execute(
        """
        UPDATE simulation_datasets
        SET processed_at = NULLIF(extra->>'processed_at', '')::timestamptz
        WHERE extra ? 'processed_at'
        """
    )

    op.execute(
        """
        UPDATE simulation_datasets
        SET extra = extra - 'processed_at'
        WHERE extra ? 'processed_at'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE bim_datasets
        SET extra = jsonb_strip_nulls(
            jsonb_build_object(
                'stats', stats,
                'units', units
            )
        )
        """
    )

    op.execute(
        """
        UPDATE simulation_datasets
        SET extra = COALESCE(extra, '{}'::jsonb) || jsonb_build_object('processed_at', processed_at)
        WHERE processed_at IS NOT NULL
        """
    )

    op.drop_column("simulation_datasets", "processed_at")
    op.drop_column("bim_datasets", "processed_at")
    op.drop_column("bim_datasets", "units")
    op.drop_column("bim_datasets", "stats")
