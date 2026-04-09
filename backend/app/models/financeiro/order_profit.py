"""Modelo de Lucratividade por Pedido."""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.order import Order


class OrderProfit(BaseModel):
    """
    Registra a lucratividade calculada de cada pedido após entrega.

    Cálculo:
        revenue        = order.total_amount
        product_cost   = Σ (quantity × stock_product.cost_price)
        delivery_cost  = custo fixo estimado por entrega
        estimated_cost = product_cost + delivery_cost
        profit         = revenue - estimated_cost
        margin_%       = profit / revenue × 100
    """
    __tablename__ = "order_profits"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    revenue: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00")
    )
    product_cost: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00"),
        comment="Custo do produto (CMV)"
    )
    delivery_cost: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00"),
        comment="Custo estimado de entrega (combustível + depreciação)"
    )
    estimated_cost: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00"),
        comment="product_cost + delivery_cost"
    )
    profit: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00")
    )
    margin_percentage: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), nullable=False, default=Decimal("0.00"),
        comment="Margem líquida %"
    )

    bairro: Mapped[Optional[str]] = mapped_column(
        nullable=True, index=True,
        comment="Snapshot do bairro para análise geográfica"
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    order: Mapped["Order"] = relationship("Order")

    __table_args__ = (
        UniqueConstraint("order_id", name="uq_order_profit_order"),
    )
