"""Hooks de integração do módulo financeiro com o restante do sistema."""
import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.models.financeiro.receivable import Receivable, ReceivableStatus
from app.models.financeiro.payable import Payable, PayableStatus
from app.models.financeiro.account import Account
from app.models.financeiro.transaction import TransactionType
from app.services.financeiro.financial_service import create_transaction

logger = logging.getLogger(__name__)

COMMISSION_RATE = 0.05  # 5% padrão, sobrescrito por settings


async def on_order_delivered(db: AsyncSession, order: Order) -> None:
    """
    Chamado quando Order.status → delivered.
    1. Cria/confirma Receivable e Transaction de receita.
    2. Calcula lucratividade do pedido (OrderProfit).
    3. Se foi fiado: confirma dívida já registrada.
    """
    try:
        from sqlalchemy import select
        from app.models.financeiro.account import Account

        # Get default account
        result = await db.execute(
            select(Account).where(Account.is_active == True, Account.deleted_at == None).limit(1)
        )
        account = result.scalar_one_or_none()
        if not account:
            logger.warning("on_order_delivered: nenhuma conta ativa encontrada")
            return

        amount = order.total_amount or Decimal("0.00")
        today = date.today()

        # Check if receivable already exists for this order
        from sqlalchemy import and_
        result = await db.execute(
            select(Receivable).where(
                and_(Receivable.order_id == order.id, Receivable.deleted_at == None)
            )
        )
        existing = result.scalar_one_or_none()

        if existing is None:
            receivable = Receivable(
                customer_id=order.customer_id,
                order_id=order.id,
                description=f"Venda - Pedido #{order.order_number}",
                amount=amount,
                due_date=today,
                status=ReceivableStatus.recebido.value,
                payment_method=order.payment_method,
            )
            db.add(receivable)
            await db.flush()

        # Create revenue transaction
        await create_transaction(
            db=db,
            account_id=account.id,
            type=TransactionType.receita.value,
            category="venda_gas",
            description=f"Receita entrega pedido #{order.order_number}",
            amount=amount,
            direction="entrada",
            reference_date=today,
            is_paid=True,
            order_id=order.id,
            created_by=1,  # system user
        )
        logger.info(f"Financeiro: receita registrada para pedido {order.id}")

        # Calcula lucratividade
        from app.services.financeiro.customer_financial_service import calculate_order_profit
        await calculate_order_profit(db, order.id)

        # Registra saída de vasilhames
        await on_order_delivered_vasilhame(db, order)

        # Se era fiado, baixa a dívida do cliente (já foi pago na entrega)
        if order.payment_method == "fiado":
            from app.services.financeiro.customer_financial_service import register_payment_received
            await register_payment_received(
                db, order.customer_id,
                amount=(order.total_amount or Decimal("0.00")),
                reference=f"pedido #{order.order_number}",
            )

        # NF-e automática
        await on_order_delivered_nfe(db, order)

        # Boleto automático para clientes PJ
        await on_order_delivered_boleto_cnpj(db, order)

    except Exception as e:
        logger.error(f"Erro em on_order_delivered: {e}", exc_info=True)


async def on_order_created_fiado(
    db: AsyncSession, order: Order
) -> None:
    """
    Chamado quando pedido é criado com payment_method='fiado'.
    Registra dívida imediata no CustomerFinancial.
    """
    try:
        from app.services.financeiro.customer_financial_service import register_fiado_order
        await register_fiado_order(
            db,
            customer_id=order.customer_id,
            order_id=order.id,
            amount=order.total_amount or Decimal("0.00"),
        )
        logger.info(f"Fiado registrado: cliente {order.customer_id} pedido #{order.order_number}")
    except Exception as e:
        logger.error(f"Erro em on_order_created_fiado: {e}", exc_info=True)


async def on_order_delivered_vasilhame(db: AsyncSession, order: Order) -> None:
    """Registra saída de vasilhame cheio ao entregar pedido."""
    try:
        from sqlalchemy import select
        from app.models.order import OrderItem
        from app.services.financeiro.vasilhame_service import VasilhameService
        from app.models.product import Product

        service = VasilhameService()
        result = await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))
        items = result.scalars().all()

        for item in items:
            prod_result = await db.execute(select(Product).where(Product.code == item.product_code))
            product = prod_result.scalar_one_or_none()
            if product and product.requer_retorno_vasilhame:
                tipo = product.code  # P13, P20, P45, G20L
                await service.registrar_saida_venda(
                    db, tipo=tipo, quantidade=item.quantity,
                    pedido_id=order.id, user_id=None
                )
    except Exception as e:
        logger.error(f"Erro em on_order_delivered_vasilhame: {e}", exc_info=True)


async def on_order_delivered_boleto_cnpj(db: AsyncSession, order: Order) -> None:
    """
    Gera boleto Asaas e envia via WhatsApp para clientes PJ (CNPJ) após entrega.
    Prazo de vencimento: 30 dias (configurável).
    """
    try:
        from sqlalchemy import select
        from app.models.customer import Customer
        from app.models.financeiro.receivable import Receivable

        if not order.customer_id:
            return

        result = await db.execute(select(Customer).where(Customer.id == order.customer_id))
        customer = result.scalar_one_or_none()
        if not customer or not customer.cpf_cnpj:
            return

        cpf_cnpj_clean = ''.join(filter(str.isdigit, customer.cpf_cnpj))
        if len(cpf_cnpj_clean) != 14:
            return  # Não é CNPJ

        # Verificar se já existe boleto para este pedido
        existing = await db.execute(
            select(Receivable).where(
                Receivable.order_id == order.id,
                Receivable.asaas_payment_id != None,
            )
        )
        if existing.scalar_one_or_none():
            return  # Boleto já gerado

        from app.services.asaas_service import create_boleto_for_order
        boleto = await create_boleto_for_order(db, order, customer, due_days=30)
        if not boleto:
            return

        # Salvar Receivable com asaas_payment_id
        receivable = Receivable(
            customer_id=order.customer_id,
            order_id=order.id,
            description=f"Boleto - Pedido #{order.order_number}",
            amount=order.total_amount,
            due_date=date.today() + timedelta(days=30),
            status="pendente",
            payment_method="boleto",
            asaas_payment_id=boleto["asaas_payment_id"],
        )
        db.add(receivable)
        await db.flush()

        # Enviar link do boleto via WhatsApp
        if customer.phone and boleto.get("boleto_url"):
            try:
                from app.integrations.waha import waha_client
                msg = (
                    f"📄 *Boleto gerado!*\n\n"
                    f"Pedido #{order.order_number} — R$ {order.total_amount:.2f}\n"
                    f"Vencimento: 30 dias\n\n"
                    f"🔗 {boleto['boleto_url']}"
                )
                await waha_client.send_text(customer.phone, msg)
            except Exception as send_err:
                logger.warning(f"Falha ao enviar boleto WhatsApp para {customer.phone}: {send_err}")

        logger.info(f"Boleto CNPJ gerado para pedido {order.id}: {boleto['asaas_payment_id']}")
    except Exception as e:
        logger.error(f"Erro em on_order_delivered_boleto_cnpj: {e}", exc_info=True)


async def on_order_delivered_nfe(db: AsyncSession, order: Order) -> None:
    """Emite NF-e automaticamente após entrega (em background, não bloqueia)."""
    try:
        from sqlalchemy import select
        from app.models.financeiro.nota_fiscal import NotaFiscal

        # Verifica se já tem NF-e
        existing = await db.execute(
            select(NotaFiscal).where(
                NotaFiscal.pedido_id == order.id,
                NotaFiscal.status.in_(["autorizada", "enviada"]),
            )
        )
        if existing.scalar_one_or_none():
            return

        from app.services.financeiro.nfe_service import NFeService
        service = NFeService()
        await service.emitir_nfe_pedido(db, order.id, user_id=order.customer_id)
        logger.info(f"NF-e emitida automaticamente para pedido {order.id}")
    except Exception as e:
        logger.error(f"Erro em on_order_delivered_nfe: {e}", exc_info=True)


async def on_driver_delivery_done(
    db: AsyncSession, driver_id: UUID, order: Order
) -> None:
    """Calcula e cria Payable de comissão do entregador."""
    try:
        from app.config import settings
        rate = getattr(settings, "commission_rate_percent", 5.0) / 100.0
        commission = (order.total_amount or Decimal("0.00")) * Decimal(str(rate))

        if commission <= 0:
            return

        # Next Friday
        today = date.today()
        days_until_friday = (4 - today.weekday()) % 7
        if days_until_friday == 0:
            days_until_friday = 7
        next_friday = today + timedelta(days=days_until_friday)

        payable = Payable(
            category="comissao_entregador",
            description=f"Comissão entrega pedido #{order.order_number}",
            amount=commission,
            due_date=next_friday,
            status=PayableStatus.pendente.value,
        )
        db.add(payable)
        await db.flush()
        logger.info(f"Financeiro: comissão R${commission:.2f} gerada para driver {driver_id}")

    except Exception as e:
        logger.error(f"Erro em on_driver_delivery_done: {e}", exc_info=True)
