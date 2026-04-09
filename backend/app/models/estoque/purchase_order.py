"""Modelo de Pedido de Compra."""
import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.estoque.purchase_order_item import PurchaseOrderItem


class PurchaseOrderStatus(str, enum.Enum):
    rascunho = "rascunho"
    enviado = "enviado"
    recebido = "recebido"
    cancelado = "cancelado"


class PurchaseOrder(BaseModel):
    __tablename__ = "purchase_orders"

    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    expected_delivery_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=PurchaseOrderStatus.rascunho.value)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    received_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    received_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    items: Mapped[List["PurchaseOrderItem"]] = relationship(
        "PurchaseOrderItem", lazy="selectin", back_populates="purchase_order"
    )
