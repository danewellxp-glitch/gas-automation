"""create_stock_module

Revision ID: 20260324_create_stock_module
Revises: 20260324_create_financial_module
Create Date: 2026-03-24 01:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "20260324_create_stock_module"
down_revision = "20260324_create_financial_module"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # suppliers
    op.create_table(
        "suppliers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("cnpj", sa.String(20), nullable=True),
        sa.Column("contact_name", sa.String(100), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("email", sa.String(150), nullable=True),
        sa.Column("address", sa.String(300), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # add FK from payables to suppliers
    op.create_foreign_key(
        "fk_payables_supplier", "payables", "suppliers", ["supplier_id"], ["id"], ondelete="SET NULL"
    )

    # stock_products
    op.create_table(
        "stock_products",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False, server_default="unidade"),
        sa.Column("cost_price", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("min_stock_alert", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("linked_product_code", sa.String(20), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_stock_products_code", "stock_products", ["code"], unique=True)

    # stock_balance
    op.create_table(
        "stock_balance",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("stock_product_id", UUID(as_uuid=True), sa.ForeignKey("stock_products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quantity_depot", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quantity_in_transit", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quantity_with_customers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_updated", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("stock_product_id", name="uq_stock_balance_product"),
    )

    # vehicle_loads
    op.create_table(
        "vehicle_loads",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("driver_id", UUID(as_uuid=True), sa.ForeignKey("drivers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("load_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="aberta"),
        sa.Column("loaded_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("driver_id", "load_date", name="uq_vehicle_load_driver_date"),
    )
    op.create_index("ix_vehicle_loads_driver", "vehicle_loads", ["driver_id"])
    op.create_index("ix_vehicle_loads_date_status", "vehicle_loads", ["load_date", "status"])

    # vehicle_load_items
    op.create_table(
        "vehicle_load_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("vehicle_load_id", UUID(as_uuid=True), sa.ForeignKey("vehicle_loads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stock_product_id", UUID(as_uuid=True), sa.ForeignKey("stock_products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity_loaded", sa.Integer(), nullable=False),
        sa.Column("quantity_delivered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quantity_returned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_vehicle_load_items_load", "vehicle_load_items", ["vehicle_load_id"])

    # stock_movements
    op.create_table(
        "stock_movements",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("stock_product_id", UUID(as_uuid=True), sa.ForeignKey("stock_products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("movement_type", sa.String(30), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("unit_cost", sa.Numeric(10, 2), nullable=True),
        sa.Column("total_cost", sa.Numeric(14, 2), nullable=True),
        sa.Column("reference_id", UUID(as_uuid=True), nullable=True),
        sa.Column("reference_type", sa.String(30), nullable=True),
        sa.Column("vehicle_load_id", UUID(as_uuid=True), sa.ForeignKey("vehicle_loads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("driver_id", UUID(as_uuid=True), sa.ForeignKey("drivers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_stock_movements_product_date", "stock_movements", ["stock_product_id", "created_at"])
    op.create_index("ix_stock_movements_type_date", "stock_movements", ["movement_type", "created_at"])
    op.create_index("ix_stock_movements_driver", "stock_movements", ["driver_id"])

    # purchase_orders
    op.create_table(
        "purchase_orders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("supplier_id", UUID(as_uuid=True), sa.ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("order_date", sa.Date(), nullable=False),
        sa.Column("expected_delivery_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="rascunho"),
        sa.Column("total_cost", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_purchase_orders_supplier", "purchase_orders", ["supplier_id"])
    op.create_index("ix_purchase_orders_status", "purchase_orders", ["status"])

    # purchase_order_items
    op.create_table(
        "purchase_order_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("purchase_order_id", UUID(as_uuid=True), sa.ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stock_product_id", UUID(as_uuid=True), sa.ForeignKey("stock_products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity_ordered", sa.Integer(), nullable=False),
        sa.Column("quantity_received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unit_cost", sa.Numeric(10, 2), nullable=False),
        sa.Column("subtotal", sa.Numeric(14, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_purchase_order_items_order", "purchase_order_items", ["purchase_order_id"])


def downgrade() -> None:
    op.drop_table("purchase_order_items")
    op.drop_table("purchase_orders")
    op.drop_table("stock_movements")
    op.drop_table("vehicle_load_items")
    op.drop_table("vehicle_loads")
    op.drop_table("stock_balance")
    op.drop_table("stock_products")
    op.drop_constraint("fk_payables_supplier", "payables", type_="foreignkey")
    op.drop_table("suppliers")
