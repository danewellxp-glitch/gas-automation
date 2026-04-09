"""customer_financial_order_profit

Revision ID: 20260325_customer_financial_order_profit
Revises: 20260324_seed_financeiro_estoque_users
Create Date: 2026-03-25 00:00:00.000000

Adiciona:
  - customer_financial  (fiado / crédito por cliente)
  - order_profits       (lucratividade por pedido)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "20260325_customer_financial_order_profit"
down_revision = "20260324_seed_financeiro_estoque_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── customer_financial ──────────────────────────────────
    op.create_table(
        "customer_financial",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("customer_id", UUID(as_uuid=True),
                  sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("balance",         sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("credit_limit",    sa.Numeric(14, 2), nullable=False, server_default="200"),
        sa.Column("total_purchases", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("total_orders",    sa.Integer(),      nullable=False, server_default="0"),
        sa.Column("last_purchase_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes",           sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("customer_id", name="uq_customer_financial_customer"),
    )
    op.create_index("ix_customer_financial_customer_id", "customer_financial", ["customer_id"])
    op.create_index("ix_customer_financial_balance",     "customer_financial", ["balance"])

    # ── order_profits ───────────────────────────────────────
    op.create_table(
        "order_profits",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("order_id", UUID(as_uuid=True),
                  sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("revenue",          sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("product_cost",     sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("delivery_cost",    sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("estimated_cost",   sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("profit",           sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("margin_percentage",sa.Numeric(6, 2),  nullable=False, server_default="0"),
        sa.Column("bairro",           sa.String(100), nullable=True),
        sa.Column("notes",            sa.Text(), nullable=True),
        sa.Column("calculated_at",    sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("order_id", name="uq_order_profit_order"),
    )
    op.create_index("ix_order_profits_order_id", "order_profits", ["order_id"])
    op.create_index("ix_order_profits_bairro",   "order_profits", ["bairro"])
    op.create_index("ix_order_profits_profit",   "order_profits", ["profit"])


def downgrade() -> None:
    op.drop_table("order_profits")
    op.drop_table("customer_financial")
