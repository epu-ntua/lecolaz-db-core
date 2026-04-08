"""add bim_storeys and bim_spaces

Revision ID: f4b9c7e21a10
Revises: d6e7f8a9b0c1
Create Date: 2026-04-08 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f4b9c7e21a10"
down_revision = "d6e7f8a9b0c1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_bim_datasets_dataset_id")
    op.execute("ALTER TABLE bim_datasets DROP CONSTRAINT IF EXISTS bim_models_pkey")
    op.execute("ALTER TABLE bim_datasets DROP CONSTRAINT IF EXISTS bim_datasets_pkey")
    op.create_primary_key("pk_bim_datasets", "bim_datasets", ["dataset_id"])
    op.drop_column("bim_datasets", "id")

    op.create_table(
        "bim_storeys",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("bim_dataset_id", sa.UUID(), nullable=False),
        sa.Column("global_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("elevation", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["bim_dataset_id"],
            ["bim_datasets.dataset_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_bim_storeys_bim_dataset_id"),
        "bim_storeys",
        ["bim_dataset_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_bim_storeys_created_at"),
        "bim_storeys",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "uq_bim_storeys_dataset_global_id",
        "bim_storeys",
        ["bim_dataset_id", "global_id"],
        unique=True,
    )

    op.create_table(
        "bim_spaces",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("bim_dataset_id", sa.UUID(), nullable=False),
        sa.Column("global_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("raw_name", sa.String(), nullable=True),
        sa.Column("storey_id", sa.UUID(), nullable=True),
        sa.Column("area", sa.Float(), nullable=True),
        sa.Column("volume", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["bim_dataset_id"],
            ["bim_datasets.dataset_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["storey_id"],
            ["bim_storeys.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_bim_spaces_bim_dataset_id"),
        "bim_spaces",
        ["bim_dataset_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_bim_spaces_storey_id"),
        "bim_spaces",
        ["storey_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_bim_spaces_created_at"),
        "bim_spaces",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "uq_bim_spaces_dataset_global_id",
        "bim_spaces",
        ["bim_dataset_id", "global_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_bim_spaces_dataset_global_id", table_name="bim_spaces")
    op.drop_index(op.f("ix_bim_spaces_created_at"), table_name="bim_spaces")
    op.drop_index(op.f("ix_bim_spaces_storey_id"), table_name="bim_spaces")
    op.drop_index(op.f("ix_bim_spaces_bim_dataset_id"), table_name="bim_spaces")
    op.drop_table("bim_spaces")

    op.drop_index("uq_bim_storeys_dataset_global_id", table_name="bim_storeys")
    op.drop_index(op.f("ix_bim_storeys_created_at"), table_name="bim_storeys")
    op.drop_index(op.f("ix_bim_storeys_bim_dataset_id"), table_name="bim_storeys")
    op.drop_table("bim_storeys")

    op.add_column("bim_datasets", sa.Column("id", sa.UUID(), nullable=True))
    op.execute("UPDATE bim_datasets SET id = dataset_id WHERE id IS NULL")
    op.alter_column("bim_datasets", "id", nullable=False)
    op.drop_constraint("pk_bim_datasets", "bim_datasets", type_="primary")
    op.create_primary_key("bim_datasets_pkey", "bim_datasets", ["id"])
    op.create_index(
        "ix_bim_datasets_dataset_id",
        "bim_datasets",
        ["dataset_id"],
        unique=True,
    )
