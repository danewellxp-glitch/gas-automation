"""
Testes unitários para Complete Handlers v2.
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
from app.core.handlers_v2.complete_handlers import (
    CompleteConfirmedHandler,
    CompleteFollowupHandler,
)


# ═══════════════════════════════════════════════════════════════
# CompleteConfirmedHandler
# ═══════════════════════════════════════════════════════════════


class TestCompleteConfirmedHandler:
    """Testes para CompleteConfirmedHandler."""

    @pytest.fixture
    def handler(self):
        return CompleteConfirmedHandler()

    @pytest.fixture
    def ctx_with_order_id(self):
        ctx = ConversationContext(
            phone="5541999999999",
            current_state=ConversationState.COMPLETE_CONFIRMED,
        )
        ctx.collected_data["order_id"] = "order-001"
        return ctx

    @pytest.mark.asyncio
    async def test_no_order_id_goes_to_human(self, handler):
        """Sem order_id escala para humano."""
        ctx = ConversationContext(
            phone="5541999999999",
            current_state=ConversationState.COMPLETE_CONFIRMED,
        )
        result = await handler.handle(message="ok", conversation_context=ctx)
        assert result.next_state == ConversationState.SUPPORT_HUMAN
        assert result.needs_human is True

    @pytest.mark.asyncio
    async def test_order_found_goes_to_followup(
        self, handler, ctx_with_order_id, customer_context, order_context, mock_async_session
    ):
        """Pedido encontrado vai para COMPLETE_FOLLOWUP."""
        mock_order = MagicMock()
        mock_order.order_number = "1001"
        mock_order.total_amount = Decimal("220.00")
        mock_order.status = "pending"
        mock_order.created_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_order
        mock_async_session.execute = AsyncMock(return_value=mock_result)

        result = await handler.handle(
            message="ok",
            conversation_context=ctx_with_order_id,
            customer_context=customer_context,
            order_context=order_context,
        )
        assert result.next_state == ConversationState.COMPLETE_FOLLOWUP
        assert "1001" in result.responses[0].text

    @pytest.mark.asyncio
    async def test_order_not_found_goes_to_human(
        self, handler, ctx_with_order_id, mock_async_session
    ):
        """Pedido não encontrado escala para humano."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_session.execute = AsyncMock(return_value=mock_result)

        result = await handler.handle(
            message="ok",
            conversation_context=ctx_with_order_id,
        )
        assert result.next_state == ConversationState.SUPPORT_HUMAN
        assert result.needs_human is True

    @pytest.mark.asyncio
    async def test_increments_order_count(
        self, handler, ctx_with_order_id, customer_context, order_context, mock_async_session
    ):
        """Incrementa order_count do cliente."""
        mock_order = MagicMock()
        mock_order.order_number = "1001"
        mock_order.total_amount = Decimal("220.00")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_order
        mock_async_session.execute = AsyncMock(return_value=mock_result)

        initial_count = customer_context.order_count
        result = await handler.handle(
            message="ok",
            conversation_context=ctx_with_order_id,
            customer_context=customer_context,
            order_context=order_context,
        )
        assert customer_context.order_count == initial_count + 1


# ═══════════════════════════════════════════════════════════════
# CompleteFollowupHandler
# ═══════════════════════════════════════════════════════════════


class TestCompleteFollowupHandler:
    """Testes para CompleteFollowupHandler."""

    @pytest.fixture
    def handler(self):
        return CompleteFollowupHandler()

    @pytest.fixture
    def ctx(self):
        return ConversationContext(
            phone="5541999999999",
            current_state=ConversationState.COMPLETE_FOLLOWUP,
        )

    @pytest.mark.asyncio
    async def test_track_order(self, handler, ctx, customer_context):
        """Rastrear vai para TRACKING_STATUS."""
        result = await handler.handle(
            message="rastrear",
            conversation_context=ctx,
            customer_context=customer_context,
        )
        assert result.next_state == ConversationState.TRACKING_STATUS

    @pytest.mark.asyncio
    async def test_track_synonyms(self, handler, ctx, customer_context):
        """Sinônimos de rastrear funcionam."""
        for word in ["status", "pedido", "track"]:
            result = await handler.handle(
                message=word,
                conversation_context=ctx,
                customer_context=customer_context,
            )
            assert result.next_state == ConversationState.TRACKING_STATUS, f"Falhou para '{word}'"

    @pytest.mark.asyncio
    async def test_new_order(self, handler, ctx, customer_context):
        """Novo pedido vai para ORDERING_PRODUCT."""
        result = await handler.handle(
            message="novo pedido",
            conversation_context=ctx,
            customer_context=customer_context,
        )
        assert result.next_state == ConversationState.ORDERING_PRODUCT
        assert ctx.collected_data == {}

    @pytest.mark.asyncio
    async def test_new_order_synonyms(self, handler, ctx, customer_context):
        """Sinônimos de novo pedido."""
        for word in ["outro", "mais", "comprar"]:
            ctx.collected_data = {"old": "data"}
            result = await handler.handle(
                message=word,
                conversation_context=ctx,
                customer_context=customer_context,
            )
            assert result.next_state == ConversationState.ORDERING_PRODUCT, f"Falhou para '{word}'"

    @pytest.mark.asyncio
    async def test_unknown_message_shows_options(self, handler, ctx, customer_context):
        """Mensagem desconhecida oferece opções."""
        result = await handler.handle(
            message="xyz",
            conversation_context=ctx,
            customer_context=customer_context,
        )
        assert result.next_state == ConversationState.COMPLETE_FOLLOWUP
        assert result.responses[0].has_buttons()
        buttons_ids = [b["id"] for b in result.responses[0].buttons]
        assert "track_order" in buttons_ids
        assert "new_order" in buttons_ids
        assert "talk_human" in buttons_ids
