"""add is_scheduled and scheduled_for to orders

Revision ID: 20260329_order_scheduling
Revises: 20260329_comodato
Create Date: 2026-03-29

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '20260329_order_scheduling'
down_revision: Union[str, None] = '20260329_comodato'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'orders',
        sa.Column(
            'is_scheduled',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
            comment='Se verdadeiro, pedido é agendado para data futura',
        ),
    )
    op.add_column(
        'orders',
        sa.Column(
            'scheduled_for',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='Data/hora agendada para entrega',
        ),
    )
    op.create_index('ix_orders_scheduled_for', 'orders', ['is_scheduled', 'scheduled_for'])


def downgrade() -> None:
    op.drop_index('ix_orders_scheduled_for', table_name='orders')
    op.drop_column('orders', 'scheduled_for')
    op.drop_column('orders', 'is_scheduled')
