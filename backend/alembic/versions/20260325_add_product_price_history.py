"""
Migration: add_product_price_history
Cria a tabela product_price_history para rastrear alterações de preço de produtos.

Destino: alembic/versions/20260325_add_product_price_history.py
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "20260325_add_product_price_history"
down_revision = "20260325_customer_financial_order_profit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_price_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("product_code", sa.String(50), nullable=False),
        sa.Column("product_name", sa.String(200), nullable=False),
        sa.Column("old_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("new_price", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("changed_by", sa.String(200), nullable=True),
    )

    op.create_index(
        "ix_product_price_history_product_code",
        "product_price_history",
        ["product_code"],
    )
    op.create_index(
        "ix_product_price_history_changed_at",
        "product_price_history",
        ["changed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_product_price_history_changed_at", table_name="product_price_history")
    op.drop_index("ix_product_price_history_product_code", table_name="product_price_history")
    op.drop_table("product_price_history")
