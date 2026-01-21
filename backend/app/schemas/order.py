"""
Schemas de Pedido.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.base import AddressSchema, BaseSchema, TimestampSchema, PaginatedResponse
from app.schemas.customer import CustomerBrief


# Re-export enums for backward compatibility
class OrderStatus:
    PENDING = "pending"
    PAID = "paid"
    PREPARING = "preparing"
    DISPATCHED = "dispatched"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentMethod:
    PIX = "pix"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    CASH = "cash"
    BOLETO = "boleto"


class OrderItemBase(BaseSchema):
    """Schema base de item do pedido."""

    product_code: str = Field(..., description="Código do produto")
    quantity: int = Field(..., ge=1, le=99, description="Quantidade")


class OrderItemCreate(OrderItemBase):
    """Schema para criar item."""
    pass


class OrderItemResponse(OrderItemBase, TimestampSchema):
    """Schema de resposta de item."""

    id: UUID
    order_id: UUID
    product_name: str
    unit_price: Decimal
    subtotal: Decimal


class OrderBase(BaseSchema):
    """Schema base de pedido."""

    delivery_address: Optional[AddressSchema] = Field(None, description="Endereço de entrega")
    delivery_bairro: Optional[str] = Field(None, max_length=100, description="Bairro")
    notes: Optional[str] = Field(None, description="Observações")


class OrderCreate(OrderBase):
    """Schema para criar pedido."""

    customer_id: UUID = Field(..., description="ID do cliente")
    items: list[OrderItemCreate] = Field(..., min_length=1, description="Itens do pedido")
    payment_method: Optional[str] = Field(None, description="Método de pagamento")

    @field_validator("items")
    @classmethod
    def validate_items(cls, v):
        if not v:
            raise ValueError("Pedido deve ter pelo menos um item")
        return v


class OrderUpdate(BaseSchema):
    """Schema para atualizar pedido."""

    status: Optional[str] = None
    payment_method: Optional[str] = None
    delivery_address: Optional[AddressSchema] = None
    notes: Optional[str] = None
    cancellation_reason: Optional[str] = Field(None, max_length=500)


class OrderResponse(OrderBase, TimestampSchema):
    """Schema de resposta de pedido."""

    id: UUID
    order_number: int
    customer_id: UUID
    status: str
    payment_method: Optional[str] = None
    total_amount: Decimal
    paid_at: Optional[datetime] = None
    dispatched_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    items: list[OrderItemResponse] = []
    customer: Optional[CustomerBrief] = None


class OrderBrief(BaseSchema):
    """Schema resumido de pedido (para listas)."""

    id: UUID
    order_number: int
    status: str
    total_amount: Decimal
    customer_name: Optional[str] = None
    customer_phone: str
    delivery_bairro: Optional[str] = None
    created_at: datetime

    @classmethod
    def from_order(cls, order) -> "OrderBrief":
        return cls(
            id=order.id,
            order_number=order.order_number,
            status=order.status,
            total_amount=order.total_amount,
            customer_name=order.customer.name if order.customer else None,
            customer_phone=order.customer.phone if order.customer else "",
            delivery_bairro=order.delivery_bairro,
            created_at=order.created_at,
        )


class OrderSummary(BaseSchema):
    """Resumo do pedido para confirmação no bot."""

    order_id: UUID
    order_number: int
    items_description: str  # "1x P13 - R$ 110,00"
    total_amount: Decimal
    delivery_address: str
    payment_method: Optional[str] = None


class OrderStatusUpdate(BaseSchema):
    """Schema para atualizar apenas o status."""

    status: str
    reason: Optional[str] = Field(None, max_length=500, description="Motivo (para cancelamento)")


class PaginatedOrdersResponse(BaseSchema):
    """Resposta paginada de pedidos."""
    
    items: list[OrderBrief]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool
    
    @classmethod
    def create(cls, items: list[OrderBrief], total: int, page: int, page_size: int):
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )
