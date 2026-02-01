"""
Handlers para cada estado da conversa.
Cada handler processa a mensagem e retorna o próximo estado.
"""

import logging
import re
from typing import Optional, List, Dict, Tuple
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.core.state_machine import ConversationState, ConversationContext
from app.core.flow_engine import MessageResponse, ProcessedMessage
from app.models.customer import Customer
from app.models.product import Product, DEFAULT_PRODUCT_CODES, WEIGHT_TO_CODE, OPTION_TO_CODE
from app.models.order import Order, OrderItem, OrderStatus

logger = logging.getLogger(__name__)

# REMOVIDO: Dados hardcoded de produtos
# Produtos devem ser buscados do banco de dados (PostgreSQL) que é sincronizado do Firebird
# Usar get_product() que busca do banco


async def get_or_create_customer(phone: str) -> Tuple[Customer, bool]:
    """
    Busca ou cria cliente pelo telefone.

    Fluxo:
    1. Busca no PostgreSQL pelo telefone
    2. Se não encontrar, busca no Firebird pelo telefone
    3. Se encontrar no Firebird, cria no PostgreSQL com dados completos
    4. Se não encontrar em nenhum, cria cliente vazio
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Customer).where(Customer.phone == phone)
        )
        customer = result.scalar_one_or_none()

        if customer:
            return customer, False

        # Cliente não existe no PostgreSQL - tentar buscar no Firebird
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
            address = firebird_customer.get("address", {})
            customer = Customer(
                phone=phone,
                name=firebird_customer.get("name"),
                email=firebird_customer.get("email"),
                cpf_cnpj=firebird_customer.get("cpf_cnpj"),
                firebird_id=firebird_customer.get("firebird_id"),
                address=address if address.get("street") else None,
            )
        else:
            customer = Customer(phone=phone)

        db.add(customer)
        await db.commit()
        await db.refresh(customer)
        return customer, True


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
    customer, is_new = await get_or_create_customer(context.phone)
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
    # Tentar extrair código do produto
    product_code = extract_product_code(message)

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


async def handle_awaiting_payment(
    context: ConversationContext,
    message: str,
) -> ProcessedMessage:
    """
    Handler para seleção de método de pagamento.
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
                "payment_method": "cash",
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
                        f"Pagamento: 💵 Dinheiro na entrega\n\n"
                        f"📍 Entrega em: {context.address.get('full_address', context.address.get('bairro', 'Endereço cadastrado'))}\n"
                        f"⏱️ Previsão: *{settings.default_delivery_time_minutes} minutos*\n\n"
                        "Você receberá atualizações sobre sua entrega!"
                    ),
                    footer="Obrigado pela preferência! 🔥",
                )
            ],
            new_state=ConversationState.ORDER_CONFIRMED,
        )

    # Cartão
    if msg_lower in ["cartao", "cartão", "3"] or "cart" in msg_lower:
        context.payment_method = "credit_card"

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


# ==================== FUNÇÕES AUXILIARES ====================


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
