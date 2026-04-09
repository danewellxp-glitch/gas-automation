"""add comodatos table

Revision ID: 20260329_comodato
Revises: 20260329_turno_acerto
Create Date: 2026-03-29

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '20260329_comodato'
down_revision: Union[str, None] = '20260329_turno_acerto'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'comodatos',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('customers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('equipamento', sa.String(200), nullable=False),
        sa.Column('numero_serie', sa.String(100), nullable=True),
        sa.Column('quantidade', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('valor_caucao', sa.Numeric(14, 2), nullable=True),
        sa.Column('data_emprestimo', sa.Date(), nullable=False),
        sa.Column('data_prevista_devolucao', sa.Date(), nullable=True),
        sa.Column('data_devolucao', sa.Date(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='ativo'),
        sa.Column('observacao', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True,
                  server_default=sa.text('now()')),
    )
    op.create_index('ix_comodatos_customer_id', 'comodatos', ['customer_id'])
    op.create_index('ix_comodatos_status', 'comodatos', ['status'])


def downgrade() -> None:
    op.drop_index('ix_comodatos_status', table_name='comodatos')
    op.drop_index('ix_comodatos_customer_id', table_name='comodatos')
    op.drop_table('comodatos')
