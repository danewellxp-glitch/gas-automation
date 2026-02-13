"""Add idempotency constraints and waha_chat_id for LID resolution.

Revision ID: 20260213_idempotency_lid
Revises: None (standalone - aplicar manualmente)
Create Date: 2026-02-13

Mudancas:
1. customers.waha_chat_id - Armazena chatId original do WAHA (@lid) para envio
2. processed_messages - Tabela de dedup de mensagens com UNIQUE em waha_message_id
3. uq_orders_customer_pending - Partial unique index impedindo 2 pedidos PENDING
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = '20260213_idempotency_lid'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add waha_chat_id to customers
    op.add_column(
        'customers',
        sa.Column(
            'waha_chat_id',
            sa.String(100),
            nullable=True,
            comment='ChatId original do WAHA (@lid) para envio de respostas',
        ),
    )
    op.create_index(
        'ix_customers_waha_chat_id',
        'customers',
        ['waha_chat_id'],
    )

    # 2. Create processed_messages table for message-level dedup
    op.create_table(
        'processed_messages',
        sa.Column(
            'id', UUID(as_uuid=True), primary_key=True,
            server_default=sa.text('gen_random_uuid()'),
        ),
        sa.Column('waha_message_id', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(50), nullable=False),
        sa.Column('flow_state', sa.String(50), nullable=True),
        sa.Column('order_id', UUID(as_uuid=True), nullable=True),
        sa.Column(
            'processed_at', sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
    )
    op.create_unique_constraint(
        'uq_processed_messages_waha_id',
        'processed_messages',
        ['waha_message_id'],
    )
    op.create_index(
        'ix_processed_messages_phone',
        'processed_messages',
        ['phone', 'processed_at'],
    )

    # 3. Partial unique index: only one PENDING order per customer
    # This is the DB-level safety net against duplicate orders.
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_orders_customer_pending
        ON orders (customer_id)
        WHERE status = 'pending'
    """)


def downgrade():
    op.execute("DROP INDEX IF EXISTS uq_orders_customer_pending")
    op.drop_table('processed_messages')
    op.drop_index('ix_customers_waha_chat_id', table_name='customers')
    op.drop_column('customers', 'waha_chat_id')
