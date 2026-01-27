"""add_auth_tables

Revision ID: e68a4ae2e2ea
Revises: 001
Create Date: 2026-01-18 21:30:00.052573

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e68a4ae2e2ea'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tabela: users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('username', sa.String(50), unique=True, nullable=False, index=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('full_name', sa.String(100), nullable=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('role', sa.String(20), server_default='user', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Tabela: conversations
    op.create_table(
        'conversations',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('phone_number', sa.String(20), nullable=False, index=True),
        sa.Column('profile_name', sa.String(100), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_message_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('status', sa.String(20), server_default='active', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Tabela: messages
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('conversation_id', sa.Integer(), sa.ForeignKey('conversations.id'), nullable=False),
        sa.Column('direction', sa.String(10), nullable=False),  # 'inbound' or 'outbound'
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('message_type', sa.String(20), server_default='text', nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('status', sa.String(20), server_default='sent', nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Tabela: audit_logs
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('resource_id', sa.String(100), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Tabela: bot_interactions
    op.create_table(
        'bot_interactions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('conversation_id', sa.Integer(), sa.ForeignKey('conversations.id'), nullable=False),
        sa.Column('bot_type', sa.String(50), nullable=False),
        sa.Column('user_message', sa.Text(), nullable=False),
        sa.Column('bot_response', sa.Text(), nullable=False),
        sa.Column('confidence_score', sa.Numeric(3, 2), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('escalated', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('escalation_reason', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Tabela: bot_context
    op.create_table(
        'bot_context',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('phone_number', sa.String(20), unique=True, nullable=False, index=True),
        sa.Column('conversation_stage', sa.String(50), server_default='greeting', nullable=False),
        sa.Column('user_intent', sa.String(100), nullable=True),
        sa.Column('collected_info', sa.Text(), server_default='{}', nullable=False),
        sa.Column('bot_responses_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('escalation_requested', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('escalation_reason', sa.Text(), nullable=True),
        sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('bot_context')
    op.drop_table('bot_interactions')
    op.drop_table('audit_logs')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('users')
