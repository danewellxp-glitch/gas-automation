"""
NLU Engine 2.0 - Sistema Híbrido de Compreensão de Linguagem Natural
Arquitetura em 3 camadas: Keyword → Pattern → LLM

Baseado em: GASMASTER_FLOW_ENGINE_2.0_COMPLETO.md - Parte 5
"""

import re
import logging
from typing import Dict, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# INTENÇÕES
# ═══════════════════════════════════════════════════════════════════════

class Intent(str, Enum):
    """Intenções detectáveis pelo NLU."""
    
    # Principais
    GREETING = "greeting"
    BUY = "buy"
    REPEAT_ORDER = "repeat_order"
    TRACK = "track"
    CONFIRM = "confirm"
    DENY = "deny"
    CANCEL = "cancel"
    
    # Suporte
    HUMAN = "human"
    HELP = "help"
    MENU = "menu"
    INFO = "info"
    FAQ = "faq"
    
    # Edição
    EDIT = "edit"
    
    # Emergência
    EMERGENCY = "emergency"
    
    # Desconhecido
    UNKNOWN = "unknown"


# ═══════════════════════════════════════════════════════════════════════
# CAMADA 1: KEYWORD MATCHER (< 10ms, 95%+ confiança)
# ═══════════════════════════════════════════════════════════════════════

KEYWORD_PATTERNS = {
    Intent.GREETING: [
        "oi", "olá", "ola", "bom dia", "boa tarde", "boa noite", "eae", "e ai",
        "opa", "fala", "salve"
    ],
    Intent.BUY: [
        "quero", "preciso", "pedir", "comprar", "gas", "gás", "botijao", "botijão",
        "p13", "p20", "p45"
    ],
    Intent.REPEAT_ORDER: [
        "mesmo", "repetir", "de novo", "igual", "o de sempre", "mesma coisa"
    ],
    Intent.TRACK: [
        "rastrear", "cadê", "cade", "status", "meu pedido", "onde está",
        "onde esta", "chegou"
    ],
    Intent.CONFIRM: [
        "sim", "ok", "certo", "confirmo", "beleza", "confirmar", "pode ser",
        "isso mesmo", "exato", "correto"
    ],
    Intent.DENY: [
        "não", "nao", "errado", "negativo", "não é", "nao e", "incorreto"
    ],
    Intent.CANCEL: [
        "cancelar", "desistir", "não quero", "nao quero", "esquecer"
    ],
    Intent.HUMAN: [
        "atendente", "humano", "pessoa", "alguém", "alguem", "operador",
        "falar com", "quero falar"
    ],
    Intent.HELP: [
        "ajuda", "socorro", "não entendi", "nao entendi", "como funciona"
    ],
    Intent.MENU: [
        "menu", "início", "inicio", "voltar", "recomeçar", "recomecar"
    ],
    Intent.INFO: [
        "horário", "horario", "preço", "preco", "quanto custa", "entrega",
        "área", "area", "bairro"
    ],
    Intent.EDIT: [
        "alterar", "mudar", "trocar", "corrigir", "modificar", "editar"
    ],
    Intent.EMERGENCY: [
        "vazamento", "cheiro de gás", "cheiro de gas", "fogo", "emergência",
        "emergencia", "perigo", "socorro"
    ],
}


def keyword_match(text: str) -> Optional[Intent]:
    """
    Camada 1: Busca por keywords exatas.
    Tempo: < 10ms
    Confiança: 95%+
    """
    text_lower = text.lower().strip()
    
    for intent, keywords in KEYWORD_PATTERNS.items():
        for keyword in keywords:
            if keyword in text_lower:
                logger.debug(f"Keyword match: '{keyword}' → {intent}")
                return intent
    
    return None


# ═══════════════════════════════════════════════════════════════════════
# CAMADA 2: PATTERN RECOGNIZER (< 20ms, 85%+ confiança)
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class PatternRule:
    """Regra de padrão regex."""
    intent: Intent
    pattern: str
    confidence: float = 0.85


PATTERN_RULES = [
    # Pedidos com quantidade e produto
    PatternRule(Intent.BUY, r"\d+\s*(p13|p20|p45)", 0.90),
    PatternRule(Intent.BUY, r"(p13|p20|p45)\s*\d+", 0.90),
    PatternRule(Intent.BUY, r"\d+\s*(botij[aã]o|botij[õo]es)", 0.85),
    
    # CPF/CNPJ
    PatternRule(Intent.CONFIRM, r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}", 0.95),  # CPF
    PatternRule(Intent.CONFIRM, r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}", 0.95),  # CNPJ
    
    # Endereço
    PatternRule(Intent.CONFIRM, r"rua\s+[\w\s]+,?\s*\d+", 0.90),
    PatternRule(Intent.CONFIRM, r"av(enida)?\s+[\w\s]+,?\s*\d+", 0.90),
    
    # Valores monetários
    PatternRule(Intent.CONFIRM, r"r\$\s*\d+", 0.85),
    PatternRule(Intent.CONFIRM, r"\d+\s*reais", 0.85),
    
    # Números de pedido
    PatternRule(Intent.TRACK, r"#?\d{4,6}", 0.90),
    PatternRule(Intent.TRACK, r"pedido\s+\d+", 0.95),
]


def pattern_match(text: str) -> Optional[Tuple[Intent, float]]:
    """
    Camada 2: Reconhecimento por padrões regex.
    Tempo: < 20ms
    Confiança: 85%+
    
    Returns:
        Tuple[Intent, confidence] ou None
    """
    text_lower = text.lower().strip()
    
    for rule in PATTERN_RULES:
        if re.search(rule.pattern, text_lower):
            logger.debug(f"Pattern match: '{rule.pattern}' → {rule.intent} ({rule.confidence})")
            return (rule.intent, rule.confidence)
    
    return None


# ═══════════════════════════════════════════════════════════════════════
# CAMADA 3: LLM CLASSIFIER (100-300ms, 70%+ confiança)
# ═══════════════════════════════════════════════════════════════════════

async def llm_classify(text: str, context: Optional[Dict] = None) -> Optional[Tuple[Intent, float]]:
    """
    Camada 3: Classificação usando LLM (Ollama).
    Tempo: 100-300ms
    Confiança: 70%+
    
    Args:
        text: Texto a classificar
        context: Contexto da conversa (estado atual, mensagens recentes)
    
    Returns:
        Tuple[Intent, confidence] ou None
    """
    try:
        from app.integrations.ollama import ollama_client
        
        # Construir prompt com contexto
        prompt = _build_classification_prompt(text, context)
        
        # Chamar Ollama
        response = await ollama_client.generate(
            prompt=prompt,
            model="qwen2.5:0.5b",
            max_tokens=50
        )
        
        # Parsear resposta
        intent, confidence = _parse_llm_response(response)
        
        if intent and confidence >= 0.70:
            logger.debug(f"LLM match: {intent} ({confidence})")
            return (intent, confidence)
        
        return None
        
    except Exception as e:
        logger.warning(f"Erro no LLM classifier: {e}")
        return None


def _build_classification_prompt(text: str, context: Optional[Dict]) -> str:
    """Constrói prompt para classificação de intenção."""
    
    base_prompt = f"""Classifique a intenção do usuário na mensagem abaixo.

Mensagem: "{text}"

Intenções possíveis:
- greeting: saudação inicial
- buy: quer comprar/pedir gás
- repeat_order: quer repetir último pedido
- track: quer rastrear pedido
- confirm: confirmando algo
- deny: negando algo
- cancel: cancelar pedido
- human: falar com atendente
- help: pedindo ajuda
- menu: voltar ao menu
- info: perguntando informação
- edit: alterar algo
- emergency: emergência
- unknown: não identificado

Responda APENAS com: <intenção>|<confiança>
Exemplo: buy|0.85
"""
    
    if context:
        state = context.get("current_state", "")
        if state:
            base_prompt += f"\nEstado atual: {state}"
    
    return base_prompt


def _parse_llm_response(response: str) -> Tuple[Optional[Intent], float]:
    """Parseia resposta do LLM."""
    try:
        # Formato esperado: "intent|0.85"
        parts = response.strip().split("|")
        if len(parts) != 2:
            return (None, 0.0)
        
        intent_str = parts[0].strip().lower()
        confidence = float(parts[1].strip())
        
        # Converter string para Intent
        try:
            intent = Intent(intent_str)
            return (intent, confidence)
        except ValueError:
            return (None, 0.0)
            
    except Exception as e:
        logger.warning(f"Erro ao parsear resposta LLM: {e}")
        return (None, 0.0)


# ═══════════════════════════════════════════════════════════════════════
# ENTITY EXTRACTOR (executa sempre em paralelo)
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class ExtractedEntities:
    """Entidades extraídas da mensagem."""
    
    product: Optional[str] = None
    quantity: Optional[int] = None
    cpf: Optional[str] = None
    cnpj: Optional[str] = None
    address_raw: Optional[str] = None
    bairro: Optional[str] = None
    payment: Optional[str] = None
    change_for: Optional[float] = None
    
    def to_dict(self) -> Dict:
        """Converte para dicionário."""
        return {
            k: v for k, v in self.__dict__.items() if v is not None
        }


def extract_entities(text: str, supported_bairros: List[str]) -> ExtractedEntities:
    """
    Extrai entidades da mensagem.
    Executa sempre, em paralelo com detecção de intenção.
    
    Args:
        text: Texto da mensagem
        supported_bairros: Lista de bairros atendidos
    
    Returns:
        ExtractedEntities com dados extraídos
    """
    entities = ExtractedEntities()
    text_lower = text.lower().strip()
    
    # Produto
    entities.product = _extract_product(text_lower)
    
    # Quantidade
    entities.quantity = _extract_quantity(text_lower)
    
    # CPF
    cpf_match = re.search(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}", text)
    if cpf_match:
        entities.cpf = re.sub(r"[^0-9]", "", cpf_match.group())
    
    # CNPJ
    cnpj_match = re.search(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}", text)
    if cnpj_match:
        entities.cnpj = re.sub(r"[^0-9]", "", cnpj_match.group())
    
    # Endereço
    address_match = re.search(r"(rua|av|avenida)\s+[\w\s]+,?\s*\d+", text_lower)
    if address_match:
        entities.address_raw = address_match.group()
    
    # Bairro
    for bairro in supported_bairros:
        if bairro.lower() in text_lower:
            entities.bairro = bairro
            break
    
    # Pagamento
    if any(word in text_lower for word in ["dinheiro", "cash"]):
        entities.payment = "cash"
    elif any(word in text_lower for word in ["cartao", "cartão", "card"]):
        entities.payment = "credit_card"
    elif "pix" in text_lower:
        entities.payment = "pix"
    
    # Troco
    change_match = re.search(r"troco\s+(?:para|pra|p/)?\s*r?\$?\s*(\d+)", text_lower)
    if change_match:
        entities.change_for = float(change_match.group(1))
    
    return entities


def _extract_product(text: str) -> Optional[str]:
    """Extrai código de produto."""
    # Códigos diretos
    if "p13" in text:
        return "P13"
    if "p20" in text:
        return "P20"
    if "p45" in text:
        return "P45"
    
    # Por peso
    if "13" in text and ("kg" in text or "kilo" in text or "quilo" in text):
        return "P13"
    if "20" in text and ("kg" in text or "kilo" in text or "quilo" in text):
        return "P20"
    if "45" in text and ("kg" in text or "kilo" in text or "quilo" in text):
        return "P45"
    
    return None


def _extract_quantity(text: str) -> Optional[int]:
    """Extrai quantidade."""
    # Procurar padrões como "2 p13", "quero 3", etc
    qty_match = re.search(r"(\d+)\s*(p13|p20|p45|botij)", text)
    if qty_match:
        qty = int(qty_match.group(1))
        if 1 <= qty <= 10:
            return qty
    
    # Números isolados (1-10)
    numbers = re.findall(r"\b([1-9]|10)\b", text)
    if numbers:
        return int(numbers[0])
    
    return None


# ═══════════════════════════════════════════════════════════════════════
# PIPELINE PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════

async def detect_intent(text: str, context: Optional[Dict] = None) -> Tuple[Intent, float, ExtractedEntities]:
    """
    Pipeline principal de NLU híbrido.
    
    Fluxo:
    1. Keyword Matcher (< 10ms) → retorna se confiança 95%+
    2. Pattern Recognizer (< 20ms) → retorna se confiança 85%+
    3. LLM Classifier (100-300ms) → fallback se confiança 70%+
    4. Entity Extractor (paralelo) → sempre executa
    
    Args:
        text: Mensagem do usuário
        context: Contexto da conversa
    
    Returns:
        Tuple[Intent, confidence, entities]
    """
    # Normalizar texto
    text = text.strip()
    
    # Extrair entidades (paralelo)
    from app.config import settings
    entities = extract_entities(text, settings.supported_bairros)
    
    # Camada 1: Keywords
    intent = keyword_match(text)
    if intent:
        return (intent, 0.95, entities)
    
    # Camada 2: Patterns
    pattern_result = pattern_match(text)
    if pattern_result:
        intent, confidence = pattern_result
        return (intent, confidence, entities)
    
    # Camada 3: LLM
    llm_result = await llm_classify(text, context)
    if llm_result:
        intent, confidence = llm_result
        return (intent, confidence, entities)
    
    # Fallback: Unknown
    return (Intent.UNKNOWN, 0.0, entities)


# ═══════════════════════════════════════════════════════════════════════
# FUNÇÕES AUXILIARES
# ═══════════════════════════════════════════════════════════════════════

def normalize_text(text: str) -> str:
    """Normaliza texto para processamento."""
    # Remove acentos
    import unicodedata
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ASCII', 'ignore').decode('ASCII')
    
    # Lowercase
    text = text.lower()
    
    # Remove pontuação extra
    text = re.sub(r'[^\w\s]', ' ', text)
    
    # Remove espaços múltiplos
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()
