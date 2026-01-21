"""Fix delivery_address column type from TEXT to JSONB

Revision ID: fix_delivery_address
Revises: 
Create Date: 2026-01-21 08:20:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = 'fix_delivery_address'
down_revision = None  # Ajustar se houver revisões anteriores
branch_labels = None
depends_on = None


def upgrade():
    # Converter coluna TEXT para JSONB usando CAST
    op.execute("""
        ALTER TABLE orders 
        ALTER COLUMN delivery_address 
        TYPE JSONB 
        USING delivery_address::jsonb
    """)


def downgrade():
    # Reverter JSONB para TEXT
    op.execute("""
        ALTER TABLE orders 
        ALTER COLUMN delivery_address 
        TYPE TEXT 
        USING delivery_address::text
    """)
