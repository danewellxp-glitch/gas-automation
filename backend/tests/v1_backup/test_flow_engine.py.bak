"""
Testes unitários do Flow Engine.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.core.state_machine import ConversationState, ConversationContext, StateTransition
from app.core.flow_engine import FlowEngine, MessageResponse, ProcessedMessage
from app.core.business_rules import BusinessRules
from app.core.nlp_utils import Intention, detect_intention


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
        """Testa transição não mapeada: executa com warning, retorna False."""
        context = ConversationContext(phone="5541999999999")
        assert not context.transition_to(ConversationState.ORDER_CONFIRMED)
        # Transição ocorre mesmo assim (safety net) mas retorna False
        assert context.state == ConversationState.ORDER_CONFIRMED


class TestBusinessRules:
    """Testes para BusinessRules."""

    @pytest.mark.asyncio
    async def test_get_product(self, db_session):
        """Testa obtenção de produto."""
        from decimal import Decimal
        from app.models.product import Product

        db_session.add(Product(code="P13", name="Botijão P13 - 13kg", weight_kg=Decimal("13.00"), price=Decimal("110.00")))
        await db_session.commit()

        product = await BusinessRules.get_product("P13", db_session)
        assert product is not None
        assert product.code == "P13"
        assert float(product.price) == 110.00

    @pytest.mark.asyncio
    async def test_get_product_case_insensitive(self, db_session):
        """Testa busca de produto case insensitive."""
        from decimal import Decimal
        from app.models.product import Product

        db_session.add(Product(code="P13", name="Botijão P13 - 13kg", weight_kg=Decimal("13.00"), price=Decimal("110.00")))
        await db_session.commit()

        product = await BusinessRules.get_product("p13", db_session)
        assert product is not None
        assert product.code == "P13"

    @pytest.mark.asyncio
    async def test_get_product_invalid(self, db_session):
        """Testa produto inválido."""
        product = await BusinessRules.get_product("INVALID", db_session)
        assert product is None

    @pytest.mark.asyncio
    async def test_list_products(self, db_session):
        """Testa listagem de produtos."""
        from decimal import Decimal
        from app.models.product import Product

        db_session.add_all([
            Product(code="P13", name="Botijão P13 - 13kg", weight_kg=Decimal("13.00"), price=Decimal("110.00")),
            Product(code="P20", name="Botijão P20 - 20kg", weight_kg=Decimal("20.00"), price=Decimal("150.00")),
            Product(code="P45", name="Botijão P45 - 45kg", weight_kg=Decimal("45.00"), price=Decimal("280.00")),
        ])
        await db_session.commit()

        products = await BusinessRules.list_products(db_session)
        assert len(products) == 3
        codes = [p.code for p in products]
        assert "P13" in codes
        assert "P20" in codes
        assert "P45" in codes

    @pytest.mark.asyncio
    async def test_calculate_order(self, db_session):
        """Testa cálculo de pedido."""
        from decimal import Decimal
        from app.models.product import Product

        db_session.add(Product(code="P13", name="Botijão P13 - 13kg", weight_kg=Decimal("13.00"), price=Decimal("110.00")))
        await db_session.commit()

        calc = await BusinessRules.calculate_order("P13", 2, db_session, "Centro")
        assert calc is not None
        assert calc.quantity == 2
        assert float(calc.unit_price) == 110.00
        assert float(calc.subtotal) == 220.00
        assert float(calc.total) >= 220.00  # Pode ter taxa de entrega

    @pytest.mark.asyncio
    async def test_calculate_order_invalid_product(self, db_session):
        """Testa cálculo com produto inválido."""
        calc = await BusinessRules.calculate_order("INVALID", 1, db_session)
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
        """Testa comando global 'menu' via NLP."""
        engine = FlowEngine()
        context = ConversationContext(phone="5541999999999")
        context.state = ConversationState.AWAITING_PAYMENT

        result = await engine._check_global_commands_nlp(context, "menu", Intention.MENU)

        assert result is not None
        assert result.new_state == ConversationState.START
        assert len(result.responses) > 0

    @pytest.mark.asyncio
    async def test_global_command_ajuda(self):
        """Testa comando global 'ajuda' via NLP."""
        engine = FlowEngine()
        context = ConversationContext(phone="5541999999999")

        result = await engine._check_global_commands_nlp(context, "ajuda", Intention.HELP)

        assert result is not None
        assert "ajuda" in result.responses[0].text.lower()

    def test_global_command_atendente_intention(self):
        """Testa que 'atendente' é detectado como intenção HUMAN pelo NLP."""
        intention = detect_intention("atendente")
        assert intention == Intention.HUMAN

    @pytest.mark.asyncio
    async def test_global_command_cancelar(self):
        """Testa comando global 'cancelar' via NLP."""
        engine = FlowEngine()
        context = ConversationContext(phone="5541999999999")
        context.order_id = "123"

        result = await engine._check_global_commands_nlp(context, "cancelar", Intention.CANCEL)

        assert result is not None
        assert result.context.order_id is None
