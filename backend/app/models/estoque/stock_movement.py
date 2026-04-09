"""Modelo de Movimentação de Estoque."""
import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class MovementType(str, enum.Enum):
    compra = "compra"
    venda = "venda"
    carga_veiculo = "carga_veiculo"
    retorno_veiculo = "retorno_veiculo"
    devolucao_cliente = "devolucao_cliente"
    ajuste_entrada = "ajuste_entrada"
    ajuste_saida = "ajuste_saida"
    perda = "perda"


class StockMovement(BaseModel):
    __tablename__ = "stock_movements"

    stock_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stock_products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    movement_type: Mapped[str] = mapped_column(String(30), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False, comment="entrada ou saida")
    unit_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    total_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    reference_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    reference_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    vehicle_load_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vehicle_loads.id", ondelete="SET NULL"), nullable=True
    )
    driver_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drivers.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    __table_args__ = (
        Index("ix_stock_movements_product_date", "stock_product_id", "created_at"),
        Index("ix_stock_movements_type_date", "movement_type", "created_at"),
        Index("ix_stock_movements_driver", "driver_id"),
    )
