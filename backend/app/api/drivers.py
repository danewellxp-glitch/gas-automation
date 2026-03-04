"""
API endpoints para Driver (Entregador).
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)

from app.auth import get_current_user

# Import opcional: fcm_client depende de firebase-admin; se falhar, push fica desabilitado
try:
    from app.integrations.fcm_client import notify_driver_new_delivery
except ImportError as e:
    logger.warning("fcm_client não disponível (firebase-admin): push desabilitado. %s", e)
    notify_driver_new_delivery = None

from app.integrations.waha import waha_client
from app.database import get_db
from app.models.auth_models import User
from app.models.customer import Customer
from app.models.delivery import Delivery, DeliveryStatus
from app.models.driver import Driver, DriverStatus
from app.models.order import Order, OrderStatus
from app.schemas.driver import (
    DeliveryProblemReport,
    DeliveryStatusUpdate,
    DriverBrief,
    DriverCreate,
    DriverLocationUpdate,
    DriverPushTokenUpdate,
    DriverResponse,
    DriverStats,
    DriverStatusUpdate,
    DriverUpdate,
    DriverTimeSummary,
    DailyRankingItem,
    DriversMetricsDashboard,
)
from app.services.driver_time_tracking_service import DriverTimeTrackingService
from app.services.geocoding_service import geocode_address, haversine_distance_km
from app.services.order_status_side_effects import on_order_delivered

router = APIRouter()

# Raio em km para considerar "chegou" (~1 minuto de carro)
ARRIVED_PROXIMITY_KM = 0.5


# ==================== ENDPOINTS DO PRÓPRIO DRIVER ====================


@router.get("/me", response_model=DriverResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Retorna perfil do driver logado.
    
    Requires: role = "driver"
    """
    # Verificar se é driver
    if current_user.role != "driver":
        raise HTTPException(status_code=403, detail="Acesso restrito a entregadores")
    
    # Buscar driver pelo phone (assumindo que username = phone)
    result = await session.execute(
        select(Driver).where(Driver.phone == current_user.username)
    )
    driver = result.scalar_one_or_none()
    
    if not driver:
        raise HTTPException(status_code=404, detail="Perfil de entregador não encontrado")
    
    return driver


@router.put("/me/status", response_model=DriverResponse)
async def update_my_status(
    status_update: DriverStatusUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Atualiza status do driver logado (online/offline/busy/break).
    
    Requires: role = "driver"
    """
    if current_user.role != "driver":
        raise HTTPException(status_code=403, detail="Acesso restrito a entregadores")
    
    # Buscar driver
    result = await session.execute(
        select(Driver).where(Driver.phone == current_user.username)
    )
    driver = result.scalar_one_or_none()
    
    if not driver:
        raise HTTPException(status_code=404, detail="Perfil de entregador não encontrado")
    
    # Atualizar status
    driver.status = status_update.status
    if status_update.status in [DriverStatus.AVAILABLE.value, DriverStatus.BUSY.value]:
        driver.last_online = datetime.now(timezone.utc)
    
    session.add(driver)
    await session.commit()
    await session.refresh(driver)
    
    # ✅ TRACKING DE TEMPO: Registrar mudança de status
    try:
        await DriverTimeTrackingService.start_time_log(
            session,
            driver.id,
            status_update.status
        )
    except Exception as e:
        # Não falhar se tracking der erro
        logger.error(f"Erro ao registrar time log: {e}")
    
    return driver


async def _check_proximity_and_auto_arrived(
    driver_id: UUID,
    lat: float,
    lng: float,
) -> None:
    """
    Background: verifica se driver está próximo do destino e auto-atualiza para 'arrived'
    + envia WhatsApp "Seu gás está a 1 minuto da sua casa!"
    """
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        try:
            # Buscar entrega in_transit do driver
            result = await session.execute(
                select(Delivery)
                .options(
                    selectinload(Delivery.order).selectinload(Order.customer),
                )
                .where(
                    and_(
                        Delivery.driver_id == driver_id,
                        Delivery.status == DeliveryStatus.IN_TRANSIT.value,
                    )
                )
                .order_by(Delivery.in_transit_at.desc())
                .limit(1)
            )
            delivery = result.scalar_one_or_none()
            if not delivery or not delivery.order:
                return

            # Garantir coordenadas do destino (geocoding se necessário)
            dest_lat = delivery.delivery_destination_lat
            dest_lng = delivery.delivery_destination_lng
            if dest_lat is None or dest_lng is None:
                coords = await geocode_address(
                    delivery.order.delivery_address,
                    delivery.bairro,
                )
                if not coords:
                    return
                dest_lat, dest_lng = coords
                delivery.delivery_destination_lat = dest_lat
                delivery.delivery_destination_lng = dest_lng
                session.add(delivery)
                await session.commit()
                await session.refresh(delivery)

            # Calcular distância
            dist_km = haversine_distance_km(lat, lng, dest_lat, dest_lng)
            if dist_km > ARRIVED_PROXIMITY_KM:
                return

            # Está próximo! Atualizar para arrived e enviar WhatsApp
            if delivery.arrived_whatsapp_sent:
                return  # Já enviou, não repetir

            delivery.update_status(DeliveryStatus.ARRIVED.value)
            delivery.arrived_whatsapp_sent = True
            session.add(delivery)
            await session.commit()

            # Enviar WhatsApp ao cliente
            customer_phone = None
            if delivery.order and delivery.order.customer:
                customer_phone = delivery.order.customer.phone

            if customer_phone:
                order_num = delivery.order.order_number if delivery.order else "?"
                msg = (
                    f"📍 Seu gás está a 1 minuto da sua casa!\n\n"
                    f"Pedido #{order_num} – o entregador está chegando. 🔥"
                )
                await waha_client.send_text(phone=customer_phone, text=msg)
                logger.info(f"Auto-arrived + WhatsApp enviado para entrega {delivery.id}")
        except Exception as e:
            logger.error(f"Erro em _check_proximity_and_auto_arrived: {e}")


@router.put("/me/location", response_model=DriverResponse)
async def update_my_location(
    location: DriverLocationUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Atualiza localização GPS do driver logado.
    Se tiver entrega in_transit e estiver próximo (~500m), auto-atualiza para 'arrived'
    e envia WhatsApp ao cliente: "Seu gás está a 1 minuto da sua casa!"
    
    Requires: role = "driver"
    """
    if current_user.role != "driver":
        raise HTTPException(status_code=403, detail="Acesso restrito a entregadores")
    
    # Buscar driver
    result = await session.execute(
        select(Driver).where(Driver.phone == current_user.username)
    )
    driver = result.scalar_one_or_none()
    
    if not driver:
        raise HTTPException(status_code=404, detail="Perfil de entregador não encontrado")
    
    # Atualizar localização
    driver.current_location = {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    session.add(driver)
    await session.commit()
    await session.refresh(driver)

    # Background: verificar proximidade e auto-arrived + WhatsApp
    background_tasks.add_task(
        _check_proximity_and_auto_arrived,
        driver.id,
        location.latitude,
        location.longitude,
    )

    return driver


@router.put("/me/push-token")
async def update_my_push_token(
    token_update: DriverPushTokenUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Registra token FCM para push notifications.

    Requires: role = "driver"
    """
    if current_user.role != "driver":
        raise HTTPException(status_code=403, detail="Acesso restrito a entregadores")

    result = await session.execute(
        select(Driver).where(Driver.phone == current_user.username)
    )
    driver = result.scalar_one_or_none()

    if not driver:
        raise HTTPException(status_code=404, detail="Perfil de entregador não encontrado")

    driver.push_token = token_update.push_token
    session.add(driver)
    await session.commit()

    return {"message": "Token registrado com sucesso"}


@router.get("/me/deliveries", response_model=List[dict])
async def get_my_deliveries(
    status: str = Query(None, description="Filtrar por status: pending, active, completed"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Retorna entregas do driver logado.
    
    - pending: Entregas disponíveis para aceitar (status=pending no bairro do driver)
    - active: Entregas em andamento (assigned, picked_up, in_transit, arrived)
    - completed: Entregas finalizadas (delivered, failed, returned)
    - None: Todas as entregas do driver
    
    Requires: role = "driver"
    """
    if current_user.role != "driver":
        raise HTTPException(status_code=403, detail="Acesso restrito a entregadores")
    
    # Buscar driver
    result = await session.execute(
        select(Driver).where(Driver.phone == current_user.username)
    )
    driver = result.scalar_one_or_none()
    
    if not driver:
        raise HTTPException(status_code=404, detail="Perfil de entregador não encontrado")
    
    # Construir query baseado no status
    if status == "pending":
        # Entregas disponíveis (sem driver alocado ainda)
        conditions = [Delivery.status == DeliveryStatus.PENDING.value]
        if driver.bairro:
            conditions.append(func.lower(Delivery.bairro) == driver.bairro.lower().strip())
        query = select(Delivery).where(
            and_(*conditions)
        ).order_by(Delivery.created_at.desc())
    
    elif status == "active":
        # Entregas ativas do driver
        query = select(Delivery).where(
            and_(
                Delivery.driver_id == driver.id,
                Delivery.status.in_([
                    DeliveryStatus.ASSIGNED.value,
                    DeliveryStatus.PICKED_UP.value,
                    DeliveryStatus.IN_TRANSIT.value,
                    DeliveryStatus.ARRIVED.value,
                ])
            )
        ).order_by(Delivery.created_at.desc())
    
    elif status == "completed":
        # Entregas finalizadas do driver
        query = select(Delivery).where(
            and_(
                Delivery.driver_id == driver.id,
                Delivery.status.in_([
                    DeliveryStatus.DELIVERED.value,
                    DeliveryStatus.FAILED.value,
                    DeliveryStatus.RETURNED.value,
                ])
            )
        ).order_by(Delivery.delivered_at.desc())
    
    else:
        # Todas as entregas do driver
        query = select(Delivery).where(
            Delivery.driver_id == driver.id
        ).order_by(Delivery.created_at.desc())
    
    result = await session.execute(query)
    deliveries = result.scalars().all()
    
    # Enriquecer com dados do pedido
    deliveries_data = []
    for delivery in deliveries:
        # Buscar pedido relacionado com customer
        order_result = await session.execute(
            select(Order)
            .options(selectinload(Order.customer))
            .where(Order.id == delivery.order_id)
        )
        order = order_result.scalar_one_or_none()
        
        if order:
            # Formatar endereço como string para compatibilidade
            delivery_address_str = None
            if order.delivery_address:
                addr = order.delivery_address
                parts = []
                if addr.get('street'):
                    parts.append(addr.get('street'))
                if addr.get('number'):
                    parts.append(addr.get('number'))
                if addr.get('complement'):
                    parts.append(addr.get('complement'))
                if parts:
                    delivery_address_str = ', '.join(parts)
            
            deliveries_data.append({
                "id": str(delivery.id),
                "order_id": str(order.id),
                "order_number": order.order_number,
                "status": delivery.status,
                "bairro": delivery.bairro,
                "delivery_address": order.delivery_address,
                "delivery_address_str": delivery_address_str,
                "estimated_minutes": delivery.estimated_minutes,
                "assigned_at": delivery.assigned_at.isoformat() if delivery.assigned_at else None,
                "picked_up_at": delivery.picked_up_at.isoformat() if delivery.picked_up_at else None,
                "in_transit_at": delivery.in_transit_at.isoformat() if delivery.in_transit_at else None,
                "arrived_at": delivery.arrived_at.isoformat() if delivery.arrived_at else None,
                "delivered_at": delivery.delivered_at.isoformat() if delivery.delivered_at else None,
                "notes": delivery.notes,
                "order_total": float(order.total_amount),
                "customer_name": order.customer.name if order.customer else None,
                "customer_phone": order.customer.phone if order.customer else None,
                "order_items": [
                    {
                        "product_code": item.product_code,
                        "product_name": item.product_name,
                        "quantity": item.quantity,
                    }
                    for item in order.items
                ],
            })
    
    return deliveries_data


@router.get("/me/stats", response_model=DriverStats)
async def get_my_stats(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Retorna estatísticas do driver logado.
    
    Requires: role = "driver"
    """
    if current_user.role != "driver":
        raise HTTPException(status_code=403, detail="Acesso restrito a entregadores")
    
    # Buscar driver
    result = await session.execute(
        select(Driver).where(Driver.phone == current_user.username)
    )
    driver = result.scalar_one_or_none()
    
    if not driver:
        raise HTTPException(status_code=404, detail="Perfil de entregador não encontrado")
    
    # Calcular estatísticas
    from app.models.auth_models import BRAZIL_TZ
    now = datetime.now(BRAZIL_TZ)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)
    
    # Entregas hoje
    today_result = await session.execute(
        select(func.count(Delivery.id)).where(
            and_(
                Delivery.driver_id == driver.id,
                Delivery.delivered_at >= today_start,
                Delivery.status == DeliveryStatus.DELIVERED.value
            )
        )
    )
    today_deliveries = today_result.scalar() or 0
    
    # Entregas esta semana
    week_result = await session.execute(
        select(func.count(Delivery.id)).where(
            and_(
                Delivery.driver_id == driver.id,
                Delivery.delivered_at >= week_start,
                Delivery.status == DeliveryStatus.DELIVERED.value
            )
        )
    )
    week_deliveries = week_result.scalar() or 0
    
    # Entregas este mês
    month_result = await session.execute(
        select(func.count(Delivery.id)).where(
            and_(
                Delivery.driver_id == driver.id,
                Delivery.delivered_at >= month_start,
                Delivery.status == DeliveryStatus.DELIVERED.value
            )
        )
    )
    month_deliveries = month_result.scalar() or 0
    
    # Tempo médio de entrega
    avg_time_result = await session.execute(
        select(func.avg(Delivery.actual_delivery_minutes)).where(
            and_(
                Delivery.driver_id == driver.id,
                Delivery.status == DeliveryStatus.DELIVERED.value,
                Delivery.actual_delivery_minutes.isnot(None)
            )
        )
    )
    avg_time = avg_time_result.scalar()
    
    # Taxa de sucesso
    total_result = await session.execute(
        select(func.count(Delivery.id)).where(
            Delivery.driver_id == driver.id
        )
    )
    total = total_result.scalar() or 0
    
    delivered_result = await session.execute(
        select(func.count(Delivery.id)).where(
            and_(
                Delivery.driver_id == driver.id,
                Delivery.status == DeliveryStatus.DELIVERED.value
            )
        )
    )
    delivered = delivered_result.scalar() or 0
    
    success_rate = (delivered / total * 100) if total > 0 else 100.0
    
    return DriverStats(
        driver_id=driver.id,
        driver_name=driver.name,
        total_deliveries=driver.total_deliveries,
        today_deliveries=today_deliveries,
        week_deliveries=week_deliveries,
        month_deliveries=month_deliveries,
        rating=driver.rating,
        average_delivery_time_minutes=float(avg_time) if avg_time else None,
        success_rate=round(success_rate, 2),
        status=driver.status,
    )


@router.put("/deliveries/{delivery_id}/status", response_model=dict)
async def update_delivery_status(
    delivery_id: UUID,
    status_update: DeliveryStatusUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Atualiza status da entrega.
    
    Requires: role = "driver"
    """
    if current_user.role != "driver":
        raise HTTPException(status_code=403, detail="Acesso restrito a entregadores")
    
    # Buscar driver
    driver_result = await session.execute(
        select(Driver).where(Driver.phone == current_user.username)
    )
    driver = driver_result.scalar_one_or_none()
    
    if not driver:
        raise HTTPException(status_code=404, detail="Perfil de entregador não encontrado")
    
    # Buscar delivery
    delivery_result = await session.execute(
        select(Delivery).where(Delivery.id == delivery_id)
    )
    delivery = delivery_result.scalar_one_or_none()
    
    if not delivery:
        raise HTTPException(status_code=404, detail="Entrega não encontrada")
    
    # Verificar se a entrega pertence ao driver
    if delivery.driver_id != driver.id:
        raise HTTPException(status_code=403, detail="Entrega não pertence a este entregador")
    
    # Atualizar status
    delivery.update_status(status_update.status)
    if status_update.notes:
        delivery.notes = status_update.notes
    
    # Atualizar status do pedido correspondente via SQL direto
    # (evita problema de FK resolution no ORM com orders.approved_by)
    if status_update.status == DeliveryStatus.PICKED_UP.value:
        await session.execute(
            update(Order).where(Order.id == delivery.order_id).values(
                status=OrderStatus.DISPATCHED.value,
                dispatched_at=datetime.now(timezone.utc)
            )
        )
    elif status_update.status == DeliveryStatus.DELIVERED.value:
        await session.execute(
            update(Order).where(Order.id == delivery.order_id).values(
                status=OrderStatus.DELIVERED.value,
                delivered_at=datetime.now(timezone.utc)
            )
        )
        # Driver volta para disponível
        driver.status = DriverStatus.AVAILABLE.value
        driver.total_deliveries += 1

    session.add(delivery)
    session.add(driver)
    await session.commit()
    await session.refresh(delivery)

    # Side-effects quando entregue: WebSocket order_update e event publisher
    if status_update.status == DeliveryStatus.DELIVERED.value:
        asyncio.create_task(on_order_delivered(delivery.order_id))

    # Notificar cliente via WhatsApp
    try:
        # Buscar telefone do cliente via order → customer
        order_result = await session.execute(
            select(Order).where(Order.id == delivery.order_id)
        )
        order = order_result.scalar_one_or_none()
        customer_phone = None
        if order and order.customer_id:
            cust_result = await session.execute(
                select(Customer).where(Customer.id == order.customer_id)
            )
            customer = cust_result.scalar_one_or_none()
            if customer:
                customer_phone = customer.phone

        if customer_phone:
            order_number = order.order_number if order else "?"

            if status_update.status == DeliveryStatus.IN_TRANSIT.value:
                # Envia link de rastreamento (localização do driver) ao cliente
                maps_link = ""
                if driver.current_location:
                    lat = driver.current_location.get("latitude")
                    lng = driver.current_location.get("longitude")
                    if lat and lng:
                        maps_link = (
                            "\n\n📍 *Rastreie a entrega* (localização do entregador):\n"
                            f"https://maps.google.com/maps?q={lat},{lng}"
                        )

                await waha_client.send_text(
                    phone=customer_phone,
                    text=(
                        f"🚗 Pedido #{order_number} saiu para entrega!\n\n"
                        f"Entregador: {driver.name}\n"
                        f"Telefone: {driver.phone}"
                        f"{maps_link}"
                    )
                )

            elif status_update.status == DeliveryStatus.DELIVERED.value:
                await waha_client.send_text(
                    phone=customer_phone,
                    text=(
                        f"✅ Pedido #{order_number} entregue!\n\n"
                        f"Obrigado pela preferencia! 🔥"
                    )
                )
    except Exception as e:
        logger.error(f"Erro ao enviar WhatsApp: {e}")

    return {
        "id": str(delivery.id),
        "status": delivery.status,
        "message": "Status atualizado com sucesso"
    }


@router.post("/deliveries/{delivery_id}/accept", response_model=dict)
async def accept_delivery(
    delivery_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Aceita uma entrega disponível (pending).
    
    Requires: role = "driver"
    """
    if current_user.role != "driver":
        raise HTTPException(status_code=403, detail="Acesso restrito a entregadores")
    
    # Buscar driver
    driver_result = await session.execute(
        select(Driver).where(Driver.phone == current_user.username)
    )
    driver = driver_result.scalar_one_or_none()
    
    if not driver:
        raise HTTPException(status_code=404, detail="Perfil de entregador não encontrado")
    
    # Verificar se driver está disponível
    if driver.status != DriverStatus.AVAILABLE.value:
        raise HTTPException(
            status_code=400, 
            detail=f"Você precisa estar disponível para aceitar entregas. Status atual: {driver.status}"
        )
    
    # Buscar delivery
    delivery_result = await session.execute(
        select(Delivery).where(Delivery.id == delivery_id)
    )
    delivery = delivery_result.scalar_one_or_none()
    
    if not delivery:
        raise HTTPException(status_code=404, detail="Entrega não encontrada")
    
    # Verificar se entrega está disponível (pending)
    if delivery.status != DeliveryStatus.PENDING.value:
        raise HTTPException(
            status_code=400,
            detail=f"Entrega não está disponível para aceitação. Status atual: {delivery.status}"
        )
    
    # Verificar se já tem driver atribuído
    if delivery.driver_id:
        raise HTTPException(
            status_code=400,
            detail="Esta entrega já foi atribuída a outro entregador"
        )
    
    # Atribuir entrega ao driver
    delivery.driver_id = driver.id
    delivery.driver_name = driver.name
    delivery.driver_phone = driver.phone
    delivery.update_status(DeliveryStatus.ASSIGNED.value)
    
    # Atualizar status do driver para ocupado
    driver.status = DriverStatus.BUSY.value
    
    session.add(delivery)
    session.add(driver)
    await session.commit()
    await session.refresh(delivery)
    
    # Enviar push notification para o próprio driver (confirmação)
    if driver.push_token and notify_driver_new_delivery:
        try:
            order_result = await session.execute(
                select(Order).where(Order.id == delivery.order_id)
            )
            order = order_result.scalar_one_or_none()
            order_number = order.order_number if order else str(delivery.order_id)[:8]

            await notify_driver_new_delivery(
                push_token=driver.push_token,
                delivery_id=str(delivery.id),
                bairro=delivery.bairro or "Sem bairro",
                order_number=str(order_number),
            )
        except Exception as e:
            logger.error(f"Erro ao enviar push: {e}")

    return {
        "id": str(delivery.id),
        "status": delivery.status,
        "message": "Entrega aceita com sucesso"
    }


@router.post("/deliveries/{delivery_id}/problem", response_model=dict)
async def report_delivery_problem(
    delivery_id: UUID,
    problem: DeliveryProblemReport,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Reporta problema na entrega.
    
    Requires: role = "driver"
    """
    if current_user.role != "driver":
        raise HTTPException(status_code=403, detail="Acesso restrito a entregadores")
    
    # Buscar driver
    driver_result = await session.execute(
        select(Driver).where(Driver.phone == current_user.username)
    )
    driver = driver_result.scalar_one_or_none()
    
    if not driver:
        raise HTTPException(status_code=404, detail="Perfil de entregador não encontrado")
    
    # Buscar delivery
    delivery_result = await session.execute(
        select(Delivery).where(Delivery.id == delivery_id)
    )
    delivery = delivery_result.scalar_one_or_none()
    
    if not delivery:
        raise HTTPException(status_code=404, detail="Entrega não encontrada")
    
    # Verificar se a entrega pertence ao driver
    if delivery.driver_id != driver.id:
        raise HTTPException(status_code=403, detail="Entrega não pertence a este entregador")
    
    # Marcar como falha
    delivery.status = DeliveryStatus.FAILED.value
    delivery.failure_reason = f"[{problem.problem_type}] {problem.description}"
    
    # TODO: Notificar operador via WebSocket
    # TODO: Criar log de evento
    
    session.add(delivery)
    await session.commit()
    
    return {
        "id": str(delivery.id),
        "status": "failed",
        "message": "Problema reportado com sucesso. Operador será notificado."
    }


# ==================== ENDPOINTS ADMIN/OPERATOR ====================


@router.get("/", response_model=List[DriverBrief])
async def list_drivers(
    status: str = Query(None, description="Filtrar por status"),
    is_active: bool = Query(None, description="Filtrar por ativo/inativo"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Lista todos os entregadores.
    
    Requires: role = "admin" or "operator"
    """
    if current_user.role not in ["admin", "operator", "owner"]:
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores e operadores")
    
    query = select(Driver)
    
    if status:
        query = query.where(Driver.status == status)
    
    if is_active is not None:
        query = query.where(Driver.is_active == is_active)
    
    query = query.order_by(Driver.created_at.desc())
    
    result = await session.execute(query)
    drivers = result.scalars().all()
    
    return drivers


@router.post("/", response_model=DriverResponse)
async def create_driver(
    driver_data: DriverCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Cria novo entregador.
    
    Requires: role = "admin"
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    
    # Verificar se telefone já existe
    existing = await session.execute(
        select(Driver).where(Driver.phone == driver_data.phone)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Telefone já cadastrado")
    
    # Criar driver
    driver = Driver(
        **driver_data.model_dump(),
        status=DriverStatus.OFFLINE.value,
        rating=5.0,
        total_deliveries=0,
        is_active=True,
    )
    
    session.add(driver)
    await session.commit()
    await session.refresh(driver)
    
    return driver


@router.get("/{driver_id}", response_model=DriverResponse)
async def get_driver(
    driver_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Retorna detalhes de um entregador.
    
    Requires: role = "admin" or "operator"
    """
    if current_user.role not in ["admin", "operator", "owner"]:
        raise HTTPException(status_code=403, detail="Acesso restrito")
    
    result = await session.execute(
        select(Driver).where(Driver.id == driver_id)
    )
    driver = result.scalar_one_or_none()
    
    if not driver:
        raise HTTPException(status_code=404, detail="Entregador não encontrado")
    
    return driver


@router.put("/{driver_id}", response_model=DriverResponse)
async def update_driver(
    driver_id: UUID,
    driver_data: DriverUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Atualiza dados de um entregador.
    
    Requires: role = "admin"
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    
    result = await session.execute(
        select(Driver).where(Driver.id == driver_id)
    )
    driver = result.scalar_one_or_none()
    
    if not driver:
        raise HTTPException(status_code=404, detail="Entregador não encontrado")
    
    # Atualizar campos não-nulos
    for field, value in driver_data.model_dump(exclude_unset=True).items():
        setattr(driver, field, value)
    
    session.add(driver)
    await session.commit()
    await session.refresh(driver)
    
    return driver


@router.delete("/{driver_id}", response_model=dict)
async def delete_driver(
    driver_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Remove um entregador (soft delete - marca como inativo).
    
    Requires: role = "admin"
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    
    result = await session.execute(
        select(Driver).where(Driver.id == driver_id)
    )
    driver = result.scalar_one_or_none()
    
    if not driver:
        raise HTTPException(status_code=404, detail="Entregador não encontrado")
    
    # Soft delete
    driver.is_active = False
    driver.status = DriverStatus.OFFLINE.value
    
    session.add(driver)
    await session.commit()
    
    return {"id": str(driver.id), "message": "Entregador removido com sucesso"}


# ==================== ENDPOINTS DE MÉTRICAS E TEMPO ====================


@router.get("/me/time-summary", response_model=DriverTimeSummary)
async def get_my_time_summary(
    period: str = Query("today", description="Período: today, week, month"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Retorna resumo de tempo trabalhado do driver logado.
    
    Requires: role = "driver"
    """
    if current_user.role != "driver":
        raise HTTPException(status_code=403, detail="Acesso restrito a entregadores")
    
    # Buscar driver
    result = await session.execute(
        select(Driver).where(Driver.phone == current_user.username)
    )
    driver = result.scalar_one_or_none()
    
    if not driver:
        raise HTTPException(status_code=404, detail="Perfil de entregador não encontrado")
    
    # Calcular datas
    from datetime import date, timedelta
    today = date.today()
    
    if period == "today":
        start_date = today
        end_date = today
    elif period == "week":
        start_date = today - timedelta(days=today.weekday())
        end_date = today
    elif period == "month":
        start_date = today.replace(day=1)
        end_date = today
    else:
        raise HTTPException(status_code=400, detail="Período inválido")
    
    # Buscar resumo
    summary = await DriverTimeTrackingService.get_driver_time_summary(
        session, driver.id, start_date, end_date
    )
    
    summary['driver_name'] = driver.name
    summary['current_status'] = driver.status
    summary['rating'] = float(driver.rating)
    
    return summary


@router.get("/metrics/ranking", response_model=List[DailyRankingItem])
async def get_deliveries_ranking(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Retorna ranking de entregas do dia.
    
    Requires: role = "admin", "owner" or "manager"
    """
    if current_user.role not in ["admin", "owner", "manager"]:
        raise HTTPException(status_code=403, detail="Acesso restrito")
    
    ranking = await DriverTimeTrackingService.get_daily_ranking(session)
    
    return ranking


@router.get("/metrics/dashboard")
async def get_drivers_metrics_dashboard(
    period: str = Query("today", description="Período: today, week, month"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Dashboard completo de métricas dos drivers.
    
    Requires: role = "admin", "owner" or "manager"
    """
    if current_user.role not in ["admin", "owner", "manager"]:
        raise HTTPException(status_code=403, detail="Acesso restrito")
    
    # Calcular datas
    from datetime import date, timedelta
    today = date.today()
    
    if period == "today":
        start_date = today
        end_date = today
    elif period == "week":
        start_date = today - timedelta(days=today.weekday())
        end_date = today
    elif period == "month":
        start_date = today.replace(day=1)
        end_date = today
    else:
        raise HTTPException(status_code=400, detail="Período inválido")

    try:
        ranking = await DriverTimeTrackingService.get_daily_ranking(session, today)
        drivers_time = await DriverTimeTrackingService.get_all_drivers_time_summary(
            session, start_date, end_date
        )
    except Exception as e:
        logger.exception("Erro ao buscar métricas de drivers: %s", e)
        ranking = []
        drivers_time = []

    total_drivers = len(drivers_time)
    total_deliveries = sum(item.get('deliveries_count', 0) for item in ranking)
    total_hours_worked = sum(d.get('total_hours', 0) for d in drivers_time)

    summary = {
        'period': period,
        'total_drivers': total_drivers,
        'total_deliveries': total_deliveries,
        'total_hours_worked': round(total_hours_worked, 2),
        'average_hours_per_driver': round(total_hours_worked / total_drivers, 2) if total_drivers > 0 else 0
    }

    return {
        'summary': summary,
        'ranking': ranking,
        'drivers_time': drivers_time
    }
