"""Modelo de Contas a Receber."""
import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class ReceivableStatus(str, enum.Enum):
    pendente = "pendente"
    recebido = "recebido"
    vencido = "vencido"
    cancelado = "cancelado"


class Receivable(BaseModel):
    __tablename__ = "receivables"

    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True
    )
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    received_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=ReceivableStatus.pendente.value)
    payment_method: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    asaas_payment_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True, comment="ID da cobrança no Asaas"
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_receivables_status_due", "status", "due_date"),
        Index("ix_receivables_customer", "customer_id"),
    )
