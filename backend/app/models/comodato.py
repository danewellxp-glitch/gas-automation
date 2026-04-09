"""
Modelo de Comodato (Empréstimo de Equipamentos).

Registra equipamentos emprestados a clientes (ex: reguladores, botijões em comodato).
"""

import enum
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class ComodatoStatus(str, enum.Enum):
    ATIVO = "ativo"
    DEVOLVIDO = "devolvido"
    PERDIDO = "perdido"
    CANCELADO = "cancelado"


class Comodato(BaseModel):
    """Registro de empréstimo de equipamento a um cliente."""

    __tablename__ = "comodatos"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Descrição do equipamento
    equipamento: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="Ex: Regulador, Botijão P13, Mangueira"
    )
    numero_serie: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="Número de série ou identificador do equipamento"
    )
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    valor_caucao: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(14, 2), nullable=True, comment="Valor de caução cobrado (0 = gratuito)"
    )

    data_emprestimo: Mapped[date] = mapped_column(
        Date, nullable=False, comment="Data de saída do equipamento"
    )
    data_prevista_devolucao: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True
    )
    data_devolucao: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="Data em que foi efetivamente devolvido"
    )

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ComodatoStatus.ATIVO.value, index=True
    )
    observacao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Quem registrou
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
