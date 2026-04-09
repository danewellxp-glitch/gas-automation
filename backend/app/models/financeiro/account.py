"""Modelo de Conta Bancária / Caixa."""
import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Numeric, String, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class AccountType(str, enum.Enum):
    caixa = "caixa"
    conta_corrente = "conta_corrente"
    conta_poupanca = "conta_poupanca"


class Account(BaseModel):
    __tablename__ = "accounts"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False, default=AccountType.caixa.value)
    bank_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    agency: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    account_number: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    initial_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_accounts_is_active", "is_active"),
    )
