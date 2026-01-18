"""Initial schema - all tables

Revision ID: 001
Revises:
Create Date: 2024-01-01

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tabela: customers
    op.create_table(
        'customers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('firebird_id', sa.Integer(), unique=True, nullable=True),
        sa.Column('asaas_customer_id', sa.String(50), unique=True, nullable=True),
        sa.Column('phone', sa.String(20), unique=True, nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('cpf_cnpj', sa.String(20), nullable=True),
        sa.Column('address', postgresql.JSONB(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Tabela: products
    op.create_table(
        'products',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('code', sa.String(10), unique=True, nullable=False, index=True),
        sa.Column('firebird_code', sa.String(50), unique=True, nullable=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('weight_kg', sa.Numeric(5, 2), nullable=False),
        sa.Column('price', sa.Numeric(10, 2), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Tabela: orders
    op.create_table(
        'orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('customers.id', ondelete='RESTRICT'), nullable=False, index=True),
        sa.Column('order_number', sa.Integer(), autoincrement=True, unique=True, nullable=False),
        sa.Column('status', sa.String(50), server_default='pending', nullable=False, index=True),
        sa.Column('payment_method', sa.String(50), nullable=True),
        sa.Column('total_amount', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('delivery_address', postgresql.JSONB(), nullable=True),
        sa.Column('delivery_bairro', sa.String(100), nullable=True, index=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('dispatched_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancellation_reason', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Tabela: order_items
    op.create_table(
        'order_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('product_code', sa.String(10), nullable=False),
        sa.Column('product_name', sa.String(100), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('unit_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('subtotal', sa.Numeric(10, 2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Tabela: payments
    op.create_table(
        'payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('asaas_payment_id', sa.String(100), unique=True, nullable=True, index=True),
        sa.Column('asaas_customer_id', sa.String(100), nullable=True),
        sa.Column('method', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), server_default='pending', nullable=False, index=True),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('net_amount', sa.Numeric(10, 2), nullable=True),
        sa.Column('fee', sa.Numeric(10, 2), nullable=True),
        sa.Column('pix_qr_code', sa.Text(), nullable=True),
        sa.Column('pix_copy_paste', sa.Text(), nullable=True),
        sa.Column('pix_expiration', sa.DateTime(timezone=True), nullable=True),
        sa.Column('boleto_url', sa.String(500), nullable=True),
        sa.Column('boleto_barcode', sa.String(100), nullable=True),
        sa.Column('boleto_digitable_line', sa.String(100), nullable=True),
        sa.Column('card_last_digits', sa.String(4), nullable=True),
        sa.Column('card_brand', sa.String(20), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('gateway_response', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Tabela: deliveries
    op.create_table(
        'deliveries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orders.id', ondelete='CASCADE'), unique=True, nullable=False, index=True),
        sa.Column('driver_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('driver_name', sa.String(100), nullable=True),
        sa.Column('driver_phone', sa.String(20), nullable=True),
        sa.Column('status', sa.String(50), server_default='pending', nullable=False, index=True),
        sa.Column('bairro', sa.String(100), nullable=True, index=True),
        sa.Column('estimated_minutes', sa.Integer(), nullable=True, server_default='40'),
        sa.Column('actual_delivery_minutes', sa.Integer(), nullable=True),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('picked_up_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('in_transit_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('arrived_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('failure_reason', sa.String(500), nullable=True),
        sa.Column('last_location', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Tabela: event_logs
    op.create_table(
        'event_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('event_type', sa.String(100), nullable=False, index=True),
        sa.Column('entity_type', sa.String(50), nullable=False, index=True),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('actor_type', sa.String(50), nullable=False, server_default='system'),
        sa.Column('actor_id', sa.String(100), nullable=True),
        sa.Column('payload', postgresql.JSONB(), nullable=True),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True),
    )

    # Inserir produtos padrão
    op.execute("""
        INSERT INTO products (id, code, name, description, weight_kg, price, is_active, created_at, updated_at)
        VALUES
            (gen_random_uuid(), 'P13', 'Botijão P13 - 13kg', 'Botijão residencial padrão de 13kg. Ideal para uso doméstico.', 13.00, 110.00, true, NOW(), NOW()),
            (gen_random_uuid(), 'P20', 'Botijão P20 - 20kg', 'Botijão de 20kg. Indicado para residências com maior consumo ou pequenos comércios.', 20.00, 150.00, true, NOW(), NOW()),
            (gen_random_uuid(), 'P45', 'Botijão P45 - 45kg', 'Botijão comercial/industrial de 45kg. Para estabelecimentos com alto consumo.', 45.00, 280.00, true, NOW(), NOW())
        ON CONFLICT DO NOTHING;
    """)


def downgrade() -> None:
    op.drop_table('event_logs')
    op.drop_table('deliveries')
    op.drop_table('payments')
    op.drop_table('order_items')
    op.drop_table('orders')
    op.drop_table('products')
    op.drop_table('customers')
