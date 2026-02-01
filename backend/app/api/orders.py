"""
API de Pedidos.
CRUD e gestão de pedidos.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.config import settings
from app.models.customer import Customer
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.tipo_preco import TipoPreco, ProdutoPreco
from app.models.auth_models import User
from app.auth import get_current_user
from app.services.firebird_export_service import export_order_to_firebird, FirebirdExportError
from app.services.event_publisher import event_publisher
from app.schemas.order import (
    OrderBrief,
    OrderCreate,
    OrderRejectRequest,
    OrderResponse,
    OrderStatusUpdate,
    OrderUpdate,
    PaginatedOrdersResponse,
)

from datetime import date, timezone
from decimal import Decimal
from sqlalchemy import or_
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


async def _export_order_after_delivered(order_id: UUID) -> None:
    """Task best-effort para exportar pedido ao Firebird."""
    try:
        trade_id = await export_order_to_firebird(order_id)
        logger.info(f"Pedido {order_id} exportado para Firebird (TRADE.ID={trade_id})")
    except FirebirdExportError as e:
        logger.warning(f"Exportação Firebird não realizada para pedido {order_id}: {e}")
    except Exception as e:
        logger.exception(f"Erro inesperado exportando pedido {order_id} para Firebird: {e}")


def _get_customer_contact(order: Order) -> Tuple[Optional[str], Optional[str]]:
    """Extrai telefone e email do cliente do pedido."""
    customer_phone = order.customer.phone if order.customer else None
    customer_email = order.customer.email if order.customer else None
    return customer_phone, customer_email


async def _broadcast_to_operators_and_admins(message: dict, bairro: Optional[str] = None) -> None:
    """Envia mensagem via WebSocket para operadores e admins."""
    from app.api.websocket import UserRole, manager as ws_manager

    if bairro:
        await ws_manager.broadcast_to_neighborhood(message, bairro)
    else:
        await ws_manager.broadcast_to_role(message, UserRole.OPERATOR)

    await ws_manager.broadcast_to_role(message, UserRole.ADMIN)


async def _notify_order_status_change(order: Order, old_status: str, new_status: str) -> None:
    """Notifica cliente sobre mudança de status do pedido via WhatsApp."""
    try:
        # Mapear status para eventos
        event_map = {
            OrderStatus.PAID.value: "order.paid",
            OrderStatus.PREPARING.value: "order.preparing",
            OrderStatus.DISPATCHED.value: "order.dispatched",
            OrderStatus.DELIVERED.value: "order.delivered",
            OrderStatus.CANCELLED.value: "order.cancelled",
        }

        event_type = event_map.get(new_status)
        if not event_type:
            return

        customer_phone, customer_email = _get_customer_contact(order)

        await event_publisher.publish_order_event(
            event_type=event_type,
            order_id=str(order.id),
            order_number=order.order_number,
            customer_id=str(order.customer_id),
            customer_phone=customer_phone,
            customer_email=customer_email,
            status=new_status,
        )

    except Exception as e:
        logger.error(f"Erro ao notificar mudança de status: {e}", exc_info=True)


async def _notify_operators_order_update(order: Order, old_status: str, new_status: str) -> None:
    """Notifica operadores sobre atualização de pedido via WebSocket."""
    try:
        message = {
            "type": "order_update",
            "order_id": str(order.id),
            "order_number": order.order_number,
            "status": new_status,
            "old_status": old_status,
            "customer_name": order.customer.name if order.customer else None,
            "total_amount": float(order.total_amount),
            "bairro": order.delivery_bairro,
        }

        await _broadcast_to_operators_and_admins(message, order.delivery_bairro)

    except Exception as e:
        logger.error(f"Erro ao notificar operadores: {e}", exc_info=True)


async def _notify_new_order(order: Order) -> None:
    """Notifica operadores sobre novo pedido pendente."""
    try:
        customer_phone, customer_email = _get_customer_contact(order)

        # Publicar evento para notification-service
        await event_publisher.publish_order_event(
            event_type="order.created",
            order_id=str(order.id),
            order_number=order.order_number,
            customer_id=str(order.customer_id),
            customer_phone=customer_phone,
            customer_email=customer_email,
            status=order.status,
        )

        # Notificar operadores via WebSocket
        message = {
            "type": "new_order",
            "order": {
                "id": str(order.id),
                "order_number": order.order_number,
                "status": order.status,
                "customer_name": order.customer.name if order.customer else None,
                "total_amount": float(order.total_amount),
                "bairro": order.delivery_bairro,
                "created_at": order.created_at.isoformat() if order.created_at else None,
            },
        }

        await _broadcast_to_operators_and_admins(message, order.delivery_bairro)

    except Exception as e:
        logger.error(f"Erro ao notificar novo pedido: {e}", exc_info=True)


async def get_preco_produto(
    db: AsyncSession,
    product: Product,
    tipo_preco_id: Optional[UUID]
) -> Decimal:
    """
    Busca o preço de um produto para uma modalidade.
    Se não houver preço específico, usa preço padrão com desconto do tipo.
    """
    if not tipo_preco_id:
        return product.price

    # Buscar tipo de preço
    tipo_result = await db.execute(
        select(TipoPreco).where(TipoPreco.id == tipo_preco_id)
    )
    tipo = tipo_result.scalar_one_or_none()

    if not tipo:
        return product.price

    # Buscar preço específico vigente
    hoje = date.today()
    preco_result = await db.execute(
        select(ProdutoPreco).where(
            and_(
                ProdutoPreco.produto_id == product.id,
                ProdutoPreco.tipo_preco_id == tipo_preco_id,
                ProdutoPreco.vigencia_inicio <= hoje,
                or_(
                    ProdutoPreco.vigencia_fim.is_(None),
                    ProdutoPreco.vigencia_fim >= hoje
                )
            )
        ).order_by(ProdutoPreco.vigencia_inicio.desc())
    )
    preco_especifico = preco_result.scalar_one_or_none()

    if preco_especifico:
        return preco_especifico.preco

    # Aplicar desconto padrão do tipo
    desconto = Decimal(str(tipo.percentual_desconto)) / Decimal("100")
    preco_com_desconto = product.price * (Decimal("1") - desconto)

    return preco_com_desconto.quantize(Decimal("0.01"))


@router.get("", response_model=PaginatedOrdersResponse)
async def list_orders(
    status: Optional[str] = Query(None, description="Filtrar por status"),
    bairro: Optional[str] = Query(None, description="Filtrar por bairro"),
    customer_id: Optional[UUID] = Query(None, description="Filtrar por cliente"),
    date_from: Optional[datetime] = Query(None, description="Data inicial"),
    date_to: Optional[datetime] = Query(None, description="Data final"),
    page: int = Query(1, ge=1, description="Número da página"),
    page_size: int = Query(30, ge=1, le=100, description="Itens por página"),
    db: AsyncSession = Depends(get_db),
):
    """
    Lista pedidos com filtros e paginação.

    Retorna versão resumida para performance.
    Suporta paginação e metadados (total, has_next, has_prev).
    """
    # Query base
    base_query = select(Order).options(selectinload(Order.customer))

    # Aplicar filtros
    filters = []

    if status:
        filters.append(Order.status == status)

    if bairro:
        filters.append(Order.delivery_bairro.ilike(f"%{bairro}%"))

    if customer_id:
        filters.append(Order.customer_id == customer_id)

    if date_from:
        filters.append(Order.created_at >= date_from)

    if date_to:
        filters.append(Order.created_at <= date_to)

    if filters:
        base_query = base_query.where(and_(*filters))

    # Contar total (antes de paginação)
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Aplicar paginação
    offset = (page - 1) * page_size
    paginated_query = base_query.order_by(Order.created_at.desc()).limit(page_size).offset(offset)

    # Executar query
    result = await db.execute(paginated_query)
    orders = result.scalars().all()

    # Retornar resposta paginada
    return PaginatedOrdersResponse.create(
        items=[OrderBrief.from_order(o) for o in orders],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/today", response_model=List[OrderBrief])
async def list_today_orders(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Lista pedidos de hoje."""
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    query = (
        select(Order)
        .options(selectinload(Order.customer))
        .where(Order.created_at >= today_start)
        .order_by(Order.created_at.desc())
    )

    if status:
        query = query.where(Order.status == status)

    result = await db.execute(query)
    orders = result.scalars().all()

    return [OrderBrief.from_order(o) for o in orders]


@router.get("/pending", response_model=List[OrderBrief])
async def list_pending_orders(
    db: AsyncSession = Depends(get_db),
):
    """Lista pedidos pendentes de aprovação (apenas status PENDING)."""
    query = (
        select(Order)
        .options(
            selectinload(Order.customer),
            selectinload(Order.items),  # Carregar items também
        )
        .where(Order.status == OrderStatus.PENDING.value)
        .order_by(Order.created_at.asc())
    )

    result = await db.execute(query)
    orders = result.scalars().all()

    return [OrderBrief.from_order(o) for o in orders]


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Busca detalhes completos de um pedido."""
    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.customer),
            selectinload(Order.items),
            selectinload(Order.payments),
            selectinload(Order.delivery),
        )
        .where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    return order


@router.get("/number/{order_number}", response_model=OrderResponse)
async def get_order_by_number(
    order_number: int,
    db: AsyncSession = Depends(get_db),
):
    """Busca pedido pelo número."""
    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.customer),
            selectinload(Order.items),
        )
        .where(Order.order_number == order_number)
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    return order


@router.post("", response_model=OrderResponse, status_code=201)
async def create_order(
    data: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Cria um novo pedido.

    Normalmente criado pelo flow engine do bot.
    
    DESATIVADO: Criação manual de pedidos está desabilitada por padrão.
    Para reativar, defina MANUAL_ORDER_CREATION_ENABLED=true no .env
    
    Usa transação atômica para garantir consistência:
    - Se qualquer operação falhar, tudo é revertido (via get_db rollback)
    - Pedido e itens são criados juntos
    """
    # Verificar se criação manual está habilitada
    if not settings.manual_order_creation_enabled:
        raise HTTPException(
            status_code=403,
            detail="Criação manual de pedidos está desabilitada. "
                   "Pedidos devem ser criados apenas através do bot/flow engine. "
                   "Para reativar, defina MANUAL_ORDER_CREATION_ENABLED=true no .env"
        )
    
    try:
        # Verificar se cliente existe
        customer = await db.execute(
            select(Customer).where(Customer.id == data.customer_id)
        )
        customer = customer.scalar_one_or_none()

        if not customer:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")

        # Processar endereço primeiro (para evitar problemas de serialização JSONB)
        delivery_addr_dict = None
        delivery_bairro = data.delivery_bairro
        
        if data.delivery_address:
            # Converter para dict Python puro, não JSON string
            delivery_addr_dict = dict(data.delivery_address.model_dump())
            if not delivery_bairro and data.delivery_address.bairro:
                delivery_bairro = data.delivery_address.bairro

        # Validar bairro (se informado)
        if delivery_bairro and settings.supported_bairros:
            # Normalizar para comparação case-insensitive
            bairro_lower = delivery_bairro.lower().strip()
            bairros_lower = [b.lower() for b in settings.supported_bairros]
            if bairro_lower not in bairros_lower:
                raise HTTPException(
                    status_code=400,
                    detail=f"Bairro '{delivery_bairro}' não atendido. "
                           f"Bairros disponíveis: {', '.join(settings.supported_bairros)}"
                )

        # Criar pedido
        order = Order(
            customer_id=data.customer_id,
            status=OrderStatus.PENDING.value,
            payment_method=data.payment_method,
            tipo_operacao=getattr(data, 'tipo_operacao', 'troca'),
            delivery_address=delivery_addr_dict,
            delivery_bairro=delivery_bairro,
            notes=data.notes,
            total_amount=0,
        )

        db.add(order)
        await db.flush()  # Obter ID

        # Adicionar itens
        total = 0
        for item_data in data.items:
            # Buscar produto
            product = await db.execute(
                select(Product).where(Product.code == item_data.product_code.upper())
            )
            product = product.scalar_one_or_none()

            if not product:
                raise HTTPException(
                    status_code=400,
                    detail=f"Produto {item_data.product_code} não encontrado"
                )

            if not product.is_active:
                raise HTTPException(
                    status_code=400,
                    detail=f"Produto {item_data.product_code} não está disponível"
                )

            # Buscar preço correto baseado no tipo de preço do cliente
            unit_price = await get_preco_produto(db, product, customer.tipo_preco_id)
            subtotal = unit_price * item_data.quantity

            # Criar item (DENTRO do loop)
            item = OrderItem(
                order_id=order.id,
                product_code=product.code,
                product_name=product.name,
                quantity=item_data.quantity,
                unit_price=unit_price,
                subtotal=subtotal,
            )
            db.add(item)
            total += subtotal

        # Atualizar total do pedido
        order.total_amount = total
        
        # Flush para persistir antes do refresh
        await db.flush()
        
        # Recarregar pedido com todas as relações e campos gerados pelo DB
        await db.refresh(order, attribute_names=['order_number'])
        
        result = await db.execute(
            select(Order)
            .options(
                selectinload(Order.customer),
                selectinload(Order.items),
            )
            .where(Order.id == order.id)
        )
        order = result.scalar_one()

        # Notificar operadores sobre novo pedido
        asyncio.create_task(_notify_new_order(order))

        return order
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar pedido: {e}")
        raise HTTPException(
            status_code=500,
            detail="Erro ao criar pedido. Tente novamente."
        )


@router.patch("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: UUID,
    data: OrderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Atualiza dados de um pedido."""
    result = await db.execute(
        select(Order).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    # Atualizar campos
    update_data = data.model_dump(exclude_unset=True)

    if "delivery_address" in update_data and update_data["delivery_address"]:
        update_data["delivery_address"] = update_data["delivery_address"].model_dump()

    for field, value in update_data.items():
        setattr(order, field, value)

    await db.commit()
    await db.refresh(order)

    return order


@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: UUID,
    data: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Atualiza o status de um pedido.

    Atualiza automaticamente os timestamps relacionados.
    """
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.customer))
        .where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    old_status = order.status

    # Validar transição de status
    valid_transitions = {
        OrderStatus.PENDING.value: [OrderStatus.PAID.value, OrderStatus.CANCELLED.value],
        OrderStatus.PAID.value: [OrderStatus.PREPARING.value, OrderStatus.DISPATCHED.value, OrderStatus.CANCELLED.value],
        OrderStatus.PREPARING.value: [OrderStatus.DISPATCHED.value, OrderStatus.CANCELLED.value],
        OrderStatus.DISPATCHED.value: [OrderStatus.DELIVERED.value, OrderStatus.CANCELLED.value],
        OrderStatus.DELIVERED.value: [],  # Final
        OrderStatus.CANCELLED.value: [],  # Final
    }

    if data.status not in valid_transitions.get(old_status, []):
        raise HTTPException(
            status_code=400,
            detail=f"Transição de {old_status} para {data.status} não permitida"
        )

    # Atualizar status e timestamps
    # Se mudando para PAID, registrar quem aprovou
    if data.status == OrderStatus.PAID.value and old_status == OrderStatus.PENDING.value:
        order.update_status(data.status, approved_by=current_user.id)
    else:
        order.update_status(data.status)

    if data.status == OrderStatus.CANCELLED.value and data.reason:
        order.cancellation_reason = data.reason

    await db.commit()
    await db.refresh(order)

    # Notificar cliente via WhatsApp sobre mudança de status
    asyncio.create_task(_notify_order_status_change(order, old_status, data.status))

    # Notificar operadores via WebSocket sobre mudança de status
    asyncio.create_task(_notify_operators_order_update(order, old_status, data.status))

    # Exportar para Firebird quando entregue (best-effort, assíncrono)
    if (
        data.status == OrderStatus.DELIVERED.value
        and settings.firebird_export_on_delivered
        and not getattr(order, "firebird_trade_id", None)
        and settings.firebird_enabled
    ):
        asyncio.create_task(_export_order_after_delivered(order.id))

    return order


@router.post("/{order_id}/export-firebird")
async def export_order_firebird(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Exporta manualmente um pedido para o Firebird (TRADE/TRADEITEM).
    """
    result = await db.execute(select(Order.id).where(Order.id == order_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    try:
        trade_id = await export_order_to_firebird(order_id)
        return {"status": "exported", "order_id": str(order_id), "firebird_trade_id": trade_id}
    except FirebirdExportError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{order_id}")
async def cancel_order(
    order_id: UUID,
    reason: Optional[str] = Query(None, description="Motivo do cancelamento"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancela um pedido."""
    result = await db.execute(
        select(Order).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    if not order.is_cancellable:
        raise HTTPException(
            status_code=400,
            detail=f"Pedido com status {order.status} não pode ser cancelado"
        )

    old_status = order.status
    order.status = OrderStatus.CANCELLED.value
    order.cancelled_at = datetime.utcnow()
    order.cancellation_reason = reason

    await db.commit()

    # Asaas foi descontinuado - logar para estorno manual se necessário
    if old_status != OrderStatus.PENDING.value:
        logger.warning(f"Pedido {order_id} cancelado (status anterior: {old_status}). Verificar estorno manual.")

    return {"message": "Pedido cancelado", "id": str(order_id)}


# ==================== Estatísticas ====================

@router.get("/stats/summary")
async def get_orders_summary(
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Retorna resumo de pedidos."""
    # Default: últimos 7 dias
    if not date_from:
        date_from = datetime.now() - timedelta(days=7)
    if not date_to:
        date_to = datetime.now()

    # Total de pedidos
    total_query = (
        select(func.count(Order.id))
        .where(Order.created_at.between(date_from, date_to))
    )
    total_result = await db.execute(total_query)
    total_orders = total_result.scalar() or 0

    # Por status
    status_query = (
        select(Order.status, func.count(Order.id))
        .where(Order.created_at.between(date_from, date_to))
        .group_by(Order.status)
    )
    status_result = await db.execute(status_query)
    by_status = {str(row[0]): row[1] for row in status_result.fetchall()}

    # Faturamento (pedidos entregues)
    revenue_query = (
        select(func.sum(Order.total_amount))
        .where(
            Order.created_at.between(date_from, date_to),
            Order.status == OrderStatus.DELIVERED.value,
        )
    )
    revenue_result = await db.execute(revenue_query)
    total_revenue = float(revenue_result.scalar() or 0)

    return {
        "period": {
            "from": date_from.isoformat(),
            "to": date_to.isoformat(),
        },
        "total_orders": total_orders,
        "by_status": by_status,
        "total_revenue": total_revenue,
        "delivered_count": by_status.get("delivered", 0),
        "cancelled_count": by_status.get("cancelled", 0),
    }


# ==================== Aprovação/Rejeição de Pedidos ====================

@router.post("/{order_id}/approve", response_model=OrderResponse)
async def approve_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Aprovar pedido pendente.
    Muda status de 'pending' para 'paid' (pago e pronto para preparação).
    """
    # Buscar pedido
    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.customer),
            selectinload(Order.items),
        )
        .where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    
    # Verificar se está pendente
    if order.status != OrderStatus.PENDING.value:
        raise HTTPException(
            status_code=400,
            detail=f"Pedido não pode ser aprovado. Status atual: {order.status}"
        )
    
    # Atualizar status para 'paid' (aprovado e pago)
    order.status = OrderStatus.PAID.value
    order.paid_at = datetime.now()
    order.approved_by = current_user.id
    
    # Calcular tempo de aprovação
    if order.created_at:
        approval_time = (datetime.now(timezone.utc) - order.created_at).total_seconds()
    else:
        approval_time = None
    
    await db.commit()
    await db.refresh(order)
    
    # Registrar aprovação no EventLog para tracking
    try:
        from app.services.operator_tracking_service import operator_tracking_service
        # Criar nova sessão para o tracking (não usar a mesma sessão)
        from app.database import AsyncSessionLocal
        async def _log_approval():
            async with AsyncSessionLocal() as tracking_db:
                await operator_tracking_service.log_order_approval(
                    tracking_db,
                    operator_id=current_user.id,
                    order_id=order.id,
                    approval_time_seconds=approval_time,
                )
        asyncio.create_task(_log_approval())
    except Exception as e:
        logger.warning(f"Erro ao registrar aprovação no tracking: {e}")
    
    return order


@router.post("/{order_id}/reject")
async def reject_order(
    order_id: UUID,
    data: OrderRejectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Rejeitar pedido pendente.
    Muda status para 'cancelled' e registra motivo.
    """
    # Buscar pedido
    result = await db.execute(
        select(Order).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    # Verificar se está pendente
    if order.status != OrderStatus.PENDING.value:
        raise HTTPException(
            status_code=400,
            detail=f"Pedido não pode ser rejeitado. Status atual: {order.status}"
        )

    # Atualizar status para 'cancelled'
    order.status = OrderStatus.CANCELLED.value
    order.cancelled_at = datetime.now()
    order.cancellation_reason = data.reason

    await db.commit()

    return {
        "success": True,
        "message": "Pedido rejeitado com sucesso",
        "order_id": str(order_id),
        "reason": data.reason
    }
