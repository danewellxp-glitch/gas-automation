"""Add tipo_operacao to orders

Revision ID: 20260123_tipo_op
Revises: 20260121_time_logs
Create Date: 2026-01-23

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '20260123_tipo_op'
down_revision = '20260121_time_logs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'orders',
        sa.Column(
            'tipo_operacao',
            sa.String(20),
            nullable=False,
            server_default='troca',
            comment='Tipo: troca (tem vasilhame), venda (novo), retira (busca)'
        )
    )


def downgrade() -> None:
    op.drop_column('orders', 'tipo_operacao')
