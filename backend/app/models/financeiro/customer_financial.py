"""Modelo de Situação Financeira do Cliente (fiado / crédito)."""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.customer import Customer


class CustomerFinancial(BaseModel):
    """
    Rastreia a situação financeira de cada cliente.

    balance > 0  → cliente tem crédito (pagou a mais / adiantamento)
    balance < 0  → cliente tem dívida (fiado / atraso)
    balance = 0  → em dia
    """
    __tablename__ = "customer_financial"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Saldo: positivo = crédito, negativo = dívida (fiado)
    balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00")
    )

    # Limite de crédito negativo permitido (ex: -500.00 = pode fiar até R$500)
    credit_limit: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("200.00")
    )

    # Acumuladores para análise
    total_purchases: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00"),
        comment="Total comprado no sistema (lifetime)"
    )
    total_orders: Mapped[int] = mapped_column(
        nullable=False, default=0
    )

    last_purchase_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    customer: Mapped["Customer"] = relationship("Customer")

    __table_args__ = (
        UniqueConstraint("customer_id", name="uq_customer_financial_customer"),
    )
