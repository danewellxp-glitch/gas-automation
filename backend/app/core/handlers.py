"""
Handlers para cada estado da conversa.
Cada handler processa a mensagem e retorna o próximo estado.
"""

import logging
import re
from typing import Optional
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.core.state_machine import ConversationState, ConversationContext
from app.core.flow_engine import MessageResponse, ProcessedMessage
from app.models.customer import Customer
from app.models.product import Product
from app.models.order import Order, OrderItem, OrderStatus

logger = logging.getLogger(__name__)

# Preços dos produtos (cache simples)
PRODUCTS = {
    "P13": {"name": "Botijão P13 - 13kg", "price": Decimal("110.00"), "weight": 13},
    "P20": {"name": "Botijão P20 - 20kg", "price": Decimal("150.00"), "weight": 20},
    "P45": {"name": "Botijão P45 - 45kg", "price": Decimal("280.00"), "weight": 45},
}


async def get_or_create_customer(phone: str) -> tuple[Customer, bool]:
    """Busca ou cria cliente pelo telefone."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Customer).where(Customer.phone == phone)
        )
        customer = result.scalar_one_or_none()

        if customer:
            return customer, False

        # Criar novo cliente
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

    # Procura por códigos específicos
    for code in ["P13", "P20", "P45"]:
        if code in msg_upper:
            return code

    # Procura por peso
    if "13" in message:
        return "P13"
    if "20" in message:
        return "P20"
    if "45" in message:
        return "P45"

    # Procura por número de opção
    if message.strip() == "1":
        return "P13"
    if message.strip() == "2":
        return "P20"
    if message.strip() == "3":
        return "P45"

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

    context.state = ConversationState.AWAITING_PRODUCT

    return ProcessedMessage(
        context=context,
        responses=[
            MessageResponse(
                text=(
                    f"{greeting}"
                    "Qual produto você deseja?\n\n"
                    "🔵 *P13* - Botijão 13kg - R$ 110,00\n"
                    "🟢 *P20* - Botijão 20kg - R$ 150,00\n"
                    "🟠 *P45* - Botijão 45kg - R$ 280,00"
                ),
                buttons=[
                    {"id": "P13", "text": "P13 - R$ 110"},
                    {"id": "P20", "text": "P20 - R$ 150"},
                    {"id": "P45", "text": "P45 - R$ 280"},
                ],
                footer="Escolha uma opção acima",
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
    product = PRODUCTS[product_code]

    context.state = ConversationState.AWAITING_QUANTITY

    return ProcessedMessage(
        context=context,
        responses=[
            MessageResponse(
                text=(
                    f"✅ *{product['name']}* selecionado!\n"
                    f"💰 Valor unitário: {format_currency(product['price'])}\n\n"
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

    product = PRODUCTS[context.selected_product]
    total = product["price"] * quantity

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
                            f"Produto: {product['name']}\n"
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
                    f"*{quantity}x {product['name']}*\n"
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

        product = PRODUCTS[context.selected_product]
        total = product["price"] * context.selected_quantity

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

    product = PRODUCTS[context.selected_product]
    total = product["price"] * context.selected_quantity

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
                    {"id": "pix", "text": "📱 Pix"},
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

    product = PRODUCTS[context.selected_product]
    total = product["price"] * context.selected_quantity

    # Pix
    if msg_lower in ["pix", "1"] or "pix" in msg_lower:
        context.payment_method = "pix"

        # Criar pedido no banco
        order = await create_order(context, total)
        context.order_id = str(order.id)

        # Emitir evento WebSocket de novo pedido
        try:
            from app.api.websocket import emit_new_order
            order_data = {
                "id": str(order.id),
                "order_number": order.order_number,
                "customer_id": str(context.customer_id),
                "status": order.status,
                "total_amount": float(order.total_amount),
                "payment_method": "pix",
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "product": product["name"],
                "quantity": context.selected_quantity,
                "address": context.address.get("full_address", ""),
            }
            await emit_new_order(order_data)
            logger.info(f"Evento WebSocket emitido para novo pedido: #{order.order_number}")
        except Exception as e:
            logger.error(f"Erro ao emitir evento WebSocket de novo pedido: {e}")

        # TODO: Gerar QR Code Pix via Asaas
        # Por enquanto, simular código Pix

        context.state = ConversationState.AWAITING_PIX

        return ProcessedMessage(
            context=context,
            responses=[
                MessageResponse(
                    text=(
                        f"📱 *Pagamento via Pix*\n\n"
                        f"Valor: *{format_currency(total)}*\n\n"
                        f"Chave Pix (CNPJ):\n`12.345.678/0001-90`\n\n"
                        f"Ou copie o código:\n"
                        f"`00020126580014br.gov.bcb.pix0136{context.order_id[:36]}`\n\n"
                        "Após o pagamento, envie o comprovante ou digite *pago*."
                    ),
                    buttons=[
                        {"id": "pix_pago", "text": "✅ Já paguei"},
                        {"id": "cancelar", "text": "❌ Cancelar"},
                    ],
                )
            ],
            new_state=ConversationState.AWAITING_PIX,
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
                "product": product["name"],
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
                        f"Produto: {context.selected_quantity}x {product['name']}\n"
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
                    {"id": "pix", "text": "📱 Pix"},
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
    msg_lower = message.lower().strip()

    product = PRODUCTS[context.selected_product]
    total = product["price"] * context.selected_quantity

    # Pagamento confirmado
    if msg_lower in ["pago", "paguei", "pix_pago", "1"] or "pag" in msg_lower:
        # TODO: Verificar pagamento via Asaas
        # Por enquanto, assumir que foi pago

        # Atualizar pedido
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Order).where(Order.id == context.order_id)
            )
            order = result.scalar_one_or_none()
            if order:
                order.status = OrderStatus.PAID.value
                await db.commit()
                order_number = order.order_number

        context.state = ConversationState.ORDER_CONFIRMED

        return ProcessedMessage(
            context=context,
            responses=[
                MessageResponse(
                    text=(
                        f"✅ *Pagamento Confirmado!*\n\n"
                        f"📦 Pedido #{order_number}\n"
                        f"Produto: {context.selected_quantity}x {product['name']}\n"
                        f"Total: *{format_currency(total)}* ✓\n\n"
                        f"📍 Entrega em: {context.address.get('full_address', context.address.get('bairro', 'Endereço cadastrado'))}\n"
                        f"⏱️ Previsão: *{settings.default_delivery_time_minutes} minutos*\n\n"
                        "🚚 Seu pedido já está sendo preparado!"
                    ),
                    footer="Obrigado pela preferência! 🔥",
                )
            ],
            new_state=ConversationState.ORDER_CONFIRMED,
        )

    # Cancelar
    if msg_lower in ["cancelar", "cancela", "2"]:
        # TODO: Cancelar pedido
        context.reset()

        return ProcessedMessage(
            context=context,
            responses=[
                MessageResponse(
                    text="❌ Pedido cancelado.\n\nDigite *menu* para fazer um novo pedido."
                )
            ],
            new_state=ConversationState.START,
        )

    # Aguardando
    return ProcessedMessage(
        context=context,
        responses=[
            MessageResponse(
                text=(
                    "⏳ Aguardando confirmação do pagamento...\n\n"
                    "Após realizar o Pix, envie o comprovante ou digite *pago*."
                ),
                buttons=[
                    {"id": "pix_pago", "text": "✅ Já paguei"},
                    {"id": "cancelar", "text": "❌ Cancelar"},
                ],
            )
        ],
        new_state=ConversationState.AWAITING_PIX,
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

    product = PRODUCTS[context.selected_product]
    total = product["price"] * context.selected_quantity

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
                "product": product["name"],
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
                        f"Produto: {context.selected_quantity}x {product['name']}\n"
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
    """
    # TODO: Buscar pedidos recentes do cliente

    return ProcessedMessage(
        context=context,
        responses=[
            MessageResponse(
                text=(
                    "📦 *Seus Pedidos Recentes*\n\n"
                    "Ainda estamos desenvolvendo esta funcionalidade.\n\n"
                    "Digite *menu* para fazer um novo pedido."
                )
            )
        ],
        new_state=ConversationState.START,
    )


async def handle_talking_to_human(
    context: ConversationContext,
    message: str,
) -> ProcessedMessage:
    """
    Handler quando transferido para atendente.
    """
    # TODO: Notificar operador via WebSocket

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
    product = PRODUCTS[context.selected_product]

    async with AsyncSessionLocal() as db:
        # Buscar produto real do banco
        result = await db.execute(
            select(Product).where(Product.code == context.selected_product)
        )
        db_product = result.scalar_one_or_none()

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
            product_name=product["name"],
            quantity=context.selected_quantity,
            unit_price=product["price"],
            subtotal=total,
        )
        db.add(item)

        await db.commit()
        await db.refresh(order)

        logger.info(f"Pedido criado: #{order.order_number} - {total}")

        return order
