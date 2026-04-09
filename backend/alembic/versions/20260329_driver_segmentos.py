"""add segmentos_atendidos to drivers

Revision ID: 20260329_driver_segmentos
Revises: 20260329_order_scheduling
Create Date: 2026-03-29

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '20260329_driver_segmentos'
down_revision: Union[str, None] = '20260329_order_scheduling'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'drivers',
        sa.Column(
            'segmentos_atendidos',
            postgresql.ARRAY(sa.String()),
            nullable=True,
            comment='Segmentos de clientes: residencial, comercial, industrial, condominio',
        ),
    )


def downgrade() -> None:
    op.drop_column('drivers', 'segmentos_atendidos')
