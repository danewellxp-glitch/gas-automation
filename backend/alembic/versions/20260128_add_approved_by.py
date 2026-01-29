"""Add approved_by field to orders

Revision ID: 20260128_approved_by
Revises: 20260128_file_export
Create Date: 2026-01-28

Adiciona campo approved_by para rastrear qual operador/admin aprovou cada pedido.
"""

from alembic import op
import sqlalchemy as sa


revision = "20260128_approved_by"
down_revision = "20260128_auditlog_meta"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column(
            "approved_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            comment="ID do operador/admin que aprovou o pedido (mudou status para PAID)",
        ),
    )
    op.create_index("ix_orders_approved_by", "orders", ["approved_by"])


def downgrade() -> None:
    op.drop_index("ix_orders_approved_by", table_name="orders")
    op.drop_column("orders", "approved_by")
