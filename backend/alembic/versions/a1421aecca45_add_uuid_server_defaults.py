"""add UUID server defaults

Revision ID: a1421aecca45
Revises: 329c9fc29af3
Create Date: 2026-08-27 11:03:10.464691

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1421aecca45'
down_revision = '329c9fc29af3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table_name in (
        "observation_types",
        "sensors",
        "observation_values",
    ):
        op.alter_column(
            table_name,
            "id",
            existing_type=sa.UUID(),
            existing_nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        )


def downgrade() -> None:
    for table_name in (
        "observation_types",
        "sensors",
        "observation_values",
    ):
        op.alter_column(
            table_name,
            "id",
            existing_type=sa.UUID(),
            existing_nullable=False,
            server_default=None,
        )