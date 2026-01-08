"""add sensor_readings hypertable

Revision ID: 49e2da1ba833
Revises: 68f6d5928c01
Create Date: 2026-01-08 12:50:36.048571

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '49e2da1ba833'
down_revision = '68f6d5928c01'
branch_labels = None
depends_on = None


def upgrade():
    # Create table
    op.execute("""
        CREATE TABLE sensor_readings (
            time        TIMESTAMPTZ       NOT NULL,
            source      TEXT              NOT NULL,
            metric      TEXT              NOT NULL,
            value       DOUBLE PRECISION  NOT NULL,
            unit        TEXT,
            metadata    JSONB
        );
    """)

    # Convert to hypertable
    op.execute("""
        SELECT create_hypertable('sensor_readings', 'time');
    """)

def downgrade():
    op.execute("""
        DROP TABLE sensor_readings;
    """)