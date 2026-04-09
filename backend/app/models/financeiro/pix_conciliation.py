"""Modelos de Conciliação PIX."""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class PixConciliationRun(BaseModel):
    """Representa uma execução de conciliação PIX para um dia."""

    __tablename__ = "pix_conciliation_runs"

    conciliation_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    total_asaas: Mapped[int] = mapped_column(nullable=False, default=0)
    total_local: Mapped[int] = mapped_column(nullable=False, default=0)
    total_conciliado: Mapped[int] = mapped_column(nullable=False, default=0)
    total_divergencia: Mapped[int] = mapped_column(nullable=False, default=0)
    total_apenas_asaas: Mapped[int] = mapped_column(nullable=False, default=0)
    total_apenas_local: Mapped[int] = mapped_column(nullable=False, default=0)

    valor_asaas: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    valor_local: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))

    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pendente_revisao")

    aprovado_por: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    aprovado_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class PixConciliationItem(BaseModel):
    """Cada item (linha) de uma conciliação PIX."""

    __tablename__ = "pix_conciliation_items"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pix_conciliation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resultado: Mapped[str] = mapped_column(String(30), nullable=False, index=True)

    # Dados do Asaas
    asaas_payment_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    asaas_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    asaas_payer_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    asaas_paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Dados locais
    transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    transaction_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
    )

    diferenca: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    observacao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolvido: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    resolvido_por: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (
        Index("ix_pix_conciliation_items_run_resultado", "run_id", "resultado"),
    )
