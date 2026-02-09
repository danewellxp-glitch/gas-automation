"""Add bairro column to drivers table

Revision ID: 20260209_driver_bairro
Revises: None (standalone)
Create Date: 2026-02-09

Adiciona campo bairro ao driver para filtrar entregas pendentes por bairro.
"""
from alembic import op
import sqlalchemy as sa

revision = '20260209_driver_bairro'
down_revision = None


def upgrade() -> None:
    op.add_column(
        'drivers',
        sa.Column('bairro', sa.String(100), nullable=True, comment='Bairro de atuação do entregador')
    )
    op.create_index('ix_drivers_bairro', 'drivers', ['bairro'])


def downgrade() -> None:
    op.drop_index('ix_drivers_bairro', table_name='drivers')
    op.drop_column('drivers', 'bairro')
