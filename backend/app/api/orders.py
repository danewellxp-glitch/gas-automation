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
from app.models.delivery import Delivery, DeliveryStatus
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.tipo_preco import TipoPreco, ProdutoPreco
from app.models.auth_models import User
from app.auth import get_current_user
from app.services.event_publisher import event_publisher
from app.services.firebird_export_service import export_order_to_firebird, FirebirdExportError
from app.services.order_status_side_effects import (
    notify_order_status_change,
    notify_operators_order_update,
)
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


async def _notify_drivers_new_delivery(order: Order, delivery: Delivery) -> None:
    """Notifica todos os drivers via WebSocket e FCM push sobre nova entrega disponível."""
    delivery_data = {
        "delivery_id": str(delivery.id),
        "order_id": str(order.id),
        "order_number": order.order_number,
        "bairro": order.delivery_bairro,
        "total_amount": float(order.total_amount),
        "customer_name": order.customer.name if order.customer else None,
        "estimated_minutes": delivery.estimated_minutes,
    }

    # WebSocket para drivers conectados
    try:
        from app.api.websocket import emit_new_delivery_available
        await emit_new_delivery_available(delivery_data)
    except Exception as e:
        logger.error(f"Erro ao notificar drivers via WebSocket: {e}", exc_info=True)

    # FCM push para drivers disponíveis (com push_token cadastrado)
    try:
        from app.integrations.fcm_client import notify_driver_new_delivery
        from app.models.driver import Driver, DriverStatus
        from app.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Driver).where(
                    and_(
                        Driver.status == DriverStatus.AVAILABLE.value,
                        Driver.push_token.isnot(None),
                        Driver.is_active == True,
                    )
                )
            )
            available_drivers = result.scalars().all()

        # Filtrar por bairro se a entrega tiver bairro definido
        bairro = order.delivery_bairro
        if bairro:
            targets = [
                d for d in available_drivers
                if not d.bairro or d.bairro.lower().strip() == bairro.lower().strip()
            ]
        else:
            targets = list(available_drivers)

        for driver in targets:
            try:
                await notify_driver_new_delivery(
                    push_token=driver.push_token,
                    delivery_id=str(delivery.id),
                    bairro=bairro or "Sem bairro",
                    order_number=str(order.order_number),
                )
            except Exception as e:
                logger.warning(f"Erro ao enviar push para driver {driver.id}: {e}")
    except ImportError:
        logger.warning("fcm_client não disponível — push FCM desabilitado")
    except Exception as e:
        logger.error(f"Erro ao enviar FCM push para drivers: {e}", exc_info=True)


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
    base_query = select(Order).options(
        selectinload(Order.customer),
        selectinload(Order.items),
    )

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

    # Contar total (query separada para evitar problemas com selectinload)
    count_filters = filters if filters else []
    count_query = select(func.count(Order.id))
    if count_filters:
        count_query = count_query.where(and_(*count_filters))
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Aplicar paginação
    offset = (page - 1) * page_size
    paginated_query = base_query.order_by(Order.created_at.desc()).limit(page_size).offset(offset)

    # Executar query
    result = await db.execute(paginated_query)
    orders = result.scalars().all()

    # Resolver nomes dos aprovadores em batch
    approver_ids = {o.approved_by for o in orders if o.approved_by}
    approver_map: dict = {}
    if approver_ids:
        approver_result = await db.execute(
            select(User.id, User.username).where(User.id.in_(approver_ids))
        )
        approver_map = {row[0]: row[1] for row in approver_result}

    # Retornar resposta paginada
    return PaginatedOrdersResponse.create(
        items=[OrderBrief.from_order(o, approved_by_name=approver_map.get(o.approved_by)) for o in orders],
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
    from app.models.auth_models import BRAZIL_TZ
    today_start = datetime.now(BRAZIL_TZ).replace(hour=0, minute=0, second=0, microsecond=0)

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


@router.get("/agendados")
async def listar_pedidos_agendados_early(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista pedidos agendados para entrega futura."""
    if current_user.role not in ("admin", "owner", "operator"):
        raise HTTPException(status_code=403, detail="Acesso negado")

    from datetime import timezone as _tz

    filters = [Order.is_scheduled == True]
    if date_from:
        filters.append(Order.scheduled_for >= datetime.combine(date_from, datetime.min.time()).replace(tzinfo=_tz.utc))
    if date_to:
        filters.append(Order.scheduled_for <= datetime.combine(date_to, datetime.max.time()).replace(tzinfo=_tz.utc))

    result = await db.execute(
        select(Order)
        .where(and_(*filters))
        .order_by(Order.scheduled_for)
    )
    orders = result.scalars().all()

    return [
        {
            "id": str(o.id),
            "order_number": o.order_number,
            "status": o.status,
            "scheduled_for": o.scheduled_for.isoformat() if o.scheduled_for else None,
            "customer_id": str(o.customer_id),
            "total_amount": float(o.total_amount),
            "delivery_bairro": o.delivery_bairro,
            "notes": o.notes,
        }
        for o in orders
    ]


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
    # Verificar se criação manual está habilitada (admin/owner podem sempre criar)
    if not settings.manual_order_creation_enabled and current_user.role not in ("admin", "owner"):
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

        # Verificar limite de crédito para pedidos fiado
        if getattr(data, "payment_method", None) == "fiado":
            try:
                from decimal import Decimal as _D
                from app.services.financeiro.customer_financial_service import check_credit_limit
                _order_total = sum(
                    getattr(item, "unit_price", 0) * getattr(item, "quantity", 1)
                    for item in (data.items or [])
                ) or _D("0")
                _allowed, _balance = await check_credit_limit(
                    db, data.customer_id, _D(str(_order_total))
                )
                if not _allowed:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Limite de crédito excedido. Saldo atual: R$ {float(_balance):.2f}"
                    )
            except HTTPException:
                raise
            except Exception as _e:
                import logging as _logging
                _logging.getLogger(__name__).warning(f"Erro ao verificar crédito: {_e}")

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

        # Registrar débito no cliente se pagamento for fiado
        if order.payment_method == "fiado":
            try:
                from app.services.financeiro.financial_hooks import on_order_created_fiado
                await on_order_created_fiado(db, order)
                await db.flush()
            except Exception as _fe:
                logger.warning(f"Erro ao registrar fiado no pedido {order.id}: {_fe}")

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

    # Notificar cliente via event publisher
    asyncio.create_task(notify_order_status_change(order, old_status, data.status))

    # Notificar operadores via WebSocket sobre mudança de status
    asyncio.create_task(notify_operators_order_update(order, old_status, data.status))

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
    order.cancelled_at = datetime.now(timezone.utc)
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
        date_from = datetime.now(timezone.utc) - timedelta(days=7)
    if not date_to:
        date_to = datetime.now(timezone.utc)

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
    order.paid_at = datetime.now(timezone.utc)
    order.approved_by = current_user.id

    # Calcular tempo de aprovação
    if order.created_at:
        created = order.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        approval_time = (datetime.now(timezone.utc) - created).total_seconds()
    else:
        approval_time = None
    
    await db.commit()
    await db.refresh(order)

    # Criar Delivery pendente para que os drivers possam ver e aceitar
    existing_delivery = await db.execute(
        select(Delivery).where(Delivery.order_id == order.id)
    )
    if not existing_delivery.scalar_one_or_none():
        delivery = Delivery(
            order_id=order.id,
            bairro=order.delivery_bairro,
            status=DeliveryStatus.PENDING.value,
            estimated_minutes=40,
        )
        db.add(delivery)
        await db.commit()
        await db.refresh(delivery)
        # Notificar drivers via WebSocket
        asyncio.create_task(_notify_drivers_new_delivery(order, delivery))
        logger.info(f"Delivery {delivery.id} criada para pedido {order.order_number}")

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
    order.cancelled_at = datetime.now(timezone.utc)
    order.cancellation_reason = data.reason

    await db.commit()

    return {
        "success": True,
        "message": "Pedido rejeitado com sucesso",
        "order_id": str(order_id),
        "reason": data.reason
    }

# ─────────────────────────────────────────────────────────
# Task 8: Troca de Motorista (sem cancelar o pedido)
# ─────────────────────────────────────────────────────────

from pydantic import BaseModel as _PydBase


class _ReassignBody(_PydBase):
    new_driver_id: UUID
    motivo: Optional[str] = None


@router.patch("/{order_id}/reassign-driver")
async def reassign_driver(
    order_id: UUID,
    body: _ReassignBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Reatribui a entrega de um pedido a outro motorista sem cancelar o pedido.
    Registra log da troca.
    """
    if current_user.role not in ("admin", "owner", "operator"):
        raise HTTPException(status_code=403, detail="Acesso negado")

    # Busca pedido
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    if order.status in (OrderStatus.DELIVERED.value, OrderStatus.CANCELLED.value):
        raise HTTPException(status_code=409, detail=f"Não é possível reatribuir pedido com status {order.status}")

    # Busca Delivery ativa
    delivery_result = await db.execute(
        select(Delivery).where(
            and_(
                Delivery.order_id == order_id,
                Delivery.status.not_in([DeliveryStatus.DELIVERED.value, DeliveryStatus.FAILED.value]),
            )
        )
    )
    delivery = delivery_result.scalar_one_or_none()
    if not delivery:
        raise HTTPException(status_code=404, detail="Nenhuma entrega ativa encontrada para este pedido")

    # Valida novo motorista
    from app.models.driver import Driver
    new_driver = await db.get(Driver, body.new_driver_id)
    if not new_driver or not new_driver.is_active:
        raise HTTPException(status_code=404, detail="Motorista não encontrado ou inativo")

    old_driver_id = delivery.driver_id

    # Atualiza delivery
    delivery.driver_id = body.new_driver_id

    # Registra no event_log
    from app.models.event_log import EventLog, EventTypes, ActorTypes
    log = EventLog(
        event_type=EventTypes.ORDER_UPDATED.value if hasattr(EventTypes, 'ORDER_UPDATED') else "order.driver_reassigned",
        actor_type=ActorTypes.OPERATOR.value if hasattr(ActorTypes, 'OPERATOR') else "operator",
        actor_id=str(current_user.id),
        entity_type="order",
        entity_id=str(order_id),
        metadata={
            "old_driver_id": str(old_driver_id),
            "new_driver_id": str(body.new_driver_id),
            "motivo": body.motivo or "",
        },
    )
    db.add(log)
    await db.commit()

    # Notifica WebSocket
    try:
        from app.api.websocket import manager as ws_manager
        await ws_manager.broadcast({
            "type": "driver_reassigned",
            "order_id": str(order_id),
            "new_driver_id": str(body.new_driver_id),
            "new_driver_name": new_driver.name,
        })
    except Exception:
        pass

    return {
        "success": True,
        "order_id": str(order_id),
        "delivery_id": str(delivery.id),
        "old_driver_id": str(old_driver_id),
        "new_driver_id": str(body.new_driver_id),
        "new_driver_name": new_driver.name,
    }


# ─────────────────────────────────────────────────────────
# Task 9: Agendamento — ver rota GET /agendados acima (antes de /{order_id})
# ─────────────────────────────────────────────────────────


class _ScheduleBody(_PydBase):
    scheduled_for: datetime


@router.patch("/{order_id}/agendar")
async def agendar_pedido(
    order_id: UUID,
    body: _ScheduleBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Agenda um pedido para entrega em data/hora específica."""
    if current_user.role not in ("admin", "owner", "operator"):
        raise HTTPException(status_code=403, detail="Acesso negado")

    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    order.is_scheduled = True
    order.scheduled_for = body.scheduled_for
    await db.commit()

    return {
        "order_id": str(order_id),
        "scheduled_for": order.scheduled_for.isoformat(),
        "is_scheduled": True,
    }
