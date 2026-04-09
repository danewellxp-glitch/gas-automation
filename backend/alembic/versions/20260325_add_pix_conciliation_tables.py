"""Add pix_conciliation_runs and pix_conciliation_items tables.

Revision ID: 20260325_add_pix_conciliation_tables
Revises: 20260325_add_categoria_produto_galao
Create Date: 2026-03-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260325_add_pix_conciliation_tables"
down_revision = "20260325_add_categoria_produto_galao"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pix_conciliation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("conciliation_date", sa.Date(), nullable=False),
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_asaas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_local", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_conciliado", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_divergencia", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_apenas_asaas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_apenas_local", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("valor_asaas", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("valor_local", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("status", sa.String(30), nullable=False, server_default="pendente_revisao"),
        sa.Column("aprovado_por", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("aprovado_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_pix_conciliation_runs_date", "pix_conciliation_runs", ["conciliation_date"])

    op.create_table(
        "pix_conciliation_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pix_conciliation_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resultado", sa.String(30), nullable=False),
        sa.Column("asaas_payment_id", sa.String(50), nullable=True),
        sa.Column("asaas_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("asaas_payer_name", sa.String(200), nullable=True),
        sa.Column("asaas_paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("transaction_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("diferenca", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("resolvido", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("resolvido_por", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_pix_conciliation_items_run_id", "pix_conciliation_items", ["run_id"])
    op.create_index("ix_pix_conciliation_items_run_resultado", "pix_conciliation_items", ["run_id", "resultado"])


def downgrade() -> None:
    op.drop_index("ix_pix_conciliation_items_run_resultado", table_name="pix_conciliation_items")
    op.drop_index("ix_pix_conciliation_items_run_id", table_name="pix_conciliation_items")
    op.drop_table("pix_conciliation_items")
    op.drop_index("ix_pix_conciliation_runs_date", table_name="pix_conciliation_runs")
    op.drop_table("pix_conciliation_runs")
