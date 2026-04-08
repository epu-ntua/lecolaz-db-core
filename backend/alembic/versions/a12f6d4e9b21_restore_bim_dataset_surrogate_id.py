"""restore bim_dataset surrogate id

Revision ID: a12f6d4e9b21
Revises: f4b9c7e21a10
Create Date: 2026-04-08 12:30:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a12f6d4e9b21"
down_revision = "f4b9c7e21a10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bim_datasets", sa.Column("id", sa.UUID(), nullable=True))
    op.execute("UPDATE bim_datasets SET id = dataset_id WHERE id IS NULL")
    op.alter_column("bim_datasets", "id", nullable=False)

    op.drop_constraint("bim_storeys_bim_dataset_id_fkey", "bim_storeys", type_="foreignkey")
    op.drop_constraint("bim_spaces_bim_dataset_id_fkey", "bim_spaces", type_="foreignkey")

    op.drop_constraint("pk_bim_datasets", "bim_datasets", type_="primary")
    op.create_primary_key("pk_bim_datasets", "bim_datasets", ["id"])
    op.create_index(
        "ix_bim_datasets_dataset_id",
        "bim_datasets",
        ["dataset_id"],
        unique=True,
    )

    op.create_foreign_key(
        "fk_bim_storeys_bim_dataset_id_bim_datasets",
        "bim_storeys",
        "bim_datasets",
        ["bim_dataset_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_bim_spaces_bim_dataset_id_bim_datasets",
        "bim_spaces",
        "bim_datasets",
        ["bim_dataset_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_bim_spaces_bim_dataset_id_bim_datasets", "bim_spaces", type_="foreignkey")
    op.drop_constraint("fk_bim_storeys_bim_dataset_id_bim_datasets", "bim_storeys", type_="foreignkey")

    op.drop_index("ix_bim_datasets_dataset_id", table_name="bim_datasets")
    op.drop_constraint("pk_bim_datasets", "bim_datasets", type_="primary")
    op.create_primary_key("pk_bim_datasets", "bim_datasets", ["dataset_id"])

    op.create_foreign_key(
        "fk_bim_storeys_bim_dataset_id_bim_datasets",
        "bim_storeys",
        "bim_datasets",
        ["bim_dataset_id"],
        ["dataset_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_bim_spaces_bim_dataset_id_bim_datasets",
        "bim_spaces",
        "bim_datasets",
        ["bim_dataset_id"],
        ["dataset_id"],
        ondelete="CASCADE",
    )

    op.drop_column("bim_datasets", "id")
