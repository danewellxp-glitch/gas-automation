"""
Testes unitários para State Machine v2.
"""

import pytest
from datetime import datetime

from app.core.state_machine_v2 import (
    ConversationState,
    StateTransition,
    ConversationContext,
    CustomerContext,
    OrderContext,
)


# ═══════════════════════════════════════════════════════════════
# ConversationState
# ═══════════════════════════════════════════════════════════════


class TestConversationState:
    """Testes para ConversationState enum."""

    def test_total_states_is_25(self):
        """Devem existir 25 estados."""
        assert len(ConversationState) == 25

    def test_greeting_states(self):
        """Fase GREETING tem 2 estados."""
        greeting_states = [s for s in ConversationState if s.value.startswith("greeting_")]
        assert len(greeting_states) == 2

    def test_identify_states(self):
        """Fase IDENTIFY tem 5 estados."""
        identify_states = [s for s in ConversationState if s.value.startswith("identify_")]
        assert len(identify_states) == 5

    def test_ordering_states(self):
        """Fase ORDERING tem 8 estados."""
        ordering_states = [s for s in ConversationState if s.value.startswith("ordering_")]
        assert len(ordering_states) == 8

    def test_checkout_states(self):
        """Fase CHECKOUT tem 3 estados."""
        checkout_states = [s for s in ConversationState if s.value.startswith("checkout_")]
        assert len(checkout_states) == 3

    def test_complete_states(self):
        """Fase COMPLETE tem 2 estados."""
        complete_states = [s for s in ConversationState if s.value.startswith("complete_")]
        assert len(complete_states) == 2

    def test_support_states(self):
        """Fase SUPPORT tem 5 estados (support_, tracking_, error_)."""
        support_states = [
            s for s in ConversationState
            if s.value.startswith(("support_", "tracking_", "error_"))
        ]
        assert len(support_states) == 5

    def test_state_values_are_strings(self):
        """Valores dos estados são strings."""
        for state in ConversationState:
            assert isinstance(state.value, str)

    def test_states_are_unique(self):
        """Valores dos estados são únicos."""
        values = [s.value for s in ConversationState]
        assert len(values) == len(set(values))


# ═══════════════════════════════════════════════════════════════
# StateTransition
# ═══════════════════════════════════════════════════════════════


class TestStateTransition:
    """Testes para StateTransition."""

    def test_all_states_have_transitions(self):
        """Todos os estados devem ter transições definidas."""
        for state in ConversationState:
            assert state in StateTransition.VALID_TRANSITIONS, f"Faltando: {state}"

    def test_valid_transition_greeting_to_identify(self):
        """GREETING_INITIAL pode ir para IDENTIFY_TYPE."""
        assert StateTransition.is_valid(
            ConversationState.GREETING_INITIAL,
            ConversationState.IDENTIFY_TYPE,
        )

    def test_valid_transition_greeting_to_returning(self):
        """GREETING_INITIAL pode ir para GREETING_RETURNING."""
        assert StateTransition.is_valid(
            ConversationState.GREETING_INITIAL,
            ConversationState.GREETING_RETURNING,
        )

    def test_valid_transition_identify_to_name(self):
        """IDENTIFY_TYPE pode ir para IDENTIFY_NAME_PF."""
        assert StateTransition.is_valid(
            ConversationState.IDENTIFY_TYPE,
            ConversationState.IDENTIFY_NAME_PF,
        )

    def test_valid_transition_checkout_to_complete(self):
        """CHECKOUT_SUMMARY pode ir para COMPLETE_CONFIRMED."""
        assert StateTransition.is_valid(
            ConversationState.CHECKOUT_SUMMARY,
            ConversationState.COMPLETE_CONFIRMED,
        )

    def test_invalid_transition(self):
        """Transição inválida retorna False."""
        assert not StateTransition.is_valid(
            ConversationState.COMPLETE_CONFIRMED,
            ConversationState.IDENTIFY_TYPE,
        )

    def test_get_valid_transitions(self):
        """get_valid_transitions retorna lista de estados."""
        transitions = StateTransition.get_valid_transitions(
            ConversationState.GREETING_INITIAL
        )
        assert isinstance(transitions, list)
        assert ConversationState.IDENTIFY_TYPE in transitions

    def test_greeting_initial_transitions(self):
        """GREETING_INITIAL tem 6 transições."""
        transitions = StateTransition.get_valid_transitions(
            ConversationState.GREETING_INITIAL
        )
        assert len(transitions) == 6

    def test_ordering_product_can_go_to_faq(self):
        """ORDERING_PRODUCT pode ir para SUPPORT_FAQ."""
        assert StateTransition.is_valid(
            ConversationState.ORDERING_PRODUCT,
            ConversationState.SUPPORT_FAQ,
        )

    def test_error_recovery_can_restart(self):
        """ERROR_RECOVERY pode ir para GREETING_INITIAL."""
        assert StateTransition.is_valid(
            ConversationState.ERROR_RECOVERY,
            ConversationState.GREETING_INITIAL,
        )

    def test_error_recovery_can_go_to_human(self):
        """ERROR_RECOVERY pode ir para SUPPORT_HUMAN."""
        assert StateTransition.is_valid(
            ConversationState.ERROR_RECOVERY,
            ConversationState.SUPPORT_HUMAN,
        )


# ═══════════════════════════════════════════════════════════════
# ConversationContext
# ═══════════════════════════════════════════════════════════════


class TestConversationContext:
    """Testes para ConversationContext dataclass."""

    def test_default_state_is_greeting_initial(self):
        """Estado padrão é GREETING_INITIAL."""
        ctx = ConversationContext(phone="5541999999999")
        assert ctx.current_state == ConversationState.GREETING_INITIAL

    def test_default_values(self):
        """Valores padrão estão corretos."""
        ctx = ConversationContext(phone="5541999999999")
        assert ctx.retry_count == 0
        assert ctx.message_count == 0
        assert ctx.is_returning is False
        assert ctx.needs_human is False
        assert ctx.collected_data == {}
        assert ctx.state_history == []
        assert ctx.return_state is None

    def test_phone_is_required(self):
        """phone é campo obrigatório."""
        ctx = ConversationContext(phone="5541999999999")
        assert ctx.phone == "5541999999999"

    def test_collected_data_is_mutable(self):
        """collected_data pode ser modificado."""
        ctx = ConversationContext(phone="5541999999999")
        ctx.collected_data["product"] = "P13"
        assert ctx.collected_data["product"] == "P13"


# ═══════════════════════════════════════════════════════════════
# CustomerContext
# ═══════════════════════════════════════════════════════════════


class TestCustomerContext:
    """Testes para CustomerContext dataclass."""

    def test_default_values(self):
        """Valores padrão estão corretos."""
        ctx = CustomerContext()
        assert ctx.customer_id is None
        assert ctx.name is None
        assert ctx.document is None
        assert ctx.customer_type is None
        assert ctx.addresses == []
        assert ctx.order_count == 0
        assert ctx.is_vip is False
        assert ctx.last_order is None

    def test_addresses_default_empty_list(self):
        """addresses padrão é lista vazia."""
        ctx = CustomerContext()
        assert ctx.addresses == []

    def test_preferences_default_empty_dict(self):
        """preferences padrão é dict vazio."""
        ctx = CustomerContext()
        assert ctx.preferences == {}


# ═══════════════════════════════════════════════════════════════
# OrderContext
# ═══════════════════════════════════════════════════════════════


class TestOrderContext:
    """Testes para OrderContext dataclass."""

    def test_default_values(self):
        """Valores padrão estão corretos."""
        ctx = OrderContext()
        assert ctx.items == []
        assert ctx.subtotal == 0.0
        assert ctx.delivery_fee == 0.0
        assert ctx.total == 0.0
        assert ctx.address is None
        assert ctx.complement is None
        assert ctx.operation_type is None
        assert ctx.payment_method is None
        assert ctx.change_for is None

    def test_items_mutable(self):
        """items pode ser modificado."""
        ctx = OrderContext()
        ctx.items.append({"product_code": "P13", "quantity": 1})
        assert len(ctx.items) == 1

    def test_validation_errors_default_empty(self):
        """validation_errors padrão é lista vazia."""
        ctx = OrderContext()
        assert ctx.validation_errors == []
