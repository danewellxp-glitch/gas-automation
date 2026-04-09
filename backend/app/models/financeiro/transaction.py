"""Modelo de Transação Financeira."""
import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class TransactionType(str, enum.Enum):
    receita = "receita"
    despesa = "despesa"
    transferencia = "transferencia"


class TransactionCategory(str, enum.Enum):
    # Receitas
    venda_gas = "venda_gas"
    deposito_vasilhame = "deposito_vasilhame"
    outras_receitas = "outras_receitas"
    # Despesas
    compra_gas = "compra_gas"
    combustivel = "combustivel"
    manutencao_veiculo = "manutencao_veiculo"
    salarios = "salarios"
    comissao_entregador = "comissao_entregador"
    aluguel = "aluguel"
    energia_agua = "energia_agua"
    impostos = "impostos"
    marketing = "marketing"
    outras_despesas = "outras_despesas"
    # Transferências
    transferencia = "transferencia"


class Transaction(BaseModel):
    __tablename__ = "transactions"

    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False, comment="entrada ou saida")
    reference_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_paid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    payable_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payables.id", ondelete="SET NULL"), nullable=True
    )
    receivable_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("receivables.id", ondelete="SET NULL"), nullable=True
    )
    cost_center_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cost_centers.id", ondelete="SET NULL"), nullable=True
    )
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_transactions_account_date", "account_id", "reference_date"),
        Index("ix_transactions_type_paid", "type", "is_paid"),
        Index("ix_transactions_order", "order_id"),
    )
