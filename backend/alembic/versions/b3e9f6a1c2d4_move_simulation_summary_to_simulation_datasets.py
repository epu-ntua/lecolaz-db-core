"""move simulation summary to simulation_datasets

Revision ID: b3e9f6a1c2d4
Revises: a7d3b92f6c11
Create Date: 2026-03-28
"""

from alembic import op


revision = "b3e9f6a1c2d4"
down_revision = "a7d3b92f6c11"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE simulation_datasets AS sd
        SET extra = COALESCE(sd.extra, '{}'::jsonb) || jsonb_strip_nulls(
            jsonb_build_object(
                'variable_count', CASE
                    WHEN d.metadata ? 'variable_count' THEN (d.metadata->>'variable_count')::integer
                    ELSE NULL
                END,
                'timestep_count', CASE
                    WHEN d.metadata ? 'timestep_count' THEN (d.metadata->>'timestep_count')::integer
                    ELSE NULL
                END,
                'skipped_values', CASE
                    WHEN d.metadata ? 'skipped_values' THEN (d.metadata->>'skipped_values')::integer
                    ELSE NULL
                END,
                'processed_at', d.metadata->>'processed_at'
            )
        )
        FROM datasets AS d
        WHERE sd.dataset_id = d.id
          AND jsonb_typeof(d.metadata) = 'object'
          AND (
            d.metadata ? 'variable_count'
            OR d.metadata ? 'timestep_count'
            OR d.metadata ? 'skipped_values'
            OR d.metadata ? 'processed_at'
          )
        """
    )

    op.execute(
        """
        UPDATE datasets
        SET metadata =
            CASE
                WHEN metadata IS NULL THEN NULL
                WHEN jsonb_typeof(metadata) <> 'object' THEN metadata
                ELSE metadata
                    - 'variable_count'
                    - 'timestep_count'
                    - 'skipped_values'
                    - 'processed_at'
            END
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE datasets AS d
        SET metadata = COALESCE(d.metadata, '{}'::jsonb) || jsonb_strip_nulls(
            jsonb_build_object(
                'variable_count', CASE
                    WHEN sd.extra ? 'variable_count' THEN (sd.extra->>'variable_count')::integer
                    ELSE NULL
                END,
                'timestep_count', CASE
                    WHEN sd.extra ? 'timestep_count' THEN (sd.extra->>'timestep_count')::integer
                    ELSE NULL
                END,
                'skipped_values', CASE
                    WHEN sd.extra ? 'skipped_values' THEN (sd.extra->>'skipped_values')::integer
                    ELSE NULL
                END,
                'processed_at', sd.extra->>'processed_at'
            )
        )
        FROM simulation_datasets AS sd
        WHERE sd.dataset_id = d.id
          AND (d.metadata IS NULL OR jsonb_typeof(d.metadata) = 'object')
          AND (
            sd.extra ? 'variable_count'
            OR sd.extra ? 'timestep_count'
            OR sd.extra ? 'skipped_values'
            OR sd.extra ? 'processed_at'
          )
        """
    )

    op.execute(
        """
        UPDATE simulation_datasets
        SET extra =
            CASE
                WHEN extra IS NULL THEN NULL
                WHEN jsonb_typeof(extra) <> 'object' THEN extra
                ELSE extra
                    - 'variable_count'
                    - 'timestep_count'
                    - 'skipped_values'
                    - 'processed_at'
            END
        """
    )
