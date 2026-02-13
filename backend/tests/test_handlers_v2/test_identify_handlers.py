"""
Testes unitários para Identify Handlers v2.
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.core.state_machine_v2 import (
    ConversationState,
    ConversationContext,
    CustomerContext,
    OrderContext,
)
from app.core.handlers_v2.identify_handlers import (
    IdentifyTypeHandler,
    IdentifyNamePFHandler,
    IdentifyNamePJHandler,
    IdentifyDocumentCPFHandler,
    IdentifyDocumentCNPJHandler,
)


# ═══════════════════════════════════════════════════════════════
# IdentifyTypeHandler
# ═══════════════════════════════════════════════════════════════


class TestIdentifyTypeHandler:
    """Testes para IdentifyTypeHandler."""

    @pytest.fixture
    def handler(self):
        return IdentifyTypeHandler()

    @pytest.fixture
    def ctx(self):
        return ConversationContext(
            phone="5541999999999",
            current_state=ConversationState.IDENTIFY_TYPE,
        )

    @pytest.mark.asyncio
    async def test_selects_pf(self, handler, ctx):
        """Selecionar PF vai para IDENTIFY_NAME_PF."""
        result = await handler.handle(message="pessoa física", conversation_context=ctx)
        assert result.next_state == ConversationState.IDENTIFY_NAME_PF
        assert result.customer_context.customer_type == "PF"
        assert ctx.collected_data["customer_type"] == "PF"

    @pytest.mark.asyncio
    async def test_selects_pf_by_number(self, handler, ctx):
        """Selecionar '1' mapeia para PF."""
        result = await handler.handle(message="1", conversation_context=ctx)
        assert result.next_state == ConversationState.IDENTIFY_NAME_PF
        assert result.customer_context.customer_type == "PF"

    @pytest.mark.asyncio
    async def test_selects_pj(self, handler, ctx):
        """Selecionar PJ vai para IDENTIFY_NAME_PJ."""
        result = await handler.handle(message="empresa", conversation_context=ctx)
        assert result.next_state == ConversationState.IDENTIFY_NAME_PJ
        assert result.customer_context.customer_type == "PJ"

    @pytest.mark.asyncio
    async def test_selects_pj_by_number(self, handler, ctx):
        """Selecionar '2' mapeia para PJ."""
        result = await handler.handle(message="2", conversation_context=ctx)
        assert result.next_state == ConversationState.IDENTIFY_NAME_PJ
        assert result.customer_context.customer_type == "PJ"

    @pytest.mark.asyncio
    async def test_selects_pj_by_cnpj_keyword(self, handler, ctx):
        """Keyword 'cnpj' mapeia para PJ."""
        result = await handler.handle(message="cnpj", conversation_context=ctx)
        assert result.next_state == ConversationState.IDENTIFY_NAME_PJ
        assert result.customer_context.customer_type == "PJ"

    @pytest.mark.asyncio
    async def test_not_understood_first_retry(self, handler, ctx):
        """Primeira tentativa inválida repete pergunta."""
        result = await handler.handle(message="abcdef", conversation_context=ctx)
        assert result.next_state == ConversationState.IDENTIFY_TYPE
        assert ctx.retry_count == 1

    @pytest.mark.asyncio
    async def test_assumes_pf_after_2_retries(self, handler):
        """Após 2 tentativas, assume PF."""
        ctx = ConversationContext(
            phone="5541999999999",
            current_state=ConversationState.IDENTIFY_TYPE,
            retry_count=1,  # Próximo incremento chega a 2
        )
        result = await handler.handle(message="xyz", conversation_context=ctx)
        assert result.next_state == ConversationState.IDENTIFY_NAME_PF
        assert result.customer_context.customer_type == "PF"
        assert "pessoa física" in result.responses[0].text.lower()

    @pytest.mark.asyncio
    async def test_escalates_to_human_at_max_retries(self, handler):
        """Escala para humano ao atingir MAX_RETRY_COUNT."""
        ctx = ConversationContext(
            phone="5541999999999",
            current_state=ConversationState.IDENTIFY_TYPE,
            retry_count=2,  # MAX_RETRY_COUNT=3, próximo incremento chega a 3
        )
        result = await handler.handle(message="xyz", conversation_context=ctx)
        assert result.next_state == ConversationState.SUPPORT_HUMAN
        assert result.needs_human is True

    @pytest.mark.asyncio
    async def test_existing_customer_context_preserved(self, handler, ctx):
        """Se customer_context já existe, preserva."""
        existing = CustomerContext(name="Teste")
        result = await handler.handle(
            message="pf", conversation_context=ctx, customer_context=existing
        )
        assert result.customer_context.name == "Teste"
        assert result.customer_context.customer_type == "PF"


# ═══════════════════════════════════════════════════════════════
# IdentifyNamePFHandler
# ═══════════════════════════════════════════════════════════════


class TestIdentifyNamePFHandler:
    """Testes para IdentifyNamePFHandler."""

    @pytest.fixture
    def handler(self):
        return IdentifyNamePFHandler()

    @pytest.fixture
    def ctx(self):
        return ConversationContext(
            phone="5541999999999",
            current_state=ConversationState.IDENTIFY_NAME_PF,
        )

    @pytest.mark.asyncio
    async def test_valid_name_goes_to_ordering(self, handler, ctx, mock_db_no_customer):
        """Nome válido vai para ORDERING_PRODUCT."""
        result = await handler.handle(message="João da Silva", conversation_context=ctx)
        assert result.next_state == ConversationState.ORDERING_PRODUCT
        assert result.customer_context.name == "João Da Silva"  # .title()
        assert ctx.collected_data["name"] == "João Da Silva"

    @pytest.mark.asyncio
    async def test_name_too_short(self, handler, ctx, mock_db_no_customer):
        """Nome muito curto permanece no estado."""
        result = await handler.handle(message="J", conversation_context=ctx)
        assert result.next_state == ConversationState.IDENTIFY_NAME_PF
        assert "curto" in result.responses[0].text.lower()

    @pytest.mark.asyncio
    async def test_name_truncated_at_100_chars(self, handler, ctx, mock_db_no_customer):
        """Nome longo é truncado em 100 chars."""
        long_name = "A" * 150
        result = await handler.handle(message=long_name, conversation_context=ctx)
        assert len(result.customer_context.name) <= 100

    @pytest.mark.asyncio
    async def test_name_is_title_cased(self, handler, ctx, mock_db_no_customer):
        """Nome é capitalizado com title()."""
        result = await handler.handle(
            message="maria souza pereira", conversation_context=ctx
        )
        assert result.customer_context.name == "Maria Souza Pereira"

    @pytest.mark.asyncio
    async def test_response_includes_product_list(self, handler, ctx, mock_db_no_customer):
        """Resposta inclui lista de produtos."""
        result = await handler.handle(message="Maria", conversation_context=ctx)
        assert result.next_state == ConversationState.ORDERING_PRODUCT
        assert "P13" in result.responses[0].text or result.responses[0].has_buttons()


# ═══════════════════════════════════════════════════════════════
# IdentifyNamePJHandler
# ═══════════════════════════════════════════════════════════════


class TestIdentifyNamePJHandler:
    """Testes para IdentifyNamePJHandler."""

    @pytest.fixture
    def handler(self):
        return IdentifyNamePJHandler()

    @pytest.fixture
    def ctx(self):
        return ConversationContext(
            phone="5541999999999",
            current_state=ConversationState.IDENTIFY_NAME_PJ,
        )

    @pytest.mark.asyncio
    async def test_valid_company_name(self, handler, ctx, mock_db_no_customer):
        """Nome de empresa válido vai para ORDERING_PRODUCT."""
        result = await handler.handle(
            message="Empresa XYZ LTDA", conversation_context=ctx
        )
        assert result.next_state == ConversationState.ORDERING_PRODUCT
        assert result.customer_context.customer_type == "PJ"
        assert ctx.collected_data["customer_type"] == "PJ"

    @pytest.mark.asyncio
    async def test_name_too_short(self, handler, ctx, mock_db_no_customer):
        """Nome de empresa muito curto permanece no estado."""
        result = await handler.handle(message="X", conversation_context=ctx)
        assert result.next_state == ConversationState.IDENTIFY_NAME_PJ


# ═══════════════════════════════════════════════════════════════
# IdentifyDocumentCPFHandler
# ═══════════════════════════════════════════════════════════════


class TestIdentifyDocumentCPFHandler:
    """Testes para IdentifyDocumentCPFHandler."""

    @pytest.fixture
    def handler(self):
        return IdentifyDocumentCPFHandler()

    @pytest.fixture
    def ctx(self):
        return ConversationContext(
            phone="5541999999999",
            current_state=ConversationState.IDENTIFY_DOCUMENT_CPF,
        )

    @pytest.mark.asyncio
    async def test_valid_cpf(self, handler, ctx, mock_db_no_customer):
        """CPF válido vai para CHECKOUT_SUMMARY."""
        # CPF válido: 529.982.247-25
        result = await handler.handle(
            message="52998224725", conversation_context=ctx
        )
        assert result.next_state == ConversationState.CHECKOUT_SUMMARY
        assert result.customer_context.document == "52998224725"
        assert "CPF registrado" in result.responses[0].text

    @pytest.mark.asyncio
    async def test_valid_cpf_with_formatting(self, handler, ctx, mock_db_no_customer):
        """CPF com pontos e traço também funciona."""
        result = await handler.handle(
            message="529.982.247-25", conversation_context=ctx
        )
        assert result.next_state == ConversationState.CHECKOUT_SUMMARY

    @pytest.mark.asyncio
    async def test_invalid_cpf_wrong_length(self, handler, ctx):
        """CPF com tamanho errado permanece no estado."""
        result = await handler.handle(message="1234", conversation_context=ctx)
        assert result.next_state == ConversationState.IDENTIFY_DOCUMENT_CPF
        assert "inválido" in result.responses[0].text.lower() or "Inválido" in result.responses[0].text

    @pytest.mark.asyncio
    async def test_invalid_cpf_all_same_digits(self, handler, ctx):
        """CPF com todos dígitos iguais é inválido."""
        result = await handler.handle(message="11111111111", conversation_context=ctx)
        assert result.next_state == ConversationState.IDENTIFY_DOCUMENT_CPF

    @pytest.mark.asyncio
    async def test_invalid_cpf_wrong_check_digits(self, handler, ctx):
        """CPF com dígitos verificadores errados é inválido."""
        result = await handler.handle(message="12345678900", conversation_context=ctx)
        assert result.next_state == ConversationState.IDENTIFY_DOCUMENT_CPF


# ═══════════════════════════════════════════════════════════════
# IdentifyDocumentCNPJHandler
# ═══════════════════════════════════════════════════════════════


class TestIdentifyDocumentCNPJHandler:
    """Testes para IdentifyDocumentCNPJHandler."""

    @pytest.fixture
    def handler(self):
        return IdentifyDocumentCNPJHandler()

    @pytest.fixture
    def ctx(self):
        return ConversationContext(
            phone="5541999999999",
            current_state=ConversationState.IDENTIFY_DOCUMENT_CNPJ,
        )

    @pytest.mark.asyncio
    async def test_valid_cnpj(self, handler, ctx, mock_db_no_customer):
        """CNPJ válido vai para CHECKOUT_SUMMARY."""
        result = await handler.handle(
            message="12345678000190", conversation_context=ctx
        )
        assert result.next_state == ConversationState.CHECKOUT_SUMMARY
        assert result.customer_context.document == "12345678000190"
        assert "CNPJ registrado" in result.responses[0].text

    @pytest.mark.asyncio
    async def test_valid_cnpj_with_formatting(self, handler, ctx, mock_db_no_customer):
        """CNPJ com formatação funciona."""
        result = await handler.handle(
            message="12.345.678/0001-90", conversation_context=ctx
        )
        assert result.next_state == ConversationState.CHECKOUT_SUMMARY

    @pytest.mark.asyncio
    async def test_invalid_cnpj_wrong_length(self, handler, ctx):
        """CNPJ com tamanho errado permanece no estado."""
        result = await handler.handle(message="123456", conversation_context=ctx)
        assert result.next_state == ConversationState.IDENTIFY_DOCUMENT_CNPJ

    @pytest.mark.asyncio
    async def test_invalid_cnpj_all_same_digits(self, handler, ctx):
        """CNPJ com todos dígitos iguais é inválido."""
        result = await handler.handle(message="11111111111111", conversation_context=ctx)
        assert result.next_state == ConversationState.IDENTIFY_DOCUMENT_CNPJ
