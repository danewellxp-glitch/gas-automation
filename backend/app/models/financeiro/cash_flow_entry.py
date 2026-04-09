"""Modelo de Entrada de Fluxo de Caixa."""
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Index, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class CashFlowEntry(BaseModel):
    __tablename__ = "cash_flow_entries"

    reference_date: Mapped[date] = mapped_column(Date, nullable=False)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    total_income: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    total_expense: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    closing_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    is_projected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("ix_cash_flow_account_date", "account_id", "reference_date"),
    )
