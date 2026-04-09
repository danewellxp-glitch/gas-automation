"""Modelo de Nota Fiscal Eletrônica (NF-e / NFC-e)."""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel as DBModel


class NotaFiscal(DBModel):
    """Nota Fiscal Eletrônica emitida para um pedido."""

    __tablename__ = "notas_fiscais"

    tipo: Mapped[str] = mapped_column(String(5), nullable=False, default="65")  # 55=NF-e, 65=NFC-e
    numero: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    serie: Mapped[str] = mapped_column(String(5), nullable=False, default="001")
    chave_acesso: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="rascunho",
    )  # rascunho, enviada, autorizada, rejeitada, cancelada, erro_emissao

    pedido_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    emitido_por: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    valor_produtos: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    valor_frete: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    valor_desconto: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    valor_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    valor_icms: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    valor_pis: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    valor_cofins: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))

    xml_enviado: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    xml_autorizado: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pdf_danfe_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    enviada_whatsapp: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    enviada_whatsapp_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    motivo_rejeicao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cancelamento_protocolo: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    emitida_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_notas_fiscais_pedido_id", "pedido_id"),
        Index("ix_notas_fiscais_customer_id", "customer_id"),
        Index("ix_notas_fiscais_status", "status"),
        Index("ix_notas_fiscais_numero", "numero"),
        Index("ix_notas_fiscais_chave_acesso", "chave_acesso"),
    )
