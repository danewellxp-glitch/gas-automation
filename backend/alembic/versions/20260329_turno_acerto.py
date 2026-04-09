"""add driver_turnos and acerto_itens_entrega tables

Revision ID: 20260329_turno_acerto
Revises: 20260329_expenses_bairros_asaas
Create Date: 2026-03-29

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '20260329_turno_acerto'
down_revision: Union[str, None] = '20260329_expenses_bairros_asaas'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── driver_turnos ───────────────────────────────────────────────────────
    op.create_table(
        'driver_turnos',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('driver_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('drivers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='aberto'),
        sa.Column('iniciado_em', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('finalizado_em', sa.DateTime(timezone=True), nullable=True),
        sa.Column('aprovado_em', sa.DateTime(timezone=True), nullable=True),
        sa.Column('aprovado_por', sa.Integer(), nullable=True),
        sa.Column('total_cobrado', sa.Numeric(14, 2), nullable=True),
        sa.Column('total_esperado', sa.Numeric(14, 2), nullable=True),
        sa.Column('diferenca', sa.Numeric(14, 2), nullable=True),
        sa.Column('observacao', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True,
                  server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_driver_turnos_driver_id', 'driver_turnos', ['driver_id'])
    op.create_index('ix_driver_turnos_status', 'driver_turnos', ['status'])

    # ── acerto_itens_entrega ────────────────────────────────────────────────
    op.create_table(
        'acerto_itens_entrega',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('turno_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('driver_turnos.id', ondelete='CASCADE'), nullable=False),
        sa.Column('delivery_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('deliveries.id', ondelete='SET NULL'), nullable=True),
        sa.Column('order_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('orders.id', ondelete='SET NULL'), nullable=True),
        sa.Column('valor_pedido', sa.Numeric(14, 2), nullable=False),
        sa.Column('valor_cobrado', sa.Numeric(14, 2), nullable=False),
        sa.Column('payment_method', sa.String(20), nullable=True),
        sa.Column('observacao', sa.String(300), nullable=True),
        sa.Column('entregue', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True,
                  server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_acerto_itens_turno_id', 'acerto_itens_entrega', ['turno_id'])


def downgrade() -> None:
    op.drop_index('ix_acerto_itens_turno_id', table_name='acerto_itens_entrega')
    op.drop_table('acerto_itens_entrega')

    op.drop_index('ix_driver_turnos_status', table_name='driver_turnos')
    op.drop_index('ix_driver_turnos_driver_id', table_name='driver_turnos')
    op.drop_table('driver_turnos')
