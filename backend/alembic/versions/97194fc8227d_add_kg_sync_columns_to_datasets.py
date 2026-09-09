"""add kg sync columns to datasets

Revision ID: 97194fc8227d
Revises: 23e8a4b2e393
Create Date: 2026-09-08 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "97194fc8227d"
down_revision = "23e8a4b2e393"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "datasets",
        sa.Column(
            "kg_synced",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "datasets",
        sa.Column("kg_synced_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "datasets",
        sa.Column("kg_error", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("datasets", "kg_error")
    op.drop_column("datasets", "kg_synced_at")
    op.drop_column("datasets", "kg_synced")
