"""
Handler Registry - Mapeamento de Estados para Handlers
Centraliza o registro de todos os handlers do Flow Engine 2.0.

Baseado em: GASMASTER_FLOW_ENGINE_2.0_COMPLETO.md - Parte 6
"""

import logging
from typing import Dict

from app.core.state_machine_v2 import ConversationState
from app.core.handlers_v2.base import BaseHandler
from app.core.handlers_v2 import (
    # GREETING
    GreetingInitialHandler,
    GreetingReturningHandler,
    
    # IDENTIFY
    IdentifyTypeHandler,
    IdentifyNamePFHandler,
    IdentifyNamePJHandler,
    IdentifyDocumentCPFHandler,
    IdentifyDocumentCNPJHandler,
    
    # ORDERING
    OrderingProductHandler,
    OrderingQuantityHandler,
    OrderingOperationHandler,
    OrderingMoreItemsHandler,
    OrderingAddressHandler,
    OrderingAddressConfirmHandler,
    OrderingComplementHandler,
    OrderingConfirmRepeatHandler,
    
    # CHECKOUT
    CheckoutPaymentHandler,
    CheckoutChangeHandler,
    CheckoutSummaryHandler,
    
    # COMPLETE
    CompleteConfirmedHandler,
    CompleteFollowupHandler,
    
    # SUPPORT
    SupportHumanHandler,
    SupportFAQHandler,
    TrackingStatusHandler,
    TrackingOptionsHandler,
    ErrorRecoveryHandler,
)

logger = logging.getLogger(__name__)


def create_handler_registry() -> Dict[ConversationState, BaseHandler]:
    """
    Cria e retorna o registro completo de handlers.
    
    Mapeia cada ConversationState para seu handler correspondente.
    
    Returns:
        Dicionário {ConversationState: BaseHandler}
    """
    
    registry = {
        # ═══════════════════════════════════════════════════════════════════
        # FASE 1: GREETING (2 handlers)
        # ═══════════════════════════════════════════════════════════════════
        ConversationState.GREETING_INITIAL: GreetingInitialHandler(),
        ConversationState.GREETING_RETURNING: GreetingReturningHandler(),
        
        # ═══════════════════════════════════════════════════════════════════
        # FASE 2: IDENTIFY (5 handlers)
        # ═══════════════════════════════════════════════════════════════════
        ConversationState.IDENTIFY_TYPE: IdentifyTypeHandler(),
        ConversationState.IDENTIFY_NAME_PF: IdentifyNamePFHandler(),
        ConversationState.IDENTIFY_NAME_PJ: IdentifyNamePJHandler(),
        ConversationState.IDENTIFY_DOCUMENT_CPF: IdentifyDocumentCPFHandler(),
        ConversationState.IDENTIFY_DOCUMENT_CNPJ: IdentifyDocumentCNPJHandler(),
        
        # ═══════════════════════════════════════════════════════════════════
        # FASE 3: ORDERING (8 handlers)
        # ═══════════════════════════════════════════════════════════════════
        ConversationState.ORDERING_PRODUCT: OrderingProductHandler(),
        ConversationState.ORDERING_QUANTITY: OrderingQuantityHandler(),
        ConversationState.ORDERING_OPERATION: OrderingOperationHandler(),
        ConversationState.ORDERING_MORE_ITEMS: OrderingMoreItemsHandler(),
        ConversationState.ORDERING_ADDRESS: OrderingAddressHandler(),
        ConversationState.ORDERING_ADDRESS_CONFIRM: OrderingAddressConfirmHandler(),
        ConversationState.ORDERING_COMPLEMENT: OrderingComplementHandler(),
        ConversationState.ORDERING_CONFIRM_REPEAT: OrderingConfirmRepeatHandler(),
        
        # ═══════════════════════════════════════════════════════════════════
        # FASE 4: CHECKOUT (3 handlers)
        # ═══════════════════════════════════════════════════════════════════
        ConversationState.CHECKOUT_PAYMENT: CheckoutPaymentHandler(),
        ConversationState.CHECKOUT_CHANGE: CheckoutChangeHandler(),
        ConversationState.CHECKOUT_SUMMARY: CheckoutSummaryHandler(),
        
        # ═══════════════════════════════════════════════════════════════════
        # FASE 5: COMPLETE (2 handlers)
        # ═══════════════════════════════════════════════════════════════════
        ConversationState.COMPLETE_CONFIRMED: CompleteConfirmedHandler(),
        ConversationState.COMPLETE_FOLLOWUP: CompleteFollowupHandler(),
        
        # ═══════════════════════════════════════════════════════════════════
        # SUPPORT (5 handlers - paralelos)
        # ═══════════════════════════════════════════════════════════════════
        ConversationState.SUPPORT_HUMAN: SupportHumanHandler(),
        ConversationState.SUPPORT_FAQ: SupportFAQHandler(),
        ConversationState.TRACKING_STATUS: TrackingStatusHandler(),
        ConversationState.TRACKING_OPTIONS: TrackingOptionsHandler(),
        ConversationState.ERROR_RECOVERY: ErrorRecoveryHandler(),
    }
    
    # Validar que todos os estados têm handlers
    missing_states = []
    for state in ConversationState:
        if state not in registry:
            missing_states.append(state.value)
    
    if missing_states:
        logger.warning(
            f"Estados sem handlers registrados: {', '.join(missing_states)}"
        )
    
    logger.info(f"HandlerRegistry criado com {len(registry)} handlers")
    
    return registry


def get_handler_for_state(
    state: ConversationState,
    registry: Dict[ConversationState, BaseHandler]
) -> BaseHandler:
    """
    Obtém handler para um estado específico.
    
    Args:
        state: Estado da conversa
        registry: Registro de handlers
    
    Returns:
        Handler correspondente
    
    Raises:
        ValueError: Se handler não encontrado
    """
    handler = registry.get(state)
    
    if not handler:
        logger.error(f"Handler não encontrado para estado: {state.value}")
        raise ValueError(f"Handler não encontrado: {state.value}")
    
    return handler


def list_all_handlers(
    registry: Dict[ConversationState, BaseHandler]
) -> Dict[str, str]:
    """
    Lista todos os handlers registrados.
    
    Args:
        registry: Registro de handlers
    
    Returns:
        Dicionário {estado: nome_do_handler}
    """
    return {
        state.value: handler.__class__.__name__
        for state, handler in registry.items()
    }


def get_handlers_by_phase(
    registry: Dict[ConversationState, BaseHandler]
) -> Dict[str, Dict[str, str]]:
    """
    Agrupa handlers por fase conversacional.
    
    Args:
        registry: Registro de handlers
    
    Returns:
        Dicionário {fase: {estado: handler}}
    """
    phases = {
        "GREETING": {},
        "IDENTIFY": {},
        "ORDERING": {},
        "CHECKOUT": {},
        "COMPLETE": {},
        "SUPPORT": {},
    }
    
    for state, handler in registry.items():
        state_name = state.value
        handler_name = handler.__class__.__name__
        
        if state_name.startswith("greeting"):
            phases["GREETING"][state_name] = handler_name
        elif state_name.startswith("identify"):
            phases["IDENTIFY"][state_name] = handler_name
        elif state_name.startswith("ordering"):
            phases["ORDERING"][state_name] = handler_name
        elif state_name.startswith("checkout"):
            phases["CHECKOUT"][state_name] = handler_name
        elif state_name.startswith("complete"):
            phases["COMPLETE"][state_name] = handler_name
        elif state_name.startswith("support") or state_name.startswith("tracking") or state_name.startswith("error"):
            phases["SUPPORT"][state_name] = handler_name
    
    return phases


# Singleton do registry
_HANDLER_REGISTRY: Dict[ConversationState, BaseHandler] = None


def get_handler_registry() -> Dict[ConversationState, BaseHandler]:
    """
    Obtém instância singleton do handler registry.
    
    Returns:
        Handler registry
    """
    global _HANDLER_REGISTRY
    
    if _HANDLER_REGISTRY is None:
        _HANDLER_REGISTRY = create_handler_registry()
    
    return _HANDLER_REGISTRY
