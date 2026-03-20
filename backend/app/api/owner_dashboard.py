"""
Owner Dashboard API
Dashboard executivo para o dono do negócio.

Responde em 30 segundos:
- 💰 Estou ganhando dinheiro?
- 📈 Está melhor ou pior que ontem/semana/mês?
- 🚚 A operação está eficiente?
- 📍 Onde estou perdendo dinheiro ou tempo?
- 👥 Minha equipe está performando?
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional, List, Dict, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import and_, case, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.auth_models import User
from app.models.business_settings import (
    BusinessSettings as BusinessSettingsModel,
    DEFAULT_MONTHLY_GOALS,
    DEFAULT_OPERATING_HOURS,
)
from app.models.customer import Customer
from app.models.delivery import Delivery, DeliveryStatus as DeliveryStatusEnum
from app.models.order import Order, OrderItem, OrderStatus, TipoOperacao
from app.models.product import Product

router = APIRouter(prefix="/owner", tags=["Owner", "Dashboard"])


def _require_owner(user: User) -> None:
    """Verifica se o usuário tem role 'owner' ou 'admin'."""
    if user.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas owners e admins podem acessar este recurso",
        )


# ==================== SCHEMAS ====================


class FinancialMetrics(BaseModel):
    """Métricas financeiras."""
    revenue_today: float
    revenue_week: float       # receita da semana atual (seg → agora)
    revenue_month: float
    revenue_yesterday: float
    revenue_last_week: float
    revenue_last_month: float
    average_ticket: float
    growth_vs_yesterday: float  # %
    growth_vs_last_week: float  # %
    growth_vs_last_month: float  # %


class OperationalMetrics(BaseModel):
    """Métricas operacionais."""
    orders_today: int
    orders_yesterday: int
    orders_completed: int
    orders_cancelled: int
    orders_cancelled_today: int
    average_delivery_time: Optional[float]  # minutos
    on_time_delivery_rate: Optional[float]  # %


class PaymentMetrics(BaseModel):
    """Métricas de pagamento."""
    cash_percentage: float
    card_percentage: float
    pix_percentage: float
    cash_count: int
    card_count: int
    pix_count: int
    cash_value: float
    card_value: float
    pix_value: float
    approval_rate: float  # %


class ExecutiveCards(BaseModel):
    """Cards executivos do topo."""
    financial: FinancialMetrics
    operational: OperationalMetrics
    payment: PaymentMetrics


class RevenueChartPoint(BaseModel):
    """Ponto do gráfico de receita."""
    date: str
    revenue: float
    orders: int


class RevenueChart(BaseModel):
    """Gráfico de receita ao longo do tempo."""
    period: str  # "day", "week", "month"
    current: list[RevenueChartPoint]
    previous: list[RevenueChartPoint]


class OrdersByType(BaseModel):
    """Pedidos por tipo."""
    troca: int
    venda: int
    retira: int
    troca_revenue: float
    venda_revenue: float
    retira_revenue: float


class OrdersByBairro(BaseModel):
    """Pedidos por bairro."""
    bairro: str
    orders: int
    revenue: float
    cancelled: int
    avg_delivery_time: Optional[float]


class TopProduct(BaseModel):
    """Produto mais vendido."""
    code: str
    name: str
    quantity: int
    revenue: float


class DriverPerformance(BaseModel):
    """Performance de entregador."""
    driver_id: Optional[str]
    driver_name: Optional[str]
    deliveries_count: int
    avg_delivery_time: Optional[float]
    on_time_rate: Optional[float]
    late_deliveries: int


class OperatorPerformance(BaseModel):
    """Performance de operador."""
    user_id: int
    username: str
    email: str
    orders_approved: int
    avg_response_time: Optional[float]  # segundos
    errors_count: int


class FinancialBreakdown(BaseModel):
    """Breakdown financeiro."""
    gross_revenue: float
    net_revenue: float
    cancelled_revenue: float
    cancelled_count: int
    cancelled_reasons: dict[str, int]
    pending_payments_count: int
    pending_payments_value: float
    repeat_customers_count: int
    new_customers_count: int
    repeat_rate: float  # %


class CustomerMetrics(BaseModel):
    """Métricas de clientes."""
    total_active: int
    new_today: int
    new_month: int
    top_customers: list[dict[str, Any]]
    repeat_rate: float


class BairroMetrics(BaseModel):
    """Métricas por bairro."""
    most_profitable: list[OrdersByBairro]
    most_cancelled: list[OrdersByBairro]
    slowest_delivery: list[OrdersByBairro]


class ExecutiveAlert(BaseModel):
    """Alerta executivo."""
    type: str  # "critical", "warning"
    title: str
    message: str
    count: Optional[int] = None
    value: Optional[float] = None


class OwnerDashboardResponse(BaseModel):
    """Resposta completa do dashboard."""
    cards: ExecutiveCards
    revenue_chart: RevenueChart
    orders_by_type: OrdersByType
    orders_by_bairro: list[OrdersByBairro]
    top_products: list[TopProduct]
    driver_performance: list[DriverPerformance]
    operator_performance: list[OperatorPerformance]
    financial_breakdown: FinancialBreakdown
    customer_metrics: CustomerMetrics
    bairro_metrics: BairroMetrics
    alerts: list[ExecutiveAlert]


# ==================== HELPERS ====================


def _get_period_dates(period: str) -> tuple[datetime, datetime, datetime, datetime]:
    """Retorna datas para período atual e anterior."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if period == "day":
        current_start = today_start
        current_end = now
        previous_start = today_start - timedelta(days=1)
        previous_end = today_start
    elif period == "week":
        days_since_monday = now.weekday()
        current_start = today_start - timedelta(days=days_since_monday)
        current_end = now
        previous_start = current_start - timedelta(days=7)
        previous_end = current_start
    elif period == "month":
        current_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current_end = now
        # Mês anterior
        if current_start.month == 1:
            previous_start = current_start.replace(year=current_start.year - 1, month=12)
        else:
            previous_start = current_start.replace(month=current_start.month - 1)
        previous_end = current_start
    else:
        raise ValueError(f"Invalid period: {period}")

    return current_start, current_end, previous_start, previous_end


# ==================== ENDPOINTS ====================


@router.get("/dashboard", response_model=OwnerDashboardResponse)
async def get_owner_dashboard(
    period: str = Query("day", regex="^(day|week|month)$"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Dashboard executivo completo para o owner.

    Retorna todas as métricas necessárias para responder em 30 segundos:
    - 💰 Estou ganhando dinheiro?
    - 📈 Está melhor ou pior que ontem/semana/mês?
    - 🚚 A operação está eficiente?
    - 📍 Onde estou perdendo dinheiro ou tempo?
    - 👥 Minha equipe está performando?
    """
    _require_owner(current_user)

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    # Início da semana atual (segunda-feira) — usado para revenue_week
    this_week_start = today_start - timedelta(days=now.weekday())
    # Janela de 7 dias rolante — usada para comparativo growth_vs_last_week
    week_start = today_start - timedelta(days=7)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)

    # ==================== FINANCIAL METRICS ====================

    # Receita hoje
    revenue_today_stmt = select(func.coalesce(func.sum(Order.total_amount), 0)).where(
        and_(
            Order.created_at >= today_start,
            Order.status != OrderStatus.CANCELLED.value,
        )
    )
    revenue_today = float((await session.execute(revenue_today_stmt)).scalar() or 0)

    # Receita ontem
    revenue_yesterday_stmt = select(func.coalesce(func.sum(Order.total_amount), 0)).where(
        and_(
            Order.created_at >= yesterday_start,
            Order.created_at < today_start,
            Order.status != OrderStatus.CANCELLED.value,
        )
    )
    revenue_yesterday = float((await session.execute(revenue_yesterday_stmt)).scalar() or 0)

    # Receita semana atual (segunda → agora)
    revenue_week_stmt = select(func.coalesce(func.sum(Order.total_amount), 0)).where(
        and_(
            Order.created_at >= this_week_start,
            Order.status != OrderStatus.CANCELLED.value,
        )
    )
    revenue_week = float((await session.execute(revenue_week_stmt)).scalar() or 0)

    # Receita semana passada (janela de 7 dias anterior)
    revenue_last_week_stmt = select(func.coalesce(func.sum(Order.total_amount), 0)).where(
        and_(
            Order.created_at >= week_start - timedelta(days=7),
            Order.created_at < week_start,
            Order.status != OrderStatus.CANCELLED.value,
        )
    )
    revenue_last_week = float((await session.execute(revenue_last_week_stmt)).scalar() or 0)

    # Receita mês atual
    revenue_month_stmt = select(func.coalesce(func.sum(Order.total_amount), 0)).where(
        and_(
            Order.created_at >= month_start,
            Order.status != OrderStatus.CANCELLED.value,
        )
    )
    revenue_month = float((await session.execute(revenue_month_stmt)).scalar() or 0)

    # Receita mês passado
    revenue_last_month_stmt = select(func.coalesce(func.sum(Order.total_amount), 0)).where(
        and_(
            Order.created_at >= last_month_start,
            Order.created_at < month_start,
            Order.status != OrderStatus.CANCELLED.value,
        )
    )
    revenue_last_month = float((await session.execute(revenue_last_month_stmt)).scalar() or 0)

    # Ticket médio hoje
    orders_today_count_stmt = select(func.count(Order.id)).where(
        and_(
            Order.created_at >= today_start,
            Order.status != OrderStatus.CANCELLED.value,
        )
    )
    orders_today_count = (await session.execute(orders_today_count_stmt)).scalar() or 0
    average_ticket = revenue_today / orders_today_count if orders_today_count > 0 else 0.0

    # Crescimento %
    growth_vs_yesterday = (
        ((revenue_today - revenue_yesterday) / revenue_yesterday * 100) if revenue_yesterday > 0 else 0.0
    )
    growth_vs_last_week = (
        ((revenue_today - revenue_last_week) / revenue_last_week * 100) if revenue_last_week > 0 else 0.0
    )
    growth_vs_last_month = (
        ((revenue_month - revenue_last_month) / revenue_last_month * 100) if revenue_last_month > 0 else 0.0
    )

    financial = FinancialMetrics(
        revenue_today=revenue_today,
        revenue_week=revenue_week,
        revenue_month=revenue_month,
        revenue_yesterday=revenue_yesterday,
        revenue_last_week=revenue_last_week,
        revenue_last_month=revenue_last_month,
        average_ticket=average_ticket,
        growth_vs_yesterday=growth_vs_yesterday,
        growth_vs_last_week=growth_vs_last_week,
        growth_vs_last_month=growth_vs_last_month,
    )

    # ==================== OPERATIONAL METRICS ====================

    # Pedidos hoje
    orders_today_stmt = select(func.count(Order.id)).where(Order.created_at >= today_start)
    orders_today = (await session.execute(orders_today_stmt)).scalar() or 0

    # Pedidos ontem
    orders_yesterday_stmt = select(func.count(Order.id)).where(
        and_(Order.created_at >= yesterday_start, Order.created_at < today_start)
    )
    orders_yesterday = (await session.execute(orders_yesterday_stmt)).scalar() or 0

    # Pedidos concluídos hoje (entregues)
    orders_completed_stmt = select(func.count(Order.id)).where(
        and_(
            Order.created_at >= today_start,
            Order.status == OrderStatus.DELIVERED.value,
        )
    )
    orders_completed = (await session.execute(orders_completed_stmt)).scalar() or 0

    # Pedidos cancelados hoje
    orders_cancelled_today_stmt = select(func.count(Order.id)).where(
        and_(
            Order.created_at >= today_start,
            Order.status == OrderStatus.CANCELLED.value,
        )
    )
    orders_cancelled_today = (await session.execute(orders_cancelled_today_stmt)).scalar() or 0
    orders_cancelled = orders_cancelled_today  # alias — ambos referem-se ao dia atual

    # Tempo médio de entrega
    avg_delivery_time_stmt = select(func.avg(Delivery.actual_delivery_minutes)).where(
        Delivery.actual_delivery_minutes.is_not(None)
    )
    avg_delivery_time_result = await session.execute(avg_delivery_time_stmt)
    avg_delivery_time_scalar = avg_delivery_time_result.scalar()
    avg_delivery_time = float(avg_delivery_time_scalar or 0) if avg_delivery_time_scalar else None

    # Taxa de entrega no prazo (assumindo 60 min como padrão)
    on_time_deliveries_stmt = select(func.count(Delivery.id)).where(
        and_(
            Delivery.status == DeliveryStatusEnum.DELIVERED.value,
            Delivery.actual_delivery_minutes.is_not(None),
            Delivery.actual_delivery_minutes <= 60,
        )
    )
    on_time_deliveries = (await session.execute(on_time_deliveries_stmt)).scalar() or 0

    total_deliveries_stmt = select(func.count(Delivery.id)).where(
        and_(
            Delivery.status == DeliveryStatusEnum.DELIVERED.value,
            Delivery.actual_delivery_minutes.is_not(None),
        )
    )
    total_deliveries = (await session.execute(total_deliveries_stmt)).scalar() or 0
    on_time_rate = (on_time_deliveries / total_deliveries * 100) if total_deliveries > 0 else None

    operational = OperationalMetrics(
        orders_today=orders_today,
        orders_yesterday=orders_yesterday,
        orders_completed=orders_completed,
        orders_cancelled=orders_cancelled,
        orders_cancelled_today=orders_cancelled_today,
        average_delivery_time=avg_delivery_time,
        on_time_delivery_rate=on_time_rate,
    )

    # ==================== PAYMENT METRICS ====================

    # Uma única query agrega count + sum por método de pagamento (hoje, não cancelados)
    payment_agg_stmt = (
        select(
            Order.payment_method,
            func.count(Order.id).label("cnt"),
            func.coalesce(func.sum(Order.total_amount), 0).label("val"),
        )
        .where(
            and_(
                Order.created_at >= today_start,
                Order.status != OrderStatus.CANCELLED.value,
                Order.payment_method.is_not(None),
            )
        )
        .group_by(Order.payment_method)
    )
    payment_rows = (await session.execute(payment_agg_stmt)).all()

    _CASH_METHODS = {"cash"}
    _CARD_METHODS = {"credit_card", "debit_card"}
    _PIX_METHODS  = {"pix"}

    cash_count, cash_value = 0, 0.0
    card_count, card_value = 0, 0.0
    pix_count,  pix_value  = 0, 0.0

    for row in payment_rows:
        method = (row.payment_method or "").lower()
        cnt = int(row.cnt or 0)
        val = float(row.val or 0)
        if method in _CASH_METHODS:
            cash_count += cnt
            cash_value += val
        elif method in _CARD_METHODS:
            card_count += cnt
            card_value += val
        elif method in _PIX_METHODS:
            pix_count += cnt
            pix_value += val

    total_payments = cash_count + card_count + pix_count
    cash_percentage = (cash_count / total_payments * 100) if total_payments > 0 else 0.0
    card_percentage = (card_count / total_payments * 100) if total_payments > 0 else 0.0
    pix_percentage  = (pix_count  / total_payments * 100) if total_payments > 0 else 0.0

    # Taxa de aprovação (pedidos pagos vs pendentes)
    paid_orders_stmt = select(func.count(Order.id)).where(
        and_(
            Order.created_at >= today_start,
            Order.status.in_([OrderStatus.PAID.value, OrderStatus.PREPARING.value, OrderStatus.DISPATCHED.value, OrderStatus.DELIVERED.value]),
        )
    )
    paid_orders = (await session.execute(paid_orders_stmt)).scalar() or 0

    approval_rate = (paid_orders / orders_today * 100) if orders_today > 0 else 0.0

    payment = PaymentMetrics(
        cash_percentage=cash_percentage,
        card_percentage=card_percentage,
        pix_percentage=pix_percentage,
        cash_count=cash_count,
        card_count=card_count,
        pix_count=pix_count,
        cash_value=cash_value,
        card_value=card_value,
        pix_value=pix_value,
        approval_rate=approval_rate,
    )

    cards = ExecutiveCards(financial=financial, operational=operational, payment=payment)

    # ==================== REVENUE CHART ====================

    current_start, current_end, previous_start, previous_end = _get_period_dates(period)

    # Receita período atual
    current_revenue_stmt = (
        select(
            func.date(Order.created_at).label("date"),
            func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
            func.count(Order.id).label("orders"),
        )
        .where(
            and_(
                Order.created_at >= current_start,
                Order.created_at <= current_end,
                Order.status != OrderStatus.CANCELLED.value,
            )
        )
        .group_by(func.date(Order.created_at))
        .order_by(func.date(Order.created_at))
    )
    current_rows = await session.execute(current_revenue_stmt)
    current_chart = [
        RevenueChartPoint(
            date=row.date.isoformat(),
            revenue=float(row.revenue or 0),
            orders=int(row.orders or 0),
        )
        for row in current_rows
    ]

    # Receita período anterior
    previous_revenue_stmt = (
        select(
            func.date(Order.created_at).label("date"),
            func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
            func.count(Order.id).label("orders"),
        )
        .where(
            and_(
                Order.created_at >= previous_start,
                Order.created_at < previous_end,
                Order.status != OrderStatus.CANCELLED.value,
            )
        )
        .group_by(func.date(Order.created_at))
        .order_by(func.date(Order.created_at))
    )
    previous_rows = await session.execute(previous_revenue_stmt)
    previous_chart = [
        RevenueChartPoint(
            date=row.date.isoformat(),
            revenue=float(row.revenue or 0),
            orders=int(row.orders or 0),
        )
        for row in previous_rows
    ]

    revenue_chart = RevenueChart(period=period, current=current_chart, previous=previous_chart)

    # ==================== ORDERS BY TYPE ====================

    orders_by_type_stmt = (
        select(
            Order.tipo_operacao,
            func.count(Order.id).label("count"),
            func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
        )
        .where(
            and_(
                Order.created_at >= month_start,
                Order.status != OrderStatus.CANCELLED.value,
            )
        )
        .group_by(Order.tipo_operacao)
    )
    orders_by_type_rows = await session.execute(orders_by_type_stmt)
    orders_by_type_dict = {row.tipo_operacao: {"count": row.count, "revenue": float(row.revenue or 0)} for row in orders_by_type_rows}

    orders_by_type = OrdersByType(
        troca=orders_by_type_dict.get(TipoOperacao.TROCA.value, {}).get("count", 0),
        venda=orders_by_type_dict.get(TipoOperacao.VENDA.value, {}).get("count", 0),
        retira=orders_by_type_dict.get(TipoOperacao.RETIRA.value, {}).get("count", 0),
        troca_revenue=orders_by_type_dict.get(TipoOperacao.TROCA.value, {}).get("revenue", 0.0),
        venda_revenue=orders_by_type_dict.get(TipoOperacao.VENDA.value, {}).get("revenue", 0.0),
        retira_revenue=orders_by_type_dict.get(TipoOperacao.RETIRA.value, {}).get("revenue", 0.0),
    )

    # ==================== ORDERS BY BAIRRO ====================

    orders_by_bairro_stmt = (
        select(
            Order.delivery_bairro,
            func.count(Order.id).label("orders"),
            func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
            func.sum(case((Order.status == OrderStatus.CANCELLED.value, 1), else_=0)).label("cancelled"),
        )
        .where(
            and_(
                Order.created_at >= month_start,
                Order.delivery_bairro.is_not(None),
            )
        )
        .group_by(Order.delivery_bairro)
        .order_by(desc("revenue"))
        .limit(10)
    )
    orders_by_bairro_rows = await session.execute(orders_by_bairro_stmt)

    # Calcular tempo médio por bairro
    bairro_list = []
    for row in orders_by_bairro_rows:
        bairro = row.delivery_bairro
        if not bairro:
            continue

        # Tempo médio de entrega para este bairro
        avg_time_stmt = (
            select(func.avg(Delivery.actual_delivery_minutes))
            .join(Order, Order.id == Delivery.order_id)
            .where(
                and_(
                    Order.delivery_bairro == bairro,
                    Delivery.actual_delivery_minutes.is_not(None),
                    Order.created_at >= month_start,
                )
            )
        )
        avg_time_result = await session.execute(avg_time_stmt)
        avg_time_scalar = avg_time_result.scalar()
        avg_time = float(avg_time_scalar or 0) if avg_time_scalar else None

        bairro_list.append(
            OrdersByBairro(
                bairro=bairro,
                orders=int(row.orders or 0),
                revenue=float(row.revenue or 0),
                cancelled=int(row.cancelled or 0),
                avg_delivery_time=avg_time,
            )
        )

    # ==================== TOP PRODUCTS ====================

    top_products_stmt = (
        select(
            OrderItem.product_code,
            OrderItem.product_name,
            func.sum(OrderItem.quantity).label("quantity"),
            func.coalesce(func.sum(OrderItem.subtotal), 0).label("revenue"),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            and_(
                Order.created_at >= month_start,
                Order.status != OrderStatus.CANCELLED.value,
            )
        )
        .group_by(OrderItem.product_code, OrderItem.product_name)
        .order_by(desc("revenue"))
        .limit(10)
    )
    top_products_rows = await session.execute(top_products_stmt)
    top_products = [
        TopProduct(
            code=row.product_code,
            name=row.product_name,
            quantity=int(row.quantity or 0),
            revenue=float(row.revenue or 0),
        )
        for row in top_products_rows
    ]

    # ==================== DRIVER PERFORMANCE ====================

    driver_perf_stmt = (
        select(
            Delivery.driver_id,
            Delivery.driver_name,
            func.count(Delivery.id).label("deliveries_count"),
            func.avg(Delivery.actual_delivery_minutes).label("avg_time"),
            func.sum(case((Delivery.actual_delivery_minutes > 60, 1), else_=0)).label("late_count"),
        )
        .where(
            and_(
                Delivery.status == DeliveryStatusEnum.DELIVERED.value,
                Delivery.actual_delivery_minutes.is_not(None),
                Delivery.delivered_at >= month_start,
            )
        )
        .group_by(Delivery.driver_id, Delivery.driver_name)
        .order_by(desc("deliveries_count"))
        .limit(10)
    )
    driver_perf_rows = await session.execute(driver_perf_stmt)

    driver_performance = []
    for row in driver_perf_rows:
        deliveries_count = int(row.deliveries_count or 0)
        avg_time = float(row.avg_time or 0) if row.avg_time else None
        late_count = int(row.late_count or 0)
        on_time_rate = ((deliveries_count - late_count) / deliveries_count * 100) if deliveries_count > 0 else None

        driver_performance.append(
            DriverPerformance(
                driver_id=str(row.driver_id) if row.driver_id else None,
                driver_name=row.driver_name,
                deliveries_count=deliveries_count,
                avg_delivery_time=avg_time,
                on_time_rate=on_time_rate,
                late_deliveries=late_count,
            )
        )

    # ==================== OPERATOR PERFORMANCE ====================

    # Buscar operadores (role operator/admin)
    operators_stmt = select(User).where(User.role.in_(["operator", "admin"]))
    operators_result = await session.execute(operators_stmt)
    operators = operators_result.scalars().all()

    # Buscar contagem de aprovações por operador em UMA única query
    approvals_stmt = (
        select(Order.approved_by, func.count(Order.id).label("count"))
        .where(
            and_(
                Order.approved_by.isnot(None),
                Order.paid_at >= month_start,
                Order.status != OrderStatus.CANCELLED.value,
            )
        )
        .group_by(Order.approved_by)
    )
    approvals_result = await session.execute(approvals_stmt)
    approvals_by_user = {row.approved_by: row.count for row in approvals_result}

    # Montar lista de performance usando o dict (sem queries adicionais)
    operator_performance = []
    for op in operators:
        operator_performance.append(
            OperatorPerformance(
                user_id=op.id,
                username=op.username,
                email=op.email,
                orders_approved=approvals_by_user.get(op.id, 0),
                avg_response_time=None,
                errors_count=0,
            )
        )

    # Ordenar por pedidos aprovados (maior primeiro)
    operator_performance.sort(key=lambda x: x.orders_approved, reverse=True)

    # ==================== FINANCIAL BREAKDOWN ====================

    # Receita bruta (todos os pedidos não cancelados)
    gross_revenue_stmt = select(func.coalesce(func.sum(Order.total_amount), 0)).where(
        and_(
            Order.created_at >= month_start,
            Order.status != OrderStatus.CANCELLED.value,
        )
    )
    gross_revenue = float((await session.execute(gross_revenue_stmt)).scalar() or 0)

    # Receita líquida (apenas entregues)
    net_revenue_stmt = select(func.coalesce(func.sum(Order.total_amount), 0)).where(
        and_(
            Order.created_at >= month_start,
            Order.status == OrderStatus.DELIVERED.value,
        )
    )
    net_revenue = float((await session.execute(net_revenue_stmt)).scalar() or 0)

    # Receita cancelada
    cancelled_revenue_stmt = select(func.coalesce(func.sum(Order.total_amount), 0)).where(
        and_(
            Order.created_at >= month_start,
            Order.status == OrderStatus.CANCELLED.value,
        )
    )
    cancelled_revenue = float((await session.execute(cancelled_revenue_stmt)).scalar() or 0)

    # Motivos de cancelamento
    cancelled_reasons_stmt = (
        select(
            Order.cancellation_reason,
            func.count(Order.id).label("count"),
        )
        .where(
            and_(
                Order.created_at >= month_start,
                Order.status == OrderStatus.CANCELLED.value,
                Order.cancellation_reason.is_not(None),
            )
        )
        .group_by(Order.cancellation_reason)
    )
    cancelled_reasons_rows = await session.execute(cancelled_reasons_stmt)
    cancelled_reasons = {row.cancellation_reason or "Sem motivo": int(row.count or 0) for row in cancelled_reasons_rows}

    # Pedidos pendentes de pagamento
    pending_payments_stmt = select(
        func.count(Order.id).label("count"),
        func.coalesce(func.sum(Order.total_amount), 0).label("value"),
    ).where(
        and_(
            Order.created_at >= month_start,
            Order.status == OrderStatus.PENDING.value,
        )
    )
    pending_result = await session.execute(pending_payments_stmt)
    pending_row = pending_result.first()
    pending_payments_count = int(pending_row.count or 0) if pending_row else 0
    pending_payments_value = float(pending_row.value or 0) if pending_row else 0.0

    # Clientes recorrentes vs novos (simplificado: contar clientes com múltiplos pedidos no mês)
    all_customers_stmt = select(func.count(func.distinct(Order.customer_id))).where(
        and_(
            Order.created_at >= month_start,
            Order.status != OrderStatus.CANCELLED.value,
        )
    )
    all_customers_count = (await session.execute(all_customers_stmt)).scalar() or 0

    # Clientes com mais de 1 pedido no mês (recorrentes)
    repeat_customers_subq = (
        select(Order.customer_id)
        .where(
            and_(
                Order.created_at >= month_start,
                Order.status != OrderStatus.CANCELLED.value,
            )
        )
        .group_by(Order.customer_id)
        .having(func.count(Order.id) > 1)
        .subquery()
    )
    repeat_customers_stmt = select(func.count()).select_from(repeat_customers_subq)
    repeat_customers_count = (await session.execute(repeat_customers_stmt)).scalar() or 0
    
    # Simplificado: assumir que novos = total - recorrentes
    new_customers_count = max(0, all_customers_count - repeat_customers_count)
    repeat_rate = (repeat_customers_count / all_customers_count * 100) if all_customers_count > 0 else 0.0

    financial_breakdown = FinancialBreakdown(
        gross_revenue=gross_revenue,
        net_revenue=net_revenue,
        cancelled_revenue=cancelled_revenue,
        cancelled_count=orders_cancelled,
        cancelled_reasons=cancelled_reasons,
        pending_payments_count=pending_payments_count,
        pending_payments_value=pending_payments_value,
        repeat_customers_count=repeat_customers_count,
        new_customers_count=new_customers_count,
        repeat_rate=repeat_rate,
    )

    # ==================== CUSTOMER METRICS ====================

    # Clientes ativos (com pedido nos últimos 30 dias)
    active_customers_stmt = select(func.count(func.distinct(Order.customer_id))).where(
        and_(
            Order.created_at >= now - timedelta(days=30),
            Order.status != OrderStatus.CANCELLED.value,
        )
    )
    total_active = (await session.execute(active_customers_stmt)).scalar() or 0

    # Novos hoje
    new_today_stmt = select(func.count(func.distinct(Order.customer_id))).where(
        and_(
            Order.created_at >= today_start,
            Order.status != OrderStatus.CANCELLED.value,
        )
    )
    new_today = (await session.execute(new_today_stmt)).scalar() or 0

    # Novos no mês
    new_month_stmt = select(func.count(func.distinct(Order.customer_id))).where(
        and_(
            Order.created_at >= month_start,
            Order.status != OrderStatus.CANCELLED.value,
        )
    )
    new_month = (await session.execute(new_month_stmt)).scalar() or 0

    # Top clientes (por valor total)
    top_customers_stmt = (
        select(
            Order.customer_id,
            func.coalesce(func.sum(Order.total_amount), 0).label("total_revenue"),
            func.count(Order.id).label("orders_count"),
        )
        .where(
            and_(
                Order.created_at >= month_start,
                Order.status != OrderStatus.CANCELLED.value,
            )
        )
        .group_by(Order.customer_id)
        .order_by(desc("total_revenue"))
        .limit(10)
    )
    top_customers_rows = await session.execute(top_customers_stmt)
    top_customers_data = list(top_customers_rows)

    # Buscar todos os clientes em uma única query
    customer_ids = [row.customer_id for row in top_customers_data if row.customer_id]
    customers_by_id = {}
    if customer_ids:
        customers_result = await session.execute(
            select(Customer).where(Customer.id.in_(customer_ids))
        )
        customers_by_id = {c.id: c for c in customers_result.scalars().all()}

    top_customers_list = []
    for row in top_customers_data:
        customer = customers_by_id.get(row.customer_id)
        top_customers_list.append({
            "customer_id": str(row.customer_id),
            "name": customer.name if customer else "Cliente",
            "phone": customer.phone if customer else "",
            "total_revenue": float(row.total_revenue or 0),
            "orders_count": int(row.orders_count or 0),
        })

    customer_metrics = CustomerMetrics(
        total_active=total_active,
        new_today=new_today,
        new_month=new_month,
        top_customers=top_customers_list,
        repeat_rate=repeat_rate,
    )

    # ==================== BAIRRO METRICS ====================

    # Mais lucrativos (já temos em orders_by_bairro)
    most_profitable = sorted(bairro_list, key=lambda x: x.revenue, reverse=True)[:5]

    # Mais cancelamentos
    most_cancelled = sorted(bairro_list, key=lambda x: x.cancelled, reverse=True)[:5]

    # Entrega mais lenta
    slowest_delivery = sorted(
        [b for b in bairro_list if b.avg_delivery_time],
        key=lambda x: x.avg_delivery_time or 0,
        reverse=True,
    )[:5]

    bairro_metrics = BairroMetrics(
        most_profitable=most_profitable,
        most_cancelled=most_cancelled,
        slowest_delivery=slowest_delivery,
    )

    # ==================== ALERTS ====================

    alerts = []

    # Entregas atrasadas
    late_deliveries_stmt = select(func.count(Delivery.id)).where(
        and_(
            Delivery.status.in_([DeliveryStatusEnum.IN_TRANSIT.value, DeliveryStatusEnum.PICKED_UP.value]),
            Delivery.picked_up_at < now - timedelta(minutes=90),
        )
    )
    late_deliveries = (await session.execute(late_deliveries_stmt)).scalar() or 0
    if late_deliveries > 0:
        alerts.append(
            ExecutiveAlert(
                type="critical",
                title="Entregas atrasadas",
                message=f"{late_deliveries} entregas em trânsito há mais de 90 minutos",
                count=late_deliveries,
            )
        )

    # Muitos cancelamentos hoje
    if orders_cancelled_today > 5:
        alerts.append(
            ExecutiveAlert(
                type="warning",
                title="Muitos cancelamentos hoje",
                message=f"{orders_cancelled_today} pedidos cancelados hoje",
                count=orders_cancelled_today,
            )
        )

    # Queda de faturamento
    if revenue_today < revenue_yesterday * 0.7 and revenue_yesterday > 0:
        alerts.append(
            ExecutiveAlert(
                type="warning",
                title="Queda de faturamento",
                message=f"Faturamento hoje ({revenue_today:.2f}) está {((revenue_today - revenue_yesterday) / revenue_yesterday * 100):.1f}% menor que ontem",
                value=revenue_today,
            )
        )

    # Pedidos pagos parados (confirmados há mais de 15 min sem avançar para preparando)
    stuck_paid_stmt = select(func.count(Order.id)).where(
        and_(
            Order.status == OrderStatus.PAID.value,
            Order.paid_at.isnot(None),
            Order.paid_at < now - timedelta(minutes=15),
        )
    )
    stuck_paid_count = int((await session.execute(stuck_paid_stmt)).scalar() or 0)
    if stuck_paid_count > 0:
        alerts.append(
            ExecutiveAlert(
                type="critical",
                title="Pedidos confirmados parados",
                message=f"{stuck_paid_count} pedido{'s' if stuck_paid_count > 1 else ''} confirmado{'s' if stuck_paid_count > 1 else ''} há mais de 15 minutos sem iniciar preparo",
                count=stuck_paid_count,
            )
        )

    return OwnerDashboardResponse(
        cards=cards,
        revenue_chart=revenue_chart,
        orders_by_type=orders_by_type,
        orders_by_bairro=bairro_list,
        top_products=top_products,
        driver_performance=driver_performance,
        operator_performance=operator_performance,
        financial_breakdown=financial_breakdown,
        customer_metrics=customer_metrics,
        bairro_metrics=bairro_metrics,
        alerts=alerts,
    )


# ==================== SPARKLINE MENSAL ====================


@router.get("/monthly-revenue", response_model=list[RevenueChartPoint])
async def get_monthly_revenue(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Receita diária do mês corrente — usado no sparkline do dashboard."""
    _require_owner(current_user)

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    stmt = (
        select(
            func.date(Order.created_at).label("date"),
            func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
            func.count(Order.id).label("orders"),
        )
        .where(
            and_(
                Order.created_at >= month_start,
                Order.created_at <= now,
                Order.status != OrderStatus.CANCELLED.value,
            )
        )
        .group_by(func.date(Order.created_at))
        .order_by(func.date(Order.created_at))
    )
    rows = (await session.execute(stmt)).all()

    return [
        RevenueChartPoint(
            date=str(row.date),
            revenue=float(row.revenue or 0),
            orders=int(row.orders or 0),
        )
        for row in rows
    ]


# ==================== RELATÓRIOS EXPORTÁVEIS ====================


@router.get("/reports/{report_type}")
async def export_report(
    report_type: str,
    start_date: str = Query(..., description="Data inicial (YYYY-MM-DD)"),
    end_date: str = Query(..., description="Data final (YYYY-MM-DD)"),
    format: str = Query("csv", regex="^(csv|pdf)$"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Exporta relatórios em CSV ou PDF.
    
    Tipos disponíveis:
    - revenue: Faturamento por período
    - orders: Pedidos por produto
    - drivers: Comissão de entregadores
    - performance: Desempenho mensal
    """
    _require_owner(current_user)

    try:
        start = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
        end = datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc)
        end = end.replace(hour=23, minute=59, second=59)
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de data inválido. Use YYYY-MM-DD")

    if report_type == "revenue":
        # Faturamento por período
        stmt = (
            select(
                func.date(Order.created_at).label("date"),
                func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
                func.count(Order.id).label("orders"),
            )
            .where(
                and_(
                    Order.created_at >= start,
                    Order.created_at <= end,
                    Order.status != OrderStatus.CANCELLED.value,
                )
            )
            .group_by(func.date(Order.created_at))
            .order_by(func.date(Order.created_at))
        )
        rows = await session.execute(stmt)
        data = [
            {
                "data": row.date.isoformat(),
                "receita": float(row.revenue or 0),
                "pedidos": int(row.orders or 0),
            }
            for row in rows
        ]

    elif report_type == "orders":
        # Pedidos por produto
        stmt = (
            select(
                OrderItem.product_code,
                OrderItem.product_name,
                func.sum(OrderItem.quantity).label("quantity"),
                func.coalesce(func.sum(OrderItem.subtotal), 0).label("revenue"),
            )
            .join(Order, Order.id == OrderItem.order_id)
            .where(
                and_(
                    Order.created_at >= start,
                    Order.created_at <= end,
                    Order.status != OrderStatus.CANCELLED.value,
                )
            )
            .group_by(OrderItem.product_code, OrderItem.product_name)
            .order_by(desc("revenue"))
        )
        rows = await session.execute(stmt)
        data = [
            {
                "codigo": row.product_code,
                "produto": row.product_name,
                "quantidade": int(row.quantity or 0),
                "receita": float(row.revenue or 0),
            }
            for row in rows
        ]

    elif report_type == "drivers":
        # Comissão de entregadores
        stmt = (
            select(
                Delivery.driver_id,
                Delivery.driver_name,
                func.count(Delivery.id).label("deliveries"),
                func.avg(Delivery.actual_delivery_minutes).label("avg_time"),
            )
            .where(
                and_(
                    Delivery.status == DeliveryStatusEnum.DELIVERED.value,
                    Delivery.delivered_at >= start,
                    Delivery.delivered_at <= end,
                )
            )
            .group_by(Delivery.driver_id, Delivery.driver_name)
            .order_by(desc("deliveries"))
        )
        rows = await session.execute(stmt)
        data = [
            {
                "entregador": row.driver_name or "Sem nome",
                "entregas": int(row.deliveries or 0),
                "tempo_medio_minutos": float(row.avg_time or 0) if row.avg_time else None,
            }
            for row in rows
        ]

    elif report_type == "performance":
        # Desempenho mensal completo
        # Receita total
        revenue_stmt = select(func.coalesce(func.sum(Order.total_amount), 0)).where(
            and_(
                Order.created_at >= start,
                Order.created_at <= end,
                Order.status != OrderStatus.CANCELLED.value,
            )
        )
        revenue = float((await session.execute(revenue_stmt)).scalar() or 0)

        # Pedidos
        orders_stmt = select(func.count(Order.id)).where(
            and_(
                Order.created_at >= start,
                Order.created_at <= end,
            )
        )
        orders = (await session.execute(orders_stmt)).scalar() or 0

        # Clientes novos
        customers_stmt = select(func.count(func.distinct(Order.customer_id))).where(
            and_(
                Order.created_at >= start,
                Order.created_at <= end,
                Order.status != OrderStatus.CANCELLED.value,
            )
        )
        customers = (await session.execute(customers_stmt)).scalar() or 0

        data = {
            "periodo_inicio": start_date,
            "periodo_fim": end_date,
            "receita_total": revenue,
            "pedidos_total": orders,
            "clientes_novos": customers,
        }

    else:
        raise HTTPException(status_code=400, detail=f"Tipo de relatório inválido: {report_type}")

    if format == "csv":
        from fastapi.responses import Response
        import csv
        import io

        output = io.StringIO()
        if isinstance(data, dict):
            writer = csv.DictWriter(output, fieldnames=data.keys())
            writer.writeheader()
            writer.writerow(data)
        else:
            if data:
                writer = csv.DictWriter(output, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
        
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="relatorio_{report_type}_{start_date}_{end_date}.csv"'},
        )
    else:
        # PDF usando ReportLab
        try:
            from app.services.pdf_export_service import pdf_export_service
            from fastapi.responses import Response
            
            pdf_buffer = pdf_export_service.export_report(
                report_type=report_type,
                data=data,
                title=f"Relatório {report_type.title()} - {start_date} a {end_date}",
            )
            
            return Response(
                content=pdf_buffer.getvalue(),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="relatorio_{report_type}_{start_date}_{end_date}.pdf"'
                },
            )
        except RuntimeError as e:
            # ReportLab não disponível, retornar JSON
            from fastapi.responses import JSONResponse
            return JSONResponse(
                content={
                    "message": "Exportação PDF não disponível. Instale reportlab: pip install reportlab",
                    "data": data,
                }
            )
        except Exception as e:
            logger.error(f"Erro ao gerar PDF: {e}", exc_info=True)
            from fastapi.responses import JSONResponse
            return JSONResponse(
                content={
                    "message": f"Erro ao gerar PDF: {str(e)}",
                    "data": data,
                },
                status_code=500,
            )


# ==================== CONFIGURAÇÕES DE NEGÓCIO ====================


class BusinessSettings(BaseModel):
    """Configurações de negócio."""
    products: list[dict[str, Any]] = []
    bairros: list[str] = []
    enabled_bairros: list[str] = []
    operating_hours: dict[str, dict[str, Any]] = {}
    promotions: list[dict[str, Any]] = []
    monthly_goals: dict[str, float] = {}


async def _get_or_create_settings(session: AsyncSession) -> BusinessSettingsModel:
    """Retorna a linha singleton de settings, criando com defaults se não existir."""
    result = await session.execute(
        select(BusinessSettingsModel).where(BusinessSettingsModel.id == 1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = BusinessSettingsModel(
            id=1,
            operating_hours=DEFAULT_OPERATING_HOURS,
            monthly_goals=DEFAULT_MONTHLY_GOALS,
            enabled_bairros=[],
            promotions=[],
        )
        session.add(row)
        await session.flush()
    return row


@router.get("/settings", response_model=BusinessSettings)
async def get_business_settings(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Retorna configurações de negócio."""
    _require_owner(current_user)

    # Buscar produtos (apenas ativos)
    products_stmt = select(Product).where(Product.is_active == True).order_by(Product.code)
    products_result = await session.execute(products_stmt)
    products = [
        {
            "code": p.code,
            "name": p.name,
            "price": float(p.price or 0),
        }
        for p in products_result.scalars().all()
    ]

    # Buscar bairros únicos dos pedidos (lista completa de bairros conhecidos)
    bairros_stmt = select(func.distinct(Order.delivery_bairro)).where(
        Order.delivery_bairro.is_not(None)
    )
    bairros_result = await session.execute(bairros_stmt)
    bairros = sorted([b[0] for b in bairros_result.all() if b[0]])

    # Ler configurações persistidas do banco
    db_settings = await _get_or_create_settings(session)
    await session.commit()

    # Se enabled_bairros estiver vazio (primeira vez), habilitar todos por padrão
    enabled_bairros = db_settings.enabled_bairros or bairros

    return BusinessSettings(
        products=products,
        bairros=bairros,
        enabled_bairros=enabled_bairros,
        operating_hours=db_settings.operating_hours or DEFAULT_OPERATING_HOURS,
        promotions=db_settings.promotions or [],
        monthly_goals=db_settings.monthly_goals or DEFAULT_MONTHLY_GOALS,
    )


@router.put("/settings")
async def update_business_settings(
    settings: BusinessSettings,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Atualiza configurações de negócio."""
    _require_owner(current_user)

    # 1. Atualizar preços de produtos na tabela products
    updated_count = 0
    for product_data in settings.products:
        code = product_data.get("code")
        if code:
            stmt = select(Product).where(Product.code == code)
            result = await session.execute(stmt)
            product = result.scalar_one_or_none()
            if product:
                new_price = Decimal(str(product_data.get("price", 0)))
                if new_price != product.price:
                    product.price = new_price
                    updated_count += 1

    # 2. Persistir horários, metas, bairros e promoções na tabela business_settings
    db_settings = await _get_or_create_settings(session)
    db_settings.operating_hours = settings.operating_hours
    db_settings.monthly_goals = settings.monthly_goals
    db_settings.enabled_bairros = settings.enabled_bairros
    db_settings.promotions = settings.promotions

    await session.commit()

    return {
        "message": "Configurações atualizadas com sucesso",
        "products_updated": updated_count,
    }
