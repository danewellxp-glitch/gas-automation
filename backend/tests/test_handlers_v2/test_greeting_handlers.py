"""
Testes unitários para Greeting Handlers v2.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

from app.core.state_machine_v2 import (
    ConversationState,
    ConversationContext,
    CustomerContext,
    OrderContext,
)
from app.core.handlers_v2.greeting_handlers import (
    GreetingInitialHandler,
    GreetingReturningHandler,
)


# ═══════════════════════════════════════════════════════════════
# GreetingInitialHandler
# ═══════════════════════════════════════════════════════════════


class TestGreetingInitialHandler:
    """Testes para GreetingInitialHandler."""

    @pytest.fixture
    def handler(self):
        return GreetingInitialHandler()

    @pytest.mark.asyncio
    async def test_new_customer_goes_to_identify_type(
        self, handler, conversation_context, mock_db_no_customer
    ):
        """Cliente novo deve ir para IDENTIFY_TYPE."""
        result = await handler.handle(
            message="oi",
            conversation_context=conversation_context,
        )
        assert result.next_state == ConversationState.IDENTIFY_TYPE
        assert result.success is True
        assert len(result.responses) == 1
        assert "GasMaster" in result.responses[0].text
        assert result.responses[0].has_buttons()
        assert conversation_context.is_returning is False

    @pytest.mark.asyncio
    async def test_known_customer_with_last_order(
        self, handler, conversation_context, mock_db_customer, mock_db_last_order
    ):
        """Cliente conhecido com histórico deve ir para GREETING_RETURNING."""
        result = await handler.handle(
            message="oi",
            conversation_context=conversation_context,
        )
        assert result.next_state == ConversationState.GREETING_RETURNING
        assert conversation_context.is_returning is True
        assert result.customer_context is not None
        assert result.customer_context.last_order is not None
        # Deve oferecer botões de repetir/novo/rastrear
        assert result.responses[0].has_buttons()
        buttons_ids = [b["id"] for b in result.responses[0].buttons]
        assert "repeat_order" in buttons_ids
        assert "new_order" in buttons_ids
        assert "track_order" in buttons_ids

    @pytest.mark.asyncio
    async def test_known_customer_without_last_order(
        self, handler, conversation_context, mock_db_customer, mock_db_no_last_order
    ):
        """Cliente conhecido sem histórico vai para GREETING_RETURNING."""
        result = await handler.handle(
            message="oi",
            conversation_context=conversation_context,
        )
        assert result.next_state == ConversationState.GREETING_RETURNING
        assert conversation_context.is_returning is True
        assert "João Silva" in result.responses[0].text

    @pytest.mark.asyncio
    async def test_abandoned_order_recovery(
        self, handler, mock_db_customer, mock_db_no_last_order
    ):
        """Pedido abandonado deve oferecer continuar."""
        ctx = ConversationContext(
            phone="5541999999999",
            current_state=ConversationState.ORDERING_PRODUCT,
            resumed_from_snapshot=True,
        )
        result = await handler.handle(
            message="oi",
            conversation_context=ctx,
        )
        # Deve manter no estado recuperado
        assert result.next_state == ConversationState.ORDERING_PRODUCT
        buttons_ids = [b["id"] for b in result.responses[0].buttons]
        assert "continue_order" in buttons_ids
        assert "new_order" in buttons_ids

    @pytest.mark.asyncio
    async def test_new_customer_creates_empty_customer_context(
        self, handler, conversation_context, mock_db_no_customer
    ):
        """Cliente novo deve criar CustomerContext vazio."""
        result = await handler.handle(
            message="bom dia",
            conversation_context=conversation_context,
        )
        assert result.customer_context is not None
        assert result.customer_context.customer_id is None
        assert result.customer_context.name is None


# ═══════════════════════════════════════════════════════════════
# GreetingReturningHandler
# ═══════════════════════════════════════════════════════════════


class TestGreetingReturningHandler:
    """Testes para GreetingReturningHandler."""

    @pytest.fixture
    def handler(self):
        return GreetingReturningHandler()

    @pytest.fixture
    def returning_context(self):
        return ConversationContext(
            phone="5541999999999",
            current_state=ConversationState.GREETING_RETURNING,
            is_returning=True,
        )

    @pytest.mark.asyncio
    async def test_repeat_order_with_history(
        self, handler, returning_context, customer_context_with_last_order
    ):
        """Repetir pedido com histórico vai para ORDERING_CONFIRM_REPEAT."""
        result = await handler.handle(
            message="repetir",
            conversation_context=returning_context,
            customer_context=customer_context_with_last_order,
        )
        assert result.next_state == ConversationState.ORDERING_CONFIRM_REPEAT
        assert "Repetir" in result.responses[0].text or "repetir" in result.responses[0].text

    @pytest.mark.asyncio
    async def test_repeat_order_without_history(
        self, handler, returning_context, customer_context_new
    ):
        """Repetir pedido sem histórico vai para ORDERING_PRODUCT."""
        result = await handler.handle(
            message="repetir",
            conversation_context=returning_context,
            customer_context=customer_context_new,
        )
        assert result.next_state == ConversationState.ORDERING_PRODUCT

    @pytest.mark.asyncio
    async def test_new_order(self, handler, returning_context, customer_context):
        """Novo pedido vai para ORDERING_PRODUCT."""
        result = await handler.handle(
            message="new_order",
            conversation_context=returning_context,
            customer_context=customer_context,
        )
        assert result.next_state == ConversationState.ORDERING_PRODUCT

    @pytest.mark.asyncio
    async def test_track_order(self, handler, returning_context, customer_context):
        """Rastrear pedido vai para TRACKING_STATUS."""
        result = await handler.handle(
            message="track_order",
            conversation_context=returning_context,
            customer_context=customer_context,
        )
        assert result.next_state == ConversationState.TRACKING_STATUS

    @pytest.mark.asyncio
    async def test_continue_abandoned_order(
        self, handler, customer_context
    ):
        """Continuar pedido abandonado mantém estado atual."""
        ctx = ConversationContext(
            phone="5541999999999",
            current_state=ConversationState.ORDERING_ADDRESS,
            is_returning=True,
        )
        result = await handler.handle(
            message="continue_order",
            conversation_context=ctx,
            customer_context=customer_context,
        )
        assert result.next_state == ConversationState.ORDERING_ADDRESS

    @pytest.mark.asyncio
    async def test_not_understood_increments_retry(
        self, handler, returning_context, customer_context
    ):
        """Mensagem não entendida incrementa retry."""
        assert returning_context.retry_count == 0
        result = await handler.handle(
            message="mensagem aleatoria xyz",
            conversation_context=returning_context,
            customer_context=customer_context,
        )
        assert returning_context.retry_count == 1
        assert result.next_state == ConversationState.GREETING_RETURNING

    @pytest.mark.asyncio
    async def test_escalates_to_human_after_max_retries(
        self, handler, customer_context
    ):
        """Escala para humano após MAX_RETRY_COUNT tentativas."""
        ctx = ConversationContext(
            phone="5541999999999",
            current_state=ConversationState.GREETING_RETURNING,
            retry_count=2,  # MAX_RETRY_COUNT = 3
        )
        result = await handler.handle(
            message="xyz abc",
            conversation_context=ctx,
            customer_context=customer_context,
        )
        assert result.next_state == ConversationState.SUPPORT_HUMAN
        assert result.needs_human is True

    @pytest.mark.asyncio
    async def test_repeat_order_button_id(
        self, handler, returning_context, customer_context_with_last_order
    ):
        """Botão 'repeat_order' funciona."""
        result = await handler.handle(
            message="repeat_order",
            conversation_context=returning_context,
            customer_context=customer_context_with_last_order,
        )
        assert result.next_state == ConversationState.ORDERING_CONFIRM_REPEAT

    @pytest.mark.asyncio
    async def test_o_de_sempre(
        self, handler, returning_context, customer_context_with_last_order
    ):
        """'o de sempre' funciona como repeat."""
        result = await handler.handle(
            message="o de sempre",
            conversation_context=returning_context,
            customer_context=customer_context_with_last_order,
        )
        assert result.next_state == ConversationState.ORDERING_CONFIRM_REPEAT

    @pytest.mark.asyncio
    async def test_fazer_pedido_synonym(self, handler, returning_context, customer_context):
        """'fazer_pedido' funciona como new_order."""
        result = await handler.handle(
            message="fazer_pedido",
            conversation_context=returning_context,
            customer_context=customer_context,
        )
        assert result.next_state == ConversationState.ORDERING_PRODUCT
