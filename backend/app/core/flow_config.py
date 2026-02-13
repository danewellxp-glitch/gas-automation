"""
Configuração do Flow Engine 2.0
Constantes e configurações centralizadas.

Baseado em: GASMASTER_FLOW_ENGINE_2.0_COMPLETO.md
"""

from typing import Dict, List, Tuple, Optional
from decimal import Decimal


# ═══════════════════════════════════════════════════════════════════════
# CONFIGURAÇÕES GERAIS
# ═══════════════════════════════════════════════════════════════════════

# Versão do Flow Engine
FLOW_ENGINE_VERSION = "2.0.0"

# TTLs (Time To Live)
CONVERSATION_TTL_SECONDS = 1800  # 30 minutos
ORDER_TTL_SECONDS = 7200  # 2 horas
SNAPSHOT_TTL_SECONDS = 86400  # 24 horas

# Dict de TTLs para ContextManager e Flow Engine V2
CONTEXT_TTL_SECONDS = {
    "conversation": CONVERSATION_TTL_SECONDS,
    "order": ORDER_TTL_SECONDS,
    "snapshot": SNAPSHOT_TTL_SECONDS,
}

# KPIs e metas de tempo de resposta (Flow Engine V2)
KPI_TARGETS = {
    "max_response_time_ms": 1000,
    "target_completion_rate": 0.85,
    "target_abandonment_rate": 0.15,
}

# Limites
MAX_RETRY_COUNT = 3
MAX_ITEMS_PER_ORDER = 10
MAX_MESSAGE_LENGTH = 4096

# Timeouts
NLU_TIMEOUT_MS = 500
LLM_TIMEOUT_MS = 3000


# ═══════════════════════════════════════════════════════════════════════
# MÉTRICAS E KPIs
# ═══════════════════════════════════════════════════════════════════════

# Metas do Flow Engine 2.0
TARGET_COMPLETION_RATE = 0.85  # 85%
TARGET_TIME_NEW_CUSTOMER = 90  # segundos
TARGET_TIME_RETURNING_CUSTOMER = 30  # segundos
TARGET_ABANDONMENT_RATE = 0.15  # 15%
TARGET_NPS = 4.5  # de 5.0

# Thresholds para alertas
ALERT_COMPLETION_RATE_THRESHOLD = 0.70  # < 70% dispara alerta
ALERT_RESPONSE_TIME_THRESHOLD = 3000  # > 3s dispara alerta
ALERT_ERROR_RATE_THRESHOLD = 0.05  # > 5% dispara alerta


# ═══════════════════════════════════════════════════════════════════════
# FEATURE FLAGS
# ═══════════════════════════════════════════════════════════════════════

FEATURE_FLAGS = {
    "flow_engine_v2_enabled": True,  # Master switch para v2.0
    "fast_track_enabled": True,  # Atalho com dados completos
    "repeat_order_enabled": True,  # Repetir último pedido
    "abandoned_order_recovery": True,  # Recuperar pedidos abandonados
    "faq_inline_enabled": True,  # FAQ sem sair do fluxo
    "llm_classification_enabled": True,  # Usar LLM para classificação
    "smart_suggestions_enabled": True,  # Sugestões baseadas em histórico
    "delivery_time_prediction": True,  # Previsão de tempo de entrega
}


# ═══════════════════════════════════════════════════════════════════════
# ROLLOUT GRADUAL
# ═══════════════════════════════════════════════════════════════════════

# Percentual de tráfego no v2.0 (0-100)
ROLLOUT_PERCENTAGE = 100  # Começar com 0%, aumentar gradualmente

# Critérios de rollback automático
ROLLBACK_CRITERIA = {
    "error_rate": 0.05,  # > 5% de erro
    "response_time_p95": 3000,  # > 3s no p95
    "completion_rate": 0.30,  # < 30% de conclusão
}


# ═══════════════════════════════════════════════════════════════════════
# MAPEAMENTOS DE COMPATIBILIDADE v1.0 → v2.0
# ═══════════════════════════════════════════════════════════════════════

STATE_MIGRATION_MAP = {
    # v1.0 → v2.0
    "start": "greeting_initial",
    "asking_customer_type": "identify_type",
    "collecting_name": "identify_name_pf",  # Assume PF por padrão
    "collecting_document": "identify_document_cpf",
    "awaiting_product": "ordering_product",
    "awaiting_quantity": "ordering_quantity",
    "confirming_address": "ordering_address_confirm",
    "awaiting_address": "ordering_address",
    "awaiting_payment": "checkout_payment",
    "processing_payment": "checkout_summary",
    "awaiting_pix": "checkout_payment",
    "confirming_order": "checkout_summary",
    "order_confirmed": "complete_confirmed",
    "tracking_order": "tracking_status",
    "talking_to_human": "support_human",
    "idle": "greeting_initial",
}


# ═══════════════════════════════════════════════════════════════════════
# ATALHOS E FAST-TRACKS
# ═══════════════════════════════════════════════════════════════════════

# Condições para fast-track (pular etapas)
FAST_TRACK_CONDITIONS = {
    "complete_order": {
        "required": ["product", "quantity", "address", "payment"],
        "target_state": "checkout_summary"
    },
    "repeat_order": {
        "required": ["last_order_exists"],
        "target_state": "ordering_confirm_repeat"
    },
    "known_customer": {
        "required": ["customer_id", "name", "address"],
        "skip_states": ["identify_type", "identify_name_pf", "ordering_address"]
    },
}


# ═══════════════════════════════════════════════════════════════════════
# TEMPLATES DE RESPOSTA RÁPIDA
# ═══════════════════════════════════════════════════════════════════════

QUICK_REPLIES = {
    "yes_no": [
        {"id": "sim", "text": "✅ Sim"},
        {"id": "nao", "text": "❌ Não"},
    ],
    "customer_type": [
        {"id": "PF", "text": "🧑 Pessoa Física"},
        {"id": "PJ", "text": "🏢 Empresa"},
    ],
    "operation_type": [
        {"id": "exchange", "text": "🔄 Troca"},
        {"id": "sale", "text": "🆕 Venda"},
        {"id": "pickup", "text": "🏪 Retira"},
    ],
    "payment_methods_pf": [
        {"id": "cash", "text": "💵 Dinheiro"},
        {"id": "credit_card", "text": "💳 Cartão"},
        {"id": "pix", "text": "📱 PIX"},
    ],
    "payment_methods_pj": [
        {"id": "cash", "text": "💵 Dinheiro"},
        {"id": "credit_card", "text": "💳 Cartão"},
        {"id": "pix", "text": "📱 PIX"},
        {"id": "invoice", "text": "📄 Faturado"},
    ],
    "main_menu": [
        {"id": "fazer_pedido", "text": "🛒 Fazer Pedido"},
        {"id": "ver_pedido", "text": "📦 Meus Pedidos"},
        {"id": "falar_atendente", "text": "👤 Atendente"},
    ],
    "order_actions": [
        {"id": "confirm", "text": "✅ Confirmar"},
        {"id": "edit", "text": "✏️ Alterar"},
        {"id": "cancel", "text": "❌ Cancelar"},
    ],
}


# ═══════════════════════════════════════════════════════════════════════
# VALIDAÇÕES
# ═══════════════════════════════════════════════════════════════════════

VALIDATION_RULES = {
    "cpf": {
        "pattern": r"^\d{11}$",
        "length": 11,
        "error_message": "CPF inválido. Digite os 11 números do CPF."
    },
    "cnpj": {
        "pattern": r"^\d{14}$",
        "length": 14,
        "error_message": "CNPJ inválido. Digite os 14 números do CNPJ."
    },
    "phone": {
        "pattern": r"^\d{10,11}$",
        "min_length": 10,
        "max_length": 11,
        "error_message": "Telefone inválido."
    },
    "address": {
        "min_length": 10,
        "max_length": 200,
        "error_message": "Endereço muito curto. Informe rua, número e bairro."
    },
    "quantity": {
        "min": 1,
        "max": 10,
        "error_message": "Quantidade deve ser entre 1 e 10."
    },
}


# ═══════════════════════════════════════════════════════════════════════
# MENSAGENS DE SISTEMA
# ═══════════════════════════════════════════════════════════════════════

SYSTEM_MESSAGES = {
    "maintenance": "🔧 Sistema em manutenção. Tente novamente em alguns minutos.",
    "error_generic": "Desculpe, ocorreu um erro. Por favor, tente novamente.",
    "timeout": "⏱️ Tempo esgotado. Digite *menu* para recomeçar.",
    "session_expired": "Sua sessão expirou. Digite *oi* para começar novamente.",
    "rate_limit": "Você está enviando mensagens muito rápido. Aguarde um momento.",
}


# ═══════════════════════════════════════════════════════════════════════
# CONFIGURAÇÕES DE LOGGING
# ═══════════════════════════════════════════════════════════════════════

LOG_LEVELS = {
    "flow_engine": "INFO",
    "nlu_engine": "INFO",
    "handlers": "INFO",
    "integrations": "WARNING",
}

# Eventos para logging estruturado
LOG_EVENTS = {
    "flow_start": "FLOW_ENGINE_START",
    "flow_complete": "FLOW_ENGINE_COMPLETE",
    "state_transition": "STATE_TRANSITION",
    "intent_detected": "INTENT_DETECTED",
    "entity_extracted": "ENTITY_EXTRACTED",
    "order_created": "ORDER_CREATED",
    "order_confirmed": "ORDER_CONFIRMED",
    "error": "ERROR",
}


# ═══════════════════════════════════════════════════════════════════════
# CONTATOS E INFORMAÇÕES
# ═══════════════════════════════════════════════════════════════════════

CONTACT_INFO = {
    "phone": "(41) 99999-9999",
    "pix_key": "(41) 99999-9999",
    "store_address": "Rua Principal, 1000 - Boqueirão",
    "emergency_number": "193",  # Corpo de Bombeiros
}


# ═══════════════════════════════════════════════════════════════════════
# FUNÇÕES AUXILIARES
# ═══════════════════════════════════════════════════════════════════════

def is_feature_enabled(feature_name: str) -> bool:
    """Verifica se uma feature está habilitada."""
    return FEATURE_FLAGS.get(feature_name, False)


def should_use_v2(phone: str) -> bool:
    """
    Determina se deve usar Flow Engine v2.0 para este usuário.
    Implementa rollout gradual baseado em hash do telefone.
    """
    if not is_feature_enabled("flow_engine_v2_enabled"):
        return False
    
    # Hash do telefone para distribuição consistente
    import hashlib
    phone_hash = int(hashlib.md5(phone.encode()).hexdigest(), 16)
    bucket = phone_hash % 100
    
    return bucket < ROLLOUT_PERCENTAGE


def get_quick_replies(category: str) -> List[Dict]:
    """Retorna quick replies para uma categoria."""
    return QUICK_REPLIES.get(category, [])


def validate_field(field_name: str, value: str) -> Tuple[bool, Optional[str]]:
    """
    Valida um campo baseado nas regras.
    
    Returns:
        Tuple[is_valid, error_message]
    """
    import re
    
    rules = VALIDATION_RULES.get(field_name)
    if not rules:
        return (True, None)
    
    # Validar padrão
    if "pattern" in rules:
        if not re.match(rules["pattern"], value):
            return (False, rules["error_message"])
    
    # Validar comprimento
    if "min_length" in rules and len(value) < rules["min_length"]:
        return (False, rules["error_message"])
    
    if "max_length" in rules and len(value) > rules["max_length"]:
        return (False, rules["error_message"])
    
    # Validar range numérico
    if "min" in rules or "max" in rules:
        try:
            num_value = int(value)
            if "min" in rules and num_value < rules["min"]:
                return (False, rules["error_message"])
            if "max" in rules and num_value > rules["max"]:
                return (False, rules["error_message"])
        except ValueError:
            return (False, rules["error_message"])
    
    return (True, None)
