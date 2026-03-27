"""rename bim and simulation tables

Revision ID: 9c6d8f41b2aa
Revises: 7f5d3d1d9f0a
Create Date: 2026-03-27 16:10:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9c6d8f41b2aa"
down_revision = "7f5d3d1d9f0a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.rename_table("bim_models", "bim_datasets")
    op.alter_column("bim_datasets", "file_id", new_column_name="dataset_id")
    op.execute(
        "ALTER INDEX IF EXISTS ix_bim_models_created_at "
        "RENAME TO ix_bim_datasets_created_at"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_bim_models_file_id "
        "RENAME TO ix_bim_datasets_dataset_id"
    )

    op.rename_table("simulation_models", "simulation_datasets")
    op.alter_column("simulation_datasets", "file_id", new_column_name="dataset_id")
    op.drop_column("simulation_datasets", "schema")
    op.drop_column("simulation_datasets", "status")
    op.execute(
        "ALTER INDEX IF EXISTS ix_simulation_models_created_at "
        "RENAME TO ix_simulation_datasets_created_at"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_simulation_models_file_id "
        "RENAME TO ix_simulation_datasets_dataset_id"
    )


def downgrade() -> None:
    op.add_column("simulation_datasets", sa.Column("schema", sa.String(), nullable=True))
    op.add_column(
        "simulation_datasets",
        sa.Column("status", sa.String(), server_default="uploaded", nullable=False),
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_simulation_datasets_dataset_id "
        "RENAME TO ix_simulation_models_file_id"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_simulation_datasets_created_at "
        "RENAME TO ix_simulation_models_created_at"
    )
    op.create_index(
        op.f("ix_simulation_models_status"),
        "simulation_datasets",
        ["status"],
        unique=False,
    )
    op.alter_column("simulation_datasets", "dataset_id", new_column_name="file_id")
    op.rename_table("simulation_datasets", "simulation_models")

    op.execute(
        "ALTER INDEX IF EXISTS ix_bim_datasets_dataset_id "
        "RENAME TO ix_bim_models_file_id"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_bim_datasets_created_at "
        "RENAME TO ix_bim_models_created_at"
    )
    op.alter_column("bim_datasets", "dataset_id", new_column_name="file_id")
    op.rename_table("bim_datasets", "bim_models")
