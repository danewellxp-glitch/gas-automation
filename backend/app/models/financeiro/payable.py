"""Modelo de Contas a Pagar."""
import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class PayableStatus(str, enum.Enum):
    pendente = "pendente"
    pago = "pago"
    vencido = "vencido"
    cancelado = "cancelado"


class Payable(BaseModel):
    __tablename__ = "payables"

    supplier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=PayableStatus.pendente.value)
    recurrence: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_payables_status_due", "status", "due_date"),
    )
