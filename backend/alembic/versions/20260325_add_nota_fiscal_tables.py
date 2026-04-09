"""add nota fiscal tables

Revision ID: 20260325_add_nota_fiscal_tables
Revises: 20260325_add_fiado_entry_tables
Create Date: 2026-03-25 00:00:01.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260325_add_nota_fiscal_tables"
down_revision = "20260325_add_fiado_entry_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notas_fiscais",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tipo", sa.String(5), nullable=False, server_default="65"),
        sa.Column("numero", sa.Integer(), nullable=True),
        sa.Column("serie", sa.String(5), nullable=False, server_default="001"),
        sa.Column("chave_acesso", sa.String(50), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="rascunho"),
        sa.Column("pedido_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("emitido_por", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("valor_produtos", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("valor_frete", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("valor_desconto", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("valor_total", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("valor_icms", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("valor_pis", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("valor_cofins", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("xml_enviado", sa.Text(), nullable=True),
        sa.Column("xml_autorizado", sa.Text(), nullable=True),
        sa.Column("pdf_danfe_url", sa.String(500), nullable=True),
        sa.Column("enviada_whatsapp", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("enviada_whatsapp_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo_rejeicao", sa.Text(), nullable=True),
        sa.Column("cancelamento_protocolo", sa.String(100), nullable=True),
        sa.Column("emitida_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_notas_fiscais_pedido_id", "notas_fiscais", ["pedido_id"])
    op.create_index("ix_notas_fiscais_customer_id", "notas_fiscais", ["customer_id"])
    op.create_index("ix_notas_fiscais_status", "notas_fiscais", ["status"])
    op.create_index("ix_notas_fiscais_numero", "notas_fiscais", ["numero"])
    op.create_index("ix_notas_fiscais_chave_acesso", "notas_fiscais", ["chave_acesso"])


def downgrade() -> None:
    op.drop_index("ix_notas_fiscais_chave_acesso", table_name="notas_fiscais")
    op.drop_index("ix_notas_fiscais_numero", table_name="notas_fiscais")
    op.drop_index("ix_notas_fiscais_status", table_name="notas_fiscais")
    op.drop_index("ix_notas_fiscais_customer_id", table_name="notas_fiscais")
    op.drop_index("ix_notas_fiscais_pedido_id", table_name="notas_fiscais")
    op.drop_table("notas_fiscais")
