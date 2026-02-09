"""
Máquina de Estados para conversas do WhatsApp.
Define os estados do fluxo de pedido e as transições válidas.
"""

import logging
from enum import Enum
from typing import Optional, List
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


class ConversationState(str, Enum):
    """Estados possíveis da conversa."""

    # Início
    START = "start"                          # Cliente iniciou conversa

    # Coleta de dados (identificacao)
    ASKING_CUSTOMER_TYPE = "asking_customer_type"  # PF ou Empresa
    COLLECTING_NAME = "collecting_name"      # Aguardando nome (PF ou empresa)
    COLLECTING_DOCUMENT = "collecting_document"    # CPF/CNPJ antes de confirmar

    # Fluxo de pedido
    AWAITING_PRODUCT = "awaiting_product"    # Aguardando seleção de produto
    AWAITING_QUANTITY = "awaiting_quantity"  # Aguardando quantidade
    CONFIRMING_ADDRESS = "confirming_address"  # Confirmando endereço
    AWAITING_ADDRESS = "awaiting_address"    # Aguardando novo endereço
    AWAITING_PAYMENT = "awaiting_payment"    # Aguardando método de pagamento
    PROCESSING_PAYMENT = "processing_payment"  # Processando pagamento
    AWAITING_PIX = "awaiting_pix"            # Aguardando confirmação Pix

    # Confirmações
    CONFIRMING_ORDER = "confirming_order"    # Confirmando pedido completo
    ORDER_CONFIRMED = "order_confirmed"      # Pedido confirmado

    # Status
    TRACKING_ORDER = "tracking_order"        # Rastreando pedido

    # Outros
    TALKING_TO_HUMAN = "talking_to_human"    # Transferido para atendente
    IDLE = "idle"                            # Conversa inativa


class StateTransition:
    """Define transições válidas entre estados."""

    VALID_TRANSITIONS = {
        ConversationState.START: [
            ConversationState.ASKING_CUSTOMER_TYPE,
            ConversationState.COLLECTING_NAME,
            ConversationState.AWAITING_PRODUCT,
            ConversationState.AWAITING_QUANTITY,
            ConversationState.AWAITING_ADDRESS,
            ConversationState.AWAITING_PAYMENT,
            ConversationState.CONFIRMING_ORDER,
            ConversationState.TRACKING_ORDER,
            ConversationState.TALKING_TO_HUMAN,
        ],
        ConversationState.ASKING_CUSTOMER_TYPE: [
            ConversationState.COLLECTING_NAME,
            ConversationState.START,
        ],
        ConversationState.COLLECTING_NAME: [
            ConversationState.AWAITING_PRODUCT,
            ConversationState.START,
        ],
        ConversationState.COLLECTING_DOCUMENT: [
            ConversationState.CONFIRMING_ORDER,
            ConversationState.START,
        ],
        ConversationState.AWAITING_PRODUCT: [
            ConversationState.AWAITING_QUANTITY,
            ConversationState.START,
            ConversationState.TALKING_TO_HUMAN,
        ],
        ConversationState.AWAITING_QUANTITY: [
            ConversationState.CONFIRMING_ADDRESS,
            ConversationState.AWAITING_ADDRESS,
            ConversationState.AWAITING_PRODUCT,
            ConversationState.TALKING_TO_HUMAN,
        ],
        ConversationState.CONFIRMING_ADDRESS: [
            ConversationState.AWAITING_PAYMENT,
            ConversationState.AWAITING_ADDRESS,
            ConversationState.AWAITING_QUANTITY,
            ConversationState.TALKING_TO_HUMAN,
        ],
        ConversationState.AWAITING_ADDRESS: [
            ConversationState.AWAITING_PAYMENT,
            ConversationState.CONFIRMING_ADDRESS,
            ConversationState.TALKING_TO_HUMAN,
        ],
        ConversationState.AWAITING_PAYMENT: [
            ConversationState.COLLECTING_DOCUMENT,
            ConversationState.PROCESSING_PAYMENT,
            ConversationState.AWAITING_PIX,
            ConversationState.CONFIRMING_ORDER,
            ConversationState.AWAITING_PRODUCT,
            ConversationState.TALKING_TO_HUMAN,
        ],
        ConversationState.PROCESSING_PAYMENT: [
            ConversationState.ORDER_CONFIRMED,
            ConversationState.AWAITING_PAYMENT,
            ConversationState.TALKING_TO_HUMAN,
        ],
        ConversationState.AWAITING_PIX: [
            ConversationState.ORDER_CONFIRMED,
            ConversationState.AWAITING_PAYMENT,
            ConversationState.START,
            ConversationState.TALKING_TO_HUMAN,
        ],
        ConversationState.CONFIRMING_ORDER: [
            ConversationState.ORDER_CONFIRMED,
            ConversationState.AWAITING_PRODUCT,
            ConversationState.AWAITING_QUANTITY,
            ConversationState.AWAITING_ADDRESS,
            ConversationState.AWAITING_PAYMENT,
            ConversationState.START,
            ConversationState.TALKING_TO_HUMAN,
        ],
        ConversationState.ORDER_CONFIRMED: [
            ConversationState.START,
            ConversationState.TRACKING_ORDER,
        ],
        ConversationState.TRACKING_ORDER: [
            ConversationState.START,
            ConversationState.TALKING_TO_HUMAN,
        ],
        ConversationState.TALKING_TO_HUMAN: [
            ConversationState.START,
        ],
        ConversationState.IDLE: [
            ConversationState.START,
        ],
    }

    @classmethod
    def is_valid(cls, from_state: ConversationState, to_state: ConversationState) -> bool:
        """Verifica se a transição é válida."""
        valid_next = cls.VALID_TRANSITIONS.get(from_state, [])
        return to_state in valid_next

    @classmethod
    def get_valid_transitions(cls, state: ConversationState) -> List[ConversationState]:
        """Retorna transições válidas a partir de um estado."""
        return cls.VALID_TRANSITIONS.get(state, [])


@dataclass
class ConversationContext:
    """Contexto completo da conversa."""

    # Identificação
    phone: str
    state: ConversationState = ConversationState.START

    # Cliente
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    customer_type: Optional[str] = None     # "PF" ou "PJ"
    is_new_customer: bool = False           # Cliente totalmente novo
    has_complete_data: bool = False         # Nome E (CPF ou endereco)

    # Pedido em construção
    order_id: Optional[str] = None
    selected_product: Optional[str] = None  # Código do produto (P13, P20, P45)
    selected_quantity: int = 1

    # Endereço
    address: Optional[dict] = None
    address_confirmed: bool = False

    # Pagamento
    payment_method: Optional[str] = None  # pix, credit_card, cash
    payment_id: Optional[str] = None
    asaas_payment_id: Optional[str] = None  # ID da cobrança no Asaas

    # Controle
    last_message_at: datetime = field(default_factory=datetime.utcnow)
    message_count: int = 0
    retry_count: int = 0

    # IA
    last_intent: Optional[str] = None
    ai_confidence: float = 0.0

    # Fluxo conversacional (NLP)
    awaiting_confirmation: bool = False
    awaiting_input_type: Optional[str] = None  # 'product', 'quantity', 'address', 'payment', 'cpf', 'name'
    pending_entities: dict = field(default_factory=dict)  # Entidades extraidas mas nao confirmadas
    recent_messages: list = field(default_factory=list)  # Ultimas 3 mensagens para contexto
    change_for: Optional[int] = None  # Valor do troco

    # Recuperação de pedido abandonado
    resumed_from_snapshot: bool = False  # True se contexto veio do PostgreSQL (Redis expirou)

    def to_dict(self) -> dict:
        """Converte para dicionário (para salvar no Redis)."""
        return {
            "phone": self.phone,
            "state": self.state.value,
            "customer_id": self.customer_id,
            "customer_name": self.customer_name,
            "customer_type": self.customer_type,
            "is_new_customer": self.is_new_customer,
            "has_complete_data": self.has_complete_data,
            "order_id": self.order_id,
            "selected_product": self.selected_product,
            "selected_quantity": self.selected_quantity,
            "address": self.address,
            "address_confirmed": self.address_confirmed,
            "payment_method": self.payment_method,
            "payment_id": self.payment_id,
            "asaas_payment_id": self.asaas_payment_id,
            "last_message_at": self.last_message_at.isoformat(),
            "message_count": self.message_count,
            "retry_count": self.retry_count,
            "last_intent": self.last_intent,
            "ai_confidence": self.ai_confidence,
            "awaiting_confirmation": self.awaiting_confirmation,
            "awaiting_input_type": self.awaiting_input_type,
            "pending_entities": self.pending_entities,
            "recent_messages": self.recent_messages,
            "change_for": self.change_for,
            "resumed_from_snapshot": self.resumed_from_snapshot,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConversationContext":
        """Cria instância a partir de dicionário."""
        return cls(
            phone=data["phone"],
            state=ConversationState(data.get("state", "start")),
            customer_id=data.get("customer_id"),
            customer_name=data.get("customer_name"),
            customer_type=data.get("customer_type"),
            is_new_customer=data.get("is_new_customer", False),
            has_complete_data=data.get("has_complete_data", False),
            order_id=data.get("order_id"),
            selected_product=data.get("selected_product"),
            selected_quantity=data.get("selected_quantity", 1),
            address=data.get("address"),
            address_confirmed=data.get("address_confirmed", False),
            payment_method=data.get("payment_method"),
            payment_id=data.get("payment_id"),
            asaas_payment_id=data.get("asaas_payment_id"),
            last_message_at=datetime.fromisoformat(data["last_message_at"]) if data.get("last_message_at") else datetime.utcnow(),
            message_count=data.get("message_count", 0),
            retry_count=data.get("retry_count", 0),
            last_intent=data.get("last_intent"),
            ai_confidence=data.get("ai_confidence", 0.0),
            awaiting_confirmation=data.get("awaiting_confirmation", False),
            awaiting_input_type=data.get("awaiting_input_type"),
            pending_entities=data.get("pending_entities", {}),
            recent_messages=data.get("recent_messages", []),
            change_for=data.get("change_for"),
            resumed_from_snapshot=data.get("resumed_from_snapshot", False),
        )

    def transition_to(self, new_state: ConversationState) -> bool:
        """
        Transiciona para um novo estado.
        Loga warning se a transição não está na tabela de válidas.
        Sempre executa a transição (safety net para não quebrar fluxos).
        """
        if self.state == new_state:
            return True
        is_valid = StateTransition.is_valid(self.state, new_state)
        if not is_valid:
            logger.warning(
                f"Transicao nao mapeada: {self.state.value} -> {new_state.value} "
                f"(phone={self.phone})"
            )
        self.state = new_state
        self.retry_count = 0
        return is_valid

    def reset(self) -> None:
        """Reseta o contexto para o estado inicial."""
        self.state = ConversationState.START
        self.is_new_customer = False
        self.has_complete_data = False
        self.order_id = None
        self.selected_product = None
        self.selected_quantity = 1
        self.address_confirmed = False
        self.payment_method = None
        self.payment_id = None
        self.asaas_payment_id = None
        self.retry_count = 0
        self.last_intent = None
        self.ai_confidence = 0.0
        self.awaiting_confirmation = False
        self.awaiting_input_type = None
        self.pending_entities = {}
        self.recent_messages = []
        self.change_for = None
        self.resumed_from_snapshot = False

    def increment_retry(self) -> int:
        """Incrementa contador de tentativas e retorna o valor atual."""
        self.retry_count += 1
        return self.retry_count
