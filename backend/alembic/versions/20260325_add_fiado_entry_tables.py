"""add fiado entry tables

Revision ID: 20260325_add_fiado_entry_tables
Revises: 20260325_add_vasilhame_estoque_tables
Create Date: 2026-03-25 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260325_add_fiado_entry_tables"
down_revision = "20260325_add_vasilhame_estoque_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fiado_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("valor_original", sa.Numeric(10, 2), nullable=False),
        sa.Column("valor_pago", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("vencimento", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="em_aberto"),
        sa.Column("cobrado_whatsapp_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cobrado_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("pago_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_fiado_entries_customer_id", "fiado_entries", ["customer_id"])
    op.create_index("ix_fiado_entries_order_id", "fiado_entries", ["order_id"])
    op.create_index("ix_fiado_entries_status", "fiado_entries", ["status"])

    op.create_table(
        "fiado_pagamentos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("entry_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("fiado_entries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("valor", sa.Numeric(10, 2), nullable=False),
        sa.Column("metodo", sa.String(30), nullable=False),
        sa.Column("asaas_payment_id", sa.String(100), nullable=True),
        sa.Column("pago_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("registrado_por", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_fiado_pagamentos_entry_id", "fiado_pagamentos", ["entry_id"])


def downgrade() -> None:
    op.drop_index("ix_fiado_pagamentos_entry_id", table_name="fiado_pagamentos")
    op.drop_table("fiado_pagamentos")
    op.drop_index("ix_fiado_entries_status", table_name="fiado_entries")
    op.drop_index("ix_fiado_entries_order_id", table_name="fiado_entries")
    op.drop_index("ix_fiado_entries_customer_id", table_name="fiado_entries")
    op.drop_table("fiado_entries")
