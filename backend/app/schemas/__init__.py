"""
Schemas Pydantic do sistema.
Exporta todos os schemas para facilitar importação.
"""

from app.schemas.base import (
    AddressSchema,
    BaseSchema,
    IDSchema,
    PaginatedResponse,
    PaginationParams,
    TimestampSchema,
)
from app.schemas.carga import (
    CargaItemBase,
    CargaItemCreate,
    CargaItemAcerto,
    CargaItemResponse,
    CargaBase,
    CargaCreate,
    CargaUpdate,
    CargaSaidaRequest,
    CargaAcertoRequest,
    CargaResponse,
    CargaBrief,
    CargaAtualResponse,
)
from app.schemas.customer import (
    CustomerBase,
    CustomerBrief,
    CustomerCreate,
    CustomerResponse,
    CustomerUpdate,
)
from app.schemas.order import (
    OrderBase,
    OrderBrief,
    OrderCreate,
    OrderItemBase,
    OrderItemCreate,
    OrderItemResponse,
    OrderResponse,
    OrderStatusUpdate,
    OrderSummary,
    OrderUpdate,
)
from app.schemas.payment import (
    CreateCreditCardPaymentRequest,
    CreatePixPaymentRequest,
    PaymentBase,
    PaymentCreate,
    PaymentResponse,
    PaymentStatusResponse,
    PaymentWebhookPayload,
    PixPaymentResponse,
)
from app.schemas.product import (
    ProductBase,
    ProductBrief,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)
from app.schemas.webhook import (
    AsaasPaymentWebhook,
    AsaasWebhookPayload,
    BotButton,
    BotResponse,
    ConversationState,
    WAHAMessage,
    WAHAMessageKey,
    WAHAWebhookPayload,
)

__all__ = [
    # Base
    "BaseSchema",
    "IDSchema",
    "TimestampSchema",
    "AddressSchema",
    "PaginationParams",
    "PaginatedResponse",
    # Carga
    "CargaItemBase",
    "CargaItemCreate",
    "CargaItemAcerto",
    "CargaItemResponse",
    "CargaBase",
    "CargaCreate",
    "CargaUpdate",
    "CargaSaidaRequest",
    "CargaAcertoRequest",
    "CargaResponse",
    "CargaBrief",
    "CargaAtualResponse",
    # Customer
    "CustomerBase",
    "CustomerCreate",
    "CustomerUpdate",
    "CustomerResponse",
    "CustomerBrief",
    # Product
    "ProductBase",
    "ProductCreate",
    "ProductUpdate",
    "ProductResponse",
    "ProductBrief",
    # Order
    "OrderBase",
    "OrderCreate",
    "OrderUpdate",
    "OrderResponse",
    "OrderBrief",
    "OrderSummary",
    "OrderStatusUpdate",
    "OrderItemBase",
    "OrderItemCreate",
    "OrderItemResponse",
    # Payment
    "PaymentBase",
    "PaymentCreate",
    "PaymentResponse",
    "PaymentStatusResponse",
    "PaymentWebhookPayload",
    "PixPaymentResponse",
    "CreatePixPaymentRequest",
    "CreateCreditCardPaymentRequest",
    # Webhook
    "WAHAMessageKey",
    "WAHAMessage",
    "WAHAWebhookPayload",
    "AsaasPaymentWebhook",
    "AsaasWebhookPayload",
    "BotButton",
    "BotResponse",
    "ConversationState",
]
