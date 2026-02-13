"""
Testes unitários para Flow Config v2.
"""

import pytest

from app.core.flow_config import (
    FLOW_ENGINE_VERSION,
    MAX_RETRY_COUNT,
    MAX_ITEMS_PER_ORDER,
    CONVERSATION_TTL_SECONDS,
    ORDER_TTL_SECONDS,
    FEATURE_FLAGS,
    ROLLOUT_PERCENTAGE,
    QUICK_REPLIES,
    VALIDATION_RULES,
    STATE_MIGRATION_MAP,
    is_feature_enabled,
    should_use_v2,
    get_quick_replies,
    validate_field,
)


class TestFlowConfig:
    """Testes para configurações do Flow Engine."""

    def test_version(self):
        assert FLOW_ENGINE_VERSION == "2.0.0"

    def test_max_retry_count(self):
        assert MAX_RETRY_COUNT == 3

    def test_max_items_per_order(self):
        assert MAX_ITEMS_PER_ORDER == 10

    def test_conversation_ttl(self):
        assert CONVERSATION_TTL_SECONDS == 1800  # 30 min

    def test_order_ttl(self):
        assert ORDER_TTL_SECONDS == 7200  # 2h


class TestFeatureFlags:
    """Testes para feature flags."""

    def test_v2_enabled(self):
        assert is_feature_enabled("flow_engine_v2_enabled") is True

    def test_fast_track_enabled(self):
        assert is_feature_enabled("fast_track_enabled") is True

    def test_repeat_order_enabled(self):
        assert is_feature_enabled("repeat_order_enabled") is True

    def test_nonexistent_flag(self):
        assert is_feature_enabled("nonexistent") is False


class TestShouldUseV2:
    """Testes para should_use_v2."""

    def test_returns_bool(self):
        result = should_use_v2("5541999999999")
        assert isinstance(result, bool)

    def test_consistent_for_same_phone(self):
        """Mesmo telefone retorna mesmo resultado."""
        r1 = should_use_v2("5541999999999")
        r2 = should_use_v2("5541999999999")
        assert r1 == r2

    def test_with_100_percent_rollout(self):
        """Com 100% rollout, todos devem usar v2."""
        # ROLLOUT_PERCENTAGE = 100
        assert should_use_v2("5541999999999") is True
        assert should_use_v2("5541888888888") is True


class TestQuickReplies:
    """Testes para quick replies."""

    def test_customer_type_replies(self):
        replies = get_quick_replies("customer_type")
        assert len(replies) == 2
        ids = [r["id"] for r in replies]
        assert "PF" in ids
        assert "PJ" in ids

    def test_operation_type_replies(self):
        replies = get_quick_replies("operation_type")
        assert len(replies) == 3

    def test_payment_methods_pf(self):
        replies = get_quick_replies("payment_methods_pf")
        assert len(replies) == 3
        ids = [r["id"] for r in replies]
        assert "invoice" not in ids

    def test_payment_methods_pj(self):
        replies = get_quick_replies("payment_methods_pj")
        assert len(replies) == 4
        ids = [r["id"] for r in replies]
        assert "invoice" in ids

    def test_main_menu(self):
        replies = get_quick_replies("main_menu")
        assert len(replies) == 3

    def test_nonexistent_category(self):
        replies = get_quick_replies("nonexistent")
        assert replies == []


class TestValidateField:
    """Testes para validate_field."""

    def test_valid_cpf(self):
        is_valid, error = validate_field("cpf", "12345678901")
        assert is_valid is True
        assert error is None

    def test_invalid_cpf_short(self):
        is_valid, error = validate_field("cpf", "1234")
        assert is_valid is False
        assert error is not None

    def test_valid_cnpj(self):
        is_valid, error = validate_field("cnpj", "12345678000190")
        assert is_valid is True

    def test_invalid_cnpj(self):
        is_valid, error = validate_field("cnpj", "123")
        assert is_valid is False

    def test_valid_quantity(self):
        is_valid, error = validate_field("quantity", "5")
        assert is_valid is True

    def test_invalid_quantity_too_high(self):
        is_valid, error = validate_field("quantity", "15")
        assert is_valid is False

    def test_invalid_quantity_zero(self):
        is_valid, error = validate_field("quantity", "0")
        assert is_valid is False

    def test_unknown_field(self):
        is_valid, error = validate_field("unknown_field", "value")
        assert is_valid is True


class TestStateMigrationMap:
    """Testes para mapeamento v1 → v2."""

    def test_start_maps_to_greeting(self):
        assert STATE_MIGRATION_MAP["start"] == "greeting_initial"

    def test_awaiting_product_maps_to_ordering(self):
        assert STATE_MIGRATION_MAP["awaiting_product"] == "ordering_product"

    def test_all_v1_states_mapped(self):
        """Todos os estados v1 têm mapeamento."""
        v1_states = [
            "start", "asking_customer_type", "collecting_name",
            "collecting_document", "awaiting_product", "awaiting_quantity",
            "confirming_address", "awaiting_address", "awaiting_payment",
            "processing_payment", "awaiting_pix", "confirming_order",
            "order_confirmed", "tracking_order", "talking_to_human", "idle",
        ]
        for state in v1_states:
            assert state in STATE_MIGRATION_MAP, f"Faltando mapeamento para {state}"
