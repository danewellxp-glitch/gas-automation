"""
Testes unitários para Checkout Handlers v2.
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
from app.core.handlers_v2.checkout_handlers import (
    CheckoutPaymentHandler,
    CheckoutChangeHandler,
    CheckoutSummaryHandler,
)


# ═══════════════════════════════════════════════════════════════
# CheckoutPaymentHandler
# ═══════════════════════════════════════════════════════════════


class TestCheckoutPaymentHandler:
    """Testes para CheckoutPaymentHandler."""

    @pytest.fixture
    def handler(self):
        return CheckoutPaymentHandler()

    @pytest.fixture
    def ctx(self):
        return ConversationContext(
            phone="5541999999999",
            current_state=ConversationState.CHECKOUT_PAYMENT,
        )

    @pytest.mark.asyncio
    async def test_cash_goes_to_change(self, handler, ctx, customer_context, order_context):
        """Dinheiro vai para CHECKOUT_CHANGE."""
        result = await handler.handle(
            message="dinheiro",
            conversation_context=ctx,
            customer_context=customer_context,
            order_context=order_context,
        )
        assert result.next_state == ConversationState.CHECKOUT_CHANGE
        assert result.order_context.payment_method == "cash"

    @pytest.mark.asyncio
    async def test_pix_goes_to_summary(self, handler, ctx, customer_context, order_context):
        """PIX vai para CHECKOUT_SUMMARY."""
        result = await handler.handle(
            message="pix",
            conversation_context=ctx,
            customer_context=customer_context,
            order_context=order_context,
        )
        assert result.next_state == ConversationState.CHECKOUT_SUMMARY
        assert result.order_context.payment_method == "pix"
        assert "PIX" in result.responses[0].text

    @pytest.mark.asyncio
    async def test_credit_card_goes_to_summary(
        self, handler, ctx, customer_context, order_context
    ):
        """Cartão de crédito vai para CHECKOUT_SUMMARY."""
        result = await handler.handle(
            message="cartão de crédito",
            conversation_context=ctx,
            customer_context=customer_context,
            order_context=order_context,
        )
        assert result.next_state == ConversationState.CHECKOUT_SUMMARY
        assert result.order_context.payment_method == "credit_card"

    @pytest.mark.asyncio
    async def test_debit_card_goes_to_summary(
        self, handler, ctx, customer_context, order_context
    ):
        """Cartão de débito vai para CHECKOUT_SUMMARY."""
        result = await handler.handle(
            message="débito",
            conversation_context=ctx,
            customer_context=customer_context,
            order_context=order_context,
        )
        assert result.next_state == ConversationState.CHECKOUT_SUMMARY
        assert result.order_context.payment_method == "debit_card"

    @pytest.mark.asyncio
    async def test_invoice_pj_goes_to_summary(
        self, handler, ctx, customer_context_pj, order_context
    ):
        """Boleto para PJ vai para CHECKOUT_SUMMARY."""
        result = await handler.handle(
            message="faturado",
            conversation_context=ctx,
            customer_context=customer_context_pj,
            order_context=order_context,
        )
        assert result.next_state == ConversationState.CHECKOUT_SUMMARY
        assert result.order_context.payment_method == "invoice"

    @pytest.mark.asyncio
    async def test_invoice_pf_rejected(
        self, handler, ctx, customer_context, order_context
    ):
        """Boleto para PF é rejeitado."""
        result = await handler.handle(
            message="faturado",
            conversation_context=ctx,
            customer_context=customer_context,
            order_context=order_context,
        )
        assert result.next_state == ConversationState.CHECKOUT_PAYMENT
        assert "não disponível" in result.responses[0].text.lower()

    @pytest.mark.asyncio
    async def test_not_understood_stays(self, handler, ctx, customer_context, order_context):
        """Mensagem não entendida permanece no estado."""
        result = await handler.handle(
            message="abcdef",
            conversation_context=ctx,
            customer_context=customer_context,
            order_context=order_context,
        )
        assert result.next_state == ConversationState.CHECKOUT_PAYMENT
        assert ctx.retry_count == 1

    @pytest.mark.asyncio
    async def test_cartao_defaults_to_credit(
        self, handler, ctx, customer_context, order_context
    ):
        """'cartão' sem especificar tipo default para credit_card."""
        result = await handler.handle(
            message="cartão",
            conversation_context=ctx,
            customer_context=customer_context,
            order_context=order_context,
        )
        assert result.order_context.payment_method == "credit_card"

    @pytest.mark.asyncio
    async def test_resets_retry_on_success(self, handler, customer_context, order_context):
        """Sucesso reseta retry."""
        ctx = ConversationContext(
            phone="5541999999999",
            current_state=ConversationState.CHECKOUT_PAYMENT,
            retry_count=2,
        )
        result = await handler.handle(
            message="pix",
            conversation_context=ctx,
            customer_context=customer_context,
            order_context=order_context,
        )
        assert ctx.retry_count == 0


# ═══════════════════════════════════════════════════════════════
# CheckoutChangeHandler
# ═══════════════════════════════════════════════════════════════


class TestCheckoutChangeHandler:
    """Testes para CheckoutChangeHandler."""

    @pytest.fixture
    def handler(self):
        return CheckoutChangeHandler()

    @pytest.fixture
    def ctx(self):
        return ConversationContext(
            phone="5541999999999",
            current_state=ConversationState.CHECKOUT_CHANGE,
        )

    @pytest.mark.asyncio
    async def test_no_change_goes_to_summary(self, handler, ctx):
        """Sem troco vai para CHECKOUT_SUMMARY."""
        result = await handler.handle(message="no_change", conversation_context=ctx)
        assert result.next_state == ConversationState.CHECKOUT_SUMMARY
        assert result.order_context.change_for is None

    @pytest.mark.asyncio
    async def test_no_change_synonyms(self, handler, ctx):
        """Sinônimos de sem troco."""
        for word in ["não", "nao", "n", "sem"]:
            result = await handler.handle(message=word, conversation_context=ctx)
            assert result.next_state == ConversationState.CHECKOUT_SUMMARY, f"Falhou para '{word}'"

    @pytest.mark.asyncio
    async def test_change_button_50(self, handler, ctx):
        """Botão change_50 define troco para R$ 50."""
        result = await handler.handle(message="change_50", conversation_context=ctx)
        assert result.next_state == ConversationState.CHECKOUT_SUMMARY
        assert result.order_context.change_for == 50.0

    @pytest.mark.asyncio
    async def test_change_button_100(self, handler, ctx):
        """Botão change_100 define troco para R$ 100."""
        result = await handler.handle(message="change_100", conversation_context=ctx)
        assert result.next_state == ConversationState.CHECKOUT_SUMMARY
        assert result.order_context.change_for == 100.0

    @pytest.mark.asyncio
    async def test_change_from_text(self, handler, ctx):
        """Extrair troco do texto."""
        result = await handler.handle(message="200", conversation_context=ctx)
        assert result.next_state == ConversationState.CHECKOUT_SUMMARY
        assert result.order_context.change_for == 200.0

    @pytest.mark.asyncio
    async def test_change_from_entities(self, handler, ctx):
        """Extrai troco das entidades."""
        result = await handler.handle(
            message="texto",
            conversation_context=ctx,
            entities={"change_for": 50.0},
        )
        assert result.next_state == ConversationState.CHECKOUT_SUMMARY
        assert result.order_context.change_for == 50.0

    @pytest.mark.asyncio
    async def test_invalid_change_value_stays(self, handler, ctx):
        """Valor inválido permanece no estado."""
        result = await handler.handle(message="abc", conversation_context=ctx)
        assert result.next_state == ConversationState.CHECKOUT_CHANGE

    @pytest.mark.asyncio
    async def test_change_saved_in_collected_data(self, handler, ctx):
        """Valor do troco é salvo em collected_data."""
        result = await handler.handle(message="change_100", conversation_context=ctx)
        assert ctx.collected_data["change_for"] == 100.0


# ═══════════════════════════════════════════════════════════════
# CheckoutSummaryHandler
# ═══════════════════════════════════════════════════════════════


class TestCheckoutSummaryHandler:
    """Testes para CheckoutSummaryHandler."""

    @pytest.fixture
    def handler(self):
        return CheckoutSummaryHandler()

    @pytest.fixture
    def ctx(self):
        return ConversationContext(
            phone="5541999999999",
            current_state=ConversationState.CHECKOUT_SUMMARY,
        )

    @pytest.mark.asyncio
    async def test_confirm_without_document_asks_cpf(
        self, handler, ctx
    ):
        """Confirmar sem documento pede CPF para PF."""
        cc = CustomerContext(customer_type="PF", name="João")
        result = await handler.handle(
            message="confirmar",
            conversation_context=ctx,
            customer_context=cc,
            order_context=OrderContext(),
        )
        assert result.next_state == ConversationState.IDENTIFY_DOCUMENT_CPF

    @pytest.mark.asyncio
    async def test_confirm_without_document_asks_cnpj(
        self, handler, ctx
    ):
        """Confirmar sem documento pede CNPJ para PJ."""
        cc = CustomerContext(customer_type="PJ", name="Empresa")
        result = await handler.handle(
            message="confirmar",
            conversation_context=ctx,
            customer_context=cc,
            order_context=OrderContext(),
        )
        assert result.next_state == ConversationState.IDENTIFY_DOCUMENT_CNPJ

    @pytest.mark.asyncio
    async def test_confirm_with_document_creates_order(
        self, handler, ctx, customer_context, order_context, mock_async_session
    ):
        """Confirmar com documento cria pedido."""
        # Mock _create_order
        mock_order = MagicMock()
        mock_order.id = "order-001"
        mock_order.order_number = "1001"
        mock_order.total_amount = Decimal("220.00")

        with patch.object(handler, "_create_order", new_callable=AsyncMock, return_value=mock_order):
            result = await handler.handle(
                message="confirmar",
                conversation_context=ctx,
                customer_context=customer_context,
                order_context=order_context,
            )
        assert result.next_state == ConversationState.COMPLETE_CONFIRMED
        assert "1001" in result.responses[0].text

    @pytest.mark.asyncio
    async def test_confirm_order_creation_fails(
        self, handler, ctx, customer_context, order_context
    ):
        """Falha ao criar pedido escala para humano."""
        with patch.object(handler, "_create_order", new_callable=AsyncMock, return_value=None):
            result = await handler.handle(
                message="confirmar",
                conversation_context=ctx,
                customer_context=customer_context,
                order_context=order_context,
            )
        assert result.next_state == ConversationState.SUPPORT_HUMAN
        assert result.needs_human is True
        assert result.success is False

    @pytest.mark.asyncio
    async def test_edit_shows_options(self, handler, ctx, customer_context, order_context):
        """Alterar mostra opções de edição."""
        result = await handler.handle(
            message="alterar",
            conversation_context=ctx,
            customer_context=customer_context,
            order_context=order_context,
        )
        assert result.next_state == ConversationState.CHECKOUT_SUMMARY
        buttons_ids = [b["id"] for b in result.responses[0].buttons]
        assert "edit_product" in buttons_ids
        assert "edit_address" in buttons_ids
        assert "edit_payment" in buttons_ids

    @pytest.mark.asyncio
    async def test_cancel_resets_context(self, handler, ctx, customer_context, order_context):
        """Cancelar reseta contextos e volta para GREETING_INITIAL."""
        result = await handler.handle(
            message="cancelar",
            conversation_context=ctx,
            customer_context=customer_context,
            order_context=order_context,
        )
        assert result.next_state == ConversationState.GREETING_INITIAL
        assert ctx.collected_data == {}
        assert result.order_context.items == []

    @pytest.mark.asyncio
    async def test_edit_product(self, handler, ctx, customer_context, order_context):
        """edit_product vai para ORDERING_PRODUCT."""
        result = await handler.handle(
            message="edit_product",
            conversation_context=ctx,
            customer_context=customer_context,
            order_context=order_context,
        )
        assert result.next_state == ConversationState.ORDERING_PRODUCT
        assert result.order_context.items == []

    @pytest.mark.asyncio
    async def test_edit_address(self, handler, ctx, customer_context, order_context):
        """edit_address vai para ORDERING_ADDRESS."""
        result = await handler.handle(
            message="edit_address",
            conversation_context=ctx,
            customer_context=customer_context,
            order_context=order_context,
        )
        assert result.next_state == ConversationState.ORDERING_ADDRESS
        assert result.order_context.address is None

    @pytest.mark.asyncio
    async def test_edit_payment(self, handler, ctx, customer_context, order_context):
        """edit_payment vai para CHECKOUT_PAYMENT."""
        result = await handler.handle(
            message="edit_payment",
            conversation_context=ctx,
            customer_context=customer_context,
            order_context=order_context,
        )
        assert result.next_state == ConversationState.CHECKOUT_PAYMENT
        assert result.order_context.payment_method is None

    @pytest.mark.asyncio
    async def test_show_summary_no_items(self, handler, ctx, customer_context):
        """Resumo sem itens vai para ORDERING_PRODUCT."""
        result = await handler.handle(
            message="resumo",
            conversation_context=ctx,
            customer_context=customer_context,
            order_context=OrderContext(),
        )
        assert result.next_state == ConversationState.ORDERING_PRODUCT

    @pytest.mark.asyncio
    async def test_show_summary_with_items(self, handler, ctx, customer_context, order_context):
        """Resumo com itens mostra detalhes."""
        result = await handler.handle(
            message="resumo",
            conversation_context=ctx,
            customer_context=customer_context,
            order_context=order_context,
        )
        assert result.next_state == ConversationState.CHECKOUT_SUMMARY
        text = result.responses[0].text
        assert "RESUMO" in text
        assert "P13" in text

    @pytest.mark.asyncio
    async def test_confirm_synonyms(self, handler, ctx, customer_context):
        """Sinônimos de confirmar funcionam."""
        cc = CustomerContext(customer_type="PF", name="João")
        for word in ["confirm", "sim", "s", "ok"]:
            result = await handler.handle(
                message=word,
                conversation_context=ctx,
                customer_context=cc,
                order_context=OrderContext(),
            )
            assert result.next_state == ConversationState.IDENTIFY_DOCUMENT_CPF, f"Falhou para '{word}'"
