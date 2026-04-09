"""Modelo de Saldo de Estoque (materializado)."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class StockBalance(BaseModel):
    __tablename__ = "stock_balance"

    stock_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stock_products.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    quantity_depot: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quantity_in_transit: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quantity_with_customers: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("stock_product_id", name="uq_stock_balance_product"),
    )
