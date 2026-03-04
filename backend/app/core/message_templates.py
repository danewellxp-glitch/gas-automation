"""
Templates de Mensagens - Flow Engine 2.0
Sistema de templates personalizados com Jinja2 e emojis.

Baseado em: GASMASTER_FLOW_ENGINE_2.0_COMPLETO.md - Parte 6
"""

from typing import Dict, Optional, List
from decimal import Decimal


# ═══════════════════════════════════════════════════════════════════════
# TEMPLATES DE SAUDAÇÃO
# ═══════════════════════════════════════════════════════════════════════

GREETING_NEW = """👋 Olá! Bem-vindo(a) à *GasMaster*!

Sou o assistente virtual e vou te ajudar.

Para começar, você é:"""

GREETING_RETURNING = """👋 Olá, {name}!

📦 Seu último pedido:
{last_order_items}
💰 Total: {last_order_total}

Deseja repetir?"""

GREETING_RETURNING_NO_HISTORY = """👋 Olá, {name}!

Como posso ajudar você hoje?"""

GREETING_ABANDONED_ORDER = """👋 Oi {name}! Vi que você estava {stage}.

Deseja continuar de onde parou?"""


# ═══════════════════════════════════════════════════════════════════════
# TEMPLATES DE IDENTIFICAÇÃO
# ═══════════════════════════════════════════════════════════════════════

ASK_CUSTOMER_TYPE = """Para começar, você é:"""

ASK_NAME_PF = """Certo! Qual o seu *nome completo*?"""

ASK_NAME_PJ = """Certo! Qual o *nome da empresa*?"""

ASK_DOCUMENT_CPF = """Para finalizar, preciso do seu *CPF*:
_(apenas números)_"""

ASK_DOCUMENT_CNPJ = """Para finalizar, preciso do *CNPJ* da empresa:
_(apenas números)_"""

INVALID_CPF = """❌ CPF inválido

Verifique e digite novamente.
💡 Pode ser só os números."""

INVALID_CNPJ = """❌ CNPJ inválido

Verifique e digite novamente.
💡 Pode ser só os números."""


# ═══════════════════════════════════════════════════════════════════════
# TEMPLATES DE PRODUTO
# ═══════════════════════════════════════════════════════════════════════

ASK_PRODUCT = """🛒 Qual botijão você precisa?

{product_list}"""

PRODUCT_SELECTED = """✅ *{product_name}* selecionado!
💰 Valor: {unit_price}"""

ASK_QUANTITY = """Quantos botijões você deseja?"""

ASK_OPERATION_TYPE = """🔄 Você vai:"""

ASK_MORE_ITEMS = """Adicionar mais produtos?"""


# ═══════════════════════════════════════════════════════════════════════
# TEMPLATES DE ENDEREÇO
# ═══════════════════════════════════════════════════════════════════════

ASK_ADDRESS = """📍 Informe o *endereço completo* para entrega, incluindo o *CEP*.
Se quiser, adicione complemento ou referência na linha de baixo.

_Exemplo:_
_Rua das Flores, 123 - Boqueirão - 81050-100_
_Casa branca, portão verde_"""

CONFIRM_ADDRESS = """📍 Confirma endereço?

{formatted_address}"""

ADDRESS_CONFIRMED = """✅ Endereço confirmado!"""

ADDRESS_OUT_OF_AREA = """📍 Infelizmente não entregamos no {bairro} ainda 😔

Entregamos em:
{covered_areas}

💡 Você pode retirar na loja:
{store_address}"""

ASK_COMPLEMENT = """Complemento/referência?
_(Ex: Casa branca, portão verde)_"""


# ═══════════════════════════════════════════════════════════════════════
# TEMPLATES DE PAGAMENTO
# ═══════════════════════════════════════════════════════════════════════

ASK_PAYMENT = """💰 *Total: {total}*

Como deseja pagar?"""

ASK_CHANGE = """Troco para quanto?"""

PAYMENT_PIX_INFO = """📱 *Pagamento via PIX*

Chave PIX: {pix_key}

Você pode pagar antes ou na entrega.
Envie o comprovante para agilizar!"""


# ═══════════════════════════════════════════════════════════════════════
# TEMPLATES DE RESUMO E CONFIRMAÇÃO
# ═══════════════════════════════════════════════════════════════════════

ORDER_SUMMARY = """📋 *RESUMO DO PEDIDO*
═══════════════════
👤 {customer_name}
📍 {address}
🛒 {items}
💰 Total: {total}
💳 Pagamento: {payment_method}
⏱️ Previsão: {delivery_estimate}
═══════════════════

Confirma?"""

ORDER_CONFIRMED = """🎉 *OS #{os_number} CONFIRMADA!*

📦 {items_summary}
📍 {address}
💰 Total: {total}
Pagamento: {payment_method}

⏱️ Previsão: *{delivery_time}*

Você receberá atualizações sobre sua entrega!
Para consultar seu pedido, envie: *OS {os_number}*

Obrigado pela preferência! 🔥"""

ORDER_REPEAT_CONFIRM = """🔄 Repetir o pedido?

{last_order_summary}

Mesmo endereço e pagamento?"""


# ═══════════════════════════════════════════════════════════════════════
# TEMPLATES DE RASTREAMENTO
# ═══════════════════════════════════════════════════════════════════════

TRACKING_STATUS = """📦 *PEDIDO #{order_number}*

{status_timeline}

🛵 Entregador: {driver_name}
⏱️ Previsão: ~{eta} min"""

TRACKING_NO_ORDERS = """📦 *Seus Pedidos*

Você ainda não fez nenhum pedido.

Digite *menu* para fazer seu primeiro pedido!"""


# ═══════════════════════════════════════════════════════════════════════
# TEMPLATES DE ERRO E RECUPERAÇÃO
# ═══════════════════════════════════════════════════════════════════════

NOT_UNDERSTOOD = """🤔 Não consegui entender.

Você pode escolher da lista ou digitar:
• P13, P20 ou P45"""

NOT_UNDERSTOOD_RETRY = """Hmm, não entendi 🤔

Você pode escolher da lista abaixo:"""

ERROR_GENERIC = """Desculpe, ocorreu um erro. 

Por favor, tente novamente ou digite *menu* para recomeçar."""

EMERGENCY_ALERT = """⚠️ *ATENÇÃO - EMERGÊNCIA*

Se você sente cheiro de gás ou há risco de vazamento:

1. NÃO acione interruptores elétricos
2. Abra portas e janelas
3. Feche o registro do botijão
4. Saia do local
5. Ligue para o Corpo de Bombeiros: *193*

Estamos transferindo você para um atendente."""


# ═══════════════════════════════════════════════════════════════════════
# TEMPLATES DE SUPORTE
# ═══════════════════════════════════════════════════════════════════════

TALKING_TO_HUMAN = """👤 Você está em atendimento humano.

Um de nossos atendentes responderá em breve.

Digite *menu* para voltar ao atendimento automático."""

OUTSIDE_BUSINESS_HOURS = """👋 Olá! Bem-vindo à *GasMaster*!

⏰ Nosso horário de funcionamento:
Seg-Sex: 8h às 18h
Sábado: 8h às 12h

Você pode deixar seu pedido agora e processaremos assim que abrirmos!"""

CLOSING_SOON = """⚠️ Atenção: Fechamos em {minutes} minutos!

Seu pedido será entregue ainda hoje se confirmado nos próximos {cutoff_minutes} minutos.

Caso contrário, será entregue amanhã às {next_delivery_time}."""


# ═══════════════════════════════════════════════════════════════════════
# FAQ RESPONSES
# ═══════════════════════════════════════════════════════════════════════

FAQ_DELIVERY_TIME = """⏱️ *Tempo de Entrega*

O tempo de entrega varia de acordo com o bairro:
{delivery_times}

Após a confirmação do pedido, você receberá atualizações em tempo real."""

FAQ_COVERAGE_AREA = """📍 *Área de Entrega*

Entregamos nos seguintes bairros:
{covered_areas}

Bairros não atendidos podem usar a opção RETIRA NA LOJA:
{store_address}"""

FAQ_PAYMENT_METHODS = """💳 *Formas de Pagamento*

Aceitamos:
• 💵 Dinheiro (troco disponível)
• 💳 Cartão de Crédito/Débito
• 📱 PIX
{invoice_option}

O pagamento é feito na entrega."""

FAQ_PRICES = """💰 *Preços*

{product_prices}

*Tipos de Operação:*
🔄 Troca: Cliente entrega vasilhame vazio
🆕 Venda: Primeira compra (inclui caução do vasilhame)
🏪 Retira: Cliente busca na loja (sem taxa de entrega)"""


# ═══════════════════════════════════════════════════════════════════════
# FUNÇÕES AUXILIARES
# ═══════════════════════════════════════════════════════════════════════

def format_currency(value: Decimal) -> str:
    """Formata valor em reais."""
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_product_list(products: List[Dict]) -> str:
    """Formata lista de produtos para exibição."""
    lines = []
    for p in products:
        emoji = p.get("emoji", "🔵")
        code = p.get("code", "")
        weight = p.get("weight_kg", 0)
        price = p.get("price", 0)
        lines.append(f"{emoji} *{code}* ({weight}kg) - {format_currency(price)}")
    return "\n".join(lines)


def format_address(address: Dict) -> str:
    """Formata endereço para exibição."""
    if not address:
        return "Endereço não informado"
    
    if address.get("full_address"):
        return address["full_address"]
    
    parts = []
    if address.get("street"):
        parts.append(address["street"])
    if address.get("number"):
        parts.append(address["number"])
    if address.get("complement"):
        parts.append(f"- {address['complement']}")
    if address.get("bairro"):
        parts.append(f"- {address['bairro']}")
    
    return ", ".join(parts) if parts else "Endereço cadastrado"


def format_items_summary(items: List[Dict]) -> str:
    """Formata resumo de itens do pedido."""
    lines = []
    for item in items:
        qty = item.get("quantity", 1)
        code = item.get("product_code", "")
        price = item.get("subtotal", 0)
        lines.append(f"• {qty}x {code} - {format_currency(price)}")
    return "\n".join(lines)


def format_delivery_estimate(bairro: str, operation_type: str) -> str:
    """Formata estimativa de entrega."""
    from app.core.product_catalog import get_coverage_area
    
    if operation_type == "pickup":
        return "Retirada na loja"
    
    area = get_coverage_area(bairro)
    if not area:
        return "A calcular"
    
    return f"{area.delivery_time_min}-{area.delivery_time_max} min"


def format_status_timeline(order_status: str, created_at: str, driver_name: Optional[str] = None) -> str:
    """Formata timeline de status do pedido."""
    statuses = {
        "pending": "⏳ Aguardando confirmação",
        "paid": "✅ Pagamento confirmado",
        "preparing": "🔧 Preparando pedido",
        "dispatched": "🚚 Saiu para entrega",
        "delivered": "📬 Entregue",
        "cancelled": "❌ Cancelado"
    }
    
    lines = []
    current_status = statuses.get(order_status, order_status)
    lines.append(f"Status: {current_status}")
    
    if driver_name:
        lines.append(f"Entregador: {driver_name}")
    
    return "\n".join(lines)


def build_message(template: str, **kwargs) -> str:
    """
    Constrói mensagem a partir de template.
    
    Args:
        template: Template de mensagem
        **kwargs: Variáveis para substituição
    
    Returns:
        Mensagem formatada
    """
    try:
        return template.format(**kwargs)
    except KeyError as e:
        # Se faltar alguma variável, retorna template com marcadores
        return template
