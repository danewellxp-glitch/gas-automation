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
from app.integrations.asaas import asaas_client, AsaasError

logger = logging.getLogger(__name__)

# REMOVIDO: Dados hardcoded de produtos
# Produtos devem ser buscados do banco de dados (PostgreSQL) que é sincronizado do Firebird
# Usar get_product() que busca do banco


async def get_or_create_customer(phone: str) -> tuple[Customer, bool]:
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


async def _get_or_create_asaas_customer(customer: Customer) -> str:
    """
    Obtém ou cria cliente no Asaas e retorna o ID.
    Atualiza o customer.asaas_customer_id no banco.
    """
    if customer.asaas_customer_id:
        return customer.asaas_customer_id

    try:
        # Criar cliente no Asaas
        asaas_customer = await asaas_client.get_or_create_customer(
            name=customer.name or f"Cliente {customer.phone}",
            cpf_cnpj=customer.cpf_cnpj,
            email=customer.email,
            phone=customer.phone,
            external_reference=str(customer.id),
        )

        # Atualizar ID no banco local
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Customer).where(Customer.id == customer.id)
            )
            db_customer = result.scalar_one_or_none()
            if db_customer:
                db_customer.asaas_customer_id = asaas_customer["id"]
                await db.commit()

        logger.info(f"Cliente Asaas criado/encontrado: {asaas_customer['id']} para customer {customer.id}")
        return asaas_customer["id"]

    except AsaasError as e:
        logger.error(f"Erro ao criar cliente no Asaas: {e.message}")
        raise


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

        # Gerar QR Code Pix via Asaas (se configurado)
        pix_payload = None
        pix_qr_code = None

        try:
            # Buscar dados do cliente para Asaas
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Customer).where(Customer.id == context.customer_id)
                )
                customer = result.scalar_one_or_none()

            if customer and customer.cpf_cnpj and settings.asaas_api_key:
                # Criar pagamento PIX no Asaas
                payment = await asaas_client.create_pix_payment(
                    customer_id=customer.asaas_customer_id or await _get_or_create_asaas_customer(customer),
                    value=total,
                    description=f"Pedido #{order.order_number} - {product['name']}",
                    external_reference=str(order.id),
                )

                # Armazenar payment_id no contexto
                context.asaas_payment_id = payment["id"]
                pix_payload = payment.get("pix", {}).get("payload", "")
                pix_qr_code = payment.get("pix", {}).get("encodedImage", "")

                # Atualizar pedido com payment_id
                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        select(Order).where(Order.id == order.id)
                    )
                    db_order = result.scalar_one_or_none()
                    if db_order:
                        db_order.asaas_payment_id = payment["id"]
                        await db.commit()

                logger.info(f"PIX Asaas criado: {payment['id']} para pedido #{order.order_number}")
            else:
                logger.warning(f"Cliente sem CPF/CNPJ ou Asaas não configurado - usando PIX simulado")

        except AsaasError as e:
            logger.error(f"Erro ao criar PIX no Asaas: {e.message}")
        except Exception as e:
            logger.error(f"Erro inesperado ao criar PIX: {e}")

        context.state = ConversationState.AWAITING_PIX

        # Montar mensagem com PIX real ou simulado
        if pix_payload:
            pix_message = (
                f"📱 *Pagamento via Pix*\n\n"
                f"Valor: *{format_currency(total)}*\n\n"
                f"Copie o código PIX abaixo:\n"
                f"`{pix_payload}`\n\n"
                "Após o pagamento, envie o comprovante ou digite *pago*."
            )
        else:
            # Fallback: PIX simulado (chave CNPJ)
            pix_message = (
                f"📱 *Pagamento via Pix*\n\n"
                f"Valor: *{format_currency(total)}*\n\n"
                f"Chave Pix (CNPJ):\n`12.345.678/0001-90`\n\n"
                f"Ou copie o código:\n"
                f"`00020126580014br.gov.bcb.pix0136{context.order_id[:36]}`\n\n"
                "Após o pagamento, envie o comprovante ou digite *pago*."
            )

        return ProcessedMessage(
            context=context,
            responses=[
                MessageResponse(
                    text=pix_message,
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

    # Pagamento confirmado
    if msg_lower in ["pago", "paguei", "pix_pago", "1"] or "pag" in msg_lower:
        # Verificar pagamento via Asaas (se configurado)
        payment_confirmed = False
        payment_status = None

        if hasattr(context, 'asaas_payment_id') and context.asaas_payment_id and settings.asaas_api_key:
            try:
                payment_status = await asaas_client.get_payment_status(context.asaas_payment_id)
                payment_confirmed = payment_status in ["RECEIVED", "CONFIRMED", "RECEIVED_IN_CASH"]
                logger.info(f"Status PIX Asaas: {payment_status} para {context.asaas_payment_id}")
            except AsaasError as e:
                logger.error(f"Erro ao verificar PIX no Asaas: {e.message}")
            except Exception as e:
                logger.error(f"Erro inesperado ao verificar PIX: {e}")

        # Se não está confirmado via Asaas, assumir que foi pago (fallback)
        # Em produção, você pode querer ser mais rigoroso
        if not payment_confirmed and payment_status and payment_status not in ["RECEIVED", "CONFIRMED"]:
            return ProcessedMessage(
                context=context,
                responses=[
                    MessageResponse(
                        text=(
                            "⏳ *Pagamento ainda não identificado*\n\n"
                            f"Status atual: {payment_status or 'Aguardando'}\n\n"
                            "Por favor, aguarde alguns instantes e confirme novamente, "
                            "ou envie o comprovante de pagamento."
                        ),
                        buttons=[
                            {"id": "pix_pago", "text": "🔄 Verificar novamente"},
                            {"id": "cancelar", "text": "❌ Cancelar"},
                        ],
                    )
                ],
                new_state=ConversationState.AWAITING_PIX,
            )

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
        # Cancelar pedido no banco de dados
        order_number = None
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Order).where(Order.id == context.order_id)
                )
                order = result.scalar_one_or_none()
                if order:
                    order.status = OrderStatus.CANCELLED.value
                    order_number = order.order_number
                    await db.commit()
                    logger.info(f"Pedido #{order_number} cancelado pelo cliente")

            # Cancelar cobrança no Asaas (se existir)
            if hasattr(context, 'asaas_payment_id') and context.asaas_payment_id and settings.asaas_api_key:
                try:
                    await asaas_client.cancel_payment(context.asaas_payment_id)
                    logger.info(f"Cobrança Asaas cancelada: {context.asaas_payment_id}")
                except AsaasError as e:
                    logger.error(f"Erro ao cancelar cobrança no Asaas: {e.message}")
                except Exception as e:
                    logger.error(f"Erro inesperado ao cancelar cobrança: {e}")

            # Emitir evento WebSocket de pedido cancelado
            try:
                from app.api.websocket import emit_order_update
                await emit_order_update(
                    order_id=context.order_id,
                    status=OrderStatus.CANCELLED.value,
                    order_data={"order_number": order_number}
                )
            except Exception as e:
                logger.error(f"Erro ao emitir evento de cancelamento: {e}")

        except Exception as e:
            logger.error(f"Erro ao cancelar pedido: {e}")

        context.reset()

        return ProcessedMessage(
            context=context,
            responses=[
                MessageResponse(
                    text=f"❌ Pedido{' #' + str(order_number) if order_number else ''} cancelado.\n\nDigite *menu* para fazer um novo pedido."
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
    # Buscar produto do banco de dados
    product = await get_product(context.selected_product)
    if not product:
        raise ValueError(f"Produto {context.selected_product} não encontrado")

    async with AsyncSessionLocal() as db:
        # Produto já foi buscado acima
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
