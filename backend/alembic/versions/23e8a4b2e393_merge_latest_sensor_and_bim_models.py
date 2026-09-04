"""merge latest sensor and BIM models

Revision ID: 23e8a4b2e393
Revises: f8c4d91ab213, 17bbf914f49d
Create Date: 2026-09-02 11:13:03.194506

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '23e8a4b2e393'
down_revision = ('f8c4d91ab213', '17bbf914f49d')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
