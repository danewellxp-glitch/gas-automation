"""Add Firebird export fields to orders

Revision ID: 20260124_firebird_export
Revises: 20260124_vasilhames
Create Date: 2026-01-24

"""

from alembic import op
import sqlalchemy as sa


revision = "20260124_firebird_export"
down_revision = "20260124_vasilhames"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column(
            "firebird_trade_id",
            sa.Integer(),
            nullable=True,
            comment="ID da venda/pedido no Firebird (TRADE.ID)",
        ),
    )
    op.create_index("ix_orders_firebird_trade_id", "orders", ["firebird_trade_id"], unique=True)

    op.add_column(
        "orders",
        sa.Column(
            "firebird_export_status",
            sa.String(20),
            nullable=True,
            comment="Status exportação Firebird: exported, failed",
        ),
    )
    op.create_index("ix_orders_firebird_export_status", "orders", ["firebird_export_status"])

    op.add_column(
        "orders",
        sa.Column(
            "firebird_exported_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Data/hora da exportação para Firebird",
        ),
    )
    op.create_index("ix_orders_firebird_exported_at", "orders", ["firebird_exported_at"])

    op.add_column(
        "orders",
        sa.Column(
            "firebird_export_attempts",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="Número de tentativas de exportação Firebird",
        ),
    )

    op.add_column(
        "orders",
        sa.Column(
            "firebird_export_error",
            sa.Text(),
            nullable=True,
            comment="Último erro de exportação Firebird",
        ),
    )

    op.create_index(
        "ix_orders_firebird_export",
        "orders",
        ["firebird_export_status", "firebird_exported_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_orders_firebird_export", table_name="orders")
    op.drop_column("orders", "firebird_export_error")
    op.drop_column("orders", "firebird_export_attempts")
    op.drop_index("ix_orders_firebird_exported_at", table_name="orders")
    op.drop_column("orders", "firebird_exported_at")
    op.drop_index("ix_orders_firebird_export_status", table_name="orders")
    op.drop_column("orders", "firebird_export_status")
    op.drop_index("ix_orders_firebird_trade_id", table_name="orders")
    op.drop_column("orders", "firebird_trade_id")

