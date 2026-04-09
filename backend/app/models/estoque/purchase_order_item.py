"""Modelo de Item do Pedido de Compra."""
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.estoque.purchase_order import PurchaseOrder


class PurchaseOrderItem(BaseModel):
    __tablename__ = "purchase_order_items"

    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stock_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stock_products.id", ondelete="RESTRICT"), nullable=False
    )
    quantity_ordered: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    purchase_order: Mapped["PurchaseOrder"] = relationship("PurchaseOrder", back_populates="items")
