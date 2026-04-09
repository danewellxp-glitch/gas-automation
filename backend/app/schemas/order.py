"""
Schemas de Pedido.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
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


class TipoOperacao:
    TROCA = "troca"    # Cliente troca vazio por cheio
    VENDA = "venda"    # Cliente compra com vasilhame novo
    RETIRA = "retira"  # Cliente busca na loja


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
    items: List[OrderItemCreate] = Field(..., min_length=1, description="Itens do pedido")
    payment_method: Optional[str] = Field(None, description="Método de pagamento")
    tipo_operacao: str = Field(default="troca", description="Tipo: troca, venda, retira")

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
    tipo_operacao: Optional[str] = None
    delivery_address: Optional[AddressSchema] = None
    notes: Optional[str] = None
    cancellation_reason: Optional[str] = Field(None, max_length=500)


class OrderResponse(OrderBase, TimestampSchema):
    """Schema de resposta de pedido."""

    id: UUID
    order_number: Optional[int] = None  # Pode ser None se ainda não gerado
    customer_id: UUID
    status: str
    payment_method: Optional[str] = None
    tipo_operacao: str = "troca"
    total_amount: Decimal
    firebird_trade_id: Optional[int] = None
    firebird_export_status: Optional[str] = None
    firebird_exported_at: Optional[datetime] = None
    firebird_export_attempts: int = 0
    firebird_export_error: Optional[str] = None
    paid_at: Optional[datetime] = None
    dispatched_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    items: List[OrderItemResponse] = []
    customer: Optional[CustomerBrief] = None


class OrderItemBrief(BaseSchema):
    """Item do pedido para listagem."""

    product_code: str
    product_name: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


class OrderBrief(BaseSchema):
    """Schema resumido de pedido (para listas)."""

    id: UUID
    order_number: int
    status: str
    total_amount: Decimal
    customer_name: Optional[str] = None
    customer_phone: str
    customer_cpf_cnpj: Optional[str] = None
    delivery_bairro: Optional[str] = None
    delivery_address: Optional[str] = None
    location_type: Optional[str] = None
    items: List[OrderItemBrief] = []
    payment_method: Optional[str] = None
    tipo_operacao: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    delivered_at: Optional[datetime] = None
    approved_by_name: Optional[str] = None
    cancellation_reason: Optional[str] = None

    @classmethod
    def from_order(cls, order, approved_by_name: Optional[str] = None) -> "OrderBrief":
        # Telefone para exibição: remover sufixo @c.us se existir
        phone = ""
        if order.customer and order.customer.phone:
            phone = (order.customer.phone or "").replace("@c.us", "").strip()
        # Endereço formatado para exibição
        delivery_address_str = None
        location_type = None
        if order.delivery_address:
            addr = order.delivery_address
            if isinstance(addr, dict):
                delivery_address_str = addr.get("full_address") or ", ".join(
                    filter(None, [addr.get("street"), addr.get("number"), addr.get("bairro")])
                )
                location_type = addr.get("location_type")
            else:
                delivery_address_str = str(addr)
        # Itens do pedido (order.items já carregado via selectinload)
        item_list = []
        if getattr(order, "items", None):
            for it in order.items:
                item_list.append(
                    OrderItemBrief(
                        product_code=it.product_code or "",
                        product_name=it.product_name or it.product_code or "",
                        quantity=it.quantity or 0,
                        unit_price=it.unit_price or Decimal("0"),
                        subtotal=it.subtotal or Decimal("0"),
                    )
                )
        return cls(
            id=order.id,
            order_number=order.order_number,
            status=order.status,
            total_amount=order.total_amount,
            customer_name=(order.customer.name or None) if order.customer else None,
            customer_phone=phone,
            customer_cpf_cnpj=(order.customer.cpf_cnpj or None) if order.customer else None,
            delivery_bairro=order.delivery_bairro,
            delivery_address=delivery_address_str,
            location_type=location_type,
            items=item_list,
            payment_method=order.payment_method,
            tipo_operacao=getattr(order, "tipo_operacao", None),
            notes=getattr(order, "notes", None),
            created_at=order.created_at,
            delivered_at=getattr(order, "delivered_at", None),
            approved_by_name=approved_by_name,
            cancellation_reason=getattr(order, "cancellation_reason", None),
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


class OrderRejectRequest(BaseSchema):
    """Schema para rejeitar um pedido."""

    reason: str = Field(
        default="Rejeitado pelo operador",
        max_length=500,
        description="Motivo da rejeição"
    )


class PaginatedOrdersResponse(BaseSchema):
    """Resposta paginada de pedidos."""
    
    items: List[OrderBrief]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool
    
    @classmethod
    def create(cls, items: List[OrderBrief], total: int, page: int, page_size: int):
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
