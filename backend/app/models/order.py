"""
Modelos de Pedido e Itens do Pedido.
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

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

    # Relacionamentos
    customer: Mapped["Customer"] = relationship(
        "Customer",
        back_populates="orders",
    )
    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    payments: Mapped[list["Payment"]] = relationship(
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
    )

    def __repr__(self) -> str:
        return f"<Order(id={self.id}, number={self.order_number}, status={self.status})>"

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

    def update_status(self, new_status: str) -> None:
        """Atualiza status e timestamps relacionados."""
        self.status = new_status

        now = func.now()
        if new_status == OrderStatus.PAID.value:
            self.paid_at = now
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
