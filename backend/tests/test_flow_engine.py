"""
Testes unitários do Flow Engine.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.core.state_machine import ConversationState, ConversationContext, StateTransition
from app.core.flow_engine import FlowEngine, MessageResponse, ProcessedMessage
from app.core.business_rules import BusinessRules


class TestConversationState:
    """Testes para ConversationState."""

    def test_states_exist(self):
        """Verifica se todos os estados existem."""
        assert ConversationState.START
        assert ConversationState.AWAITING_PRODUCT
        assert ConversationState.AWAITING_QUANTITY
        assert ConversationState.CONFIRMING_ADDRESS
        assert ConversationState.AWAITING_ADDRESS
        assert ConversationState.AWAITING_PAYMENT
        assert ConversationState.AWAITING_PIX
        assert ConversationState.ORDER_CONFIRMED
        assert ConversationState.TRACKING_ORDER
        assert ConversationState.TALKING_TO_HUMAN

    def test_state_values(self):
        """Verifica valores dos estados."""
        assert ConversationState.START.value == "start"
        assert ConversationState.AWAITING_PRODUCT.value == "awaiting_product"


class TestStateTransition:
    """Testes para StateTransition."""

    def test_valid_transition_from_start(self):
        """Testa transições válidas a partir de START."""
        assert StateTransition.is_valid(
            ConversationState.START,
            ConversationState.AWAITING_PRODUCT
        )
        assert StateTransition.is_valid(
            ConversationState.START,
            ConversationState.TRACKING_ORDER
        )
        assert StateTransition.is_valid(
            ConversationState.START,
            ConversationState.TALKING_TO_HUMAN
        )

    def test_invalid_transition(self):
        """Testa transição inválida."""
        assert not StateTransition.is_valid(
            ConversationState.START,
            ConversationState.ORDER_CONFIRMED
        )

    def test_get_valid_transitions(self):
        """Testa obtenção de transições válidas."""
        transitions = StateTransition.get_valid_transitions(ConversationState.START)
        assert ConversationState.AWAITING_PRODUCT in transitions
        assert ConversationState.TRACKING_ORDER in transitions


class TestConversationContext:
    """Testes para ConversationContext."""

    def test_create_context(self):
        """Testa criação de contexto."""
        context = ConversationContext(phone="5541999999999")
        assert context.phone == "5541999999999"
        assert context.state == ConversationState.START
        assert context.message_count == 0

    def test_to_dict(self):
        """Testa conversão para dicionário."""
        context = ConversationContext(phone="5541999999999")
        context.selected_product = "P13"
        context.selected_quantity = 2

        data = context.to_dict()
        assert data["phone"] == "5541999999999"
        assert data["selected_product"] == "P13"
        assert data["selected_quantity"] == 2

    def test_from_dict(self):
        """Testa criação a partir de dicionário."""
        data = {
            "phone": "5541999999999",
            "state": "awaiting_product",
            "selected_product": "P13",
            "selected_quantity": 2,
            "message_count": 5,
        }
        context = ConversationContext.from_dict(data)
        assert context.phone == "5541999999999"
        assert context.state == ConversationState.AWAITING_PRODUCT
        assert context.selected_product == "P13"

    def test_reset(self):
        """Testa reset do contexto."""
        context = ConversationContext(phone="5541999999999")
        context.state = ConversationState.AWAITING_PAYMENT
        context.selected_product = "P13"
        context.order_id = "123"

        context.reset()

        assert context.state == ConversationState.START
        assert context.selected_product is None
        assert context.order_id is None

    def test_transition_to_valid(self):
        """Testa transição válida."""
        context = ConversationContext(phone="5541999999999")
        assert context.transition_to(ConversationState.AWAITING_PRODUCT)
        assert context.state == ConversationState.AWAITING_PRODUCT

    def test_transition_to_invalid(self):
        """Testa transição inválida."""
        context = ConversationContext(phone="5541999999999")
        assert not context.transition_to(ConversationState.ORDER_CONFIRMED)
        assert context.state == ConversationState.START


class TestBusinessRules:
    """Testes para BusinessRules."""

    def test_get_product(self):
        """Testa obtenção de produto."""
        product = BusinessRules.get_product("P13")
        assert product is not None
        assert product.code == "P13"
        assert product.price == 110.00

    def test_get_product_case_insensitive(self):
        """Testa busca de produto case insensitive."""
        product = BusinessRules.get_product("p13")
        assert product is not None
        assert product.code == "P13"

    def test_get_product_invalid(self):
        """Testa produto inválido."""
        product = BusinessRules.get_product("INVALID")
        assert product is None

    def test_list_products(self):
        """Testa listagem de produtos."""
        products = BusinessRules.list_products()
        assert len(products) == 3
        codes = [p.code for p in products]
        assert "P13" in codes
        assert "P20" in codes
        assert "P45" in codes

    def test_calculate_order(self):
        """Testa cálculo de pedido."""
        calc = BusinessRules.calculate_order("P13", 2, "Centro")
        assert calc is not None
        assert calc.quantity == 2
        assert calc.unit_price == 110.00
        assert calc.subtotal == 220.00
        assert calc.total >= 220.00  # Pode ter taxa de entrega

    def test_calculate_order_invalid_product(self):
        """Testa cálculo com produto inválido."""
        calc = BusinessRules.calculate_order("INVALID", 1)
        assert calc is None

    def test_validate_quantity_valid(self):
        """Testa validação de quantidade válida."""
        valid, msg = BusinessRules.validate_quantity(1)
        assert valid
        assert msg == ""

        valid, msg = BusinessRules.validate_quantity(5)
        assert valid

    def test_validate_quantity_invalid(self):
        """Testa validação de quantidade inválida."""
        valid, msg = BusinessRules.validate_quantity(0)
        assert not valid
        assert "mínima" in msg.lower()

        valid, msg = BusinessRules.validate_quantity(100)
        assert not valid
        assert "máxima" in msg.lower()

    def test_validate_payment_method(self):
        """Testa validação de método de pagamento."""
        valid, _ = BusinessRules.validate_payment_method("pix")
        assert valid

        valid, _ = BusinessRules.validate_payment_method("dinheiro")
        assert valid

        valid, msg = BusinessRules.validate_payment_method("bitcoin")
        assert not valid

    def test_format_currency(self):
        """Testa formatação de moeda."""
        from decimal import Decimal
        result = BusinessRules.format_currency(Decimal("110.00"))
        assert "110" in result
        assert "R$" in result


class TestMessageResponse:
    """Testes para MessageResponse."""

    def test_create_response(self):
        """Testa criação de resposta."""
        response = MessageResponse(text="Olá!")
        assert response.text == "Olá!"
        assert response.buttons is None
        assert not response.has_buttons()

    def test_response_with_buttons(self):
        """Testa resposta com botões."""
        response = MessageResponse(
            text="Escolha:",
            buttons=[{"id": "1", "text": "Opção 1"}]
        )
        assert response.has_buttons()
        assert len(response.buttons) == 1


class TestFlowEngine:
    """Testes para FlowEngine."""

    def test_create_engine(self):
        """Testa criação do engine."""
        engine = FlowEngine()
        assert engine._handlers is not None
        assert len(engine._handlers) > 0

    def test_handlers_registered(self):
        """Testa se handlers estão registrados."""
        engine = FlowEngine()
        assert ConversationState.START in engine._handlers
        assert ConversationState.AWAITING_PRODUCT in engine._handlers
        assert ConversationState.AWAITING_QUANTITY in engine._handlers

    @pytest.mark.asyncio
    async def test_global_command_menu(self):
        """Testa comando global 'menu'."""
        engine = FlowEngine()
        context = ConversationContext(phone="5541999999999")
        context.state = ConversationState.AWAITING_PAYMENT

        result = await engine._check_global_commands(context, "menu")

        assert result is not None
        assert result.context.state == ConversationState.START
        assert len(result.responses) > 0

    @pytest.mark.asyncio
    async def test_global_command_ajuda(self):
        """Testa comando global 'ajuda'."""
        engine = FlowEngine()
        context = ConversationContext(phone="5541999999999")

        result = await engine._check_global_commands(context, "ajuda")

        assert result is not None
        assert "ajuda" in result.responses[0].text.lower()

    @pytest.mark.asyncio
    async def test_global_command_atendente(self):
        """Testa comando global 'atendente'."""
        engine = FlowEngine()
        context = ConversationContext(phone="5541999999999")

        result = await engine._check_global_commands(context, "atendente")

        assert result is not None
        assert result.new_state == ConversationState.TALKING_TO_HUMAN

    @pytest.mark.asyncio
    async def test_global_command_cancelar(self):
        """Testa comando global 'cancelar'."""
        engine = FlowEngine()
        context = ConversationContext(phone="5541999999999")
        context.order_id = "123"

        result = await engine._check_global_commands(context, "cancelar")

        assert result is not None
        assert result.context.order_id is None
