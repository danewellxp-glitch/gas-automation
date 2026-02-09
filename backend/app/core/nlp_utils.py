from __future__ import annotations

"""
GASMASTER - NLP Utilities
Normalizacao de texto, deteccao de intencao e extracao de entidades
para o assistente conversacional WhatsApp.
"""

import re
import unicodedata
from typing import Optional

try:
    from unidecode import unidecode
except ImportError:
    def unidecode(text: str) -> str:
        """Fallback: remove acentos usando unicodedata."""
        nfkd = unicodedata.normalize("NFKD", text)
        return "".join(c for c in nfkd if not unicodedata.combining(c))

from app.core.dictionaries import (
    PRODUCT_SYNONYMS,
    QUANTITY_SYNONYMS,
    PAYMENT_SYNONYMS,
    CONFIRM_SYNONYMS,
    DENY_SYNONYMS,
    GREETING_SYNONYMS,
    BUY_KEYWORDS,
    TRACK_KEYWORDS,
    HUMAN_KEYWORDS,
    EMERGENCY_KEYWORDS,
    CANCEL_KEYWORDS,
    MENU_KEYWORDS,
    HELP_KEYWORDS,
    BACK_KEYWORDS,
    ABBREVIATIONS,
    COMMON_TYPOS,
    CHANGE_KEYWORDS,
    REPEAT_ORDER_KEYWORDS,
    EDIT_KEYWORDS,
    EDIT_PRODUCT_KEYWORDS,
    EDIT_QUANTITY_KEYWORDS,
    EDIT_ADDRESS_KEYWORDS,
    EDIT_PAYMENT_KEYWORDS,
    FAQ_KEYWORDS,
)


# ============================================================
# INTENCOES
# ============================================================

class Intention:
    EMERGENCY = "EMERGENCY"
    BUY = "BUY"
    TRACK = "TRACK"
    HUMAN = "HUMAN"
    CANCEL = "CANCEL"
    CONFIRM = "CONFIRM"
    DENY = "DENY"
    GREETING = "GREETING"
    MENU = "MENU"
    HELP = "HELP"
    BACK = "BACK"
    REPEAT_ORDER = "REPEAT_ORDER"
    EDIT = "EDIT"
    INFO = "INFO"
    UNKNOWN = "UNKNOWN"


# ============================================================
# NORMALIZACAO DE TEXTO
# ============================================================

def normalize_text(text: str) -> str:
    """
    Normaliza texto para deteccao de intencoes e entidades.

    Pipeline:
    1. Lowercase
    2. Remove acentos (unidecode)
    3. Corrige erros ortograficos comuns
    4. Remove pontuacao (exceto numeros e hifen em codigos como P-13)
    5. Expande abreviacoes do internes
    6. Remove espacos extras
    """
    if not text:
        return ""

    # 1. Lowercase
    text = text.lower().strip()

    # 2. Remove acentos
    text = unidecode(text)

    # 3. Remove pontuacao (preserva numeros, letras, espacos e hifen)
    text = re.sub(r"[^\w\s\-/]", " ", text)

    # 4. Remove espacos extras
    text = " ".join(text.split())

    # 5. Corrige erros ortograficos comuns
    for typo, correct in COMMON_TYPOS.items():
        typo_norm = unidecode(typo.lower())
        if typo_norm in text:
            text = text.replace(typo_norm, correct)

    # 6. Expande abreviacoes (word boundary para nao substituir dentro de palavras)
    for abbrev, full in ABBREVIATIONS.items():
        abbrev_norm = unidecode(abbrev.lower())
        text = re.sub(rf"\b{re.escape(abbrev_norm)}\b", full, text)

    # 7. Remove espacos extras novamente
    text = " ".join(text.split())

    return text


# ============================================================
# DETECCAO DE INTENCAO
# ============================================================

def _text_contains_any(text: str, keywords: list) -> bool:
    """Verifica se o texto contem qualquer uma das keywords."""
    text_norm = unidecode(text.lower())
    for kw in keywords:
        kw_norm = unidecode(kw.lower())
        if kw_norm in text_norm:
            return True
    return False


def _text_matches_any_word(text: str, keywords: list) -> bool:
    """Verifica match por palavra inteira (word boundary)."""
    text_norm = unidecode(text.lower())
    words = set(text_norm.split())
    for kw in keywords:
        kw_norm = unidecode(kw.lower())
        # Se keyword eh uma unica palavra, usa set lookup
        if " " not in kw_norm:
            if kw_norm in words:
                return True
        else:
            # Multi-word keyword: substring match
            if kw_norm in text_norm:
                return True
    return False


def detect_intention(text: str, context=None) -> str:
    """
    Detecta a intencao principal da mensagem.
    Usa hierarquia de prioridades:
    EMERGENCY > BUY > TRACK > HUMAN > CANCEL > CONFIRM > DENY > GREETING > UNKNOWN

    Args:
        text: Texto ja normalizado (ou nao, sera normalizado internamente)
        context: ConversationContext (opcional, para intencoes contextuais)

    Returns:
        String com a intencao detectada (ex: "BUY", "TRACK", etc)
    """
    normalized = normalize_text(text)

    if not normalized:
        return Intention.UNKNOWN

    # --- EMERGENCIA (prioridade maxima) ---
    if _text_contains_any(normalized, EMERGENCY_KEYWORDS):
        return Intention.EMERGENCY

    # --- MENU / NAVEGACAO ---
    if _text_matches_any_word(normalized, MENU_KEYWORDS):
        return Intention.MENU

    # --- AJUDA ---
    if _text_contains_any(normalized, HELP_KEYWORDS):
        return Intention.HELP

    # --- VOLTAR ---
    if _text_matches_any_word(normalized, BACK_KEYWORDS):
        return Intention.BACK

    # --- ATENDENTE HUMANO ---
    if _text_contains_any(normalized, HUMAN_KEYWORDS):
        return Intention.HUMAN

    # --- CANCELAR ---
    if _text_contains_any(normalized, CANCEL_KEYWORDS):
        return Intention.CANCEL

    # --- FAQ / INFO (perguntas fora de contexto) ---
    if detect_faq_category(normalized):
        return Intention.INFO

    # --- REPETIR PEDIDO ---
    if _text_contains_any(normalized, REPEAT_ORDER_KEYWORDS):
        return Intention.REPEAT_ORDER

    # --- COMPRAR (alta prioridade) ---
    if _text_contains_any(normalized, BUY_KEYWORDS):
        return Intention.BUY

    # Detectar produto mencionado = intencao de compra
    product = extract_product(normalized)
    if product:
        return Intention.BUY

    # --- RASTREAR ---
    if _text_contains_any(normalized, TRACK_KEYWORDS):
        return Intention.TRACK

    # --- EDITAR (contextual - so se tem pedido em andamento) ---
    if context and _has_pending_order(context):
        if _text_contains_any(normalized, EDIT_KEYWORDS):
            return Intention.EDIT

    # --- CONFIRMAR (contextual - so se robo perguntou algo) ---
    awaiting = _is_awaiting_confirmation(context)
    if awaiting:
        if _text_matches_any_word(normalized, CONFIRM_SYNONYMS):
            return Intention.CONFIRM
        if _text_matches_any_word(normalized, DENY_SYNONYMS):
            return Intention.DENY

    # --- SAUDACAO ---
    if _text_matches_any_word(normalized, GREETING_SYNONYMS):
        return Intention.GREETING

    return Intention.UNKNOWN


def detect_faq_category(text: str) -> Optional[str]:
    """
    Detecta se o texto e uma pergunta de FAQ.

    Returns:
        Categoria da FAQ (ex: "horario", "entrega") ou None
    """
    normalized = normalize_text(text) if text else ""
    if not normalized:
        return None
    for category, keywords in FAQ_KEYWORDS.items():
        for kw in keywords:
            if kw in normalized:
                return category
    return None


def _is_awaiting_confirmation(context) -> bool:
    """Verifica se o contexto indica que estamos aguardando confirmacao."""
    if context is None:
        return False
    # Suporta tanto o campo novo quanto o estado antigo
    if hasattr(context, "awaiting_confirmation") and context.awaiting_confirmation:
        return True
    if hasattr(context, "state"):
        state_val = context.state.value if hasattr(context.state, "value") else str(context.state)
        return state_val in ("confirming_order", "confirming_address")
    return False


def _has_pending_order(context) -> bool:
    """Verifica se ha um pedido em andamento no contexto."""
    if context is None:
        return False
    if hasattr(context, "selected_product") and context.selected_product:
        return True
    if hasattr(context, "pending_entities"):
        pe = context.pending_entities
        if isinstance(pe, dict) and pe.get("product"):
            return True
    return False


# ============================================================
# EXTRACAO DE ENTIDADES
# ============================================================

def extract_product(text: str) -> Optional[str]:
    """
    Extrai produto da mensagem.
    Retorna codigo do produto (P13, P20, P45) ou None.

    Usa o dicionario PRODUCT_SYNONYMS para match por substring.
    Prioriza matches mais longos (mais especificos) para evitar
    falsos positivos (ex: "botijao grande" nao deve matchar P13 por "botijao").
    """
    normalized = unidecode(text.lower())

    # Coleta todos os matches com tamanho do sinonimo
    matches = []  # (product, syn_length, syn)

    for product, synonyms in PRODUCT_SYNONYMS.items():
        for syn in synonyms:
            syn_norm = unidecode(syn.lower())
            # Para sinonimos curtos (1, 2, 3), usar word boundary
            if len(syn_norm) <= 2:
                if re.search(rf"\b{re.escape(syn_norm)}\b", normalized):
                    matches.append((product, len(syn_norm), syn_norm))
            else:
                if syn_norm in normalized:
                    matches.append((product, len(syn_norm), syn_norm))

    if not matches:
        return None

    # Priorizar match mais longo (mais especifico)
    matches.sort(key=lambda x: x[1], reverse=True)
    return matches[0][0]


def extract_quantity(text: str) -> Optional[int]:
    """
    Extrai quantidade da mensagem.
    Retorna inteiro (1-10) ou None.
    """
    normalized = unidecode(text.lower())

    # Primeiro: tenta match por sinonimos escritos por extenso
    for qty, synonyms in QUANTITY_SYNONYMS.items():
        for syn in synonyms:
            syn_norm = unidecode(syn.lower())
            if syn_norm in normalized:
                return qty

    # Segundo: procura numero explicito no texto
    # Padrão: "2 p13", "manda 3", etc
    numbers = re.findall(r"\b(\d{1,2})\b", normalized)
    if numbers:
        # Pega o primeiro numero que parece quantidade (1-10)
        # Ignora numeros que sao claramente parte de codigo de produto
        for num_str in numbers:
            num = int(num_str)
            if 1 <= num <= 10:
                # Verifica se nao eh parte de codigo de produto (13, 20, 45)
                if num not in (13, 20, 45):
                    return num

    return None


def extract_payment(text: str) -> Optional[str]:
    """
    Extrai forma de pagamento da mensagem.
    Retorna: 'cash', 'credit_card', 'debit_card', 'pix' ou None.
    """
    normalized = unidecode(text.lower())

    for payment, synonyms in PAYMENT_SYNONYMS.items():
        for syn in synonyms:
            syn_norm = unidecode(syn.lower())
            if syn_norm in normalized:
                return payment

    return None


def extract_change_amount(text: str) -> Optional[int]:
    """
    Extrai valor do troco da mensagem.
    Ex: "troco pra 200" -> 200
    """
    normalized = unidecode(text.lower())

    patterns = [
        r"troco\s*(?:pra|para|de|p/)?\s*(\d+)",
        r"troco\s*(?:pra|para|de|p/)?\s*r?\$?\s*(\d+)",
        r"(\d+)\s*(?:de\s*)?troco",
    ]

    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            value = int(match.group(1))
            if 10 <= value <= 1000:  # Range razoavel para troco
                return value

    return None


def extract_address_raw(text: str) -> Optional[str]:
    """
    Extrai texto bruto do endereco da mensagem.
    Procura padroes como "Rua X, 123" ou "Av Y 456".
    """
    normalized = text.strip()  # Preserva maiusculas no endereco

    # Padroes de endereco brasileiro
    patterns = [
        # Rua/Av/Travessa + nome + numero
        r"(?:rua|r\.|av\.?|avenida|travessa|trav\.?|alameda|al\.?|estrada|rod\.?|rodovia)\s+[\w\s]+[,\s]+\d+",
        # Formato "endereco: ..."
        r"(?:endereco|endereço|entrega|entregar)\s*:?\s*(.+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, normalized, re.IGNORECASE)
        if match:
            return match.group(0).strip()

    # Se a mensagem inteira parece um endereco (tem numero + nome de rua)
    if re.search(r"\d{1,5}", normalized) and len(normalized) > 10:
        # Verifica se tem palavras tipicas de endereco
        address_indicators = [
            "rua", "av", "avenida", "travessa", "alameda",
            "estrada", "rodovia", "numero", "nº", "n.",
            "bairro", "cep", "esquina", "proximo",
        ]
        text_lower = normalized.lower()
        if any(ind in text_lower for ind in address_indicators):
            return normalized

    return None


def extract_bairro(text: str, supported_bairros: list) -> Optional[str]:
    """
    Extrai bairro da mensagem e verifica se eh suportado.
    Retorna o nome original do bairro (com acentos) ou None.
    """
    normalized = unidecode(text.lower())

    for bairro in supported_bairros:
        bairro_norm = unidecode(bairro.lower())
        if bairro_norm in normalized:
            return bairro

    return None


def extract_cpf_cnpj(text: str) -> Optional[str]:
    """
    Extrai CPF ou CNPJ da mensagem.
    Aceita com ou sem formatacao.
    """
    # Remove tudo exceto numeros
    digits = re.sub(r"\D", "", text)

    # CPF: 11 digitos
    if len(digits) == 11:
        return digits

    # CNPJ: 14 digitos
    if len(digits) == 14:
        return digits

    # Tenta encontrar no texto original
    cpf_pattern = r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}"
    cnpj_pattern = r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}"

    cnpj_match = re.search(cnpj_pattern, text)
    if cnpj_match:
        return re.sub(r"\D", "", cnpj_match.group(0))

    cpf_match = re.search(cpf_pattern, text)
    if cpf_match:
        return re.sub(r"\D", "", cpf_match.group(0))

    return None


def validate_cpf(cpf: str) -> bool:
    """Valida CPF (apenas digitos)."""
    if len(cpf) != 11:
        return False
    if cpf == cpf[0] * 11:
        return False

    # Primeiro digito verificador
    total = sum(int(cpf[i]) * (10 - i) for i in range(9))
    remainder = total % 11
    d1 = 0 if remainder < 2 else 11 - remainder
    if int(cpf[9]) != d1:
        return False

    # Segundo digito verificador
    total = sum(int(cpf[i]) * (11 - i) for i in range(10))
    remainder = total % 11
    d2 = 0 if remainder < 2 else 11 - remainder
    return int(cpf[10]) == d2


def validate_cnpj(cnpj: str) -> bool:
    """Valida CNPJ (apenas digitos)."""
    if len(cnpj) != 14:
        return False
    if cnpj == cnpj[0] * 14:
        return False

    weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    total = sum(int(cnpj[i]) * weights1[i] for i in range(12))
    remainder = total % 11
    d1 = 0 if remainder < 2 else 11 - remainder
    if int(cnpj[12]) != d1:
        return False

    weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    total = sum(int(cnpj[i]) * weights2[i] for i in range(13))
    remainder = total % 11
    d2 = 0 if remainder < 2 else 11 - remainder
    return int(cnpj[13]) == d2


def extract_entities(text: str, supported_bairros: list[str] = None) -> dict:
    """
    Extrai todas as entidades possiveis de uma mensagem.

    Retorna dict com chaves presentes apenas se detectadas:
    - product: str (P13, P20, P45)
    - quantity: int (1-10)
    - payment: str (cash, credit_card, debit_card, pix)
    - change_for: int (valor do troco)
    - address_raw: str (texto do endereco)
    - bairro: str (bairro identificado)
    - cpf_cnpj: str (CPF ou CNPJ)
    - name: str (nome, se identificado)
    """
    normalized = normalize_text(text)
    entities = {}

    # Produto
    product = extract_product(normalized)
    if product:
        entities["product"] = product

    # Quantidade
    quantity = extract_quantity(normalized)
    if quantity:
        entities["quantity"] = quantity

    # Pagamento
    payment = extract_payment(normalized)
    if payment:
        entities["payment"] = payment

    # Troco
    change = extract_change_amount(normalized)
    if change:
        entities["change_for"] = change

    # Endereco (usa texto original, nao normalizado, para preservar formatacao)
    address = extract_address_raw(text)
    if address:
        entities["address_raw"] = address

    # Bairro
    if supported_bairros:
        bairro = extract_bairro(text, supported_bairros)
        if bairro:
            entities["bairro"] = bairro

    # CPF/CNPJ
    cpf_cnpj = extract_cpf_cnpj(text)
    if cpf_cnpj:
        entities["cpf_cnpj"] = cpf_cnpj

    return entities


def detect_edit_field(text: str) -> Optional[str]:
    """
    Detecta qual campo o cliente quer editar.
    Retorna: 'product', 'quantity', 'address', 'payment' ou None.
    """
    normalized = normalize_text(text)

    if _text_contains_any(normalized, EDIT_PRODUCT_KEYWORDS):
        return "product"
    if _text_contains_any(normalized, EDIT_QUANTITY_KEYWORDS):
        return "quantity"
    if _text_contains_any(normalized, EDIT_ADDRESS_KEYWORDS):
        return "address"
    if _text_contains_any(normalized, EDIT_PAYMENT_KEYWORDS):
        return "payment"

    return None


def detect_urgency(text: str) -> Optional[str]:
    """
    Detecta nivel de urgencia da mensagem.
    Retorna: 'immediate', 'today', 'specific', 'flexible' ou None.
    """
    from app.core.dictionaries import URGENCY_KEYWORDS

    normalized = normalize_text(text)

    for level, keywords in URGENCY_KEYWORDS.items():
        if _text_contains_any(normalized, keywords):
            return level

    return None


def is_repeat_order(text: str) -> bool:
    """Verifica se o cliente quer repetir o ultimo pedido."""
    normalized = normalize_text(text)
    return _text_contains_any(normalized, REPEAT_ORDER_KEYWORDS)
