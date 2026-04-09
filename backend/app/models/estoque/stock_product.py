"""Modelo de Produto de Estoque."""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class StockProduct(BaseModel):
    __tablename__ = "stock_products"

    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="unidade")
    cost_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    min_stock_alert: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    linked_product_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
