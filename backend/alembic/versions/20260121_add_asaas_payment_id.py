"""add asaas_payment_id to orders table

Revision ID: 20260121_asaas_payment
Revises:
Create Date: 2026-01-21

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '20260121_asaas_payment'
down_revision = None
depends_on = None


def upgrade():
    # Add asaas_payment_id column to orders table
    op.add_column(
        'orders',
        sa.Column(
            'asaas_payment_id',
            sa.String(100),
            nullable=True,
            comment='ID da cobrança no Asaas (PIX/Boleto)'
        )
    )

    # Create index for faster lookups
    op.create_index(
        'ix_orders_asaas_payment_id',
        'orders',
        ['asaas_payment_id']
    )


def downgrade():
    op.drop_index('ix_orders_asaas_payment_id', 'orders')
    op.drop_column('orders', 'asaas_payment_id')
