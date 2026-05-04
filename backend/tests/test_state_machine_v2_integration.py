"""
Integration tests: state_machine v2 migration — admin debug returns v2 enum values.
"""
import pytest
from app.core.state_machine_v2 import ConversationState, StateTransition


class TestV2EnumExports:
    """Verify v2 ConversationState is accessible and has expected values."""

    def test_v2_has_25_plus_states(self):
        states = list(ConversationState)
        assert len(states) >= 25, f"Expected >=25 v2 states, got {len(states)}"

    def test_greeting_states_exist(self):
        assert ConversationState.GREETING_INITIAL
        assert ConversationState.GREETING_INITIAL.value == "greeting_initial"
        assert ConversationState.GREETING_RETURNING
        assert ConversationState.GREETING_RETURNING.value == "greeting_returning"

    def test_identify_states_exist(self):
        assert ConversationState.IDENTIFY_TYPE
        assert ConversationState.IDENTIFY_NAME_PF
        assert ConversationState.IDENTIFY_NAME_PJ
        assert ConversationState.IDENTIFY_DOCUMENT_CPF
        assert ConversationState.IDENTIFY_DOCUMENT_CNPJ

    def test_ordering_states_exist(self):
        assert ConversationState.ORDERING_PRODUCT
        assert ConversationState.ORDERING_QUANTITY
        assert ConversationState.ORDERING_OPERATION
        assert ConversationState.ORDERING_MORE_ITEMS
        assert ConversationState.ORDERING_ADDRESS
        assert ConversationState.ORDERING_ADDRESS_CONFIRM
        assert ConversationState.ORDERING_COMPLEMENT

    def test_checkout_states_exist(self):
        assert ConversationState.CHECKOUT_PAYMENT
        assert ConversationState.CHECKOUT_CHANGE
        assert ConversationState.CHECKOUT_SUMMARY

    def test_complete_states_exist(self):
        assert ConversationState.COMPLETE_CONFIRMED
        assert ConversationState.COMPLETE_FOLLOWUP

    def test_support_states_exist(self):
        assert ConversationState.SUPPORT_HUMAN
        assert ConversationState.SUPPORT_FAQ
        assert ConversationState.TRACKING_STATUS
        assert ConversationState.TRACKING_OPTIONS
        assert ConversationState.ERROR_RECOVERY

    def test_v2_state_values_are_snake_case(self):
        for state in ConversationState:
            value = state.value
            assert "_" in value or value == value.lower(), \
                f"State {state.name} has unexpected value: {value}"


class TestStateTransitionV2:
    """Verify v2 StateTransition works with v2 states."""

    def test_valid_transition_from_greeting(self):
        assert StateTransition.is_valid(
            ConversationState.GREETING_INITIAL,
            ConversationState.IDENTIFY_TYPE
        )
        assert StateTransition.is_valid(
            ConversationState.GREETING_INITIAL,
            ConversationState.ORDERING_PRODUCT
        )
        assert StateTransition.is_valid(
            ConversationState.GREETING_INITIAL,
            ConversationState.SUPPORT_HUMAN
        )

    def test_valid_transition_ordering(self):
        assert StateTransition.is_valid(
            ConversationState.ORDERING_PRODUCT,
            ConversationState.ORDERING_QUANTITY
        )

    def test_valid_transition_checkout(self):
        assert StateTransition.is_valid(
            ConversationState.CHECKOUT_PAYMENT,
            ConversationState.CHECKOUT_SUMMARY
        )

    def test_get_valid_transitions(self):
        transitions = StateTransition.get_valid_transitions(
            ConversationState.GREETING_INITIAL
        )
        assert len(transitions) > 0
        assert ConversationState.IDENTIFY_TYPE in transitions

    def test_no_v1_state_names(self):
        """Verify v1 state values are NOT present in the enum."""
        v1_values = [
            "start", "asking_customer_type", "collecting_name",
            "collecting_document", "awaiting_product", "awaiting_quantity",
            "confirming_address", "awaiting_address", "awaiting_payment",
            "processing_payment", "awaiting_pix", "confirming_order",
            "order_confirmed", "tracking_order", "talking_to_human", "idle",
        ]
        v2_values = {s.value for s in ConversationState}
        for v1_val in v1_values:
            assert v1_val not in v2_values, \
                f"v1 state value '{v1_val}' should not be in v2 ConversationState"
