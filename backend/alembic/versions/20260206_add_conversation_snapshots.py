"""Add conversation_snapshots table for PostgreSQL context backup

Revision ID: 20260206_conv_snapshots
Revises: None (standalone)
Create Date: 2026-02-06

Permite recuperar o estado da conversa quando o Redis TTL expira.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision = '20260206_conv_snapshots'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.tables WHERE table_name = 'conversation_snapshots'"
    ))
    if result.fetchone():
        print("Tabela conversation_snapshots ja existe, pulando")
        return

    op.create_table(
        'conversation_snapshots',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('phone', sa.String(20), unique=True, nullable=False),
        sa.Column('state', sa.String(50), nullable=False, server_default='start'),
        sa.Column('context_json', JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_conversation_snapshots_phone', 'conversation_snapshots', ['phone'])
    print("Tabela conversation_snapshots criada com sucesso")


def downgrade() -> None:
    op.drop_index('ix_conversation_snapshots_phone', table_name='conversation_snapshots')
    op.drop_table('conversation_snapshots')
