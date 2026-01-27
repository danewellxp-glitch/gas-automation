"""
Schemas de Webhooks (WAHA e Asaas).
"""

from datetime import datetime
from typing import Any, Optional, List, Dict

from pydantic import Field

from app.schemas.base import BaseSchema


# ==================== WAHA (WhatsApp) ====================

class WAHAMessageKey(BaseSchema):
    """Chave de identificação da mensagem."""

    remoteJid: str  # Número do remetente (5541999999999@s.whatsapp.net)
    fromMe: bool  # Se a mensagem foi enviada por nós
    id: str  # ID da mensagem


class WAHAMessage(BaseSchema):
    """Mensagem do WhatsApp."""

    key: WAHAMessageKey
    message: Optional[dict] = None  # Conteúdo da mensagem
    messageTimestamp: Optional[int] = None
    pushName: Optional[str] = None  # Nome do contato

    @property
    def phone(self) -> str:
        """
        Retorna o chatId completo para enviar respostas.
        Pode ser formato @lid ou @c.us.
        """
        return self.key.remoteJid  # Manter formato completo para resposta

    @property
    def phone_number(self) -> str:
        """Extrai apenas o número (sem sufixo @lid ou @c.us)."""
        jid = self.key.remoteJid
        return jid.split("@")[0] if "@" in jid else jid

    @property
    def text(self) -> Optional[str]:
        """Extrai o texto da mensagem."""
        if not self.message:
            return None

        # Mensagem de texto simples
        if "conversation" in self.message:
            return self.message["conversation"]

        # Mensagem com texto estendido
        if "extendedTextMessage" in self.message:
            return self.message["extendedTextMessage"].get("text")

        # Resposta de botão
        if "buttonsResponseMessage" in self.message:
            return self.message["buttonsResponseMessage"].get("selectedButtonId")

        # Lista de seleção
        if "listResponseMessage" in self.message:
            return self.message["listResponseMessage"].get("singleSelectReply", {}).get("selectedRowId")

        return None

    @property
    def button_id(self) -> Optional[str]:
        """Extrai o ID do botão clicado (se houver)."""
        if not self.message:
            return None

        if "buttonsResponseMessage" in self.message:
            return self.message["buttonsResponseMessage"].get("selectedButtonId")

        if "listResponseMessage" in self.message:
            return self.message["listResponseMessage"].get("singleSelectReply", {}).get("selectedRowId")

        return None

    @property
    def is_button_response(self) -> bool:
        """Verifica se é resposta de botão."""
        return self.button_id is not None

    @property
    def location(self) -> Optional[Dict[str, float]]:
        """
        Extrai coordenadas de mensagem de localização.
        Retorna: {'latitude': float, 'longitude': float} ou None
        """
        if not self.message:
            return None

        # Mensagem de localização do WhatsApp
        if "locationMessage" in self.message:
            loc = self.message["locationMessage"]
            return {
                "latitude": loc.get("degreesLatitude"),
                "longitude": loc.get("degreesLongitude"),
                "name": loc.get("name"),
                "address": loc.get("address"),
            }

        return None

    @property
    def is_location(self) -> bool:
        """Verifica se é mensagem de localização."""
        return self.location is not None


class WAHAWebhookPayload(BaseSchema):
    """Payload do webhook WAHA."""

    event: str  # message, message.ack, session.status
    session: str  # Nome da sessão
    payload: dict  # Dados do evento

    @property
    def message(self) -> Optional[WAHAMessage]:
        """Extrai a mensagem do payload."""
        if self.event == "message" and "message" in self.payload:
            return WAHAMessage(**self.payload["message"])
        return None


# ==================== Asaas (Pagamentos) ====================

class AsaasPaymentWebhook(BaseSchema):
    """Webhook de pagamento Asaas."""

    event: str  # PAYMENT_CONFIRMED, PAYMENT_RECEIVED, PAYMENT_OVERDUE, etc
    payment: dict  # Dados do pagamento

    @property
    def payment_id(self) -> str:
        """ID do pagamento no Asaas."""
        return self.payment.get("id", "")

    @property
    def status(self) -> str:
        """Status do pagamento."""
        return self.payment.get("status", "")

    @property
    def value(self) -> float:
        """Valor do pagamento."""
        return self.payment.get("value", 0)

    @property
    def net_value(self) -> float:
        """Valor líquido."""
        return self.payment.get("netValue", 0)

    @property
    def billing_type(self) -> str:
        """Tipo de cobrança (PIX, BOLETO, CREDIT_CARD)."""
        return self.payment.get("billingType", "")

    @property
    def external_reference(self) -> Optional[str]:
        """Referência externa (nosso order_id)."""
        return self.payment.get("externalReference")


class AsaasWebhookPayload(BaseSchema):
    """Payload genérico do webhook Asaas."""

    event: str
    payment: Optional[dict] = None
    transfer: Optional[dict] = None

    def get_payment_webhook(self) -> Optional[AsaasPaymentWebhook]:
        """Retorna webhook de pagamento se aplicável."""
        if self.payment:
            return AsaasPaymentWebhook(event=self.event, payment=self.payment)
        return None


# ==================== Respostas do Bot ====================

class BotButton(BaseSchema):
    """Botão para mensagem do WhatsApp."""

    id: str  # ID único do botão
    text: str  # Texto exibido (max 20 chars)


class BotResponse(BaseSchema):
    """Resposta do bot para enviar ao cliente."""

    text: str  # Texto da mensagem
    buttons: Optional[List[BotButton]] = None  # Botões (max 3)
    image_url: Optional[str] = None  # URL de imagem
    image_base64: Optional[str] = None  # Imagem em base64


class ConversationState(BaseSchema):
    """Estado da conversa armazenado no Redis."""

    step: str  # Estado atual (start, awaiting_product, etc)
    customer_phone: str
    customer_id: Optional[str] = None
    cart: List[Dict] = Field(default_factory=list)  # [{product_code, quantity, price}]
    selected_product: Optional[str] = None
    selected_quantity: Optional[int] = None
    delivery_address: Optional[Dict] = None
    payment_method: Optional[str] = None
    order_id: Optional[str] = None
    last_message_at: Optional[datetime] = None
    last_bot_message: Optional[str] = None
    context: dict = Field(default_factory=dict)  # Dados extras

    @property
    def cart_total(self) -> float:
        """Calcula total do carrinho."""
        return sum(
            item.get("quantity", 1) * item.get("price", 0)
            for item in self.cart
        )

    @property
    def cart_description(self) -> str:
        """Descrição do carrinho para exibição."""
        if not self.cart:
            return "Carrinho vazio"

        items = []
        for item in self.cart:
            qty = item.get("quantity", 1)
            code = item.get("product_code", "?")
            price = item.get("price", 0)
            items.append(f"{qty}x {code} - R$ {price * qty:.2f}")

        return "\n".join(items)
