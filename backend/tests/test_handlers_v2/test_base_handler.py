"""
Testes unitários para BaseHandler e dataclasses base.
"""

import pytest
from decimal import Decimal

from app.core.state_machine_v2 import (
    ConversationState,
    ConversationContext,
    CustomerContext,
)
from app.core.handlers_v2.base import (
    BaseHandler,
    HandlerResult,
    MessageResponse,
)
from app.core.flow_config import MAX_RETRY_COUNT


# ═══════════════════════════════════════════════════════════════
# MessageResponse
# ═══════════════════════════════════════════════════════════════


class TestMessageResponse:
    """Testes para MessageResponse dataclass."""

    def test_text_only(self):
        resp = MessageResponse(text="Hello")
        assert resp.text == "Hello"
        assert resp.buttons is None
        assert resp.image_url is None
        assert resp.footer is None

    def test_with_buttons(self):
        resp = MessageResponse(
            text="Choose:",
            buttons=[{"id": "opt1", "text": "Option 1"}],
        )
        assert resp.has_buttons() is True

    def test_without_buttons(self):
        resp = MessageResponse(text="Hello")
        assert resp.has_buttons() is False

    def test_empty_buttons_list(self):
        resp = MessageResponse(text="Hello", buttons=[])
        assert resp.has_buttons() is False

    def test_with_image_url(self):
        resp = MessageResponse(text="Image", image_url="https://example.com/img.png")
        assert resp.image_url == "https://example.com/img.png"

    def test_with_footer(self):
        resp = MessageResponse(text="Text", footer="Footer text")
        assert resp.footer == "Footer text"


# ═══════════════════════════════════════════════════════════════
# HandlerResult
# ═══════════════════════════════════════════════════════════════


class TestHandlerResult:
    """Testes para HandlerResult dataclass."""

    def test_default_values(self):
        ctx = ConversationContext(phone="5541999999999")
        result = HandlerResult(conversation_context=ctx)
        assert result.success is True
        assert result.error is None
        assert result.needs_human is False
        assert result.should_save_snapshot is False
        assert result.responses == []
        assert result.next_state is None

    def test_responses_initialized_to_empty_list(self):
        ctx = ConversationContext(phone="5541999999999")
        result = HandlerResult(conversation_context=ctx)
        assert result.responses == []

    def test_with_responses(self):
        ctx = ConversationContext(phone="5541999999999")
        result = HandlerResult(
            conversation_context=ctx,
            responses=[MessageResponse(text="Test")],
            next_state=ConversationState.GREETING_RETURNING,
        )
        assert len(result.responses) == 1
        assert result.next_state == ConversationState.GREETING_RETURNING

    def test_error_result(self):
        ctx = ConversationContext(phone="5541999999999")
        result = HandlerResult(
            conversation_context=ctx,
            success=False,
            error="Something went wrong",
            needs_human=True,
        )
        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.needs_human is True


# ═══════════════════════════════════════════════════════════════
# BaseHandler helpers
# ═══════════════════════════════════════════════════════════════


class ConcreteHandler(BaseHandler):
    """Handler concreto para testar métodos do BaseHandler."""

    async def handle(self, message, conversation_context, **kwargs):
        pass


class TestBaseHandlerHelpers:
    """Testes para métodos auxiliares do BaseHandler."""

    @pytest.fixture
    def handler(self):
        return ConcreteHandler()

    def test_create_response(self, handler):
        resp = handler._create_response(text="Hello")
        assert isinstance(resp, MessageResponse)
        assert resp.text == "Hello"

    def test_create_response_with_buttons(self, handler):
        resp = handler._create_response(
            text="Choose",
            buttons=[{"id": "1", "text": "One"}],
        )
        assert resp.has_buttons()

    def test_create_result(self, handler):
        ctx = ConversationContext(phone="5541999999999")
        resp = handler._create_response(text="Test")
        result = handler._create_result(
            conversation_context=ctx,
            responses=[resp],
            next_state=ConversationState.GREETING_RETURNING,
        )
        assert isinstance(result, HandlerResult)
        assert result.next_state == ConversationState.GREETING_RETURNING

    def test_format_currency(self, handler):
        result = handler._format_currency(Decimal("110.00"))
        assert "R$" in result
        assert "110" in result

    def test_format_currency_thousands(self, handler):
        result = handler._format_currency(Decimal("1234.56"))
        assert "R$" in result
        assert "1.234,56" in result

    def test_format_address_full(self, handler):
        address = {"full_address": "Rua das Flores, 123 - Boqueirão"}
        result = handler._format_address(address)
        assert result == "Rua das Flores, 123 - Boqueirão"

    def test_format_address_parts(self, handler):
        address = {
            "street": "Rua A",
            "number": "100",
            "bairro": "Centro",
        }
        result = handler._format_address(address)
        assert "Rua A" in result
        assert "100" in result
        assert "Centro" in result

    def test_format_address_none(self, handler):
        result = handler._format_address(None)
        assert result == "Endereço não informado"

    def test_format_address_empty(self, handler):
        result = handler._format_address({})
        assert result == "Endereço cadastrado"

    def test_increment_retry(self, handler):
        ctx = ConversationContext(phone="5541999999999")
        assert ctx.retry_count == 0
        handler._increment_retry(ctx)
        assert ctx.retry_count == 1
        handler._increment_retry(ctx)
        assert ctx.retry_count == 2

    def test_reset_retry(self, handler):
        ctx = ConversationContext(phone="5541999999999", retry_count=5)
        # Manualmente setar retry_count (o campo não aceita no construtor por default_factory)
        ctx.retry_count = 5
        handler._reset_retry(ctx)
        assert ctx.retry_count == 0

    def test_should_escalate_false(self, handler):
        ctx = ConversationContext(phone="5541999999999")
        ctx.retry_count = 0
        assert handler._should_escalate_to_human(ctx) is False

    def test_should_escalate_at_max(self, handler):
        ctx = ConversationContext(phone="5541999999999")
        ctx.retry_count = MAX_RETRY_COUNT
        assert handler._should_escalate_to_human(ctx) is True

    def test_should_escalate_above_max(self, handler):
        ctx = ConversationContext(phone="5541999999999")
        ctx.retry_count = MAX_RETRY_COUNT + 1
        assert handler._should_escalate_to_human(ctx) is True

    def test_validate_cpf_valid(self, handler):
        # CPF válido: 529.982.247-25
        assert handler._validate_cpf("52998224725") is True

    def test_validate_cpf_invalid_all_same(self, handler):
        assert handler._validate_cpf("11111111111") is False

    def test_validate_cpf_invalid_length(self, handler):
        assert handler._validate_cpf("123") is False

    def test_validate_cpf_invalid_check_digits(self, handler):
        assert handler._validate_cpf("12345678900") is False

    def test_validate_cnpj_valid(self, handler):
        assert handler._validate_cnpj("12345678000190") is True

    def test_validate_cnpj_invalid_length(self, handler):
        assert handler._validate_cnpj("123") is False

    def test_validate_cnpj_invalid_all_same(self, handler):
        assert handler._validate_cnpj("11111111111111") is False
