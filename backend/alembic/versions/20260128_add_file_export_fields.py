"""Add file export fields to orders

Revision ID: 20260128_file_export
Revises: 20260124_firebird_export
Create Date: 2026-01-28

Adiciona campos para rastreamento de exportação de pedidos para arquivos
(CSV, XML, Gasmaster TXT) como alternativa à exportação direta para Firebird.
"""

from alembic import op
import sqlalchemy as sa


revision = "20260128_file_export"
down_revision = "20260124_firebird_export"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column(
            "file_export_status",
            sa.String(20),
            nullable=True,
            comment="Status exportação arquivo: exported, pending, failed",
        ),
    )
    op.create_index("ix_orders_file_export_status", "orders", ["file_export_status"])

    op.add_column(
        "orders",
        sa.Column(
            "file_exported_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Data/hora da exportação para arquivo",
        ),
    )
    op.create_index("ix_orders_file_exported_at", "orders", ["file_exported_at"])


def downgrade() -> None:
    op.drop_index("ix_orders_file_exported_at", table_name="orders")
    op.drop_column("orders", "file_exported_at")
    op.drop_index("ix_orders_file_export_status", table_name="orders")
    op.drop_column("orders", "file_export_status")
