"""
Testes unitários para Support Handlers v2.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.state_machine_v2 import (
    ConversationState,
    ConversationContext,
    CustomerContext,
    OrderContext,
)
from app.core.handlers_v2.support_handlers import (
    SupportHumanHandler,
    SupportFAQHandler,
    TrackingStatusHandler,
    TrackingOptionsHandler,
    ErrorRecoveryHandler,
)


# ═══════════════════════════════════════════════════════════════
# SupportHumanHandler
# ═══════════════════════════════════════════════════════════════


class TestSupportHumanHandler:
    """Testes para SupportHumanHandler."""

    @pytest.fixture
    def handler(self):
        return SupportHumanHandler()

    @pytest.fixture
    def ctx(self):
        return ConversationContext(
            phone="5541999999999",
            current_state=ConversationState.SUPPORT_HUMAN,
        )

    @pytest.mark.asyncio
    async def test_back_to_bot(self, handler, ctx):
        """'menu' volta para GREETING_INITIAL."""
        result = await handler.handle(message="menu", conversation_context=ctx)
        assert result.next_state == ConversationState.GREETING_INITIAL
        assert result.needs_human is not True

    @pytest.mark.asyncio
    async def test_back_synonyms(self, handler, ctx):
        """Sinônimos de voltar funcionam."""
        for word in ["bot", "voltar"]:
            result = await handler.handle(message=word, conversation_context=ctx)
            assert result.next_state == ConversationState.GREETING_INITIAL, f"Falhou para '{word}'"

    @pytest.mark.asyncio
    async def test_stays_in_human_mode(self, handler, ctx, customer_context):
        """Mensagens normais permanecem no atendimento humano."""
        with patch("app.api.websocket.emit_new_message", new_callable=AsyncMock):
            result = await handler.handle(
                message="preciso de ajuda com o pagamento",
                conversation_context=ctx,
                customer_context=customer_context,
            )
        assert result.next_state == ConversationState.SUPPORT_HUMAN
        assert result.needs_human is True

    @pytest.mark.asyncio
    async def test_notifies_operators_via_websocket(self, handler, ctx, customer_context):
        """Notifica operadores via WebSocket."""
        with patch("app.api.websocket.emit_new_message", new_callable=AsyncMock) as mock_emit:
            result = await handler.handle(
                message="ajuda",
                conversation_context=ctx,
                customer_context=customer_context,
            )
            mock_emit.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_error_doesnt_crash(self, handler, ctx):
        """Erro no WebSocket não causa crash."""
        with patch(
            "app.api.websocket.emit_new_message",
            new_callable=AsyncMock,
            side_effect=Exception("WS Error"),
        ):
            result = await handler.handle(
                message="ajuda",
                conversation_context=ctx,
            )
        assert result.next_state == ConversationState.SUPPORT_HUMAN
        assert result.needs_human is True


# ═══════════════════════════════════════════════════════════════
# SupportFAQHandler
# ═══════════════════════════════════════════════════════════════


class TestSupportFAQHandler:
    """Testes para SupportFAQHandler."""

    @pytest.fixture
    def handler(self):
        return SupportFAQHandler()

    @pytest.fixture
    def ctx_from_ordering(self):
        return ConversationContext(
            phone="5541999999999",
            current_state=ConversationState.SUPPORT_FAQ,
            return_state=ConversationState.ORDERING_PRODUCT,
        )

    @pytest.mark.asyncio
    async def test_faq_business_hours(self, handler, ctx_from_ordering):
        """Pergunta sobre horário retorna FAQ."""
        result = await handler.handle(
            message="qual o horário de vocês?",
            conversation_context=ctx_from_ordering,
        )
        assert result.next_state == ConversationState.ORDERING_PRODUCT
        assert "Horário" in result.responses[0].text or "horário" in result.responses[0].text

    @pytest.mark.asyncio
    async def test_faq_prices(self, handler, ctx_from_ordering):
        """Pergunta sobre preço retorna FAQ."""
        result = await handler.handle(
            message="quanto custa?",
            conversation_context=ctx_from_ordering,
        )
        assert result.next_state == ConversationState.ORDERING_PRODUCT
        assert "Preço" in result.responses[0].text or "P13" in result.responses[0].text

    @pytest.mark.asyncio
    async def test_faq_delivery_time(self, handler, ctx_from_ordering):
        """Pergunta sobre entrega retorna FAQ."""
        result = await handler.handle(
            message="quanto tempo demora a entrega?",
            conversation_context=ctx_from_ordering,
        )
        assert result.next_state == ConversationState.ORDERING_PRODUCT
        assert "Entrega" in result.responses[0].text or "min" in result.responses[0].text

    @pytest.mark.asyncio
    async def test_faq_coverage_area(self, handler, ctx_from_ordering):
        """Pergunta sobre área retorna FAQ."""
        result = await handler.handle(
            message="vocês entregam no meu bairro?",
            conversation_context=ctx_from_ordering,
        )
        assert result.next_state == ConversationState.ORDERING_PRODUCT

    @pytest.mark.asyncio
    async def test_faq_payment_methods(self, handler, ctx_from_ordering):
        """Pergunta sobre pagamento retorna FAQ."""
        result = await handler.handle(
            message="quais formas de pagamento?",
            conversation_context=ctx_from_ordering,
        )
        assert result.next_state == ConversationState.ORDERING_PRODUCT
        assert "Pagamento" in result.responses[0].text

    @pytest.mark.asyncio
    async def test_unknown_faq_returns_to_previous_state(self, handler, ctx_from_ordering):
        """Pergunta desconhecida retorna ao estado anterior."""
        result = await handler.handle(
            message="xyz abc def",
            conversation_context=ctx_from_ordering,
        )
        assert result.next_state == ConversationState.ORDERING_PRODUCT

    @pytest.mark.asyncio
    async def test_faq_without_return_state(self, handler):
        """FAQ sem return_state vai para GREETING_INITIAL."""
        ctx = ConversationContext(
            phone="5541999999999",
            current_state=ConversationState.SUPPORT_FAQ,
        )
        result = await handler.handle(
            message="xyz",
            conversation_context=ctx,
        )
        assert result.next_state == ConversationState.GREETING_INITIAL

    @pytest.mark.asyncio
    async def test_faq_adds_return_prompt(self, handler):
        """FAQ no meio do pedido adiciona prompt de retorno."""
        ctx = ConversationContext(
            phone="5541999999999",
            current_state=ConversationState.SUPPORT_FAQ,
            return_state=ConversationState.CHECKOUT_PAYMENT,
        )
        result = await handler.handle(
            message="qual o horário?",
            conversation_context=ctx,
        )
        assert "pagar" in result.responses[0].text.lower() or "Voltando" in result.responses[0].text


# ═══════════════════════════════════════════════════════════════
# TrackingStatusHandler
# ═══════════════════════════════════════════════════════════════


class TestTrackingStatusHandler:
    """Testes para TrackingStatusHandler."""

    @pytest.fixture
    def handler(self):
        return TrackingStatusHandler()

    @pytest.fixture
    def ctx(self):
        return ConversationContext(
            phone="5541999999999",
            current_state=ConversationState.TRACKING_STATUS,
        )

    @pytest.mark.asyncio
    async def test_no_customer_shows_no_orders(self, handler, ctx):
        """Sem cliente mostra mensagem sem pedidos."""
        result = await handler.handle(
            message="status",
            conversation_context=ctx,
        )
        assert result.next_state == ConversationState.GREETING_INITIAL

    @pytest.mark.asyncio
    async def test_no_customer_id_shows_no_orders(self, handler, ctx):
        """Cliente sem ID mostra mensagem sem pedidos."""
        result = await handler.handle(
            message="status",
            conversation_context=ctx,
            customer_context=CustomerContext(),
        )
        assert result.next_state == ConversationState.GREETING_INITIAL

    @pytest.mark.asyncio
    async def test_with_orders_shows_tracking(self, handler, ctx, customer_context, mock_async_session):
        """Com pedidos mostra tracking e vai para TRACKING_OPTIONS."""
        mock_order = MagicMock()
        mock_order.order_number = "1001"
        mock_order.status = "pending"
        mock_order.total_amount = 220.0

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_order]
        mock_result.scalars.return_value = mock_scalars
        mock_async_session.execute = AsyncMock(return_value=mock_result)

        result = await handler.handle(
            message="status",
            conversation_context=ctx,
            customer_context=customer_context,
        )
        assert result.next_state == ConversationState.TRACKING_OPTIONS
        assert "1001" in result.responses[0].text

    @pytest.mark.asyncio
    async def test_no_active_orders(self, handler, ctx, customer_context, mock_async_session):
        """Sem pedidos ativos mostra mensagem."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_async_session.execute = AsyncMock(return_value=mock_result)

        result = await handler.handle(
            message="status",
            conversation_context=ctx,
            customer_context=customer_context,
        )
        assert result.next_state == ConversationState.GREETING_INITIAL


# ═══════════════════════════════════════════════════════════════
# TrackingOptionsHandler
# ═══════════════════════════════════════════════════════════════


class TestTrackingOptionsHandler:
    """Testes para TrackingOptionsHandler."""

    @pytest.fixture
    def handler(self):
        return TrackingOptionsHandler()

    @pytest.fixture
    def ctx(self):
        return ConversationContext(
            phone="5541999999999",
            current_state=ConversationState.TRACKING_OPTIONS,
        )

    @pytest.mark.asyncio
    async def test_new_order(self, handler, ctx, customer_context):
        """Novo pedido vai para ORDERING_PRODUCT."""
        result = await handler.handle(
            message="new_order",
            conversation_context=ctx,
            customer_context=customer_context,
        )
        assert result.next_state == ConversationState.ORDERING_PRODUCT
        assert ctx.collected_data == {}

    @pytest.mark.asyncio
    async def test_menu(self, handler, ctx, customer_context):
        """Menu vai para GREETING_INITIAL."""
        result = await handler.handle(
            message="menu",
            conversation_context=ctx,
            customer_context=customer_context,
        )
        assert result.next_state == ConversationState.GREETING_INITIAL

    @pytest.mark.asyncio
    async def test_voltar(self, handler, ctx, customer_context):
        """'voltar' vai para GREETING_INITIAL."""
        result = await handler.handle(
            message="voltar",
            conversation_context=ctx,
            customer_context=customer_context,
        )
        assert result.next_state == ConversationState.GREETING_INITIAL

    @pytest.mark.asyncio
    async def test_not_understood_stays(self, handler, ctx, customer_context):
        """Mensagem desconhecida permanece."""
        result = await handler.handle(
            message="xyz",
            conversation_context=ctx,
            customer_context=customer_context,
        )
        assert result.next_state == ConversationState.TRACKING_OPTIONS


# ═══════════════════════════════════════════════════════════════
# ErrorRecoveryHandler
# ═══════════════════════════════════════════════════════════════


class TestErrorRecoveryHandler:
    """Testes para ErrorRecoveryHandler."""

    @pytest.fixture
    def handler(self):
        return ErrorRecoveryHandler()

    @pytest.fixture
    def ctx(self):
        return ConversationContext(
            phone="5541999999999",
            current_state=ConversationState.ERROR_RECOVERY,
            state_history=["ordering_product"],
        )

    @pytest.mark.asyncio
    async def test_retry_returns_to_previous_state(self, handler, ctx):
        """Retry volta ao estado anterior do histórico."""
        result = await handler.handle(message="retry", conversation_context=ctx)
        assert result.next_state == ConversationState.ORDERING_PRODUCT

    @pytest.mark.asyncio
    async def test_retry_synonyms(self, handler, ctx):
        """Sinônimos de retry funcionam."""
        for word in ["tentar", "sim", "s"]:
            ctx.state_history = ["ordering_product"]
            result = await handler.handle(message=word, conversation_context=ctx)
            assert result.next_state == ConversationState.ORDERING_PRODUCT, f"Falhou para '{word}'"

    @pytest.mark.asyncio
    async def test_restart_goes_to_greeting(self, handler, ctx):
        """Restart vai para GREETING_INITIAL."""
        result = await handler.handle(message="recomeçar", conversation_context=ctx)
        assert result.next_state == ConversationState.GREETING_INITIAL
        assert ctx.collected_data == {}
        assert ctx.state_history == []

    @pytest.mark.asyncio
    async def test_restart_synonyms(self, handler, ctx):
        """Sinônimos de restart funcionam."""
        for word in ["restart", "começar", "novo"]:
            ctx.state_history = ["ordering_product"]
            ctx.collected_data = {"key": "value"}
            result = await handler.handle(message=word, conversation_context=ctx)
            assert result.next_state == ConversationState.GREETING_INITIAL, f"Falhou para '{word}'"

    @pytest.mark.asyncio
    async def test_human_escalation(self, handler, ctx):
        """Escalar para humano."""
        result = await handler.handle(message="atendente", conversation_context=ctx)
        assert result.next_state == ConversationState.SUPPORT_HUMAN
        assert result.needs_human is True

    @pytest.mark.asyncio
    async def test_human_synonyms(self, handler, ctx):
        """Sinônimos de atendente funcionam."""
        for word in ["human", "ajuda"]:
            result = await handler.handle(message=word, conversation_context=ctx)
            assert result.next_state == ConversationState.SUPPORT_HUMAN, f"Falhou para '{word}'"

    @pytest.mark.asyncio
    async def test_not_understood_offers_options(self, handler, ctx):
        """Mensagem desconhecida oferece opções."""
        result = await handler.handle(message="xyz", conversation_context=ctx)
        assert result.next_state == ConversationState.ERROR_RECOVERY
        buttons_ids = [b["id"] for b in result.responses[0].buttons]
        assert "retry" in buttons_ids
        assert "restart" in buttons_ids
        assert "human" in buttons_ids
