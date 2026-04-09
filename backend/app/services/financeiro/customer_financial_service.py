"""
Serviços de fiado, lucratividade e insights financeiros.

Separa responsabilidades do financial_service.py central.
"""
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financeiro.customer_financial import CustomerFinancial
from app.models.financeiro.order_profit import OrderProfit
from app.models.customer import Customer
from app.models.order import Order, OrderItem, OrderStatus

logger = logging.getLogger(__name__)

# Custo fixo estimado por entrega (combustível + desgaste veículo)
DEFAULT_DELIVERY_COST = Decimal("8.00")


# ─────────────────────────────────────────────────────────
# CustomerFinancial helpers
# ─────────────────────────────────────────────────────────

async def _get_or_create_customer_financial(
    db: AsyncSession, customer_id: UUID
) -> CustomerFinancial:
    """Retorna ou cria o registro financeiro do cliente."""
    result = await db.execute(
        select(CustomerFinancial).where(
            CustomerFinancial.customer_id == customer_id
        ).with_for_update()
    )
    cf = result.scalar_one_or_none()
    if not cf:
        cf = CustomerFinancial(
            customer_id=customer_id,
            balance=Decimal("0.00"),
            credit_limit=Decimal("200.00"),
        )
        db.add(cf)
        await db.flush()
    return cf


async def update_customer_balance(
    db: AsyncSession,
    customer_id: UUID,
    amount: Decimal,
    notes: Optional[str] = None,
) -> CustomerFinancial:
    """
    Atualiza o saldo do cliente.

    amount > 0  → reduz dívida / adiciona crédito (ex: pagamento recebido)
    amount < 0  → aumenta dívida (ex: pedido fiado)
    """
    cf = await _get_or_create_customer_financial(db, customer_id)
    cf.balance += amount
    cf.updated_at = datetime.now(timezone.utc)
    if notes:
        cf.notes = notes
    await db.flush()
    logger.info(
        f"CustomerFinancial {customer_id}: balance {cf.balance - amount} → {cf.balance}"
    )
    return cf


async def check_credit_limit(
    db: AsyncSession,
    customer_id: UUID,
    order_amount: Decimal,
) -> tuple[bool, Decimal]:
    """
    Verifica se o cliente pode fazer um novo pedido fiado.

    Returns:
        (allowed: bool, current_balance: Decimal)
    """
    result = await db.execute(
        select(CustomerFinancial).where(CustomerFinancial.customer_id == customer_id)
    )
    cf = result.scalar_one_or_none()
    if not cf:
        return True, Decimal("0.00")  # sem histórico = pode

    projected_balance = cf.balance - order_amount
    allowed = projected_balance >= -cf.credit_limit
    return allowed, cf.balance


async def register_fiado_order(
    db: AsyncSession,
    customer_id: UUID,
    order_id: UUID,
    amount: Decimal,
) -> CustomerFinancial:
    """Registra débito no cliente quando pedido é criado via fiado."""
    cf = await update_customer_balance(
        db, customer_id, -amount,
        notes=f"Fiado - pedido {order_id}"
    )
    cf.total_orders += 1
    cf.total_purchases += amount
    cf.last_purchase_at = datetime.now(timezone.utc)
    await db.flush()
    return cf


async def register_payment_received(
    db: AsyncSession,
    customer_id: UUID,
    amount: Decimal,
    reference: str = "",
) -> CustomerFinancial:
    """Registra pagamento recebido — reduz dívida ou adiciona crédito."""
    return await update_customer_balance(
        db, customer_id, amount,
        notes=f"Pagamento recebido{' - ' + reference if reference else ''}"
    )


# ─────────────────────────────────────────────────────────
# Order Profit
# ─────────────────────────────────────────────────────────

async def calculate_order_profit(
    db: AsyncSession,
    order_id: UUID,
    delivery_cost: Optional[Decimal] = None,
) -> Optional[OrderProfit]:
    """
    Calcula e persiste a lucratividade do pedido.

    Busca custo de produto via StockProduct.linked_product_code.
    Se não encontrar custo, usa 0 (sem dado de CMV).
    """
    from sqlalchemy.orm import selectinload
    from app.models.estoque.stock_product import StockProduct

    result = await db.execute(
        select(Order).options(selectinload(Order.items))
        .where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        logger.warning(f"calculate_order_profit: pedido {order_id} não encontrado")
        return None

    revenue = order.total_amount or Decimal("0.00")
    cost_by_delivery = delivery_cost if delivery_cost is not None else DEFAULT_DELIVERY_COST

    # CMV: custo dos produtos
    product_cost = Decimal("0.00")
    for item in order.items:
        sp_result = await db.execute(
            select(StockProduct).where(
                and_(
                    StockProduct.linked_product_code == item.product_code,
                    StockProduct.is_active == True,
                )
            )
        )
        sp = sp_result.scalar_one_or_none()
        if not sp:
            sp_result2 = await db.execute(
                select(StockProduct).where(
                    and_(StockProduct.code == item.product_code, StockProduct.is_active == True)
                )
            )
            sp = sp_result2.scalar_one_or_none()

        if sp and sp.cost_price:
            product_cost += sp.cost_price * item.quantity

    estimated_cost = product_cost + cost_by_delivery
    profit = revenue - estimated_cost
    margin_pct = (profit / revenue * 100) if revenue > 0 else Decimal("0.00")

    # Upsert
    existing = await db.execute(
        select(OrderProfit).where(OrderProfit.order_id == order_id).with_for_update()
    )
    op = existing.scalar_one_or_none()

    bairro = getattr(order, "delivery_bairro", None)
    now = datetime.now(timezone.utc)

    if op:
        op.revenue = revenue
        op.product_cost = product_cost
        op.delivery_cost = cost_by_delivery
        op.estimated_cost = estimated_cost
        op.profit = profit
        op.margin_percentage = margin_pct.quantize(Decimal("0.01"))
        op.bairro = bairro
        op.calculated_at = now
    else:
        op = OrderProfit(
            order_id=order_id,
            revenue=revenue,
            product_cost=product_cost,
            delivery_cost=cost_by_delivery,
            estimated_cost=estimated_cost,
            profit=profit,
            margin_percentage=margin_pct.quantize(Decimal("0.01")),
            bairro=bairro,
            calculated_at=now,
        )
        db.add(op)

    await db.flush()
    logger.info(
        f"OrderProfit {order_id}: receita={revenue} custo={estimated_cost} "
        f"lucro={profit} margem={margin_pct:.1f}%"
    )
    return op


# ─────────────────────────────────────────────────────────
# Owner Insights
# ─────────────────────────────────────────────────────────

async def get_top_profitable_bairros(
    db: AsyncSession, limit: int = 10
) -> list[dict]:
    """
    Top bairros por lucro total.
    Retorna: bairro, total_orders, total_revenue, total_profit, avg_margin.
    """
    result = await db.execute(
        select(
            OrderProfit.bairro,
            func.count(OrderProfit.id).label("total_orders"),
            func.sum(OrderProfit.revenue).label("total_revenue"),
            func.sum(OrderProfit.profit).label("total_profit"),
            func.avg(OrderProfit.margin_percentage).label("avg_margin"),
        )
        .where(OrderProfit.bairro.isnot(None))
        .group_by(OrderProfit.bairro)
        .order_by(desc("total_profit"))
        .limit(limit)
    )
    rows = result.all()
    return [
        {
            "bairro":        r.bairro,
            "total_orders":  r.total_orders,
            "total_revenue": float(r.total_revenue or 0),
            "total_profit":  float(r.total_profit or 0),
            "avg_margin":    float(r.avg_margin or 0),
        }
        for r in rows
    ]


async def get_most_expensive_deliveries(
    db: AsyncSession, limit: int = 10
) -> list[dict]:
    """
    Entregas com maior custo estimado (menor margem).
    Útil para identificar rotas ineficientes.
    """
    result = await db.execute(
        select(OrderProfit, Order)
        .join(Order, OrderProfit.order_id == Order.id)
        .order_by(OrderProfit.estimated_cost.desc())
        .limit(limit)
    )
    rows = result.all()
    return [
        {
            "order_id":       str(op.order_id),
            "order_number":   order.order_number,
            "bairro":         op.bairro,
            "revenue":        float(op.revenue),
            "estimated_cost": float(op.estimated_cost),
            "profit":         float(op.profit),
            "margin":         float(op.margin_percentage),
        }
        for op, order in rows
    ]


async def get_high_risk_customers(
    db: AsyncSession, limit: int = 20
) -> list[dict]:
    """
    Clientes com dívida elevada (balance mais negativo primeiro).
    Inclui % do limite de crédito utilizado.
    """
    result = await db.execute(
        select(CustomerFinancial, Customer)
        .join(Customer, CustomerFinancial.customer_id == Customer.id)
        .where(CustomerFinancial.balance < 0)
        .order_by(CustomerFinancial.balance.asc())  # mais negativo primeiro
        .limit(limit)
    )
    rows = result.all()
    return [
        {
            "customer_id":     str(cf.customer_id),
            "customer_name":   c.name or c.phone,
            "customer_phone":  c.phone,
            "balance":         float(cf.balance),
            "credit_limit":    float(cf.credit_limit),
            "limit_used_pct":  round(abs(float(cf.balance)) / float(cf.credit_limit) * 100, 1)
                               if cf.credit_limit > 0 else 100.0,
            "total_purchases": float(cf.total_purchases),
            "total_orders":    cf.total_orders,
            "last_purchase_at": cf.last_purchase_at.isoformat() if cf.last_purchase_at else None,
        }
        for cf, c in rows
    ]


async def get_customer_financial_summary(
    db: AsyncSession, customer_id: UUID
) -> Optional[dict]:
    """Retorna situação financeira de um cliente específico."""
    result = await db.execute(
        select(CustomerFinancial).where(CustomerFinancial.customer_id == customer_id)
    )
    cf = result.scalar_one_or_none()
    if not cf:
        return None
    return {
        "balance":         float(cf.balance),
        "credit_limit":    float(cf.credit_limit),
        "total_purchases": float(cf.total_purchases),
        "total_orders":    cf.total_orders,
        "last_purchase_at": cf.last_purchase_at.isoformat() if cf.last_purchase_at else None,
        "status": "em_dia" if cf.balance >= 0 else (
            "devendo" if cf.balance > -cf.credit_limit else "limite_excedido"
        ),
    }


# ─────────────────────────────────────────────────────────
# Fiado Entry helpers
# ─────────────────────────────────────────────────────────

async def create_fiado_entry(db: AsyncSession, customer_id: UUID, order_id: UUID, valor: Decimal):
    """Cria entry de fiado. Vencimento = hoje + 7 dias."""
    from datetime import date, timedelta
    from app.models.financeiro.fiado_entry import FiadoEntry

    entry = FiadoEntry(
        customer_id=customer_id,
        order_id=order_id,
        valor_original=valor,
        valor_pago=Decimal("0.00"),
        vencimento=date.today() + timedelta(days=7),
        status="em_aberto",
    )
    db.add(entry)
    await db.flush()
    return entry


async def registrar_pagamento_fiado(
    db: AsyncSession,
    entry_id: UUID,
    valor: Decimal,
    metodo: str,
    user_id: UUID,
    asaas_payment_id=None,
):
    """Registra pagamento parcial/total de entry fiado."""
    from app.models.financeiro.fiado_entry import FiadoEntry, FiadoPagamento
    from datetime import datetime, timezone

    result = await db.execute(
        select(FiadoEntry).where(FiadoEntry.id == entry_id).with_for_update()
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise ValueError(f"FiadoEntry {entry_id} não encontrado")

    pagamento = FiadoPagamento(
        entry_id=entry_id,
        valor=valor,
        metodo=metodo,
        asaas_payment_id=asaas_payment_id,
        pago_at=datetime.now(timezone.utc),
        registrado_por=user_id,
    )
    db.add(pagamento)

    entry.valor_pago += valor
    if entry.valor_pago >= entry.valor_original:
        entry.status = "pago"
        entry.pago_at = datetime.now(timezone.utc)
    elif entry.valor_pago > 0:
        entry.status = "pago_parcial"

    await db.flush()
    return pagamento


async def get_aging_report(db: AsyncSession) -> dict:
    """Aging report: 0-7d, 8-15d, 16-30d, 30d+"""
    from app.models.financeiro.fiado_entry import FiadoEntry
    from datetime import date

    hoje = date.today()
    result = await db.execute(
        select(FiadoEntry).where(
            FiadoEntry.status.in_(["em_aberto", "pago_parcial", "vencido"])
        )
    )
    entries = result.scalars().all()

    buckets = {
        "0_7_dias":      {"clientes": set(), "valor": Decimal("0.00"), "count": 0},
        "8_15_dias":     {"clientes": set(), "valor": Decimal("0.00"), "count": 0},
        "16_30_dias":    {"clientes": set(), "valor": Decimal("0.00"), "count": 0},
        "acima_30_dias": {"clientes": set(), "valor": Decimal("0.00"), "count": 0},
    }

    for entry in entries:
        dias = (hoje - entry.vencimento).days
        pendente = entry.valor_original - entry.valor_pago
        if dias <= 7:
            b = "0_7_dias"
        elif dias <= 15:
            b = "8_15_dias"
        elif dias <= 30:
            b = "16_30_dias"
        else:
            b = "acima_30_dias"
        buckets[b]["clientes"].add(str(entry.customer_id))
        buckets[b]["valor"] += pendente
        buckets[b]["count"] += 1

    total_valor = sum(b["valor"] for b in buckets.values())
    total_clientes: set = set()
    for b in buckets.values():
        total_clientes.update(b["clientes"])

    return {
        k: {
            "clientes": len(v["clientes"]),
            "valor": float(v["valor"]),
            "count": v["count"],
        }
        for k, v in buckets.items()
    } | {"total": {"clientes": len(total_clientes), "valor": float(total_valor)}}


async def get_entries_para_cobranca(db: AsyncSession) -> list:
    """Entries vencidas há mais de 1 dia, não cobradas nas últimas 48h."""
    from app.models.financeiro.fiado_entry import FiadoEntry
    from sqlalchemy import or_
    from datetime import date, datetime, timezone, timedelta

    hoje = date.today()
    limite_cobranca = datetime.now(timezone.utc) - timedelta(hours=48)

    result = await db.execute(
        select(FiadoEntry).where(
            and_(
                FiadoEntry.vencimento < hoje,
                FiadoEntry.status.in_(["em_aberto", "pago_parcial"]),
                or_(
                    FiadoEntry.cobrado_whatsapp_at == None,
                    FiadoEntry.cobrado_whatsapp_at < limite_cobranca,
                ),
            )
        ).order_by(FiadoEntry.vencimento)
    )
    return result.scalars().all()


async def enviar_cobranca_whatsapp(db: AsyncSession, entry_id: UUID) -> bool:
    """Envia cobrança WhatsApp para cliente da entry."""
    from app.models.financeiro.fiado_entry import FiadoEntry
    from app.models.customer import Customer
    from datetime import datetime, timezone
    import httpx
    from app.config import settings

    result = await db.execute(select(FiadoEntry).where(FiadoEntry.id == entry_id))
    entry = result.scalar_one_or_none()
    if not entry:
        return False

    cust_result = await db.execute(select(Customer).where(Customer.id == entry.customer_id))
    customer = cust_result.scalar_one_or_none()
    if not customer:
        return False

    pendente = entry.valor_original - entry.valor_pago
    mensagem = (
        f"Olá {customer.name}! 👋\n\n"
        f"Você tem uma conta em aberto de *R$ {float(pendente):.2f}* "
        f"referente a um pedido fiado.\n"
        f"📅 Vencimento: {entry.vencimento.strftime('%d/%m/%Y')}\n\n"
        f"Entre em contato para regularizar. Obrigado!"
    )

    phone = getattr(customer, "phone", None) or getattr(customer, "whatsapp", None)
    if not phone:
        return False

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{settings.waha_url}/api/sendText",
                headers={"X-Api-Key": settings.waha_api_key},
                json={
                    "session": settings.waha_session_name,
                    "chatId": f"{phone}@c.us",
                    "text": mensagem,
                },
            )

        entry.cobrado_whatsapp_at = datetime.now(timezone.utc)
        entry.cobrado_count += 1
        await db.flush()
        return resp.status_code < 300
    except Exception:
        return False
