"""merge observation_values hypertable and kg sync

Revision ID: b8431184fd5c
Revises: 6b2d9f4a8c71, 97194fc8227d
Create Date: 2026-10-01 09:19:11.852458

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b8431184fd5c'
down_revision = ('6b2d9f4a8c71', '97194fc8227d')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
