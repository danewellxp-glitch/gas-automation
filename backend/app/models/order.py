"""
Modelos de Pedido e Itens do Pedido.
"""

import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Optional, List

import sqlalchemy as sa
from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.delivery import Delivery
    from app.models.payment import Payment


class OrderStatus(str, enum.Enum):
    """Status do pedido."""
    PENDING = "pending"           # Aguardando pagamento
    PAID = "paid"                 # Pago, aguardando preparo
    PREPARING = "preparing"       # Em preparação
    DISPATCHED = "dispatched"     # Saiu para entrega
    DELIVERED = "delivered"       # Entregue
    CANCELLED = "cancelled"       # Cancelado


class TipoOperacao(str, enum.Enum):
    """Tipo de operação do pedido."""
    TROCA = "troca"       # Cliente troca vazio por cheio (tem vasilhame)
    VENDA = "venda"       # Cliente compra com vasilhame novo (paga caução)
    RETIRA = "retira"     # Cliente busca na loja (sem entrega)


class PaymentMethod(str, enum.Enum):
    """Método de pagamento."""
    PIX = "pix"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    CASH = "cash"
    BOLETO = "boleto"


class Order(BaseModel):
    """
    Modelo de Pedido.

    Attributes:
        customer_id: FK para cliente
        order_number: Número sequencial do pedido (para exibição)
        status: Status atual do pedido
        payment_method: Método de pagamento escolhido
        total_amount: Valor total do pedido
        delivery_address: Endereço de entrega (snapshot)
        notes: Observações do cliente
        delivered_at: Data/hora da entrega
    """

    __tablename__ = "orders"

    # Relacionamento com cliente
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Identificação
    order_number: Mapped[int] = mapped_column(
        Integer,
        unique=True,
        nullable=False,
        server_default=sa.text("nextval('order_number_seq')"),
        comment="Número sequencial para exibição"
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default=OrderStatus.PENDING.value,
        nullable=False,
        index=True,
    )

    # Pagamento
    payment_method: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    asaas_payment_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="ID da cobrança no Asaas (PIX/Boleto)"
    )

    # Tipo de operação (TROCA/VENDA/RETIRA)
    tipo_operacao: Mapped[str] = mapped_column(
        String(20),
        default=TipoOperacao.TROCA.value,
        nullable=False,
        comment="Tipo: troca (tem vasilhame), venda (novo), retira (busca)"
    )

    # Integração Firebird (exportação para TRADE/TRADEITEM)
    firebird_trade_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        unique=True,
        index=True,
        comment="ID da venda/pedido no Firebird (TRADE.ID)"
    )
    firebird_export_status: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        index=True,
        comment="Status exportação Firebird: exported, failed"
    )
    firebird_exported_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data/hora da exportação para Firebird"
    )
    firebird_export_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Número de tentativas de exportação Firebird"
    )
    firebird_export_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Último erro de exportação Firebird"
    )

    # Exportação para arquivos (alternativa ao Firebird)
    file_export_status: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        index=True,
        comment="Status exportação arquivo: exported, pending, failed"
    )
    file_exported_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data/hora da exportação para arquivo"
    )

    # Valores
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    # Endereço de entrega (snapshot do momento do pedido)
    delivery_address: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Snapshot do endereço: {street, number, complement, bairro, city, cep}"
    )
    delivery_bairro: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Bairro para alocação de entregador"
    )

    # Observações
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Observações do cliente ou operador"
    )

    # Timestamps específicos
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    dispatched_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    delivered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancellation_reason: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    
    # Tracking de aprovação
    # use_alter=True para evitar conflito de metadata entre SQLModel (User) e BaseModel (Order)
    approved_by: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL", use_alter=True, name="fk_orders_approved_by_users"),
        nullable=True,
        index=True,
        comment="ID do operador/admin que aprovou o pedido (mudou status para PAID)"
    )

    # Relacionamentos
    customer: Mapped["Customer"] = relationship(
        "Customer",
        back_populates="orders",
    )
    items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    payments: Mapped[List["Payment"]] = relationship(
        "Payment",
        back_populates="order",
        lazy="selectin",
    )
    delivery: Mapped[Optional["Delivery"]] = relationship(
        "Delivery",
        back_populates="order",
        uselist=False,
    )

    # Índices
    __table_args__ = (
        Index("ix_orders_status_created", "status", "created_at"),
        Index("ix_orders_customer_status", "customer_id", "status"),
        Index("ix_orders_bairro_status", "delivery_bairro", "status"),
        Index("ix_orders_firebird_export", "firebird_export_status", "firebird_exported_at"),
    )

    def __repr__(self) -> str:
        return f"<Order(id={self.id}, number={self.order_number}, status={self.status})>"

    @property
    def os_number(self) -> str:
        """Número da OS formatado com 8 dígitos (ex: 00000004)."""
        return str(self.order_number).zfill(8)

    @property
    def is_payable(self) -> bool:
        """Verifica se o pedido ainda pode ser pago."""
        return self.status == OrderStatus.PENDING.value

    @property
    def is_cancellable(self) -> bool:
        """Verifica se o pedido pode ser cancelado."""
        return self.status in [OrderStatus.PENDING.value, OrderStatus.PAID.value]

    def calculate_total(self) -> Decimal:
        """Recalcula o total baseado nos itens."""
        return sum(item.subtotal for item in self.items)

    def update_status(self, new_status: str, approved_by: Optional[int] = None) -> None:
        """Atualiza status e timestamps relacionados."""
        self.status = new_status

        now = datetime.now(timezone.utc)
        if new_status == OrderStatus.PAID.value:
            self.paid_at = now
            if approved_by is not None:
                self.approved_by = approved_by
        elif new_status == OrderStatus.DISPATCHED.value:
            self.dispatched_at = now
        elif new_status == OrderStatus.DELIVERED.value:
            self.delivered_at = now
        elif new_status == OrderStatus.CANCELLED.value:
            self.cancelled_at = now


class OrderItem(BaseModel):
    """
    Modelo de Item do Pedido.

    Attributes:
        order_id: FK para pedido
        product_code: Código do produto (P13, P20, P45)
        product_name: Nome do produto (snapshot)
        quantity: Quantidade
        unit_price: Preço unitário (snapshot)
        subtotal: Subtotal (quantity * unit_price)
    """

    __tablename__ = "order_items"

    # Relacionamento com pedido
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Dados do produto (snapshot)
    product_code: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Código do produto (P13, P20, P45)"
    )
    product_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Nome do produto no momento do pedido"
    )

    # Quantidade e valores
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Preço unitário no momento do pedido"
    )
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Subtotal (quantity * unit_price)"
    )

    # Relacionamento
    order: Mapped["Order"] = relationship(
        "Order",
        back_populates="items",
    )

    def __repr__(self) -> str:
        return f"<OrderItem(product={self.product_code}, qty={self.quantity}, subtotal={self.subtotal})>"

    def calculate_subtotal(self) -> Decimal:
        """Calcula subtotal."""
        return Decimal(str(self.quantity)) * self.unit_price
