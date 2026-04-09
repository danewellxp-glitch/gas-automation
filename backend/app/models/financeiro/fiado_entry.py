"""Modelos para fiado: entradas de crédito a prazo e seus pagamentos."""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel as DBModel


class FiadoEntry(DBModel):
    """Registro de uma venda fiada para um cliente."""

    __tablename__ = "fiado_entries"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=False,
    )
    valor_original: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    valor_pago: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    vencimento: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="em_aberto",
    )  # em_aberto, pago_parcial, pago, vencido, negociado
    cobrado_whatsapp_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cobrado_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    observacao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pago_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    pagamentos: Mapped[list["FiadoPagamento"]] = relationship(
        "FiadoPagamento", back_populates="entry", lazy="select"
    )

    @property
    def valor_pendente(self) -> Decimal:
        return self.valor_original - self.valor_pago

    __table_args__ = (
        Index("ix_fiado_entries_customer_id", "customer_id"),
        Index("ix_fiado_entries_order_id", "order_id"),
        Index("ix_fiado_entries_status", "status"),
    )


class FiadoPagamento(DBModel):
    """Registro de um pagamento parcial ou total de uma entrada de fiado."""

    __tablename__ = "fiado_pagamentos"

    entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fiado_entries.id", ondelete="CASCADE"),
        nullable=False,
    )
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    metodo: Mapped[str] = mapped_column(String(30), nullable=False)  # PIX, dinheiro, cartao, etc
    asaas_payment_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pago_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    registrado_por: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Relationships
    entry: Mapped["FiadoEntry"] = relationship("FiadoEntry", back_populates="pagamentos")

    __table_args__ = (
        Index("ix_fiado_pagamentos_entry_id", "entry_id"),
    )
