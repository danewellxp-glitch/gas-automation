"""
Modelos de Acerto de Turno do Entregador.

DriverTurno: Representa um turno de trabalho (início/fim).
AcertoItemEntrega: Cada entrega lançada no turno com valores cobrados.
"""

import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class TurnoStatus(str, enum.Enum):
    ABERTO = "aberto"
    AGUARDANDO_APROVACAO = "aguardando_aprovacao"
    APROVADO = "aprovado"
    REJEITADO = "rejeitado"


class DriverTurno(BaseModel):
    """Turno de trabalho de um entregador."""

    __tablename__ = "driver_turnos"

    driver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("drivers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=TurnoStatus.ABERTO.value, index=True
    )
    iniciado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    finalizado_em: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    aprovado_em: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    aprovado_por: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Resumo financeiro (calculado ao fechar)
    total_cobrado: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(14, 2), nullable=True, comment="Soma de tudo que o entregador cobrou"
    )
    total_esperado: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(14, 2), nullable=True, comment="Soma dos totais dos pedidos"
    )
    diferenca: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(14, 2), nullable=True, comment="total_cobrado - total_esperado"
    )
    observacao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class AcertoItemEntrega(BaseModel):
    """Registro de uma entrega dentro de um turno para acerto financeiro."""

    __tablename__ = "acerto_itens_entrega"

    turno_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("driver_turnos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    delivery_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deliveries.id", ondelete="SET NULL"),
        nullable=True,
    )
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
    )
    valor_pedido: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, comment="Total esperado do pedido"
    )
    valor_cobrado: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, comment="Valor efetivamente cobrado pelo entregador"
    )
    payment_method: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="Forma de pagamento recebida"
    )
    observacao: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    entregue: Mapped[bool] = mapped_column(default=True, nullable=False)
