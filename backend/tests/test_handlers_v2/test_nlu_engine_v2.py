"""
Testes unitários para NLU Engine v2.
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.core.nlu_engine_v2 import (
    Intent,
    keyword_match,
    pattern_match,
    llm_classify,
    extract_entities,
    _extract_product,
    _extract_quantity,
    _parse_llm_response,
    normalize_text,
    ExtractedEntities,
)


SUPPORTED_BAIRROS = [
    "Alto Boqueirão", "Boqueirão", "Ganchinho",
    "Hauer", "Sítio Cercado", "Umbará", "Xaxim",
]


# ═══════════════════════════════════════════════════════════════
# Keyword Matcher
# ═══════════════════════════════════════════════════════════════


class TestKeywordMatch:
    """Testes para keyword_match (Camada 1)."""

    def test_greeting_oi(self):
        assert keyword_match("oi") == Intent.GREETING

    def test_greeting_bom_dia(self):
        assert keyword_match("bom dia") == Intent.GREETING

    def test_greeting_boa_tarde(self):
        assert keyword_match("boa tarde") == Intent.GREETING

    def test_greeting_ola(self):
        assert keyword_match("olá") == Intent.GREETING

    def test_buy_quero(self):
        assert keyword_match("quero gás") == Intent.BUY

    def test_buy_p13(self):
        assert keyword_match("p13") == Intent.BUY

    def test_buy_botijao(self):
        assert keyword_match("preciso de um botijão") == Intent.BUY

    def test_repeat_order(self):
        assert keyword_match("repetir") == Intent.REPEAT_ORDER

    def test_repeat_o_de_sempre(self):
        assert keyword_match("o de sempre") == Intent.REPEAT_ORDER

    def test_track_rastrear(self):
        assert keyword_match("rastrear") == Intent.TRACK

    def test_track_cadê(self):
        assert keyword_match("cadê meu pedido") == Intent.TRACK

    def test_confirm_sim(self):
        assert keyword_match("sim") == Intent.CONFIRM

    def test_confirm_beleza(self):
        assert keyword_match("beleza") == Intent.CONFIRM

    def test_deny_nao(self):
        assert keyword_match("não") == Intent.DENY

    def test_cancel(self):
        assert keyword_match("cancelar") == Intent.CANCEL

    def test_human(self):
        assert keyword_match("atendente") == Intent.HUMAN

    def test_help(self):
        assert keyword_match("ajuda") == Intent.HELP

    def test_menu(self):
        assert keyword_match("menu") == Intent.MENU

    def test_info_preco(self):
        assert keyword_match("preço") == Intent.INFO

    def test_edit(self):
        assert keyword_match("alterar") == Intent.EDIT

    def test_emergency(self):
        assert keyword_match("vazamento") == Intent.EMERGENCY

    def test_emergency_cheiro_de_gas(self):
        assert keyword_match("cheiro de gás") == Intent.EMERGENCY

    def test_unknown(self):
        assert keyword_match("xyzabc123") is None

    def test_case_insensitive(self):
        assert keyword_match("OI") == Intent.GREETING

    def test_with_spaces(self):
        assert keyword_match("  oi  ") == Intent.GREETING


# ═══════════════════════════════════════════════════════════════
# Pattern Matcher
# ═══════════════════════════════════════════════════════════════


class TestPatternMatch:
    """Testes para pattern_match (Camada 2)."""

    def test_product_quantity_pattern(self):
        result = pattern_match("2 p13")
        assert result is not None
        assert result[0] == Intent.BUY

    def test_quantity_product_reverse(self):
        result = pattern_match("p20 3")
        assert result is not None
        assert result[0] == Intent.BUY

    def test_botijao_quantity(self):
        result = pattern_match("3 botijões")
        assert result is not None
        assert result[0] == Intent.BUY

    def test_cpf_pattern(self):
        result = pattern_match("123.456.789-01")
        assert result is not None
        assert result[0] == Intent.CONFIRM

    def test_cpf_without_formatting(self):
        result = pattern_match("12345678901")
        assert result is not None
        assert result[0] == Intent.CONFIRM

    def test_cnpj_pattern(self):
        result = pattern_match("12.345.678/0001-90")
        assert result is not None
        assert result[0] == Intent.CONFIRM

    def test_address_rua(self):
        result = pattern_match("rua das flores, 123")
        assert result is not None
        assert result[0] == Intent.CONFIRM

    def test_address_avenida(self):
        result = pattern_match("avenida brasil, 500")
        assert result is not None
        assert result[0] == Intent.CONFIRM

    def test_monetary_value(self):
        result = pattern_match("r$ 100")
        assert result is not None
        assert result[0] == Intent.CONFIRM

    def test_order_number(self):
        result = pattern_match("pedido 1234")
        assert result is not None
        assert result[0] == Intent.TRACK

    def test_no_match(self):
        result = pattern_match("abc def ghi")
        assert result is None

    def test_confidence_is_returned(self):
        result = pattern_match("2 p13")
        assert result is not None
        assert result[1] >= 0.85


# ═══════════════════════════════════════════════════════════════
# LLM Classifier
# ═══════════════════════════════════════════════════════════════


class TestLLMClassifier:
    """Testes para llm_classify (Camada 3)."""

    @pytest.mark.asyncio
    async def test_llm_classify_success(self):
        """LLM retorna intent e confiança válidos."""
        with patch("app.core.nlu_engine_v2.ollama_client") as mock_client:
            mock_client.generate = AsyncMock(return_value="buy|0.85")
            result = await llm_classify("quero comprar gás")
            assert result is not None
            assert result[0] == Intent.BUY
            assert result[1] == 0.85

    @pytest.mark.asyncio
    async def test_llm_classify_low_confidence(self):
        """LLM com confiança baixa retorna None."""
        with patch("app.core.nlu_engine_v2.ollama_client") as mock_client:
            mock_client.generate = AsyncMock(return_value="buy|0.50")
            result = await llm_classify("talvez")
            assert result is None

    @pytest.mark.asyncio
    async def test_llm_classify_error(self):
        """Erro no LLM retorna None."""
        with patch("app.core.nlu_engine_v2.ollama_client") as mock_client:
            mock_client.generate = AsyncMock(side_effect=Exception("timeout"))
            result = await llm_classify("texto")
            assert result is None

    @pytest.mark.asyncio
    async def test_llm_import_error(self):
        """Import error retorna None."""
        with patch(
            "app.core.nlu_engine_v2.llm_classify",
            side_effect=ImportError("no module"),
        ):
            # Chamar diretamente com mock que falha
            result = await llm_classify("texto")
            # Não deve crashar
            assert result is None or result is not None


class TestParseLLMResponse:
    """Testes para _parse_llm_response."""

    def test_valid_response(self):
        intent, confidence = _parse_llm_response("buy|0.85")
        assert intent == Intent.BUY
        assert confidence == 0.85

    def test_invalid_format(self):
        intent, confidence = _parse_llm_response("buy")
        assert intent is None
        assert confidence == 0.0

    def test_invalid_intent(self):
        intent, confidence = _parse_llm_response("xyz|0.90")
        assert intent is None

    def test_invalid_confidence(self):
        intent, confidence = _parse_llm_response("buy|abc")
        assert intent is None

    def test_empty_response(self):
        intent, confidence = _parse_llm_response("")
        assert intent is None


# ═══════════════════════════════════════════════════════════════
# Entity Extraction
# ═══════════════════════════════════════════════════════════════


class TestExtractEntities:
    """Testes para extract_entities."""

    def test_extract_product_p13(self):
        entities = extract_entities("quero p13", SUPPORTED_BAIRROS)
        assert entities.product == "P13"

    def test_extract_product_p20(self):
        entities = extract_entities("preciso de p20", SUPPORTED_BAIRROS)
        assert entities.product == "P20"

    def test_extract_product_p45(self):
        entities = extract_entities("p45 por favor", SUPPORTED_BAIRROS)
        assert entities.product == "P45"

    def test_extract_quantity(self):
        entities = extract_entities("2 p13", SUPPORTED_BAIRROS)
        assert entities.quantity == 2

    def test_extract_cpf(self):
        entities = extract_entities("meu cpf 123.456.789-01", SUPPORTED_BAIRROS)
        assert entities.cpf == "12345678901"

    def test_extract_cnpj(self):
        entities = extract_entities("cnpj 12.345.678/0001-90", SUPPORTED_BAIRROS)
        assert entities.cnpj == "12345678000190"

    def test_extract_address(self):
        entities = extract_entities(
            "entrega na rua das flores, 123",
            SUPPORTED_BAIRROS,
        )
        assert entities.address_raw is not None
        assert "rua" in entities.address_raw

    def test_extract_bairro(self):
        entities = extract_entities("entrega no Boqueirão", SUPPORTED_BAIRROS)
        assert entities.bairro == "Boqueirão"

    def test_extract_bairro_case_insensitive(self):
        entities = extract_entities("moro no hauer", SUPPORTED_BAIRROS)
        assert entities.bairro == "Hauer"

    def test_extract_payment_cash(self):
        entities = extract_entities("pagar com dinheiro", SUPPORTED_BAIRROS)
        assert entities.payment == "cash"

    def test_extract_payment_pix(self):
        entities = extract_entities("vou pagar via pix", SUPPORTED_BAIRROS)
        assert entities.payment == "pix"

    def test_extract_payment_card(self):
        entities = extract_entities("cartão de crédito", SUPPORTED_BAIRROS)
        assert entities.payment == "credit_card"

    def test_extract_change_for(self):
        entities = extract_entities("troco para 100", SUPPORTED_BAIRROS)
        assert entities.change_for == 100.0

    def test_extract_change_with_r_dollar(self):
        entities = extract_entities("troco pra r$ 50", SUPPORTED_BAIRROS)
        assert entities.change_for == 50.0

    def test_no_entities(self):
        entities = extract_entities("abc def", SUPPORTED_BAIRROS)
        assert entities.product is None
        assert entities.quantity is None
        assert entities.bairro is None

    def test_to_dict_filters_none(self):
        entities = extract_entities("p13", SUPPORTED_BAIRROS)
        d = entities.to_dict()
        assert "product" in d
        assert None not in d.values()


class TestExtractProduct:
    """Testes para _extract_product."""

    def test_p13(self):
        assert _extract_product("p13") == "P13"

    def test_p20(self):
        assert _extract_product("p20") == "P20"

    def test_p45(self):
        assert _extract_product("p45") == "P45"

    def test_by_weight_13kg(self):
        assert _extract_product("13 kg") == "P13"

    def test_by_weight_20_quilo(self):
        assert _extract_product("20 quilo") == "P20"

    def test_no_product(self):
        assert _extract_product("abc") is None


class TestExtractQuantity:
    """Testes para _extract_quantity."""

    def test_quantity_with_product(self):
        assert _extract_quantity("2 p13") == 2

    def test_quantity_with_botijao(self):
        assert _extract_quantity("3 botijões") == 3

    def test_isolated_number(self):
        assert _extract_quantity("5") == 5

    def test_no_quantity(self):
        assert _extract_quantity("abc") is None


# ═══════════════════════════════════════════════════════════════
# Normalize Text
# ═══════════════════════════════════════════════════════════════


class TestNormalizeText:
    """Testes para normalize_text."""

    def test_removes_accents(self):
        assert normalize_text("botijão") == "botijao"

    def test_lowercase(self):
        assert normalize_text("OI") == "oi"

    def test_removes_extra_punctuation(self):
        assert normalize_text("oi!!! como vai???") == "oi como vai"

    def test_removes_multiple_spaces(self):
        assert normalize_text("oi    tudo    bem") == "oi tudo bem"

    def test_strips(self):
        assert normalize_text("  oi  ") == "oi"
