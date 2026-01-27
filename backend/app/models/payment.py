"""
Modelo de Pagamento.
Integração com Asaas para Pix, Cartão e Boleto.
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.order import Order


class PaymentStatus(str, enum.Enum):
    """Status do pagamento."""
    PENDING = "pending"           # Aguardando pagamento
    CONFIRMED = "confirmed"       # Confirmado/Aprovado
    RECEIVED = "received"         # Recebido (para boleto)
    OVERDUE = "overdue"          # Vencido
    REFUNDED = "refunded"         # Estornado
    REFUND_REQUESTED = "refund_requested"  # Estorno solicitado
    CHARGEBACK_REQUESTED = "chargeback_requested"  # Chargeback solicitado
    CHARGEBACK_DISPUTE = "chargeback_dispute"  # Disputa de chargeback
    AWAITING_CHARGEBACK_REVERSAL = "awaiting_chargeback_reversal"
    DUNNING_REQUESTED = "dunning_requested"  # Negativação solicitada
    DUNNING_RECEIVED = "dunning_received"    # Negativação recebida
    AWAITING_RISK_ANALYSIS = "awaiting_risk_analysis"  # Análise de risco
    FAILED = "failed"             # Falhou


class PaymentMethod(str, enum.Enum):
    """Método de pagamento (Asaas)."""
    PIX = "PIX"
    CREDIT_CARD = "CREDIT_CARD"
    BOLETO = "BOLETO"
    CASH = "CASH"  # Dinheiro na entrega (não vai para Asaas)


class Payment(BaseModel):
    """
    Modelo de Pagamento.

    Attributes:
        order_id: FK para pedido
        asaas_payment_id: ID do pagamento no Asaas
        method: Método de pagamento
        status: Status atual
        amount: Valor do pagamento
        pix_qr_code: QR Code Pix (base64)
        pix_copy_paste: Código Pix copia e cola
        boleto_url: URL do boleto
        boleto_barcode: Código de barras do boleto
        paid_at: Data/hora do pagamento
        due_date: Data de vencimento
    """

    __tablename__ = "payments"

    # Relacionamento com pedido
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Identificação Asaas
    asaas_payment_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        unique=True,
        nullable=True,
        index=True,
        comment="ID do pagamento no Asaas"
    )
    asaas_customer_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="ID do cliente no Asaas"
    )

    # Método e status
    method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default=PaymentStatus.PENDING.value,
        nullable=False,
        index=True,
    )

    # Valores
    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    net_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Valor líquido após taxas"
    )
    fee: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Taxa cobrada pelo gateway"
    )

    # Dados Pix
    pix_qr_code: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="QR Code Pix em base64"
    )
    pix_copy_paste: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Código Pix copia e cola"
    )
    pix_expiration: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data/hora de expiração do Pix"
    )

    # Dados Boleto
    boleto_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="URL do boleto PDF"
    )
    boleto_barcode: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Código de barras do boleto"
    )
    boleto_digitable_line: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Linha digitável do boleto"
    )

    # Dados Cartão (não armazenamos dados sensíveis)
    card_last_digits: Mapped[Optional[str]] = mapped_column(
        String(4),
        nullable=True,
        comment="Últimos 4 dígitos do cartão"
    )
    card_brand: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Bandeira do cartão"
    )

    # Datas
    due_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data de vencimento"
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data/hora do pagamento confirmado"
    )

    # Metadados do gateway
    gateway_response: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Resposta completa do gateway"
    )

    # Relacionamento
    order: Mapped["Order"] = relationship(
        "Order",
        back_populates="payments",
    )

    # Índices
    __table_args__ = (
        Index("ix_payments_status_method", "status", "method"),
        Index("ix_payments_order_status", "order_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Payment(id={self.id}, method={self.method}, status={self.status}, amount={self.amount})>"

    @property
    def is_paid(self) -> bool:
        """Verifica se o pagamento foi confirmado."""
        return self.status in [PaymentStatus.CONFIRMED.value, PaymentStatus.RECEIVED.value]

    @property
    def is_pending(self) -> bool:
        """Verifica se o pagamento está pendente."""
        return self.status == PaymentStatus.PENDING.value

    @property
    def is_expired(self) -> bool:
        """Verifica se o pagamento Pix expirou."""
        if self.method == PaymentMethod.PIX.value and self.pix_expiration:
            from datetime import timezone
            return datetime.now(timezone.utc) > self.pix_expiration
        return False
