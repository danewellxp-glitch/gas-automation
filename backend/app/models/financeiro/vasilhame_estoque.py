"""Modelos de Estoque de Vasilhames."""
import uuid
from decimal import Decimal
from typing import Optional

from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class VasilhameEstoque(BaseModel):
    """Posição de estoque de cada tipo de vasilhame."""

    __tablename__ = "vasilhame_estoque"

    tipo: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
    qtd_cheios: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    qtd_vazios: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    qtd_em_campo: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    custo_unitario: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))

    __table_args__ = (
        UniqueConstraint("tipo", name="uq_vasilhame_estoque_tipo"),
    )


class VasilhameMovimento(BaseModel):
    """Registro de cada movimentação de vasilhame."""

    __tablename__ = "vasilhame_movimentos"

    tipo_vasilhame: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    tipo_movimento: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False)

    custo_unitario: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    custo_total: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)

    pedido_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    entregador_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    observacao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    saldo_cheios_antes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    saldo_vazios_antes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    saldo_em_campo_antes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
