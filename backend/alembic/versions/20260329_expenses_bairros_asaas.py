"""add expenses table, driver bairros_atendidos, receivable asaas_payment_id

Revision ID: 20260329_expenses_bairros_asaas
Revises: 8da4be72398d
Create Date: 2026-03-29

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260329_expenses_bairros_asaas'
down_revision: Union[str, None] = '8da4be72398d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── expenses table ─────────────────────────────────────────────────────
    op.create_table(
        'expenses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('tipo', sa.String(50), nullable=False),
        sa.Column('grupo', sa.String(30), nullable=False),
        sa.Column('descricao', sa.String(300), nullable=False),
        sa.Column('valor', sa.Numeric(14, 2), nullable=False),
        sa.Column('valor_parcela', sa.Numeric(14, 2), nullable=False),
        sa.Column('data_lancamento', sa.Date(), nullable=False),
        sa.Column('data_vencimento', sa.Date(), nullable=False),
        sa.Column('periodicidade', sa.String(20), nullable=False, server_default='unico'),
        sa.Column('parcelas_total', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('parcela_atual', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('grupo_parcela_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('pago', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('data_pagamento', sa.Date(), nullable=True),
        sa.Column('veiculo_placa', sa.String(10), nullable=True),
        sa.Column('funcionario_id', sa.Integer(), nullable=True),
        sa.Column('fornecedor', sa.String(200), nullable=True),
        sa.Column('numero_nota', sa.String(100), nullable=True),
        sa.Column('observacao', sa.Text(), nullable=True),
        sa.Column('conta_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True,
                  server_default=sa.text('now()')),
    )
    op.create_index('ix_expenses_tipo', 'expenses', ['tipo'])
    op.create_index('ix_expenses_grupo', 'expenses', ['grupo'])
    op.create_index('ix_expenses_pago', 'expenses', ['pago'])
    op.create_index('ix_expenses_grupo_parcela_id', 'expenses', ['grupo_parcela_id'])
    op.create_index('ix_expenses_veiculo_placa', 'expenses', ['veiculo_placa'])
    op.create_index('ix_expenses_funcionario_id', 'expenses', ['funcionario_id'])
    op.create_index('ix_expenses_tipo_vencimento', 'expenses', ['tipo', 'data_vencimento'])
    op.create_index('ix_expenses_pago_vencimento', 'expenses', ['pago', 'data_vencimento'])
    op.create_index('ix_expenses_grupo_vencimento', 'expenses', ['grupo', 'data_vencimento'])

    # ── drivers.bairros_atendidos ───────────────────────────────────────────
    op.add_column(
        'drivers',
        sa.Column(
            'bairros_atendidos',
            postgresql.ARRAY(sa.String()),
            nullable=True,
            comment='Lista de bairros que o entregador atende',
        ),
    )

    # ── receivables.asaas_payment_id ───────────────────────────────────────
    op.add_column(
        'receivables',
        sa.Column(
            'asaas_payment_id',
            sa.String(100),
            nullable=True,
            comment='ID da cobrança no Asaas',
        ),
    )
    op.create_index('ix_receivables_asaas_payment_id', 'receivables', ['asaas_payment_id'])


def downgrade() -> None:
    op.drop_index('ix_receivables_asaas_payment_id', table_name='receivables')
    op.drop_column('receivables', 'asaas_payment_id')

    op.drop_column('drivers', 'bairros_atendidos')

    op.drop_index('ix_expenses_grupo_vencimento', table_name='expenses')
    op.drop_index('ix_expenses_pago_vencimento', table_name='expenses')
    op.drop_index('ix_expenses_tipo_vencimento', table_name='expenses')
    op.drop_index('ix_expenses_funcionario_id', table_name='expenses')
    op.drop_index('ix_expenses_veiculo_placa', table_name='expenses')
    op.drop_index('ix_expenses_grupo_parcela_id', table_name='expenses')
    op.drop_index('ix_expenses_pago', table_name='expenses')
    op.drop_index('ix_expenses_grupo', table_name='expenses')
    op.drop_index('ix_expenses_tipo', table_name='expenses')
    op.drop_table('expenses')
