"""
Testes unitários para o método send_responses (flow_engine.py).

Documenta o bug de duplicação de mensagens e o comportamento correto após o fix.

─── CONTEXTO DO BUG ──────────────────────────────────────────────────────────

O WAHA Plus NÃO suporta botões interativos (/api/sendButtons → 501) nem listas
(/api/sendList → 501). Quando esses endpoints falham, o WAHAClient usa fallbacks
em texto puro — mas o fallback de lista (_send_list_as_text) concatena o texto
original com os itens da seção, duplicando conteúdo que já estava no texto:

    Texto original: "🛒 Qual botijão?\n\n• P13 - 13kg\n• P20 - 20kg"
    Fallback adiciona: "*Botijões*\n1. P13 - 13kg\n2. P20 - 20kg"
    Resultado final:  produto aparece 2x no WhatsApp ↑

─── ESTRUTURA DOS TESTES ─────────────────────────────────────────────────────

  TestProvaDosBugs          — confirmam que o bug EXISTE agora (passam antes do fix)
  TestComportamentoDesejado — descrevem o que QUEREMOS (falham antes, passam após o fix)
  TestRegressao             — comportamentos que SEMPRE devem funcionar

─── COMO RODAR ───────────────────────────────────────────────────────────────

  # Da raiz do projeto (sem precisar de Docker/Postgres/Redis):
  cd /home/daniel/gas-automation
  python -m pytest backend/tests/test_send_responses_dedup.py -v

  # Para ver só os que falham (bugs ativos):
  python -m pytest backend/tests/test_send_responses_dedup.py -v --tb=short -x

"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.core.flow_engine import FlowEngineWrapper

PHONE = "5541999999999@c.us"


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def engine():
    """Instância do FlowEngineWrapper — não precisa de DB nem Redis."""
    return FlowEngineWrapper()


@pytest.fixture
def mock_waha():
    """
    Substitui o waha_client global por um AsyncMock.
    Todos os métodos de envio (send_text, send_buttons, send_list) são mocks
    que retornam sucesso sem fazer chamadas HTTP reais.
    """
    mock = MagicMock()
    mock.send_text = AsyncMock(return_value={"id": "msg-ok"})
    mock.send_buttons = AsyncMock(return_value={"id": "msg-ok"})
    mock.send_list = AsyncMock(return_value={"id": "msg-ok"})

    with patch("app.integrations.waha.waha_client", mock):
        yield mock


# ─────────────────────────────────────────────────────────────────────────────
# Seção 1: Documentação do fallback problemático (mantida como referência)
# ─────────────────────────────────────────────────────────────────────────────

class TestProvaDosBugs:
    """
    Documenta por que send_list nunca deve ser chamado diretamente:
    o fallback _send_list_as_text duplica conteúdo que já está no texto.
    """

    @pytest.mark.asyncio
    async def test_fallback_list_duplica_produto_no_texto(self):
        """
        PROVA DA DUPLICAÇÃO REAL: demonstra o que o cliente vê no WhatsApp.

        Chama _send_list_as_text diretamente (o fallback do send_list)
        e captura o texto que seria enviado ao cliente.
        O produto 'P13' aparece 2x: uma no texto original, outra na seção.
        """
        from app.integrations.waha import WAHAClient

        textos_enviados = []

        async def captura_send_text(phone, text):
            textos_enviados.append(text)
            return {"id": "ok"}

        client = WAHAClient(
            base_url="http://fake-waha",
            session_name="default",
            api_key="fake-key",
        )
        # Substituir send_text pela função de captura
        client.send_text = captura_send_text

        texto_original = "🛒 Qual botijão?\n\n• P13 - 13kg\n• P20 - 20kg"
        sections = [{
            "title": "Botijões Disponíveis",
            "rows": [
                {"id": "P13", "title": "P13 - 13kg"},
                {"id": "P20", "title": "P20 - 20kg"},
            ],
        }]

        await client._send_list_as_text(PHONE, texto_original, "Ver Produtos", sections)

        assert textos_enviados, "Nenhum texto foi capturado"
        texto_final = textos_enviados[0]

        # BUG CONFIRMADO: P13 aparece 2x (1 no texto original + 1 no fallback)
        ocorrencias = texto_final.count("P13")
        assert ocorrencias == 2, (
            f"Esperado 2 ocorrências (bug ativo), encontrado {ocorrencias}.\n"
            f"Texto enviado ao cliente:\n{texto_final}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Seção 2: Comportamento Desejado (FALHAM agora, PASSAM após o fix)
# ─────────────────────────────────────────────────────────────────────────────

class TestComportamentoDesejado:
    """
    Descrevem o que o sistema DEVE fazer após o fix.
    FALHAM antes do fix (confirmam que ainda está quebrado).
    PASSAM após o fix (confirmam que foi resolvido).
    """

    @pytest.mark.asyncio
    async def test_buttons_deve_usar_send_text_com_opcoes_numeradas(self, engine, mock_waha):
        """
        CORRETO: respostas com buttons devem chamar send_text diretamente,
        com as opções numeradas no final do texto (1. Dinheiro  2. PIX  3. Cartão).
        Nunca deve chamar send_buttons.
        """
        responses = [{
            "text": "Como deseja pagar?",
            "buttons": [
                {"id": "cash",        "text": "💵 Dinheiro"},
                {"id": "pix",         "text": "📱 PIX"},
                {"id": "credit_card", "text": "💳 Cartão"},
            ],
        }]

        await engine.send_responses(PHONE, responses)

        # Não deve chamar send_buttons (causa erro 501 no WAHA Plus)
        mock_waha.send_buttons.assert_not_called()

        # Deve chamar send_text uma única vez
        mock_waha.send_text.assert_called_once()

        # O texto deve conter as opções numeradas para o cliente digitar
        texto_enviado = mock_waha.send_text.call_args[0][1]
        assert "1." in texto_enviado, "Opção 1 não encontrada no texto"
        assert "2." in texto_enviado, "Opção 2 não encontrada no texto"
        assert "3." in texto_enviado, "Opção 3 não encontrada no texto"
        assert "💵 Dinheiro" in texto_enviado
        assert "📱 PIX" in texto_enviado
        assert "💳 Cartão" in texto_enviado

    @pytest.mark.asyncio
    async def test_list_sections_deve_usar_send_text_sem_duplicar(self, engine, mock_waha):
        """
        CORRETO: respostas com list_sections devem chamar send_text com o
        texto original (que já contém a lista de produtos).
        Nunca deve chamar send_list (que causaria duplicação via fallback).
        """
        texto_original = "🛒 Qual botijão você precisa?\n\n• P13 - 13kg\n• P20 - 20kg\n• P45 - 45kg"

        responses = [{
            "text": texto_original,
            "list_sections": [{
                "title": "Botijões Disponíveis",
                "rows": [
                    {"id": "P13", "title": "P13 - 13kg"},
                    {"id": "P20", "title": "P20 - 20kg"},
                    {"id": "P45", "title": "P45 - 45kg"},
                ],
            }],
        }]

        await engine.send_responses(PHONE, responses)

        # Não deve chamar send_list (fallback dela duplica conteúdo)
        mock_waha.send_list.assert_not_called()

        # Deve chamar send_text uma vez
        mock_waha.send_text.assert_called_once()

        # O texto enviado deve ser exatamente o texto original
        texto_enviado = mock_waha.send_text.call_args[0][1]
        assert texto_enviado == texto_original

    @pytest.mark.asyncio
    async def test_p13_aparece_apenas_uma_vez_no_texto_enviado(self, engine, mock_waha):
        """
        CORRETO: P13 deve aparecer somente 1x no texto enviado ao cliente.
        Antes do fix aparece 2x (texto original + fallback da lista).
        """
        texto_original = "🛒 Qual botijão?\n\n• P13 - 13kg\n• P20 - 20kg"

        responses = [{
            "text": texto_original,
            "list_sections": [{
                "title": "Botijões",
                "rows": [
                    {"id": "P13", "title": "P13 - 13kg"},
                    {"id": "P20", "title": "P20 - 20kg"},
                ],
            }],
        }]

        await engine.send_responses(PHONE, responses)

        mock_waha.send_text.assert_called_once()
        texto_enviado = mock_waha.send_text.call_args[0][1]

        ocorrencias = texto_enviado.count("P13")
        assert ocorrencias == 1, (
            f"'P13' aparece {ocorrencias}x — esperado 1x (sem duplicação).\n"
            f"Texto enviado ao cliente:\n{texto_enviado}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Seção 3: Regressão (PASSAM antes e depois do fix — nunca devem quebrar)
# ─────────────────────────────────────────────────────────────────────────────

class TestRegressao:
    """
    Comportamentos que funcionam corretamente e devem continuar funcionando
    independentemente do fix.
    """

    @pytest.mark.asyncio
    async def test_texto_simples_chama_send_text(self, engine, mock_waha):
        """Mensagem sem botões nem lista: send_text é chamado normalmente."""
        responses = [{"text": "Qual é o seu nome?"}]

        await engine.send_responses(PHONE, responses)

        mock_waha.send_text.assert_called_once_with(PHONE, "Qual é o seu nome?")
        mock_waha.send_buttons.assert_not_called()
        mock_waha.send_list.assert_not_called()

    @pytest.mark.asyncio
    async def test_conteudo_duplicado_enviado_apenas_uma_vez(self, engine, mock_waha):
        """Duas respostas com o mesmo texto: enviado só 1x (deduplicação existente)."""
        texto = "Mensagem repetida"
        responses = [
            {"text": texto},
            {"text": texto},
        ]

        await engine.send_responses(PHONE, responses)

        assert mock_waha.send_text.call_count == 1

    @pytest.mark.asyncio
    async def test_multiplas_respostas_distintas_enviadas_todas(self, engine, mock_waha):
        """Duas respostas com textos diferentes: ambas são enviadas."""
        responses = [
            {"text": "📱 Chave PIX: (41) 99999-9999"},
            {"text": "Resumo do pedido:\n• 2x P13 — R$ 220,00"},
        ]

        await engine.send_responses(PHONE, responses)

        assert mock_waha.send_text.call_count == 2

    @pytest.mark.asyncio
    async def test_retorna_contagem_correta(self, engine, mock_waha):
        """send_responses retorna dict com sent/failed."""
        responses = [
            {"text": "Mensagem 1"},
            {"text": "Mensagem 2"},
        ]

        resultado = await engine.send_responses(PHONE, responses)

        assert resultado["sent"] == 2
        assert resultado["failed"] == 0

    @pytest.mark.asyncio
    async def test_erro_em_uma_resposta_nao_para_as_outras(self, engine, mock_waha):
        """Se send_text falhar na 1ª resposta, a 2ª ainda é enviada."""
        mock_waha.send_text.side_effect = [
            Exception("WAHA timeout"),
            {"id": "ok"},
        ]

        responses = [
            {"text": "Primeira mensagem"},
            {"text": "Segunda mensagem"},
        ]

        resultado = await engine.send_responses(PHONE, responses)

        assert resultado["failed"] == 1
        assert resultado["sent"] == 1

    @pytest.mark.asyncio
    async def test_resposta_sem_texto_nao_causa_erro(self, engine, mock_waha):
        """Response com texto vazio não deve causar exceção nem envio."""
        responses = [{"text": ""}]

        resultado = await engine.send_responses(PHONE, responses)

        # Texto vazio não deve ser enviado (dedup ou skip por ser falsy)
        assert resultado["failed"] == 0
