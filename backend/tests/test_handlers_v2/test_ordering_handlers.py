"""
Testes unitários para Ordering Handlers v2.
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.core.state_machine_v2 import (
    ConversationState,
    ConversationContext,
    CustomerContext,
    OrderContext,
)
from app.core.handlers_v2.ordering_handlers import (
    OrderingProductHandler,
    OrderingQuantityHandler,
    OrderingOperationHandler,
    OrderingMoreItemsHandler,
    OrderingAddressHandler,
    OrderingAddressConfirmHandler,
    OrderingComplementHandler,
    OrderingConfirmRepeatHandler,
)


# ═══════════════════════════════════════════════════════════════
# OrderingProductHandler
# ═══════════════════════════════════════════════════════════════


class TestOrderingProductHandler:
    """Testes para OrderingProductHandler."""

    @pytest.fixture
    def handler(self):
        return OrderingProductHandler()

    @pytest.fixture
    def ctx(self):
        return ConversationContext(
            phone="5541999999999",
            current_state=ConversationState.ORDERING_PRODUCT,
        )

    @pytest.mark.asyncio
    async def test_select_p13_by_code(self, handler, ctx):
        """Selecionar P13 vai para ORDERING_QUANTITY."""
        result = await handler.handle(message="P13", conversation_context=ctx)
        assert result.next_state == ConversationState.ORDERING_QUANTITY
        assert ctx.collected_data["product_code"] == "P13"
        assert "P13" in result.responses[0].text or "Botijão" in result.responses[0].text

    @pytest.mark.asyncio
    async def test_select_p20_by_code(self, handler, ctx):
        """Selecionar P20 vai para ORDERING_QUANTITY."""
        result = await handler.handle(message="quero p20", conversation_context=ctx)
        assert result.next_state == ConversationState.ORDERING_QUANTITY
        assert ctx.collected_data["product_code"] == "P20"

    @pytest.mark.asyncio
    async def test_select_p45_by_code(self, handler, ctx):
        """Selecionar P45 vai para ORDERING_QUANTITY."""
        result = await handler.handle(message="p45", conversation_context=ctx)
        assert result.next_state == ConversationState.ORDERING_QUANTITY
        assert ctx.collected_data["product_code"] == "P45"

    @pytest.mark.asyncio
    async def test_select_by_option_number_1(self, handler, ctx):
        """Opção '1' mapeia para P13."""
        result = await handler.handle(message="1", conversation_context=ctx)
        assert result.next_state == ConversationState.ORDERING_QUANTITY
        assert ctx.collected_data["product_code"] == "P13"

    @pytest.mark.asyncio
    async def test_select_by_option_number_2(self, handler, ctx):
        """Opção '2' mapeia para P20."""
        result = await handler.handle(message="2", conversation_context=ctx)
        assert result.next_state == ConversationState.ORDERING_QUANTITY
        assert ctx.collected_data["product_code"] == "P20"

    @pytest.mark.asyncio
    async def test_select_by_option_number_3(self, handler, ctx):
        """Opção '3' mapeia para P45."""
        result = await handler.handle(message="3", conversation_context=ctx)
        assert result.next_state == ConversationState.ORDERING_QUANTITY
        assert ctx.collected_data["product_code"] == "P45"

    @pytest.mark.asyncio
    async def test_select_from_entities(self, handler, ctx):
        """Extrai produto das entidades NLU."""
        result = await handler.handle(
            message="qualquer coisa",
            conversation_context=ctx,
            entities={"product": "P13"},
        )
        assert result.next_state == ConversationState.ORDERING_QUANTITY
        assert ctx.collected_data["product_code"] == "P13"

    @pytest.mark.asyncio
    async def test_not_understood_shows_product_list(self, handler, ctx):
        """Mensagem não entendida mostra lista de produtos."""
        result = await handler.handle(message="abcdef", conversation_context=ctx)
        assert result.next_state == ConversationState.ORDERING_PRODUCT
        assert ctx.retry_count == 1
        text = result.responses[0].text
        assert "P13" in text or result.responses[0].has_buttons()

    @pytest.mark.asyncio
    async def test_escalates_after_max_retries(self, handler):
        """Escala para humano após MAX_RETRY_COUNT."""
        ctx = ConversationContext(
            phone="5541999999999",
            current_state=ConversationState.ORDERING_PRODUCT,
            retry_count=2,
        )
        result = await handler.handle(message="xyz", conversation_context=ctx)
        assert result.next_state == ConversationState.SUPPORT_HUMAN
        assert result.needs_human is True

    @pytest.mark.asyncio
    async def test_resets_retry_on_success(self, handler):
        """Seleção válida reseta retry_count."""
        ctx = ConversationContext(
            phone="5541999999999",
            current_state=ConversationState.ORDERING_PRODUCT,
            retry_count=2,
        )
        result = await handler.handle(message="P13", conversation_context=ctx)
        assert ctx.retry_count == 0

    @pytest.mark.asyncio
    async def test_creates_order_context_if_none(self, handler, ctx):
        """Cria OrderContext se não existe."""
        result = await handler.handle(
            message="P13", conversation_context=ctx, order_context=None
        )
        assert result.order_context is not None


# ═══════════════════════════════════════════════════════════════
# OrderingQuantityHandler
# ═══════════════════════════════════════════════════════════════


class TestOrderingQuantityHandler:
    """Testes para OrderingQuantityHandler."""

    @pytest.fixture
    def handler(self):
        return OrderingQuantityHandler()

    @pytest.fixture
    def ctx(self):
        ctx = ConversationContext(
            phone="5541999999999",
            current_state=ConversationState.ORDERING_QUANTITY,
        )
        ctx.collected_data["product_code"] = "P13"
        return ctx

    @pytest.mark.asyncio
    async def test_valid_quantity_number(self, handler, ctx):
        """Quantidade numérica válida vai para ORDERING_OPERATION."""
        result = await handler.handle(message="2", conversation_context=ctx)
        assert result.next_state == ConversationState.ORDERING_OPERATION
        assert ctx.collected_data["quantity"] == 2

    @pytest.mark.asyncio
    async def test_button_qty_1(self, handler, ctx):
        """Botão qty_1 mapeia para quantidade 1."""
        result = await handler.handle(message="qty_1", conversation_context=ctx)
        assert result.next_state == ConversationState.ORDERING_OPERATION
        assert ctx.collected_data["quantity"] == 1

    @pytest.mark.asyncio
    async def test_button_qty_3(self, handler, ctx):
        """Botão qty_3 mapeia para quantidade 3."""
        result = await handler.handle(message="qty_3", conversation_context=ctx)
        assert result.next_state == ConversationState.ORDERING_OPERATION
        assert ctx.collected_data["quantity"] == 3

    @pytest.mark.asyncio
    async def test_quantity_from_entities(self, handler, ctx):
        """Extrai quantidade das entidades."""
        result = await handler.handle(
            message="texto",
            conversation_context=ctx,
            entities={"quantity": 5},
        )
        assert result.next_state == ConversationState.ORDERING_OPERATION
        assert ctx.collected_data["quantity"] == 5

    @pytest.mark.asyncio
    async def test_invalid_quantity_zero(self, handler, ctx):
        """Quantidade 0 permanece no estado."""
        result = await handler.handle(message="0", conversation_context=ctx)
        assert result.next_state == ConversationState.ORDERING_QUANTITY
        assert ctx.retry_count == 1

    @pytest.mark.asyncio
    async def test_invalid_quantity_too_high(self, handler, ctx):
        """Quantidade > 10 permanece no estado."""
        result = await handler.handle(message="15", conversation_context=ctx)
        assert result.next_state == ConversationState.ORDERING_QUANTITY

    @pytest.mark.asyncio
    async def test_invalid_quantity_text(self, handler, ctx):
        """Texto sem número permanece no estado."""
        result = await handler.handle(message="muitos", conversation_context=ctx)
        assert result.next_state == ConversationState.ORDERING_QUANTITY

    @pytest.mark.asyncio
    async def test_resets_retry_on_success(self, handler):
        """Quantidade válida reseta retry."""
        ctx = ConversationContext(
            phone="5541999999999",
            current_state=ConversationState.ORDERING_QUANTITY,
            retry_count=2,
        )
        ctx.collected_data["product_code"] = "P13"
        result = await handler.handle(message="3", conversation_context=ctx)
        assert ctx.retry_count == 0


# ═══════════════════════════════════════════════════════════════
# OrderingOperationHandler
# ═══════════════════════════════════════════════════════════════


class TestOrderingOperationHandler:
    """Testes para OrderingOperationHandler."""

    @pytest.fixture
    def handler(self):
        return OrderingOperationHandler()

    @pytest.fixture
    def ctx(self):
        ctx = ConversationContext(
            phone="5541999999999",
            current_state=ConversationState.ORDERING_OPERATION,
        )
        ctx.collected_data["product_code"] = "P13"
        ctx.collected_data["quantity"] = 2
        return ctx

    @pytest.mark.asyncio
    async def test_exchange_operation(self, handler, ctx):
        """Troca vai para ORDERING_MORE_ITEMS."""
        result = await handler.handle(message="troca", conversation_context=ctx)
        assert result.next_state == ConversationState.ORDERING_MORE_ITEMS
        assert result.order_context.operation_type == "exchange"
        assert len(result.order_context.items) == 1
        assert result.order_context.items[0]["product_code"] == "P13"
        assert result.order_context.items[0]["quantity"] == 2
        assert result.order_context.items[0]["operation_type"] == "exchange"

    @pytest.mark.asyncio
    async def test_sale_operation(self, handler, ctx):
        """Venda vai para ORDERING_MORE_ITEMS com preço de venda."""
        result = await handler.handle(message="comprar", conversation_context=ctx)
        assert result.next_state == ConversationState.ORDERING_MORE_ITEMS
        assert result.order_context.operation_type == "sale"
        # P13 sale = R$ 110 (site GÁSMASTER), qty 2 = R$ 220
        assert result.order_context.items[0]["unit_price"] == 110.0
        assert result.order_context.items[0]["subtotal"] == 220.0

    @pytest.mark.asyncio
    async def test_pickup_operation(self, handler, ctx):
        """Retira vai para ORDERING_MORE_ITEMS."""
        result = await handler.handle(message="retira", conversation_context=ctx)
        assert result.next_state == ConversationState.ORDERING_MORE_ITEMS
        assert result.order_context.operation_type == "pickup"

    @pytest.mark.asyncio
    async def test_not_understood(self, handler, ctx):
        """Operação não entendida permanece no estado."""
        result = await handler.handle(message="abcdef", conversation_context=ctx)
        assert result.next_state == ConversationState.ORDERING_OPERATION
        assert ctx.retry_count == 1

    @pytest.mark.asyncio
    async def test_exchange_price_for_exchange(self, handler, ctx):
        """Preço de troca para operação exchange."""
        result = await handler.handle(message="trocar", conversation_context=ctx)
        # P13 exchange = R$ 110, qty 2 = R$ 220
        assert result.order_context.items[0]["unit_price"] == 110.0
        assert result.order_context.subtotal == 220.0


# ═══════════════════════════════════════════════════════════════
# OrderingMoreItemsHandler
# ═══════════════════════════════════════════════════════════════


class TestOrderingMoreItemsHandler:
    """Testes para OrderingMoreItemsHandler."""

    @pytest.fixture
    def handler(self):
        return OrderingMoreItemsHandler()

    @pytest.fixture
    def ctx(self):
        ctx = ConversationContext(
            phone="5541999999999",
            current_state=ConversationState.ORDERING_MORE_ITEMS,
        )
        ctx.collected_data["product_code"] = "P13"
        ctx.collected_data["quantity"] = 1
        return ctx

    @pytest.mark.asyncio
    async def test_add_more_goes_to_product(self, handler, ctx, order_context):
        """Adicionar mais vai para ORDERING_PRODUCT."""
        result = await handler.handle(
            message="add_more",
            conversation_context=ctx,
            order_context=order_context,
        )
        assert result.next_state == ConversationState.ORDERING_PRODUCT
        # Limpa dados do produto anterior
        assert "product_code" not in ctx.collected_data
        assert "quantity" not in ctx.collected_data

    @pytest.mark.asyncio
    async def test_add_more_synonyms(self, handler, ctx, order_context):
        """Sinônimos de 'sim' funcionam."""
        for word in ["sim", "s", "adicionar", "mais"]:
            ctx.collected_data["product_code"] = "P13"
            ctx.collected_data["quantity"] = 1
            result = await handler.handle(
                message=word,
                conversation_context=ctx,
                order_context=order_context,
            )
            assert result.next_state == ConversationState.ORDERING_PRODUCT, f"Falhou para '{word}'"

    @pytest.mark.asyncio
    async def test_finalize_pickup_goes_to_payment(self, handler, ctx):
        """Finalizar com pickup vai para CHECKOUT_PAYMENT."""
        oc = OrderContext(operation_type="pickup")
        result = await handler.handle(
            message="finalizar",
            conversation_context=ctx,
            order_context=oc,
        )
        assert result.next_state == ConversationState.CHECKOUT_PAYMENT

    @pytest.mark.asyncio
    async def test_finalize_delivery_with_address(
        self, handler, ctx, customer_context
    ):
        """Finalizar delivery com endereço vai para ORDERING_ADDRESS_CONFIRM."""
        oc = OrderContext(operation_type="exchange")
        result = await handler.handle(
            message="finalize",
            conversation_context=ctx,
            customer_context=customer_context,
            order_context=oc,
        )
        assert result.next_state == ConversationState.ORDERING_ADDRESS_CONFIRM
        assert result.order_context.address is not None

    @pytest.mark.asyncio
    async def test_finalize_delivery_without_address(self, handler, ctx):
        """Finalizar delivery sem endereço vai para ORDERING_ADDRESS."""
        oc = OrderContext(operation_type="exchange")
        result = await handler.handle(
            message="não",
            conversation_context=ctx,
            customer_context=CustomerContext(),
            order_context=oc,
        )
        assert result.next_state == ConversationState.ORDERING_ADDRESS

    @pytest.mark.asyncio
    async def test_finalize_synonyms(self, handler, ctx):
        """Sinônimos de finalizar funcionam."""
        oc = OrderContext(operation_type="pickup")
        for word in ["finalizar", "não", "nao", "n"]:
            result = await handler.handle(
                message=word,
                conversation_context=ctx,
                order_context=oc,
            )
            assert result.next_state == ConversationState.CHECKOUT_PAYMENT, f"Falhou para '{word}'"

    @pytest.mark.asyncio
    async def test_not_understood(self, handler, ctx, order_context):
        """Mensagem não entendida permanece no estado."""
        result = await handler.handle(
            message="xyz",
            conversation_context=ctx,
            order_context=order_context,
        )
        assert result.next_state == ConversationState.ORDERING_MORE_ITEMS


# ═══════════════════════════════════════════════════════════════
# OrderingAddressHandler
# ═══════════════════════════════════════════════════════════════


class TestOrderingAddressHandler:
    """Testes para OrderingAddressHandler."""

    @pytest.fixture
    def handler(self):
        return OrderingAddressHandler()

    @pytest.fixture
    def ctx(self):
        return ConversationContext(
            phone="5541999999999",
            current_state=ConversationState.ORDERING_ADDRESS,
        )

    @pytest.mark.asyncio
    async def test_valid_address_with_bairro(self, handler, ctx):
        """Endereço com bairro coberto vai para ORDERING_ADDRESS_CONFIRM."""
        result = await handler.handle(
            message="Rua das Flores, 123 - Boqueirão",
            conversation_context=ctx,
        )
        assert result.next_state == ConversationState.ORDERING_ADDRESS_CONFIRM
        assert result.order_context.address is not None
        assert result.order_context.address["bairro"] == "Boqueirão"
        assert result.order_context.delivery_fee == 0.0

    @pytest.mark.asyncio
    async def test_valid_address_with_delivery_fee(self, handler, ctx):
        """Bairro com taxa de entrega calcula delivery_fee."""
        result = await handler.handle(
            message="Rua Principal, 500 - Ganchinho",
            conversation_context=ctx,
        )
        assert result.next_state == ConversationState.ORDERING_ADDRESS_CONFIRM
        assert result.order_context.delivery_fee == 5.0

    @pytest.mark.asyncio
    async def test_address_too_short(self, handler, ctx):
        """Endereço muito curto permanece no estado."""
        result = await handler.handle(message="Rua A", conversation_context=ctx)
        assert result.next_state == ConversationState.ORDERING_ADDRESS
        assert "curto" in result.responses[0].text.lower()

    @pytest.mark.asyncio
    async def test_bairro_from_entities(self, handler, ctx):
        """Extrai bairro das entidades."""
        result = await handler.handle(
            message="Rua das Acácias, 456, apt 12",
            conversation_context=ctx,
            entities={"bairro": "Hauer"},
        )
        assert result.order_context.address["bairro"] == "Hauer"

    @pytest.mark.asyncio
    async def test_address_saved_in_collected_data(self, handler, ctx):
        """Endereço é salvo em collected_data."""
        result = await handler.handle(
            message="Rua Xaxim, 100 - Xaxim",
            conversation_context=ctx,
        )
        assert "address" in ctx.collected_data
        assert ctx.collected_data["address"]["bairro"] == "Xaxim"


# ═══════════════════════════════════════════════════════════════
# OrderingAddressConfirmHandler
# ═══════════════════════════════════════════════════════════════


class TestOrderingAddressConfirmHandler:
    """Testes para OrderingAddressConfirmHandler."""

    @pytest.fixture
    def handler(self):
        return OrderingAddressConfirmHandler()

    @pytest.fixture
    def ctx(self):
        return ConversationContext(
            phone="5541999999999",
            current_state=ConversationState.ORDERING_ADDRESS_CONFIRM,
        )

    @pytest.mark.asyncio
    async def test_confirm_goes_to_complement(
        self, handler, ctx, customer_context, order_context, mock_db_no_customer
    ):
        """Confirmar endereço vai para ORDERING_COMPLEMENT."""
        result = await handler.handle(
            message="sim",
            conversation_context=ctx,
            customer_context=customer_context,
            order_context=order_context,
        )
        assert result.next_state == ConversationState.ORDERING_COMPLEMENT

    @pytest.mark.asyncio
    async def test_confirm_synonyms(
        self, handler, ctx, customer_context, order_context, mock_db_no_customer
    ):
        """Sinônimos de confirmação funcionam."""
        for word in ["confirm_addr", "s", "correto", "confirmar"]:
            result = await handler.handle(
                message=word,
                conversation_context=ctx,
                customer_context=customer_context,
                order_context=order_context,
            )
            assert result.next_state == ConversationState.ORDERING_COMPLEMENT, f"Falhou para '{word}'"

    @pytest.mark.asyncio
    async def test_change_goes_to_address(self, handler, ctx, order_context):
        """Alterar endereço vai para ORDERING_ADDRESS."""
        result = await handler.handle(
            message="change_addr",
            conversation_context=ctx,
            order_context=order_context,
        )
        assert result.next_state == ConversationState.ORDERING_ADDRESS
        assert result.order_context.address is None

    @pytest.mark.asyncio
    async def test_not_understood_stays(self, handler, ctx, order_context):
        """Mensagem não entendida permanece."""
        result = await handler.handle(
            message="xyz",
            conversation_context=ctx,
            order_context=order_context,
        )
        assert result.next_state == ConversationState.ORDERING_ADDRESS_CONFIRM


# ═══════════════════════════════════════════════════════════════
# OrderingComplementHandler
# ═══════════════════════════════════════════════════════════════


class TestOrderingComplementHandler:
    """Testes para OrderingComplementHandler."""

    @pytest.fixture
    def handler(self):
        return OrderingComplementHandler()

    @pytest.fixture
    def ctx(self):
        return ConversationContext(
            phone="5541999999999",
            current_state=ConversationState.ORDERING_COMPLEMENT,
        )

    @pytest.mark.asyncio
    async def test_complement_provided(self, handler, ctx, order_context_empty):
        """Complemento informado vai para CHECKOUT_PAYMENT."""
        result = await handler.handle(
            message="Casa branca, portão verde",
            conversation_context=ctx,
            order_context=order_context_empty,
        )
        assert result.next_state == ConversationState.CHECKOUT_PAYMENT
        assert result.order_context.complement == "Casa branca, portão verde"

    @pytest.mark.asyncio
    async def test_skip_complement(self, handler, ctx, order_context_empty):
        """Pular complemento vai para CHECKOUT_PAYMENT."""
        for skip_word in ["não", "nao", "n", "sem", "pular", "skip"]:
            result = await handler.handle(
                message=skip_word,
                conversation_context=ctx,
                order_context=order_context_empty,
            )
            assert result.next_state == ConversationState.CHECKOUT_PAYMENT, f"Falhou para '{skip_word}'"

    @pytest.mark.asyncio
    async def test_complement_truncated_at_200(self, handler, ctx, order_context_empty):
        """Complemento longo é truncado em 200 chars."""
        long_text = "A" * 300
        result = await handler.handle(
            message=long_text,
            conversation_context=ctx,
            order_context=order_context_empty,
        )
        assert len(result.order_context.complement) <= 200


# ═══════════════════════════════════════════════════════════════
# OrderingConfirmRepeatHandler
# ═══════════════════════════════════════════════════════════════


class TestOrderingConfirmRepeatHandler:
    """Testes para OrderingConfirmRepeatHandler."""

    @pytest.fixture
    def handler(self):
        return OrderingConfirmRepeatHandler()

    @pytest.fixture
    def ctx(self):
        return ConversationContext(
            phone="5541999999999",
            current_state=ConversationState.ORDERING_CONFIRM_REPEAT,
        )

    @pytest.mark.asyncio
    async def test_confirm_repeat_with_history(
        self, handler, ctx, customer_context_with_last_order
    ):
        """Confirmar repetição vai para CHECKOUT_PAYMENT."""
        result = await handler.handle(
            message="sim",
            conversation_context=ctx,
            customer_context=customer_context_with_last_order,
        )
        assert result.next_state == ConversationState.CHECKOUT_PAYMENT
        assert len(result.order_context.items) > 0

    @pytest.mark.asyncio
    async def test_confirm_repeat_without_history(self, handler, ctx, customer_context_new):
        """Confirmar sem histórico vai para ORDERING_PRODUCT."""
        result = await handler.handle(
            message="sim",
            conversation_context=ctx,
            customer_context=customer_context_new,
        )
        assert result.next_state == ConversationState.ORDERING_PRODUCT

    @pytest.mark.asyncio
    async def test_change_repeat(self, handler, ctx, customer_context_with_last_order):
        """Alterar pedido vai para ORDERING_PRODUCT."""
        result = await handler.handle(
            message="alterar",
            conversation_context=ctx,
            customer_context=customer_context_with_last_order,
        )
        assert result.next_state == ConversationState.ORDERING_PRODUCT

    @pytest.mark.asyncio
    async def test_change_repeat_synonyms(self, handler, ctx, customer_context_with_last_order):
        """Sinônimos de alterar funcionam."""
        for word in ["change_repeat", "não", "nao", "n"]:
            result = await handler.handle(
                message=word,
                conversation_context=ctx,
                customer_context=customer_context_with_last_order,
            )
            assert result.next_state == ConversationState.ORDERING_PRODUCT, f"Falhou para '{word}'"

    @pytest.mark.asyncio
    async def test_not_understood_stays(self, handler, ctx, customer_context_with_last_order):
        """Mensagem não entendida permanece."""
        result = await handler.handle(
            message="xyz",
            conversation_context=ctx,
            customer_context=customer_context_with_last_order,
        )
        assert result.next_state == ConversationState.ORDERING_CONFIRM_REPEAT

    @pytest.mark.asyncio
    async def test_repeat_copies_last_order_items(
        self, handler, ctx, customer_context_with_last_order
    ):
        """Repetição copia itens do último pedido."""
        result = await handler.handle(
            message="confirm_repeat",
            conversation_context=ctx,
            customer_context=customer_context_with_last_order,
        )
        assert result.order_context.items == customer_context_with_last_order.last_order["items"]

    @pytest.mark.asyncio
    async def test_repeat_copies_address(
        self, handler, ctx, customer_context_with_last_order
    ):
        """Repetição copia endereço do cliente."""
        result = await handler.handle(
            message="repetir",
            conversation_context=ctx,
            customer_context=customer_context_with_last_order,
        )
        assert result.order_context.address is not None
        assert result.order_context.address["bairro"] == "Xaxim"
