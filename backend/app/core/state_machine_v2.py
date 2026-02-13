"""
Máquina de Estados 2.0 para conversas do WhatsApp.
Flow Engine 2.0 - Estados organizados em FASES com atalhos inteligentes.

Baseado em: GASMASTER_FLOW_ENGINE_2.0_COMPLETO.md
"""

import logging
from enum import Enum
from typing import Optional, List, Dict
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


class ConversationState(str, Enum):
    """
    Estados organizados em fases lógicas.
    Nomenclatura: FASE_ACAO
    Total: 25 estados
    """
    
    # ═══════════════════════════════════════════════════════════════════════
    # FASE 1: GREETING (Boas-vindas) - 2 estados
    # ═══════════════════════════════════════════════════════════════════════
    
    GREETING_INITIAL = "greeting_initial"
    """
    Estado inicial - primeira mensagem do cliente.
    
    TRANSIÇÕES:
    → Cliente conhecido → GREETING_RETURNING
    → Cliente novo → IDENTIFY_TYPE
    → Intenção clara com dados → ORDERING_PRODUCT (fast-track)
    → "falar com atendente" → SUPPORT_HUMAN
    → "rastrear pedido" → TRACKING_STATUS
    """
    
    GREETING_RETURNING = "greeting_returning"
    """
    Cliente conhecido retornando.
    
    TRANSIÇÕES:
    → Repetir pedido → ORDERING_CONFIRM_REPEAT
    → Novo pedido → ORDERING_PRODUCT
    → Continuar abandonado → Estado onde parou
    → Tem pedido em andamento → TRACKING_STATUS
    """
    
    # ═══════════════════════════════════════════════════════════════════════
    # FASE 2: IDENTIFY (Identificação) - 5 estados
    # ═══════════════════════════════════════════════════════════════════════
    
    IDENTIFY_TYPE = "identify_type"
    """
    Pergunta se é PF ou PJ.
    
    TRANSIÇÕES:
    → Pessoa Física → IDENTIFY_NAME_PF
    → Pessoa Jurídica → IDENTIFY_NAME_PJ
    """
    
    IDENTIFY_NAME_PF = "identify_name_pf"
    """Coleta nome completo (PF). → IDENTIFY_DOCUMENT_CPF"""
    
    IDENTIFY_NAME_PJ = "identify_name_pj"
    """Coleta razão social (PJ). → IDENTIFY_DOCUMENT_CNPJ"""
    
    IDENTIFY_DOCUMENT_CPF = "identify_document_cpf"
    """Coleta e valida CPF. → ORDERING_PRODUCT"""
    
    IDENTIFY_DOCUMENT_CNPJ = "identify_document_cnpj"
    """Coleta e valida CNPJ. → ORDERING_PRODUCT"""
    
    # ═══════════════════════════════════════════════════════════════════════
    # FASE 3: ORDERING (Pedido) - 8 estados
    # ═══════════════════════════════════════════════════════════════════════
    
    ORDERING_PRODUCT = "ordering_product"
    """
    Seleção de produto(s).
    
    TRANSIÇÕES:
    → Produto selecionado → ORDERING_QUANTITY
    → Múltiplos produtos → Processa todos e vai para ORDERING_OPERATION
    """
    
    ORDERING_QUANTITY = "ordering_quantity"
    """Define quantidade. → ORDERING_OPERATION"""
    
    ORDERING_OPERATION = "ordering_operation"
    """
    Tipo de operação: Troca / Venda / Retira.
    
    TRANSIÇÕES:
    → Troca ou Venda → ORDERING_MORE_ITEMS
    → Retira → ORDERING_MORE_ITEMS (sem delivery)
    """
    
    ORDERING_MORE_ITEMS = "ordering_more_items"
    """
    Pergunta se quer adicionar mais.
    
    TRANSIÇÕES:
    → Sim → ORDERING_PRODUCT
    → Não + Retira → CHECKOUT_PAYMENT
    → Não + Entrega → ORDERING_ADDRESS
    """
    
    ORDERING_ADDRESS = "ordering_address"
    """
    Coleta endereço de entrega.
    
    TRANSIÇÕES:
    → Endereço válido → ORDERING_ADDRESS_CONFIRM
    → Cliente tem endereços → Oferece seleção
    → Fora da área → Informa e pede outro
    """
    
    ORDERING_ADDRESS_CONFIRM = "ordering_address_confirm"
    """Confirma endereço formatado. → ORDERING_COMPLEMENT"""
    
    ORDERING_COMPLEMENT = "ordering_complement"
    """Coleta complemento/referência. → CHECKOUT_PAYMENT"""
    
    ORDERING_CONFIRM_REPEAT = "ordering_confirm_repeat"
    """
    Confirma repetição do último pedido.
    
    TRANSIÇÕES:
    → Confirmar → CHECKOUT_PAYMENT
    → Alterar → ORDERING_PRODUCT
    """
    
    # ═══════════════════════════════════════════════════════════════════════
    # FASE 4: CHECKOUT (Finalização) - 3 estados
    # ═══════════════════════════════════════════════════════════════════════
    
    CHECKOUT_PAYMENT = "checkout_payment"
    """
    Seleção de pagamento.
    
    TRANSIÇÕES:
    → Dinheiro → CHECKOUT_CHANGE
    → Outros → CHECKOUT_SUMMARY
    """
    
    CHECKOUT_CHANGE = "checkout_change"
    """Pergunta troco para quanto. → CHECKOUT_SUMMARY"""
    
    CHECKOUT_SUMMARY = "checkout_summary"
    """
    Mostra resumo e pede confirmação.
    
    TRANSIÇÕES:
    → Confirmar → COMPLETE_CONFIRMED
    → Alterar produto → ORDERING_PRODUCT
    → Alterar endereço → ORDERING_ADDRESS
    → Alterar pagamento → CHECKOUT_PAYMENT
    → Cancelar → GREETING_INITIAL
    """
    
    # ═══════════════════════════════════════════════════════════════════════
    # FASE 5: COMPLETE (Conclusão) - 2 estados
    # ═══════════════════════════════════════════════════════════════════════
    
    COMPLETE_CONFIRMED = "complete_confirmed"
    """Pedido confirmado com sucesso. → COMPLETE_FOLLOWUP"""
    
    COMPLETE_FOLLOWUP = "complete_followup"
    """
    Pós-venda e acompanhamento.
    
    TRANSIÇÕES:
    → Rastrear → TRACKING_STATUS
    → Novo pedido → ORDERING_PRODUCT
    """
    
    # ═══════════════════════════════════════════════════════════════════════
    # ESTADOS DE SUPORTE (Paralelos) - 5 estados
    # ═══════════════════════════════════════════════════════════════════════
    
    SUPPORT_HUMAN = "support_human"
    """
    Atendimento humano.
    Acessível de qualquer estado via "falar com atendente".
    Retorna ao estado anterior quando liberado.
    """
    
    SUPPORT_FAQ = "support_faq"
    """
    Respondendo pergunta frequente inline.
    Responde e retorna ao estado anterior automaticamente.
    """
    
    TRACKING_STATUS = "tracking_status"
    """Mostrando status do pedido. → TRACKING_OPTIONS"""
    
    TRACKING_OPTIONS = "tracking_options"
    """
    Opções após ver status.
    
    TRANSIÇÕES:
    → Atualizar → TRACKING_STATUS
    → Problema → SUPPORT_HUMAN
    → Novo pedido → ORDERING_PRODUCT
    """
    
    ERROR_RECOVERY = "error_recovery"
    """Estado de recuperação após erro crítico."""


class StateTransition:
    """Define transições válidas entre estados."""

    VALID_TRANSITIONS = {
        # GREETING
        ConversationState.GREETING_INITIAL: [
            ConversationState.GREETING_RETURNING,
            ConversationState.IDENTIFY_TYPE,
            ConversationState.ORDERING_PRODUCT,
            ConversationState.CHECKOUT_SUMMARY,  # Fast-track
            ConversationState.SUPPORT_HUMAN,
            ConversationState.TRACKING_STATUS,
        ],
        ConversationState.GREETING_RETURNING: [
            ConversationState.ORDERING_CONFIRM_REPEAT,
            ConversationState.ORDERING_PRODUCT,
            ConversationState.TRACKING_STATUS,
        ],
        
        # IDENTIFY
        ConversationState.IDENTIFY_TYPE: [
            ConversationState.IDENTIFY_NAME_PF,
            ConversationState.IDENTIFY_NAME_PJ,
        ],
        ConversationState.IDENTIFY_NAME_PF: [
            ConversationState.IDENTIFY_DOCUMENT_CPF,
            ConversationState.ORDERING_PRODUCT,  # Pode pular documento
        ],
        ConversationState.IDENTIFY_NAME_PJ: [
            ConversationState.IDENTIFY_DOCUMENT_CNPJ,
            ConversationState.ORDERING_PRODUCT,  # Pode pular documento
        ],
        ConversationState.IDENTIFY_DOCUMENT_CPF: [
            ConversationState.ORDERING_PRODUCT,
        ],
        ConversationState.IDENTIFY_DOCUMENT_CNPJ: [
            ConversationState.ORDERING_PRODUCT,
        ],
        
        # ORDERING
        ConversationState.ORDERING_PRODUCT: [
            ConversationState.ORDERING_QUANTITY,
            ConversationState.ORDERING_OPERATION,
            ConversationState.SUPPORT_HUMAN,
            ConversationState.SUPPORT_FAQ,
        ],
        ConversationState.ORDERING_QUANTITY: [
            ConversationState.ORDERING_OPERATION,
            ConversationState.ORDERING_PRODUCT,
        ],
        ConversationState.ORDERING_OPERATION: [
            ConversationState.ORDERING_MORE_ITEMS,
        ],
        ConversationState.ORDERING_MORE_ITEMS: [
            ConversationState.ORDERING_PRODUCT,  # Adicionar mais
            ConversationState.ORDERING_ADDRESS,  # Entrega
            ConversationState.CHECKOUT_PAYMENT,  # Retira
        ],
        ConversationState.ORDERING_ADDRESS: [
            ConversationState.ORDERING_ADDRESS_CONFIRM,
            ConversationState.ORDERING_ADDRESS,  # Retry
        ],
        ConversationState.ORDERING_ADDRESS_CONFIRM: [
            ConversationState.ORDERING_COMPLEMENT,
            ConversationState.ORDERING_ADDRESS,  # Alterar
        ],
        ConversationState.ORDERING_COMPLEMENT: [
            ConversationState.CHECKOUT_PAYMENT,
        ],
        ConversationState.ORDERING_CONFIRM_REPEAT: [
            ConversationState.CHECKOUT_PAYMENT,
            ConversationState.ORDERING_PRODUCT,  # Alterar
        ],
        
        # CHECKOUT
        ConversationState.CHECKOUT_PAYMENT: [
            ConversationState.CHECKOUT_CHANGE,
            ConversationState.CHECKOUT_SUMMARY,
        ],
        ConversationState.CHECKOUT_CHANGE: [
            ConversationState.CHECKOUT_SUMMARY,
        ],
        ConversationState.CHECKOUT_SUMMARY: [
            ConversationState.COMPLETE_CONFIRMED,
            ConversationState.ORDERING_PRODUCT,  # Alterar
            ConversationState.ORDERING_ADDRESS,  # Alterar
            ConversationState.CHECKOUT_PAYMENT,  # Alterar
            ConversationState.GREETING_INITIAL,  # Cancelar
        ],
        
        # COMPLETE
        ConversationState.COMPLETE_CONFIRMED: [
            ConversationState.COMPLETE_FOLLOWUP,
        ],
        ConversationState.COMPLETE_FOLLOWUP: [
            ConversationState.TRACKING_STATUS,
            ConversationState.ORDERING_PRODUCT,
            ConversationState.GREETING_INITIAL,
        ],
        
        # SUPPORT (podem ir para qualquer lugar)
        ConversationState.SUPPORT_HUMAN: [
            ConversationState.GREETING_INITIAL,
            ConversationState.ORDERING_PRODUCT,
            ConversationState.TRACKING_STATUS,
        ],
        ConversationState.SUPPORT_FAQ: [
            # Retorna ao estado anterior
        ],
        ConversationState.TRACKING_STATUS: [
            ConversationState.TRACKING_OPTIONS,
            ConversationState.GREETING_INITIAL,
        ],
        ConversationState.TRACKING_OPTIONS: [
            ConversationState.TRACKING_STATUS,
            ConversationState.SUPPORT_HUMAN,
            ConversationState.ORDERING_PRODUCT,
        ],
        ConversationState.ERROR_RECOVERY: [
            ConversationState.GREETING_INITIAL,
            ConversationState.SUPPORT_HUMAN,
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
class CustomerContext:
    """Contexto do cliente (PERSISTENTE - Redis → PostgreSQL → Firebird)."""
    
    customer_id: Optional[str] = None
    name: Optional[str] = None
    document: Optional[str] = None  # CPF ou CNPJ
    customer_type: Optional[str] = None  # "PF" ou "PJ"
    
    # Endereços
    addresses: List[Dict] = field(default_factory=list)
    default_address_idx: int = 0
    
    # Histórico
    last_order: Optional[Dict] = None
    order_count: int = 0
    
    # Preferências aprendidas
    preferences: Dict = field(default_factory=dict)
    
    # VIP
    is_vip: bool = False


@dataclass
class ConversationContext:
    """Contexto da sessão (30min TTL)."""
    
    # Identificação
    phone: str
    session_id: Optional[str] = None
    
    # Estado
    current_state: ConversationState = ConversationState.GREETING_INITIAL
    state_history: List[str] = field(default_factory=list)
    return_state: Optional[ConversationState] = None  # Para FAQ/Support
    
    # Dados coletados
    collected_data: Dict = field(default_factory=dict)
    flow_step: int = 0
    
    # Flags
    is_returning: bool = False
    needs_human: bool = False
    
    # Controle
    last_message_at: datetime = field(default_factory=datetime.utcnow)
    message_count: int = 0
    retry_count: int = 0
    
    # WAHA
    waha_chat_id: Optional[str] = None
    
    # Recuperação
    resumed_from_snapshot: bool = False


@dataclass
class OrderContext:
    """Contexto do pedido atual (2h TTL)."""
    
    # Itens
    items: List[Dict] = field(default_factory=list)
    
    # Valores
    subtotal: float = 0.0
    delivery_fee: float = 0.0
    total: float = 0.0
    
    # Entrega
    address: Optional[Dict] = None
    complement: Optional[str] = None
    operation_type: Optional[str] = None  # "exchange", "sale", "pickup"
    
    # Pagamento
    payment_method: Optional[str] = None
    change_for: Optional[float] = None
    
    # Validação
    validation_errors: List[str] = field(default_factory=list)


# Compatibilidade com código existente
class ConversationStateV1(str, Enum):
    """Estados v1.0 (deprecated - manter para migração)."""
    START = "start"
    ASKING_CUSTOMER_TYPE = "asking_customer_type"
    COLLECTING_NAME = "collecting_name"
    COLLECTING_DOCUMENT = "collecting_document"
    AWAITING_PRODUCT = "awaiting_product"
    AWAITING_QUANTITY = "awaiting_quantity"
    CONFIRMING_ADDRESS = "confirming_address"
    AWAITING_ADDRESS = "awaiting_address"
    AWAITING_PAYMENT = "awaiting_payment"
    PROCESSING_PAYMENT = "processing_payment"
    AWAITING_PIX = "awaiting_pix"
    CONFIRMING_ORDER = "confirming_order"
    ORDER_CONFIRMED = "order_confirmed"
    TRACKING_ORDER = "tracking_order"
    TALKING_TO_HUMAN = "talking_to_human"
    IDLE = "idle"
