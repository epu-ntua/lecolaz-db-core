"""rename file_metadata to datasets

Revision ID: 7f5d3d1d9f0a
Revises: 162682acb8bc
Create Date: 2026-03-27 14:05:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7f5d3d1d9f0a"
down_revision = "162682acb8bc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.rename_table("file_metadata", "datasets")
    op.execute(
        "ALTER INDEX IF EXISTS ix_file_metadata_created_at "
        "RENAME TO ix_datasets_created_at"
    )
    op.alter_column("datasets", "extra", new_column_name="metadata")
    op.add_column("datasets", sa.Column("type", sa.String(), nullable=True))
    op.add_column("datasets", sa.Column("subtype", sa.String(), nullable=True))
    op.add_column(
        "datasets",
        sa.Column("status", sa.String(), nullable=False, server_default="raw"),
    )
    op.add_column("datasets", sa.Column("source", sa.String(), nullable=True))
    op.add_column(
        "datasets",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.execute(
        """
        UPDATE datasets
        SET type = CASE
            WHEN EXISTS (
                SELECT 1 FROM bim_models WHERE bim_models.file_id = datasets.id
            ) THEN 'bim'
            WHEN EXISTS (
                SELECT 1 FROM simulation_models WHERE simulation_models.file_id = datasets.id
            ) THEN 'simulation'
            ELSE 'generic'
        END
        """
    )
    op.execute(
        """
        UPDATE datasets
        SET subtype = CASE
            WHEN EXISTS (
                SELECT 1 FROM simulation_models WHERE simulation_models.file_id = datasets.id
            ) THEN 'energyplus_eso'
            WHEN lower(filename) LIKE '%.ifczip' THEN 'ifczip'
            WHEN lower(filename) LIKE '%.ifcxml' THEN 'ifcxml'
            WHEN lower(filename) LIKE '%.ifc' THEN 'ifc'
            WHEN strpos(filename, '.') > 0 THEN split_part(lower(filename), '.', array_length(string_to_array(filename, '.'), 1))
            ELSE NULL
        END
        """
    )
    op.execute("UPDATE datasets SET source = 'upload' WHERE source IS NULL")
    op.alter_column("datasets", "type", nullable=False)


def downgrade() -> None:
    op.drop_column("datasets", "updated_at")
    op.drop_column("datasets", "source")
    op.drop_column("datasets", "status")
    op.drop_column("datasets", "subtype")
    op.drop_column("datasets", "type")
    op.alter_column("datasets", "metadata", new_column_name="extra")
    op.execute(
        "ALTER INDEX IF EXISTS ix_datasets_created_at "
        "RENAME TO ix_file_metadata_created_at"
    )
    op.rename_table("datasets", "file_metadata")
