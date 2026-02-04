"""
Handlers para cada estado da conversa.
Cada handler processa a mensagem e retorna o proximo estado.

Inclui:
- Handlers de estado originais (fluxo por menus)
- Handlers conversacionais (fluxo por intencao NLP)
"""

import logging
import re
from typing import Optional, List, Dict, Tuple
from decimal import Decimal

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.core.state_machine import ConversationState, ConversationContext
from app.core.flow_engine import MessageResponse, ProcessedMessage
from app.core.nlp_utils import (
    extract_product,
    extract_entities,
    detect_edit_field,
    normalize_text,
)
from app.models.customer import Customer
from app.models.product import Product, DEFAULT_PRODUCT_CODES, WEIGHT_TO_CODE, OPTION_TO_CODE
from app.models.order import Order, OrderItem, OrderStatus

logger = logging.getLogger(__name__)

# REMOVIDO: Dados hardcoded de produtos
# Produtos devem ser buscados do banco de dados (PostgreSQL) que é sincronizado do Firebird
# Usar get_product() que busca do banco


async def get_or_create_customer(phone: str) -> Tuple[Customer, bool, bool]:
    """
    Busca ou cria cliente pelo telefone.

    Retorna:
        tuple: (customer, is_new, has_complete_data)
        - customer: objeto Customer
        - is_new: True se foi criado agora (nao existia em lugar nenhum)
        - has_complete_data: True se tem nome E (cpf_cnpj OU endereco)

    Fluxo:
    1. Busca no PostgreSQL pelo telefone
    2. Se nao encontrar, busca no Firebird pelo telefone
    3. Se encontrar no Firebird, cria no PostgreSQL com dados completos
    4. Se nao encontrar em nenhum, cria cliente vazio
    """
    def _has_complete_data(c: Customer) -> bool:
        has_name = bool(c.name and c.name.strip())
        has_doc_or_addr = bool(c.cpf_cnpj) or bool(c.address and (c.address.get("street") or c.address.get("full_address")))
        return has_name and has_doc_or_addr

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Customer).where(Customer.phone == phone)
        )
        customer = result.scalar_one_or_none()

        if customer:
            return customer, False, _has_complete_data(customer)

        # Cliente nao existe no PostgreSQL - tentar buscar no Firebird
        firebird_customer = None
        try:
            from app.integrations.firebird import firebird_client
            if firebird_client.is_available:
                firebird_customer = firebird_client.get_customer_by_phone(phone)
                if firebird_customer:
                    logger.info(f"Cliente encontrado no Firebird: {firebird_customer.get('name')} (ID: {firebird_customer.get('firebird_id')})")
        except Exception as e:
            logger.warning(f"Erro ao buscar cliente no Firebird: {e}")

        # Criar cliente com dados do Firebird (se encontrado) ou vazio
        if firebird_customer:
            address = firebird_customer.get("address", {}) or {}
            has_addr = address.get("street") or address.get("full_address")
            customer = Customer(
                phone=phone,
                name=firebird_customer.get("name"),
                email=firebird_customer.get("email"),
                cpf_cnpj=firebird_customer.get("cpf_cnpj"),
                firebird_id=firebird_customer.get("firebird_id"),
                address=address if has_addr else None,
            )
        else:
            customer = Customer(phone=phone)

        db.add(customer)
        await db.commit()
        await db.refresh(customer)
        return customer, True, _has_complete_data(customer)


async def get_product(code: str) -> Optional[Product]:
    """Busca produto pelo código."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Product).where(Product.code == code.upper())
        )
        return result.scalar_one_or_none()


def extract_product_code(message: str) -> Optional[str]:
    """Extrai código do produto da mensagem."""
    msg_upper = message.upper().strip()

    # Procura por códigos específicos (usa constantes centralizadas)
    for code in DEFAULT_PRODUCT_CODES:
        if code in msg_upper:
            return code

    # Procura por peso (usa mapeamento centralizado)
    for weight, code in WEIGHT_TO_CODE.items():
        if weight in message:
            return code

    # Procura por número de opção (usa mapeamento centralizado)
    option_code = OPTION_TO_CODE.get(message.strip())
    if option_code:
        return option_code

    return None


def extract_quantity(message: str) -> Optional[int]:
    """Extrai quantidade da mensagem."""
    # Remove tudo exceto números
    numbers = re.findall(r'\d+', message)
    if numbers:
        qty = int(numbers[0])
        if 1 <= qty <= 10:  # Limite razoável
            return qty
    return None


def format_currency(value: Decimal) -> str:
    """Formata valor em reais."""
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


async def _get_or_create_asaas_customer(customer: Customer) -> str:
    # Integração Asaas/Pix foi descontinuada.
    raise RuntimeError("Asaas disabled")


# ==================== HANDLERS ====================


async def handle_start(
    context: ConversationContext,
    message: str,
) -> ProcessedMessage:
    """
    Handler do estado inicial.
    Dá boas-vindas e oferece opções.
    """
    # Buscar ou criar cliente
    customer, is_new, has_complete_data = await get_or_create_customer(context.phone)
    context.customer_id = str(customer.id)
    context.customer_name = customer.name

    if is_new:
        greeting = (
            "👋 *Olá! Bem-vindo à Distribuidora de Gás!*\n\n"
            "Sou o assistente virtual e vou ajudar você a fazer seu pedido de gás.\n\n"
        )
    else:
        name = customer.name or "cliente"
        greeting = f"👋 *Olá, {name}!* Que bom ter você de volta!\n\n"

    # Buscar produtos ativos do banco de dados
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Product)
            .where(Product.is_active == True)
            .order_by(Product.code)
        )
        products = result.scalars().all()

    # Montar mensagem com produtos reais
    if not products:
        product_text = "⚠️ Nenhum produto disponível no momento."
        buttons = []
    else:
        product_lines = []
        buttons = []
        for p in products:
            price_str = f"R$ {p.price:.2f}".replace(".", ",")
            product_lines.append(f"🔵 *{p.code}* - {p.name} - {price_str}")
            buttons.append({"id": p.code, "text": f"{p.code} - {price_str}"})
        product_text = "\n".join(product_lines)

    context.state = ConversationState.AWAITING_PRODUCT

    return ProcessedMessage(
        context=context,
        responses=[
            MessageResponse(
                text=(
                    f"{greeting}"
                    "Qual produto você deseja?\n\n"
                    f"{product_text}"
                ),
                buttons=buttons,
                footer="Escolha uma opção acima" if buttons else "Entre em contato com o suporte",
            )
        ],
        new_state=ConversationState.AWAITING_PRODUCT,
    )


async def handle_awaiting_product(
    context: ConversationContext,
    message: str,
) -> ProcessedMessage:
    """
    Handler para seleção de produto.
    """
    # Tentar extrair codigo do produto (basico + NLP)
    product_code = extract_product_code(message)

    # Fallback: usar NLP com dicionario de sinonimos expandido
    if not product_code:
        product_code = extract_product(message)

    # Verificar se veio de pending_entities (extraido pelo flow_engine)
    if not product_code and context.pending_entities.get("product"):
        product_code = context.pending_entities["product"]

    if not product_code:
        # Incrementar tentativas
        context.increment_retry()

        if context.retry_count >= 3:
            # Muitas tentativas, oferecer ajuda
            context.retry_count = 0
            return ProcessedMessage(
                context=context,
                responses=[
                    MessageResponse(
                        text=(
                            "🤔 Não consegui entender sua escolha.\n\n"
                            "Por favor, escolha uma das opções abaixo:"
                        ),
                        buttons=[
                            {"id": "P13", "text": "P13 - R$ 110"},
                            {"id": "P20", "text": "P20 - R$ 150"},
                            {"id": "P45", "text": "P45 - R$ 280"},
                        ],
                    )
                ],
                new_state=ConversationState.AWAITING_PRODUCT,
            )

        return ProcessedMessage(
            context=context,
            responses=[
                MessageResponse(
                    text=(
                        "Por favor, escolha um produto:\n"
                        "• Digite *P13* para o botijão de 13kg\n"
                        "• Digite *P20* para o botijão de 20kg\n"
                        "• Digite *P45* para o botijão de 45kg"
                    ),
                )
            ],
            new_state=ConversationState.AWAITING_PRODUCT,
        )

    # Produto válido selecionado
    context.selected_product = product_code
    context.retry_count = 0
    
    # Buscar produto do banco de dados
    product = await get_product(product_code)
    if not product:
        return ProcessedMessage(
            context=context,
            responses=[
                MessageResponse(
                    text=f"❌ Produto {product_code} não encontrado. Por favor, escolha um produto válido."
                )
            ],
            new_state=ConversationState.AWAITING_PRODUCT,
        )

    context.state = ConversationState.AWAITING_QUANTITY

    return ProcessedMessage(
        context=context,
        responses=[
            MessageResponse(
                text=(
                    f"✅ *{product.name}* selecionado!\n"
                    f"💰 Valor unitário: {format_currency(product.price)}\n\n"
                    "Quantos botijões você deseja?"
                ),
                buttons=[
                    {"id": "qty_1", "text": "1 botijão"},
                    {"id": "qty_2", "text": "2 botijões"},
                    {"id": "qty_3", "text": "3 botijões"},
                ],
            )
        ],
        new_state=ConversationState.AWAITING_QUANTITY,
    )


async def handle_awaiting_quantity(
    context: ConversationContext,
    message: str,
) -> ProcessedMessage:
    """
    Handler para seleção de quantidade.
    """
    # Tentar extrair quantidade
    quantity = extract_quantity(message)

    # Verificar se é botão de quantidade
    if message.startswith("qty_"):
        quantity = int(message.replace("qty_", ""))

    if not quantity or quantity < 1 or quantity > 10:
        context.increment_retry()

        return ProcessedMessage(
            context=context,
            responses=[
                MessageResponse(
                    text="Por favor, informe uma quantidade entre 1 e 10 botijões.",
                    buttons=[
                        {"id": "qty_1", "text": "1 botijão"},
                        {"id": "qty_2", "text": "2 botijões"},
                        {"id": "qty_3", "text": "3 botijões"},
                    ],
                )
            ],
            new_state=ConversationState.AWAITING_QUANTITY,
        )

    context.selected_quantity = quantity
    context.retry_count = 0

    # Buscar produto do banco de dados
    product = await get_product(context.selected_product)
    if not product:
        return ProcessedMessage(
            context=context,
            responses=[
                MessageResponse(
                    text="❌ Produto não encontrado. Por favor, escolha um produto válido."
                )
            ],
            new_state=ConversationState.AWAITING_PRODUCT,
        )
    total = product.price * quantity

    # Verificar se cliente tem endereço cadastrado
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Customer).where(Customer.id == context.customer_id)
        )
        customer = result.scalar_one_or_none()

        if customer and customer.address:
            context.address = customer.address
            addr = customer.address
            address_text = f"{addr.get('street', '')}, {addr.get('number', '')}"
            if addr.get("complement"):
                address_text += f" - {addr['complement']}"
            address_text += f"\n{addr.get('bairro', '')} - {addr.get('city', 'Curitiba')}"

            context.state = ConversationState.CONFIRMING_ADDRESS

            return ProcessedMessage(
                context=context,
                responses=[
                    MessageResponse(
                        text=(
                            f"📦 *Resumo do Pedido*\n\n"
                            f"Produto: {product.name}\n"
                            f"Quantidade: {quantity}\n"
                            f"Total: *{format_currency(total)}*\n\n"
                            f"📍 *Endereço de entrega:*\n{address_text}\n\n"
                            "O endereço está correto?"
                        ),
                        buttons=[
                            {"id": "confirmar_end", "text": "✅ Sim, correto"},
                            {"id": "alterar_end", "text": "✏️ Alterar"},
                        ],
                    )
                ],
                new_state=ConversationState.CONFIRMING_ADDRESS,
            )

    # Cliente sem endereço
    context.state = ConversationState.AWAITING_ADDRESS

    return ProcessedMessage(
        context=context,
        responses=[
            MessageResponse(
                text=(
                    f"📦 Você selecionou:\n"
                    f"*{quantity}x {product.name}*\n"
                    f"Total: *{format_currency(total)}*\n\n"
                    "📍 Por favor, informe o *endereço completo* para entrega:\n\n"
                    "_Exemplo: Rua das Flores, 123 - Boqueirão_"
                )
            )
        ],
        new_state=ConversationState.AWAITING_ADDRESS,
    )


async def handle_confirming_address(
    context: ConversationContext,
    message: str,
) -> ProcessedMessage:
    """
    Handler para confirmação de endereço.
    """
    msg_lower = message.lower().strip()

    # Confirmar endereço
    if msg_lower in ["sim", "correto", "confirmar", "confirmar_end", "s", "1"] or "sim" in msg_lower:
        context.address_confirmed = True
        context.state = ConversationState.AWAITING_PAYMENT

        # Buscar produto do banco de dados
        product = await get_product(context.selected_product)
        if not product:
            return ProcessedMessage(
                context=context,
                responses=[
                    MessageResponse(
                        text="❌ Produto não encontrado. Por favor, escolha um produto válido."
                    )
                ],
                new_state=ConversationState.AWAITING_PRODUCT,
            )
        total = product.price * context.selected_quantity

        return ProcessedMessage(
            context=context,
            responses=[
                MessageResponse(
                    text=(
                        f"✅ Endereço confirmado!\n\n"
                        f"💰 *Total: {format_currency(total)}*\n\n"
                        "Como deseja pagar?"
                    ),
                    buttons=[
                        {"id": "pix", "text": "📱 Pix"},
                        {"id": "dinheiro", "text": "💵 Dinheiro"},
                        {"id": "cartao", "text": "💳 Cartão"},
                    ],
                )
            ],
            new_state=ConversationState.AWAITING_PAYMENT,
        )

    # Alterar endereço
    if msg_lower in ["alterar", "não", "nao", "alterar_end", "n", "2"] or "alterar" in msg_lower:
        context.state = ConversationState.AWAITING_ADDRESS
        context.address = None

        return ProcessedMessage(
            context=context,
            responses=[
                MessageResponse(
                    text=(
                        "📍 Por favor, informe o *endereço completo* para entrega:\n\n"
                        "_Exemplo: Rua das Flores, 123 - Boqueirão_"
                    )
                )
            ],
            new_state=ConversationState.AWAITING_ADDRESS,
        )

    # Não entendeu
    return ProcessedMessage(
        context=context,
        responses=[
            MessageResponse(
                text="Por favor, confirme se o endereço está correto:",
                buttons=[
                    {"id": "confirmar_end", "text": "✅ Sim, correto"},
                    {"id": "alterar_end", "text": "✏️ Alterar"},
                ],
            )
        ],
        new_state=ConversationState.CONFIRMING_ADDRESS,
    )


async def handle_awaiting_address(
    context: ConversationContext,
    message: str,
) -> ProcessedMessage:
    """
    Handler para recebimento de novo endereço.
    """
    # Validar endereço básico
    if len(message.strip()) < 10:
        return ProcessedMessage(
            context=context,
            responses=[
                MessageResponse(
                    text=(
                        "❌ Endereço muito curto.\n\n"
                        "Por favor, informe o endereço completo:\n"
                        "Rua, número, complemento e bairro.\n\n"
                        "_Exemplo: Rua das Flores, 123, apto 45 - Boqueirão_"
                    )
                )
            ],
            new_state=ConversationState.AWAITING_ADDRESS,
        )

    # Extrair bairro se possível
    bairro = None
    for b in settings.supported_bairros:
        if b.lower() in message.lower():
            bairro = b
            break

    # Salvar endereço
    context.address = {
        "full_address": message.strip(),
        "bairro": bairro,
    }

    # Atualizar cliente no banco
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Customer).where(Customer.id == context.customer_id)
        )
        customer = result.scalar_one_or_none()
        if customer:
            customer.address = context.address
            await db.commit()

    context.address_confirmed = True
    context.state = ConversationState.AWAITING_PAYMENT

    # Buscar produto do banco de dados
    product = await get_product(context.selected_product)
    if not product:
        return ProcessedMessage(
            context=context,
            responses=[
                MessageResponse(
                    text="❌ Produto não encontrado. Por favor, escolha um produto válido."
                )
            ],
            new_state=ConversationState.AWAITING_PRODUCT,
        )
    total = product.price * context.selected_quantity

    return ProcessedMessage(
        context=context,
        responses=[
            MessageResponse(
                text=(
                    f"✅ Endereço registrado!\n"
                    f"📍 {message.strip()}\n\n"
                    f"💰 *Total: {format_currency(total)}*\n\n"
                    "Como deseja pagar?"
                ),
                buttons=[
                    {"id": "dinheiro", "text": "💵 Dinheiro"},
                    {"id": "cartao", "text": "💳 Cartão"},
                ],
            )
        ],
        new_state=ConversationState.AWAITING_PAYMENT,
    )


async def _payment_selected_maybe_ask_document(
    context: ConversationContext,
    product,
    total,
) -> ProcessedMessage:
    """
    Apos selecionar pagamento: se cliente tem CPF/CNPJ, mostra resumo.
    Se nao tem, pede documento (COLLECTING_DOCUMENT).
    """
    customer = await _get_customer(context.customer_id)
    if customer and customer.cpf_cnpj:
        doc = customer.cpf_cnpj
        doc_type = "CNPJ" if len(doc) == 14 else "CPF"
        masked = _format_cpf_cnpj(doc)
        return await _show_order_summary_for_confirmation(context, doc_type, masked)

    customer_type = context.customer_type or "PF"
    if customer_type == "PJ":
        doc_text = "Para finalizar, preciso do *CNPJ* da empresa:\n_(apenas numeros)_"
    else:
        doc_text = "Para finalizar, preciso do seu *CPF*:\n_(apenas numeros)_"

    payment_label = "Dinheiro" if context.payment_method == "cash" else "Cartao"
    context.state = ConversationState.COLLECTING_DOCUMENT

    return ProcessedMessage(
        context=context,
        responses=[
            MessageResponse(
                text=f"Pagamento: {payment_label}\n\n{doc_text}"
            )
        ],
        new_state=ConversationState.COLLECTING_DOCUMENT,
    )


async def handle_awaiting_payment(
    context: ConversationContext,
    message: str,
) -> ProcessedMessage:
    """
    Handler para seleção de método de pagamento.
    Apos escolher, vai para COLLECTING_DOCUMENT se nao tem CPF/CNPJ.
    """
    msg_lower = message.lower().strip()

    # Buscar produto do banco de dados
    product = await get_product(context.selected_product)
    if not product:
        return ProcessedMessage(
            context=context,
            responses=[
                MessageResponse(
                    text="❌ Produto não encontrado. Por favor, escolha um produto válido."
                )
            ],
            new_state=ConversationState.AWAITING_PRODUCT,
        )
    total = product.price * context.selected_quantity

    # Pix (DESCONTINUADO)
    if msg_lower in ["pix", "1"] or "pix" in msg_lower:
        return ProcessedMessage(
            context=context,
            responses=[
                MessageResponse(
                    text=(
                        "⚠️ Pagamento via Pix foi descontinuado.\n\n"
                        "Por favor, escolha outra forma de pagamento:"
                    ),
                    buttons=[
                        {"id": "dinheiro", "text": "💵 Dinheiro"},
                        {"id": "cartao", "text": "💳 Cartão"},
                    ],
                )
            ],
            new_state=ConversationState.AWAITING_PAYMENT,
        )

    # Dinheiro
    if msg_lower in ["dinheiro", "2"] or "dinheiro" in msg_lower:
        context.payment_method = "cash"
        return await _payment_selected_maybe_ask_document(context, product, total)

    # Cartão
    if msg_lower in ["cartao", "cartão", "3"] or "cart" in msg_lower:
        context.payment_method = "credit_card"
        return await _payment_selected_maybe_ask_document(context, product, total)

    # Não entendeu
    return ProcessedMessage(
        context=context,
        responses=[
            MessageResponse(
                text="Por favor, escolha uma forma de pagamento:",
                buttons=[
                    {"id": "dinheiro", "text": "💵 Dinheiro"},
                    {"id": "cartao", "text": "💳 Cartão"},
                ],
            )
        ],
        new_state=ConversationState.AWAITING_PAYMENT,
    )


async def handle_awaiting_pix(
    context: ConversationContext,
    message: str,
) -> ProcessedMessage:
    """
    Handler para confirmação de pagamento Pix.
    """
    # Pix foi descontinuado. Se alguém cair nesse estado (conversa antiga),
    # voltamos para a seleção de pagamento sem quebrar o fluxo.
    return ProcessedMessage(
        context=context,
        responses=[
            MessageResponse(
                text=(
                    "⚠️ Pagamento via Pix foi descontinuado.\n\n"
                    "Escolha uma forma de pagamento na entrega:"
                ),
                buttons=[
                    {"id": "dinheiro", "text": "💵 Dinheiro"},
                    {"id": "cartao", "text": "💳 Cartão"},
                ],
            )
        ],
        new_state=ConversationState.AWAITING_PAYMENT,
    )


async def handle_order_confirmed(
    context: ConversationContext,
    message: str,
) -> ProcessedMessage:
    """
    Handler após confirmação do pedido.
    """
    msg_lower = message.lower().strip()

    # Verificar status
    if "status" in msg_lower or "pedido" in msg_lower:
        return await handle_tracking_order(context, message)

    # Novo pedido
    context.reset()
    return await handle_start(context, message)


async def handle_confirming_order(
    context: ConversationContext,
    message: str,
) -> ProcessedMessage:
    """
    Handler para confirmar pedido com cartão.
    """
    msg_lower = message.lower().strip()

    # Buscar produto do banco de dados
    product = await get_product(context.selected_product)
    if not product:
        return ProcessedMessage(
            context=context,
            responses=[
                MessageResponse(
                    text="❌ Produto não encontrado. Por favor, escolha um produto válido."
                )
            ],
            new_state=ConversationState.AWAITING_PRODUCT,
        )
    total = product.price * context.selected_quantity

    # Confirmar pedido
    if msg_lower in ["confirmar", "confirmar_cartao", "1", "sim"] or "confirm" in msg_lower:
        context.payment_method = "credit_card"

        # Criar pedido
        order = await create_order(context, total)
        context.order_id = str(order.id)
        context.state = ConversationState.ORDER_CONFIRMED

        # Emitir evento WebSocket de novo pedido
        try:
            from app.api.websocket import emit_new_order
            order_data = {
                "id": str(order.id),
                "order_number": order.order_number,
                "customer_id": str(context.customer_id),
                "status": order.status,
                "total_amount": float(order.total_amount),
                "payment_method": context.payment_method,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "product": product.name,
                "quantity": context.selected_quantity,
                "address": context.address.get("full_address", ""),
            }
            await emit_new_order(order_data)
            logger.info(f"Evento WebSocket emitido para novo pedido: #{order.order_number}")
        except Exception as e:
            logger.error(f"Erro ao emitir evento WebSocket de novo pedido: {e}")

        return ProcessedMessage(
            context=context,
            responses=[
                MessageResponse(
                    text=(
                        f"✅ *Pedido Confirmado!*\n\n"
                        f"📦 Pedido #{order.order_number}\n"
                        f"Produto: {context.selected_quantity}x {product.name}\n"
                        f"Total: *{format_currency(total)}*\n"
                        f"Pagamento: 💳 Cartão na entrega\n\n"
                        f"📍 Entrega em: {context.address.get('full_address', context.address.get('bairro', 'Endereço cadastrado'))}\n"
                        f"⏱️ Previsão: *{settings.default_delivery_time_minutes} minutos*\n\n"
                        "Você receberá atualizações sobre sua entrega!"
                    ),
                    footer="Obrigado pela preferência! 🔥",
                )
            ],
            new_state=ConversationState.ORDER_CONFIRMED,
        )

    # Voltar
    if msg_lower in ["voltar", "voltar_pagamento", "2"] or "volt" in msg_lower:
        return await handle_awaiting_payment(context, "")

    # Não entendeu
    return ProcessedMessage(
        context=context,
        responses=[
            MessageResponse(
                text=(
                    "💳 *Pagamento com Cartão*\n\n"
                    "O pagamento com cartão será feito na entrega.\n"
                    "Aceitamos débito e crédito.\n\n"
                    "Deseja confirmar o pedido?"
                ),
                buttons=[
                    {"id": "confirmar_cartao", "text": "✅ Confirmar"},
                    {"id": "voltar_pagamento", "text": "🔙 Voltar"},
                ],
            )
        ],
        new_state=ConversationState.CONFIRMING_ORDER,
    )


async def handle_tracking_order(
    context: ConversationContext,
    message: str,
) -> ProcessedMessage:
    """
    Handler para rastreamento de pedido.
    Busca pedidos recentes do cliente e exibe status.
    """
    # Buscar pedidos recentes do cliente
    orders_text = ""
    try:
        async with AsyncSessionLocal() as db:
            from sqlalchemy import desc
            result = await db.execute(
                select(Order)
                .where(Order.customer_id == context.customer_id)
                .order_by(desc(Order.created_at))
                .limit(5)
            )
            orders = result.scalars().all()

            if orders:
                orders_text = "📦 *Seus Pedidos Recentes*\n\n"
                status_emoji = {
                    OrderStatus.PENDING.value: "⏳",
                    OrderStatus.PAID.value: "✅",
                    OrderStatus.PREPARING.value: "🔧",
                    OrderStatus.DISPATCHED.value: "🚚",
                    OrderStatus.DELIVERED.value: "📬",
                    OrderStatus.CANCELLED.value: "❌",
                }
                status_label = {
                    OrderStatus.PENDING.value: "Aguardando pagamento",
                    OrderStatus.PAID.value: "Pago",
                    OrderStatus.PREPARING.value: "Em preparação",
                    OrderStatus.DISPATCHED.value: "Saiu para entrega",
                    OrderStatus.DELIVERED.value: "Entregue",
                    OrderStatus.CANCELLED.value: "Cancelado",
                }

                for order in orders:
                    emoji = status_emoji.get(order.status, "📦")
                    label = status_label.get(order.status, order.status)
                    date_str = order.created_at.strftime("%d/%m %H:%M") if order.created_at else ""
                    orders_text += (
                        f"{emoji} *Pedido #{order.order_number}*\n"
                        f"   Status: {label}\n"
                        f"   Total: {format_currency(order.total_amount)}\n"
                        f"   Data: {date_str}\n\n"
                    )

                orders_text += "Digite *menu* para fazer um novo pedido."
            else:
                orders_text = (
                    "📦 *Seus Pedidos*\n\n"
                    "Você ainda não fez nenhum pedido.\n\n"
                    "Digite *menu* para fazer seu primeiro pedido!"
                )

    except Exception as e:
        logger.error(f"Erro ao buscar pedidos do cliente: {e}")
        orders_text = (
            "📦 *Seus Pedidos*\n\n"
            "Não foi possível buscar seus pedidos no momento.\n\n"
            "Digite *menu* para fazer um novo pedido."
        )

    return ProcessedMessage(
        context=context,
        responses=[
            MessageResponse(text=orders_text)
        ],
        new_state=ConversationState.START,
    )


async def handle_talking_to_human(
    context: ConversationContext,
    message: str,
) -> ProcessedMessage:
    """
    Handler quando transferido para atendente.
    Notifica operadores via WebSocket.
    """
    # Notificar operador via WebSocket
    try:
        from app.api.websocket import emit_new_message

        # Buscar dados do cliente para contexto
        customer_data = None
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Customer).where(Customer.id == context.customer_id)
            )
            customer = result.scalar_one_or_none()
            if customer:
                customer_data = {
                    "id": str(customer.id),
                    "name": customer.name,
                    "phone": customer.phone,
                    "bairro": customer.address.get("bairro") if customer.address else None,
                }

        await emit_new_message(
            phone=context.phone,
            message=f"🔔 ATENDIMENTO HUMANO SOLICITADO\n{message}",
            direction="incoming",
            customer_data=customer_data,
        )
        logger.info(f"Notificação enviada para operadores: atendimento humano solicitado por {context.phone}")

    except Exception as e:
        logger.error(f"Erro ao notificar operadores via WebSocket: {e}")

    return ProcessedMessage(
        context=context,
        responses=[
            MessageResponse(
                text=(
                    "👤 Você está em atendimento humano.\n\n"
                    "Um de nossos atendentes responderá em breve.\n\n"
                    "Digite *menu* para voltar ao atendimento automático."
                )
            )
        ],
        new_state=ConversationState.TALKING_TO_HUMAN,
    )


# ==================== HANDLERS CONVERSACIONAIS (NLP) ====================


async def handle_greeting(
    context: ConversationContext,
    message: str,
) -> ProcessedMessage:
    """
    Saudacao inteligente: diferencia cliente novo, recorrente e incompleto.
    - NOVO: pede nome -> CPF -> produtos
    - RECORRENTE (dados completos): oferece "o de sempre" ou produtos
    - INCOMPLETO: pede o que falta (nome ou CPF)
    """
    customer, is_new, has_complete_data = await get_or_create_customer(context.phone)
    context.customer_id = str(customer.id)
    context.customer_name = customer.name
    context.is_new_customer = is_new
    context.has_complete_data = has_complete_data

    # ========== CENARIO 1: Cliente NOVO - perguntar PF ou Empresa ==========
    has_name = bool(customer.name and len(customer.name.strip()) > 2)
    if is_new and not has_name:
        context.state = ConversationState.ASKING_CUSTOMER_TYPE
        return ProcessedMessage(
            context=context,
            responses=[
                MessageResponse(
                    text=(
                        "Ola! Bem-vindo a *GasMaster*!\n\n"
                        "Sou o assistente virtual e vou te ajudar.\n\n"
                        "Para comecar, voce e:"
                    ),
                    buttons=[
                        {"id": "PF", "text": "Pessoa Fisica"},
                        {"id": "PJ", "text": "Empresa"},
                    ],
                )
            ],
            new_state=ConversationState.ASKING_CUSTOMER_TYPE,
        )

    # ========== CENARIO 2: Cliente RECORRENTE com nome ==========
    if has_name:
        context.customer_type = customer.tipo_documento or "PF"
        last_order = await _get_last_order(customer)
        if last_order:
            # Oferecer atalho "o de sempre"
            last_items = await _get_order_items(last_order)
            if last_items:
                item = last_items[0]
                addr_text = _format_address(customer.address) if customer.address else "endereco cadastrado"
                context.state = ConversationState.START

                return ProcessedMessage(
                    context=context,
                    responses=[
                        MessageResponse(
                            text=(
                                f"Oi {customer.name}!\n\n"
                                f"Quer o de sempre? {item.quantity}x {item.product_code} "
                                f"no endereco {addr_text}?\n"
                            ),
                            buttons=[
                                {"id": "repeat_order", "text": "Sim, o de sempre"},
                                {"id": "fazer_pedido", "text": "Outro pedido"},
                                {"id": "falar_atendente", "text": "Falar com alguem"},
                            ],
                        )
                    ],
                    new_state=ConversationState.START,
                )
        # Tem nome mas sem ultimo pedido - cai no bloco de produtos abaixo

    # ========== CENARIO 3: Cliente INCOMPLETO (existe mas falta nome) ==========
    if not has_name:
        context.state = ConversationState.COLLECTING_NAME
        return ProcessedMessage(
            context=context,
            responses=[
                MessageResponse(
                    text=(
                        "Ola! Vi que voce ja entrou em contato antes.\n\n"
                        "Para agilizar seu pedido, qual e o seu *nome completo*?"
                    )
                )
            ],
            new_state=ConversationState.COLLECTING_NAME,
        )

    # Cliente recorrente (sem ultimo pedido): mostrar produtos
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Product)
            .where(Product.is_active == True)
            .order_by(Product.code)
        )
        products = result.scalars().all()

    if not products:
        product_text = "Nenhum produto disponivel no momento."
        buttons = []
    else:
        product_lines = []
        buttons = []
        for p in products:
            price_str = f"R$ {p.price:.2f}".replace(".", ",")
            product_lines.append(f"*{p.code}* ({p.weight_kg}kg) - {price_str}")
            buttons.append({"id": p.code, "text": f"{p.code} - {price_str}"})
        product_text = "\n".join(product_lines)

    greeting_name = customer.name if customer and customer.name else ""
    greeting = f"Oi {greeting_name}!\n\n" if greeting_name else "Ola!\n\n"

    # Se ja extraiu produto da mensagem, pular para coleta
    if context.pending_entities.get("product"):
        return await handle_collect_missing_data(context, message)

    context.state = ConversationState.AWAITING_PRODUCT

    return ProcessedMessage(
        context=context,
        responses=[
            MessageResponse(
                text=(
                    f"{greeting}"
                    "Qual botijao voce precisa?\n\n"
                    f"{product_text}"
                ),
                buttons=buttons,
            )
        ],
        new_state=ConversationState.AWAITING_PRODUCT,
    )


# ---------- Handler: ASKING_CUSTOMER_TYPE ----------

async def handle_asking_customer_type(
    context: ConversationContext,
    message: str,
) -> ProcessedMessage:
    """
    Handler para perguntar se cliente e PF ou Empresa.
    """
    msg = message.lower().strip()

    is_pf = any(x in msg for x in ["pf", "fisica", "física", "pessoa", "1"])
    is_pj = any(x in msg for x in ["pj", "empresa", "juridica", "jurídica", "cnpj", "2"])

    if is_pj:
        context.customer_type = "PJ"
        context.state = ConversationState.COLLECTING_NAME
        return ProcessedMessage(
            context=context,
            responses=[
                MessageResponse(
                    text="Certo! Qual o *nome da empresa*?"
                )
            ],
            new_state=ConversationState.COLLECTING_NAME,
        )

    if is_pf:
        context.customer_type = "PF"
        context.state = ConversationState.COLLECTING_NAME
        return ProcessedMessage(
            context=context,
            responses=[
                MessageResponse(
                    text="Certo! Qual o seu *nome completo*?"
                )
            ],
            new_state=ConversationState.COLLECTING_NAME,
        )

    context.increment_retry()
    if context.retry_count >= 2:
        context.customer_type = "PF"
        context.retry_count = 0
        context.state = ConversationState.COLLECTING_NAME
        return ProcessedMessage(
            context=context,
            responses=[
                MessageResponse(
                    text="Vou continuar como pessoa fisica.\n\nQual o seu *nome completo*?"
                )
            ],
            new_state=ConversationState.COLLECTING_NAME,
        )

    return ProcessedMessage(
        context=context,
        responses=[
            MessageResponse(
                text="Por favor, escolha uma opcao:",
                buttons=[
                    {"id": "PF", "text": "Pessoa Fisica"},
                    {"id": "PJ", "text": "Empresa"},
                ],
            )
        ],
        new_state=ConversationState.ASKING_CUSTOMER_TYPE,
    )


# ---------- Validacao CPF/CNPJ ----------

def _validate_cpf(cpf: str) -> bool:
    """Valida CPF brasileiro."""
    cpf = re.sub(r"[^0-9]", "", cpf)
    if len(cpf) != 11:
        return False
    if cpf == cpf[0] * 11:
        return False
    for i in range(9, 11):
        value = sum((int(cpf[num]) * ((i + 1) - num) for num in range(0, i)))
        digit = ((value * 10) % 11) % 10
        if digit != int(cpf[i]):
            return False
    return True


def _validate_cnpj(cnpj: str) -> bool:
    """Valida CNPJ brasileiro (simplificado)."""
    cnpj = re.sub(r"[^0-9]", "", cnpj)
    if len(cnpj) != 14:
        return False
    if cnpj == cnpj[0] * 14:
        return False
    return True


def _format_cpf_cnpj(value: str) -> str:
    """Formata CPF ou CNPJ para exibicao parcial."""
    clean = re.sub(r"[^0-9]", "", value)
    if len(clean) == 11:
        return f"***.{clean[3:6]}.{clean[6:9]}-**"
    if len(clean) == 14:
        return f"**.{clean[2:5]}.{clean[5:8]}/{clean[8:12]}-**"
    return value


async def handle_collecting_name(
    context: ConversationContext,
    message: str,
) -> ProcessedMessage:
    """
    Handler para coletar nome do cliente ou empresa.
    Apos coletar, vai DIRETO para produtos (CPF/CNPJ sera pedido antes de confirmar).
    """
    name = message.strip()

    if len(name) < 2:
        return ProcessedMessage(
            context=context,
            responses=[
                MessageResponse(
                    text="Nome muito curto. Por favor, digite o nome completo:"
                )
            ],
            new_state=ConversationState.COLLECTING_NAME,
        )

    if len(name) > 100:
        name = name[:100]

    name = name.title()

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Customer).where(Customer.phone == context.phone)
        )
        customer = result.scalar_one_or_none()
        if customer:
            customer.name = name
            if context.customer_type:
                customer.tipo_documento = context.customer_type
            await db.commit()
            logger.info(f"Nome salvo para cliente {customer.id}: {name}")

    context.customer_name = name
    if not context.customer_type:
        context.customer_type = "PF"

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Product)
            .where(Product.is_active == True)
            .order_by(Product.code)
        )
        products = result.scalars().all()

    if not products:
        product_text = "Nenhum produto disponivel no momento."
        buttons = []
    else:
        product_lines = []
        buttons = []
        for p in products:
            price_str = f"R$ {p.price:.2f}".replace(".", ",")
            product_lines.append(f"*{p.code}* ({p.weight_kg}kg) - {price_str}")
            buttons.append({"id": p.code, "text": f"{p.code} - {price_str}"})
        product_text = "\n".join(product_lines)

    greeting = f"Prazer, *{name}*!"

    context.state = ConversationState.AWAITING_PRODUCT

    return ProcessedMessage(
        context=context,
        responses=[
            MessageResponse(
                text=(
                    f"{greeting}\n\n"
                    "Qual botijao voce precisa?\n\n"
                    f"{product_text}"
                ),
                buttons=buttons,
            )
        ],
        new_state=ConversationState.AWAITING_PRODUCT,
    )


async def _show_order_summary_for_confirmation(
    context: ConversationContext,
    doc_type: str,
    masked_doc: str,
) -> ProcessedMessage:
    """Mostra resumo do pedido com documento para confirmacao final."""
    product = await get_product(context.selected_product)
    if not product:
        return await handle_collect_missing_data(context, "")

    total = product.price * context.selected_quantity
    address_text = _format_address(context.address) if context.address else "Endereco cadastrado"

    payment_labels = {"cash": "Dinheiro", "credit_card": "Cartao", "debit_card": "Cartao", "pix": "PIX"}
    payment_text = payment_labels.get(context.payment_method, context.payment_method or "")
    if context.payment_method == "cash" and context.change_for:
        payment_text += f" (troco p/ R$ {context.change_for})"

    context.awaiting_confirmation = True
    context.state = ConversationState.CONFIRMING_ORDER

    return ProcessedMessage(
        context=context,
        responses=[
            MessageResponse(
                text=(
                    f"*Resumo do Pedido*\n\n"
                    f"- {context.customer_name}\n"
                    f"- {doc_type}: {masked_doc}\n\n"
                    f"- {context.selected_quantity}x {product.code} - {format_currency(total)}\n"
                    f"- Entrega: {address_text}\n"
                    f"- Pagamento: {payment_text}\n\n"
                    "Tudo certo?"
                ),
                buttons=[
                    {"id": "confirm", "text": "Confirmar"},
                    {"id": "edit", "text": "Alterar"},
                    {"id": "cancel", "text": "Cancelar"},
                ],
            )
        ],
        new_state=ConversationState.CONFIRMING_ORDER,
    )


async def handle_collecting_document(
    context: ConversationContext,
    message: str,
) -> ProcessedMessage:
    """
    Handler para coletar CPF (PF) ou CNPJ (PJ) ANTES de confirmar pedido.
    Chamado apos selecao de pagamento, quando cliente nao tem documento cadastrado.
    """
    doc = re.sub(r"[^0-9]", "", message)
    customer_type = context.customer_type or "PF"

    if customer_type == "PJ":
        if len(doc) != 14:
            return ProcessedMessage(
                context=context,
                responses=[
                    MessageResponse(
                        text="CNPJ invalido. Digite os *14 numeros* do CNPJ:"
                    )
                ],
                new_state=ConversationState.COLLECTING_DOCUMENT,
            )
        if not _validate_cnpj(doc):
            return ProcessedMessage(
                context=context,
                responses=[
                    MessageResponse(text="CNPJ invalido. Verifique e digite novamente:")
                ],
                new_state=ConversationState.COLLECTING_DOCUMENT,
            )
        doc_type = "CNPJ"
        masked_doc = f"**.{doc[2:5]}.{doc[5:8]}/{doc[8:12]}-**"
    else:
        if len(doc) != 11:
            return ProcessedMessage(
                context=context,
                responses=[
                    MessageResponse(
                        text="CPF invalido. Digite os *11 numeros* do CPF:"
                    )
                ],
                new_state=ConversationState.COLLECTING_DOCUMENT,
            )
        if not _validate_cpf(doc):
            return ProcessedMessage(
                context=context,
                responses=[
                    MessageResponse(text="CPF invalido. Verifique e digite novamente:")
                ],
                new_state=ConversationState.COLLECTING_DOCUMENT,
            )
        doc_type = "CPF"
        masked_doc = f"***.{doc[3:6]}.{doc[6:9]}-**"

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Customer).where(Customer.phone == context.phone)
        )
        customer = result.scalar_one_or_none()
        if customer:
            customer.cpf_cnpj = doc
            await db.commit()

    return await _show_order_summary_for_confirmation(context, doc_type, masked_doc)


async def handle_collect_missing_data(
    context: ConversationContext,
    message: str,
) -> ProcessedMessage:
    """
    Coleta inteligente: pergunta apenas o que falta, na ordem de prioridade.
    Permite que o cliente forneca multiplos dados em uma unica mensagem.
    """
    pe = context.pending_entities

    # Garantir que temos customer_id
    if not context.customer_id:
        customer, _, _ = await get_or_create_customer(context.phone)
        context.customer_id = str(customer.id)
        context.customer_name = customer.name

    # Consolidar dados pendentes no contexto
    if pe.get("product") and not context.selected_product:
        context.selected_product = pe["product"]
    if pe.get("quantity"):
        context.selected_quantity = pe["quantity"]
    # Quantidade padrao 1 quando temos produto
    if context.selected_product and not context.selected_quantity:
        context.selected_quantity = 1
    if pe.get("payment"):
        context.payment_method = pe["payment"]
    if pe.get("change_for"):
        context.change_for = pe["change_for"]
    if pe.get("address_raw") and not context.address:
        bairro = pe.get("bairro")
        context.address = {
            "full_address": pe["address_raw"],
            "bairro": bairro,
        }
        context.address_confirmed = True

    # 1. Falta produto?
    if not context.selected_product:
        context.awaiting_input_type = "product"
        context.state = ConversationState.AWAITING_PRODUCT

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Product)
                .where(Product.is_active == True)
                .order_by(Product.code)
            )
            products = result.scalars().all()

        buttons = []
        product_lines = []
        for p in products:
            price_str = f"R$ {p.price:.2f}".replace(".", ",")
            product_lines.append(f"*{p.code}* ({p.weight_kg}kg) - {price_str}")
            buttons.append({"id": p.code, "text": f"{p.code} - {price_str}"})

        return ProcessedMessage(
            context=context,
            responses=[
                MessageResponse(
                    text=(
                        "Qual botijao voce precisa?\n\n"
                        + "\n".join(product_lines)
                    ),
                    buttons=buttons,
                )
            ],
            new_state=ConversationState.AWAITING_PRODUCT,
        )

    # 2. Falta quantidade? (se nao veio explicitamente, assume 1)
    # Quantidade default eh 1, entao so pergunta se nao extraiu
    if not pe.get("quantity") and context.selected_quantity == 1 and context.awaiting_input_type != "quantity_confirmed":
        # Se veio junto com produto, pode pular
        pass  # Aceita default de 1

    # 3. Falta endereco?
    if not context.address:
        # Verificar se cliente tem endereco no cadastro
        customer = await _get_customer(context.customer_id)
        if customer and customer.address:
            context.address = customer.address
            context.address_confirmed = True
        else:
            context.awaiting_input_type = "address"
            context.state = ConversationState.AWAITING_ADDRESS

            return ProcessedMessage(
                context=context,
                responses=[
                    MessageResponse(
                        text=(
                            "Qual o endereco de entrega?\n"
                            "(Ex: Rua das Flores, 123 - Boqueirao)"
                        )
                    )
                ],
                new_state=ConversationState.AWAITING_ADDRESS,
            )

    # 4. Falta pagamento?
    if not context.payment_method:
        context.awaiting_input_type = "payment"
        context.state = ConversationState.AWAITING_PAYMENT

        return ProcessedMessage(
            context=context,
            responses=[
                MessageResponse(
                    text="Como prefere pagar?",
                    buttons=[
                        {"id": "dinheiro", "text": "Dinheiro"},
                        {"id": "cartao", "text": "Cartao"},
                    ],
                )
            ],
            new_state=ConversationState.AWAITING_PAYMENT,
        )

    # Tudo coletado - mostrar confirmacao
    return await handle_show_confirmation(context, message)


async def handle_show_confirmation(
    context: ConversationContext,
    message: str,
) -> ProcessedMessage:
    """
    Mostra resumo completo do pedido para confirmacao final.
    """
    pe = context.pending_entities

    product_code = context.selected_product or pe.get("product")
    quantity = context.selected_quantity or pe.get("quantity", 1)
    payment = context.payment_method or pe.get("payment", "cash")

    if not product_code:
        return await handle_collect_missing_data(context, message)

    product = await get_product(product_code)
    if not product:
        context.selected_product = None
        return await handle_collect_missing_data(context, message)

    # Calcular total
    total = product.price * quantity

    # Formatar endereco
    address_text = _format_address(context.address) if context.address else "Endereco cadastrado"

    # Formatar pagamento
    payment_labels = {
        "cash": "Dinheiro",
        "credit_card": "Cartao de Credito",
        "debit_card": "Cartao de Debito",
        "pix": "PIX",
    }
    payment_text = payment_labels.get(payment, payment)

    if payment == "cash" and context.change_for:
        payment_text += f" (troco p/ R$ {context.change_for})"

    # Salvar dados finais no contexto
    context.selected_product = product_code
    context.selected_quantity = quantity
    context.payment_method = payment
    context.awaiting_confirmation = True
    context.state = ConversationState.CONFIRMING_ORDER

    return ProcessedMessage(
        context=context,
        responses=[
            MessageResponse(
                text=(
                    f"*Resumo do Pedido*\n\n"
                    f"- {quantity}x {product.code} ({product.name}) - {format_currency(total)}\n"
                    f"- Entrega: {address_text}\n"
                    f"- Pagamento: {payment_text}\n\n"
                    "Tudo certo?"
                ),
                buttons=[
                    {"id": "confirm", "text": "Confirmar"},
                    {"id": "edit", "text": "Alterar"},
                    {"id": "cancel", "text": "Cancelar"},
                ],
            )
        ],
        new_state=ConversationState.CONFIRMING_ORDER,
    )


async def handle_confirm_order(
    context: ConversationContext,
    message: str,
) -> ProcessedMessage:
    """
    Confirma pedido apos resumo - cria Order no banco e emite WebSocket.
    """
    product = await get_product(context.selected_product)
    if not product:
        context.reset()
        return await handle_start(context, message)

    total = product.price * context.selected_quantity

    # Criar pedido no banco
    order = await create_order(context, total)
    context.order_id = str(order.id)
    context.state = ConversationState.ORDER_CONFIRMED
    context.awaiting_confirmation = False

    # Emitir evento WebSocket
    try:
        from app.api.websocket import emit_new_order
        order_data = {
            "id": str(order.id),
            "order_number": order.order_number,
            "customer_id": str(context.customer_id),
            "status": order.status,
            "total_amount": float(order.total_amount),
            "payment_method": context.payment_method,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "product": product.name,
            "quantity": context.selected_quantity,
            "address": context.address.get("full_address", "") if context.address else "",
        }
        await emit_new_order(order_data)
        logger.info(f"WebSocket: novo pedido #{order.order_number}")
    except Exception as e:
        logger.error(f"Erro WebSocket novo pedido: {e}")

    # Formatar pagamento
    payment_labels = {
        "cash": "Dinheiro na entrega",
        "credit_card": "Cartao na entrega",
        "debit_card": "Cartao de debito na entrega",
        "pix": "PIX",
    }
    payment_text = payment_labels.get(context.payment_method, context.payment_method)
    addr_text = context.address.get("full_address", "") if context.address else "Endereco cadastrado"
    name = context.customer_name or ""
    thanks = f"\nObrigado, {name}!" if name else "\nObrigado pela preferencia!"

    return ProcessedMessage(
        context=context,
        responses=[
            MessageResponse(
                text=(
                    f"Pedido #{order.order_number} confirmado!\n\n"
                    f"- {context.selected_quantity}x {product.name} - {format_currency(total)}\n"
                    f"- Entrega: {addr_text}\n"
                    f"- Pagamento: {payment_text}\n\n"
                    f"Previsao de entrega: {settings.default_delivery_time_minutes} minutos\n"
                    f"Acompanhe pelo WhatsApp ou digite 'status'"
                    f"{thanks}"
                ),
            )
        ],
        new_state=ConversationState.ORDER_CONFIRMED,
    )


async def handle_edit_order(
    context: ConversationContext,
    message: str,
) -> ProcessedMessage:
    """
    Permite alterar campo especifico do pedido antes da confirmacao.
    """
    context.awaiting_confirmation = False
    field = detect_edit_field(message)

    if field == "product":
        context.selected_product = None
        context.pending_entities.pop("product", None)
        return await handle_collect_missing_data(context, message)

    if field == "quantity":
        context.selected_quantity = 1
        context.pending_entities.pop("quantity", None)
        context.awaiting_input_type = "quantity"
        context.state = ConversationState.AWAITING_QUANTITY

        return ProcessedMessage(
            context=context,
            responses=[
                MessageResponse(
                    text=f"Quantos botijoes {context.selected_product} voce quer?",
                    buttons=[
                        {"id": "qty_1", "text": "1"},
                        {"id": "qty_2", "text": "2"},
                        {"id": "qty_3", "text": "3"},
                    ],
                )
            ],
            new_state=ConversationState.AWAITING_QUANTITY,
        )

    if field == "address":
        context.address = None
        context.address_confirmed = False
        context.pending_entities.pop("address_raw", None)
        context.pending_entities.pop("bairro", None)
        context.state = ConversationState.AWAITING_ADDRESS

        return ProcessedMessage(
            context=context,
            responses=[
                MessageResponse(
                    text=(
                        "Qual o novo endereco de entrega?\n"
                        "(Ex: Rua das Flores, 123 - Boqueirao)"
                    )
                )
            ],
            new_state=ConversationState.AWAITING_ADDRESS,
        )

    if field == "payment":
        context.payment_method = None
        context.pending_entities.pop("payment", None)
        context.state = ConversationState.AWAITING_PAYMENT

        return ProcessedMessage(
            context=context,
            responses=[
                MessageResponse(
                    text="Como prefere pagar?",
                    buttons=[
                        {"id": "dinheiro", "text": "Dinheiro"},
                        {"id": "cartao", "text": "Cartao"},
                    ],
                )
            ],
            new_state=ConversationState.AWAITING_PAYMENT,
        )

    # Campo nao especificado: mostrar opcoes
    return ProcessedMessage(
        context=context,
        responses=[
            MessageResponse(
                text="O que voce quer alterar?",
                buttons=[
                    {"id": "edit_product", "text": "Produto"},
                    {"id": "edit_quantity", "text": "Quantidade"},
                    {"id": "edit_address", "text": "Endereco"},
                ],
            )
        ],
        new_state=ConversationState.CONFIRMING_ORDER,
    )


async def handle_not_understood(
    context: ConversationContext,
    message: str,
) -> ProcessedMessage:
    """
    Recuperacao graciosa quando nao entende a mensagem.
    3 niveis: reformula -> botoes -> transfere para humano.
    """
    context.increment_retry()

    if context.retry_count <= 1:
        return ProcessedMessage(
            context=context,
            responses=[
                MessageResponse(
                    text=(
                        "Nao consegui entender. Voce quer:\n\n"
                        "- Comprar gas?\n"
                        "- Ver status de um pedido?\n"
                        "- Falar com atendente?"
                    ),
                    buttons=[
                        {"id": "fazer_pedido", "text": "Comprar gas"},
                        {"id": "ver_pedido", "text": "Ver pedido"},
                        {"id": "falar_atendente", "text": "Atendente"},
                    ],
                )
            ],
            new_state=context.state,
        )

    if context.retry_count == 2:
        return ProcessedMessage(
            context=context,
            responses=[
                MessageResponse(
                    text="Hmm, ainda nao entendi. Toca em uma opcao:",
                    buttons=[
                        {"id": "fazer_pedido", "text": "Comprar gas"},
                        {"id": "ver_pedido", "text": "Ver pedido"},
                        {"id": "falar_atendente", "text": "Atendente"},
                    ],
                )
            ],
            new_state=context.state,
        )

    # 3+ tentativas: transferir para humano
    context.retry_count = 0
    return await handle_talking_to_human(context, message)


async def handle_emergency(
    context: ConversationContext,
    message: str,
) -> ProcessedMessage:
    """
    Handler de emergencia (vazamento, cheiro de gas, fogo).
    Prioridade maxima - sempre responde independente do estado.
    """
    # Notificar operadores via WebSocket
    try:
        from app.api.websocket import emit_new_message

        await emit_new_message(
            phone=context.phone,
            message=f"EMERGENCIA - {message}",
            direction="incoming",
            customer_data={"phone": context.phone, "name": context.customer_name},
        )
    except Exception as e:
        logger.error(f"Erro ao notificar emergencia: {e}")

    context.state = ConversationState.TALKING_TO_HUMAN

    return ProcessedMessage(
        context=context,
        responses=[
            MessageResponse(
                text=(
                    "*ATENCAO - EMERGENCIA*\n\n"
                    "Se voce sente cheiro de gas ou ha risco de vazamento:\n\n"
                    "1. NAO acione interruptores eletricos\n"
                    "2. Abra portas e janelas\n"
                    "3. Feche o registro do botijao\n"
                    "4. Saia do local\n"
                    "5. Ligue para o Corpo de Bombeiros: *193*\n\n"
                    "Estamos transferindo voce para um atendente."
                )
            )
        ],
        new_state=ConversationState.TALKING_TO_HUMAN,
    )


async def handle_repeat_order(
    context: ConversationContext,
    message: str,
) -> ProcessedMessage:
    """
    Repete o ultimo pedido do cliente (atalho 'o de sempre').
    """
    if not context.customer_id:
        customer, _, _ = await get_or_create_customer(context.phone)
        context.customer_id = str(customer.id)
        context.customer_name = customer.name

    customer = await _get_customer(context.customer_id)
    if not customer:
        return await handle_greeting(context, message)

    last_order = await _get_last_order(customer)
    if not last_order:
        return await handle_greeting(context, message)

    items = await _get_order_items(last_order)
    if not items:
        return await handle_greeting(context, message)

    item = items[0]

    # Preencher contexto com dados do ultimo pedido
    context.selected_product = item.product_code
    context.selected_quantity = item.quantity
    context.payment_method = last_order.payment_method
    if customer.address:
        context.address = customer.address
        context.address_confirmed = True
    elif last_order.delivery_address:
        context.address = last_order.delivery_address
        context.address_confirmed = True

    # Mostrar confirmacao direta
    return await handle_show_confirmation(context, message)


# ==================== FUNCOES AUXILIARES ====================


def _format_address(address: Optional[dict]) -> str:
    """Formata endereco para exibicao."""
    if not address:
        return "Endereco nao informado"

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

    return ", ".join(parts) if parts else "Endereco cadastrado"


async def _get_customer(customer_id: str) -> Optional[Customer]:
    """Busca cliente por ID."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        return result.scalar_one_or_none()


async def _get_last_order(customer: Customer) -> Optional[Order]:
    """Busca ultimo pedido nao-cancelado do cliente."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Order)
            .where(Order.customer_id == customer.id)
            .where(Order.status != OrderStatus.CANCELLED.value)
            .order_by(desc(Order.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()


async def _get_order_items(order: Order) -> list:
    """Busca itens de um pedido."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(OrderItem).where(OrderItem.order_id == order.id)
        )
        return result.scalars().all()


async def create_order(
    context: ConversationContext,
    total: Decimal,
) -> Order:
    """Cria pedido no banco de dados."""
    async with AsyncSessionLocal() as db:
        # Buscar produto do banco de dados
        result = await db.execute(
            select(Product).where(Product.code == context.selected_product)
        )
        product = result.scalar_one_or_none()
        if not product:
            raise ValueError(f"Produto {context.selected_product} não encontrado")

        # Criar pedido
        order = Order(
            customer_id=context.customer_id,
            status=OrderStatus.PENDING.value,
            payment_method=context.payment_method,
            total_amount=total,
            delivery_address=context.address,
            delivery_bairro=context.address.get("bairro") if context.address else None,
        )
        db.add(order)
        await db.flush()

        # Criar item do pedido
        item = OrderItem(
            order_id=order.id,
            product_code=context.selected_product,
            product_name=product.name,
            quantity=context.selected_quantity,
            unit_price=product.price,
            subtotal=total,
        )
        db.add(item)

        await db.commit()
        await db.refresh(order)

        logger.info(f"Pedido criado: #{order.order_number} - {total}")

        return order
