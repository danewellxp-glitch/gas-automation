"""
Cliente Ollama (IA Local).
Usado como fallback para entender mensagens fora do fluxo estruturado.

Documentação: https://github.com/ollama/ollama/blob/main/docs/api.md
"""

import json
import logging
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class OllamaError(Exception):
    """Exceção para erros da API Ollama."""
    pass


class IntentAnalysis:
    """Resultado da análise de intenção."""

    def __init__(
        self,
        intent: str,
        product: Optional[str] = None,
        quantity: Optional[int] = None,
        confidence: float = 0.0,
        suggested_response: Optional[str] = None,
        raw_response: Optional[str] = None,
    ):
        self.intent = intent
        self.product = product
        self.quantity = quantity
        self.confidence = confidence
        self.suggested_response = suggested_response
        self.raw_response = raw_response

    @property
    def is_confident(self) -> bool:
        """Verifica se a análise tem confiança suficiente."""
        return self.confidence >= settings.ai_confidence_threshold

    def to_dict(self) -> dict:
        return {
            "intent": self.intent,
            "product": self.product,
            "quantity": self.quantity,
            "confidence": self.confidence,
            "suggested_response": self.suggested_response,
            "is_confident": self.is_confident,
        }


class OllamaClient:
    """
    Cliente para integração com Ollama (IA Local).

    Usado para:
    - Entender mensagens de texto livre
    - Identificar intenção do cliente
    - Sugerir respostas quando o bot não entende
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self.base_url = (base_url or settings.ollama_url).rstrip("/")
        self.model = model or settings.ollama_model
        self.timeout = timeout or settings.ollama_timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Retorna cliente HTTP."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        """Fecha o cliente HTTP."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def is_available(self) -> bool:
        """Verifica se Ollama está disponível."""
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Ollama não disponível: {e}")
            return False

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 500,
    ) -> str:
        """
        Gera resposta do modelo.

        Args:
            prompt: Texto do prompt
            system: Prompt de sistema (opcional)
            temperature: Criatividade (0-1, menor = mais determinístico)
            max_tokens: Máximo de tokens na resposta
        """
        client = await self._get_client()

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        if system:
            payload["system"] = system

        try:
            response = await client.post("/api/generate", json=payload)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except httpx.HTTPError as e:
            logger.error(f"Erro ao chamar Ollama: {e}")
            raise OllamaError(f"Erro na geração: {str(e)}")

    async def analyze_intent(self, message: str) -> IntentAnalysis:
        """
        Analisa a intenção de uma mensagem do cliente.

        Intents possíveis:
        - comprar_gas: Cliente quer comprar gás
        - duvida_produto: Dúvida sobre qual produto escolher
        - consultar_pedido: Quer saber status do pedido
        - reclamacao: Reclamação ou problema
        - saudacao: Apenas cumprimento
        - despedida: Encerramento
        - outro: Não identificado

        Returns:
            IntentAnalysis com intent, produto (se identificado), confidence
        """
        system_prompt = """Você é um assistente de análise de mensagens para uma distribuidora de gás.
Analise a mensagem do cliente e extraia:
1. A intenção principal (intent)
2. Se mencionou algum produto específico (P13, P20 ou P45)
3. Quantidade (se mencionada)
4. Sua confiança na análise (0 a 1)

Intents possíveis:
- comprar_gas: Cliente quer comprar gás
- duvida_produto: Não sabe qual produto escolher
- consultar_pedido: Quer saber status de pedido
- reclamacao: Problema ou reclamação
- saudacao: Cumprimento (oi, olá, bom dia)
- despedida: Encerramento (tchau, obrigado)
- outro: Não se encaixa nas anteriores

IMPORTANTE: Responda APENAS com JSON válido, sem texto adicional.
Formato: {"intent": "...", "product": null ou "P13"/"P20"/"P45", "quantity": null ou número, "confidence": 0.0 a 1.0}"""

        prompt = f"""Mensagem do cliente: "{message}"

Analise e responda em JSON:"""

        try:
            response = await self.generate(
                prompt=prompt,
                system=system_prompt,
                temperature=0.1,  # Baixa temperatura para respostas consistentes
                max_tokens=200,
            )

            # Tentar extrair JSON da resposta
            analysis = self._parse_json_response(response)

            return IntentAnalysis(
                intent=analysis.get("intent", "outro"),
                product=analysis.get("product"),
                quantity=analysis.get("quantity"),
                confidence=float(analysis.get("confidence", 0.5)),
                raw_response=response,
            )

        except Exception as e:
            logger.error(f"Erro na análise de intent: {e}")
            return IntentAnalysis(
                intent="outro",
                confidence=0.0,
                raw_response=str(e),
            )

    async def suggest_response(
        self,
        customer_message: str,
        context: Optional[dict] = None,
    ) -> str:
        """
        Sugere uma resposta para o cliente.

        Args:
            customer_message: Mensagem do cliente
            context: Contexto adicional (carrinho, histórico, etc)

        Returns:
            Sugestão de resposta
        """
        system_prompt = """Você é um atendente virtual de uma distribuidora de gás em Curitiba.
Seja educado, direto e objetivo. Use português brasileiro informal mas profissional.

Produtos disponíveis:
- P13 (13kg): R$ 110 - Residencial padrão
- P20 (20kg): R$ 150 - Residencial/comercial
- P45 (45kg): R$ 280 - Comercial/industrial

Sempre direcione o cliente para escolher um produto ou falar com atendente humano se não souber responder.
Mantenha respostas curtas (máximo 2-3 frases)."""

        context_str = ""
        if context:
            if context.get("cart"):
                context_str += f"\nCarrinho atual: {context['cart']}"
            if context.get("step"):
                context_str += f"\nEtapa do fluxo: {context['step']}"

        prompt = f"""Mensagem do cliente: "{customer_message}"
{context_str}

Resposta sugerida (curta e direta):"""

        try:
            response = await self.generate(
                prompt=prompt,
                system=system_prompt,
                temperature=0.7,
                max_tokens=150,
            )
            return response.strip()
        except Exception as e:
            logger.error(f"Erro ao sugerir resposta: {e}")
            return "Desculpe, não entendi. Posso ajudar você a pedir gás! Qual botijão você precisa?"

    async def classify_sentiment(self, message: str) -> dict:
        """
        Classifica o sentimento da mensagem.

        Returns:
            {"sentiment": "positive/negative/neutral", "confidence": 0.0-1.0}
        """
        prompt = f"""Classifique o sentimento da mensagem abaixo.
Responda APENAS com JSON: {{"sentiment": "positive" ou "negative" ou "neutral", "confidence": 0.0 a 1.0}}

Mensagem: "{message}"

JSON:"""

        try:
            response = await self.generate(prompt=prompt, temperature=0.1, max_tokens=50)
            return self._parse_json_response(response)
        except Exception as e:
            logger.debug(f"Erro ao classificar sentimento: {e}")
            return {"sentiment": "neutral", "confidence": 0.5}

    def _parse_json_response(self, response: str) -> dict:
        """Extrai JSON de uma resposta que pode conter texto adicional."""
        # Tentar parse direto
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Tentar encontrar JSON na resposta
        import re
        json_match = re.search(r'\{[^{}]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Fallback
        return {}


# Instância global (singleton)
ollama_client = OllamaClient()


# Funções de conveniência
async def analyze_message(message: str) -> IntentAnalysis:
    """Analisa intenção de uma mensagem."""
    return await ollama_client.analyze_intent(message)


async def get_ai_response(message: str, context: dict = None) -> str:
    """Obtém sugestão de resposta da IA."""
    return await ollama_client.suggest_response(message, context)


async def is_ai_available() -> bool:
    """Verifica se a IA está disponível."""
    return await ollama_client.is_available()
