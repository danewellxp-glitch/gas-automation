"""create_financial_module

Revision ID: 20260324_create_financial_module
Revises: 20260320_add_business_settings
Create Date: 2026-03-24 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "20260324_create_financial_module"
down_revision = "20260320_add_business_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # accounts
    op.create_table(
        "accounts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("type", sa.String(30), nullable=False, server_default="caixa"),
        sa.Column("bank_name", sa.String(100), nullable=True),
        sa.Column("agency", sa.String(20), nullable=True),
        sa.Column("account_number", sa.String(30), nullable=True),
        sa.Column("balance", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column("initial_balance", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_accounts_is_active", "accounts", ["is_active"])

    # cost_centers (needed before transactions)
    op.create_table(
        "cost_centers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("reference_id", UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # receivables
    op.create_table(
        "receivables",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("order_id", UUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("description", sa.String(300), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pendente"),
        sa.Column("payment_method", sa.String(20), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_receivables_status_due", "receivables", ["status", "due_date"])
    op.create_index("ix_receivables_customer", "receivables", ["customer_id"])

    # payables (supplier_id FK added after suppliers table in estoque migration)
    op.create_table(
        "payables",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("supplier_id", UUID(as_uuid=True), nullable=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("description", sa.String(300), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pendente"),
        sa.Column("recurrence", sa.String(20), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_payables_status_due", "payables", ["status", "due_date"])

    # transactions
    op.create_table(
        "transactions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", UUID(as_uuid=True), sa.ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("description", sa.String(300), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("reference_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_paid", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("order_id", UUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("payable_id", UUID(as_uuid=True), sa.ForeignKey("payables.id", ondelete="SET NULL"), nullable=True),
        sa.Column("receivable_id", UUID(as_uuid=True), sa.ForeignKey("receivables.id", ondelete="SET NULL"), nullable=True),
        sa.Column("cost_center_id", UUID(as_uuid=True), sa.ForeignKey("cost_centers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_transactions_account_date", "transactions", ["account_id", "reference_date"])
    op.create_index("ix_transactions_type_paid", "transactions", ["type", "is_paid"])
    op.create_index("ix_transactions_order", "transactions", ["order_id"])
    op.create_index("ix_transactions_type", "transactions", ["type"])

    # cash_flow_entries
    op.create_table(
        "cash_flow_entries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("reference_date", sa.Date(), nullable=False),
        sa.Column("account_id", UUID(as_uuid=True), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("opening_balance", sa.Numeric(14, 2), nullable=False),
        sa.Column("total_income", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column("total_expense", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column("closing_balance", sa.Numeric(14, 2), nullable=False),
        sa.Column("is_projected", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_cash_flow_account_date", "cash_flow_entries", ["account_id", "reference_date"])


def downgrade() -> None:
    op.drop_table("cash_flow_entries")
    op.drop_table("transactions")
    op.drop_table("payables")
    op.drop_table("receivables")
    op.drop_table("cost_centers")
    op.drop_table("accounts")
