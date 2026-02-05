"""Fix botcontext table schema - add missing columns

Revision ID: 20260205_fix_botcontext
Revises:
Create Date: 2026-02-05

A tabela botcontext tinha apenas:
- id, phone_number, context_data (jsonb), last_updated

O modelo BotContext espera:
- id, phone_number, conversation_stage, user_intent, collected_info,
  bot_responses_count, escalation_requested, escalation_reason,
  last_updated, expires_at

Esta migration adiciona as colunas faltantes.
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime, timedelta


# revision identifiers, used by Alembic.
revision = '20260205_fix_botcontext'
down_revision = None  # Standalone migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Verificar quais colunas já existem e adicionar apenas as faltantes
    conn = op.get_bind()

    # Verificar colunas existentes
    result = conn.execute(sa.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'botcontext'
    """))
    existing_columns = {row[0] for row in result}

    # Colunas que o modelo precisa
    columns_to_add = []

    if 'conversation_stage' not in existing_columns:
        columns_to_add.append(
            "ADD COLUMN conversation_stage VARCHAR(50) DEFAULT 'greeting'"
        )

    if 'user_intent' not in existing_columns:
        columns_to_add.append(
            "ADD COLUMN user_intent VARCHAR(100)"
        )

    if 'collected_info' not in existing_columns:
        columns_to_add.append(
            "ADD COLUMN collected_info TEXT"
        )

    if 'bot_responses_count' not in existing_columns:
        columns_to_add.append(
            "ADD COLUMN bot_responses_count INTEGER DEFAULT 0"
        )

    if 'escalation_requested' not in existing_columns:
        columns_to_add.append(
            "ADD COLUMN escalation_requested BOOLEAN DEFAULT FALSE"
        )

    if 'escalation_reason' not in existing_columns:
        columns_to_add.append(
            "ADD COLUMN escalation_reason VARCHAR(255)"
        )

    if 'expires_at' not in existing_columns:
        columns_to_add.append(
            "ADD COLUMN expires_at TIMESTAMP"
        )

    # Executar alterações
    if columns_to_add:
        for col_sql in columns_to_add:
            op.execute(f"ALTER TABLE botcontext {col_sql}")

        # Migrar dados existentes de context_data (jsonb) para collected_info (text)
        # Se context_data existir e collected_info estiver vazio
        if 'context_data' in existing_columns:
            op.execute("""
                UPDATE botcontext
                SET collected_info = context_data::text
                WHERE collected_info IS NULL
                AND context_data IS NOT NULL
            """)

        print(f"✓ Adicionadas {len(columns_to_add)} colunas na tabela botcontext")
    else:
        print("✓ Tabela botcontext já tem todas as colunas necessárias")


def downgrade() -> None:
    # Remover colunas adicionadas (opcional - manter context_data original)
    columns_to_remove = [
        'conversation_stage',
        'user_intent',
        'collected_info',
        'bot_responses_count',
        'escalation_requested',
        'escalation_reason',
        'expires_at'
    ]

    for col in columns_to_remove:
        try:
            op.drop_column('botcontext', col)
        except Exception:
            pass  # Coluna pode não existir
