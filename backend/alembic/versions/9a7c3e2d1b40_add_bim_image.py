"""Add optional building image reference.

Revision ID: 9a7c3e2d1b40
Revises: c8cc320edf1d
"""
from alembic import op
import sqlalchemy as sa

revision = "9a7c3e2d1b40"
down_revision = "c8cc320edf1d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bim_datasets", sa.Column("image_object_key", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("bim_datasets", "image_object_key")
