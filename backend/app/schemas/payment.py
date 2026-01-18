"""
Schemas de Pagamento.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import Field

from app.models.payment import PaymentMethod, PaymentStatus
from app.schemas.base import BaseSchema, TimestampSchema


class PaymentBase(BaseSchema):
    """Schema base de pagamento."""

    method: PaymentMethod = Field(..., description="Método de pagamento")
    amount: Decimal = Field(..., gt=0, description="Valor")


class PaymentCreate(PaymentBase):
    """Schema para criar pagamento."""

    order_id: UUID = Field(..., description="ID do pedido")


class PaymentResponse(PaymentBase, TimestampSchema):
    """Schema de resposta de pagamento."""

    id: UUID
    order_id: UUID
    asaas_payment_id: Optional[str] = None
    status: PaymentStatus
    net_amount: Optional[Decimal] = None
    fee: Optional[Decimal] = None

    # Pix
    pix_qr_code: Optional[str] = None
    pix_copy_paste: Optional[str] = None
    pix_expiration: Optional[datetime] = None

    # Boleto
    boleto_url: Optional[str] = None
    boleto_barcode: Optional[str] = None
    boleto_digitable_line: Optional[str] = None

    # Cartão
    card_last_digits: Optional[str] = None
    card_brand: Optional[str] = None

    # Datas
    due_date: Optional[datetime] = None
    paid_at: Optional[datetime] = None


class PixPaymentResponse(BaseSchema):
    """Resposta específica para pagamento Pix."""

    payment_id: UUID
    asaas_payment_id: str
    qr_code: str  # Base64 da imagem
    copy_paste: str  # Código copia e cola
    expiration: datetime
    amount: Decimal


class PaymentWebhookPayload(BaseSchema):
    """Payload do webhook de pagamento Asaas."""

    event: str  # PAYMENT_CONFIRMED, PAYMENT_RECEIVED, etc
    payment: dict


class PaymentStatusResponse(BaseSchema):
    """Resposta de consulta de status."""

    payment_id: UUID
    status: PaymentStatus
    is_paid: bool
    paid_at: Optional[datetime] = None


class CreatePixPaymentRequest(BaseSchema):
    """Request para criar pagamento Pix."""

    order_id: UUID
    customer_name: str
    customer_cpf_cnpj: str
    customer_email: Optional[str] = None
    amount: Decimal
    description: str


class CreateCreditCardPaymentRequest(BaseSchema):
    """Request para criar pagamento com cartão."""

    order_id: UUID
    customer_name: str
    customer_cpf_cnpj: str
    customer_email: str
    customer_phone: str
    amount: Decimal
    description: str

    # Dados do cartão (tokenizados)
    card_holder_name: str
    card_number: str
    card_expiry_month: str
    card_expiry_year: str
    card_cvv: str

    # Endereço de cobrança
    billing_address: Optional[dict] = None
    installments: int = Field(1, ge=1, le=12, description="Número de parcelas")
