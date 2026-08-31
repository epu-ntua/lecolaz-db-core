"""move processed_at to dataset metadata

Revision ID: c7e8d2f41ab3
Revises: b6d4a1c93e20
Create Date: 2026-04-08 20:55:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c7e8d2f41ab3"
down_revision = "b6d4a1c93e20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE datasets AS d
        SET metadata = jsonb_strip_nulls(
            COALESCE(d.metadata, '{}'::jsonb) ||
            jsonb_build_object('processed_at', bd.processed_at)
        )
        FROM bim_datasets AS bd
        WHERE bd.dataset_id = d.id
          AND bd.processed_at IS NOT NULL
        """
    )

    op.execute(
        """
        UPDATE datasets AS d
        SET metadata = jsonb_strip_nulls(
            COALESCE(d.metadata, '{}'::jsonb) ||
            jsonb_build_object('processed_at', sd.processed_at)
        )
        FROM simulation_datasets AS sd
        WHERE sd.dataset_id = d.id
          AND sd.processed_at IS NOT NULL
        """
    )

    op.drop_column("simulation_datasets", "processed_at")
    op.drop_column("bim_datasets", "processed_at")


def downgrade() -> None:
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
        UPDATE bim_datasets AS bd
        SET processed_at = NULLIF(d.metadata->>'processed_at', '')::timestamptz
        FROM datasets AS d
        WHERE bd.dataset_id = d.id
          AND d.metadata ? 'processed_at'
        """
    )
    op.execute(
        """
        UPDATE simulation_datasets AS sd
        SET processed_at = NULLIF(d.metadata->>'processed_at', '')::timestamptz
        FROM datasets AS d
        WHERE sd.dataset_id = d.id
          AND d.metadata ? 'processed_at'
        """
    )
