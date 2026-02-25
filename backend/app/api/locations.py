"""
API de Localizacoes - Mapa em tempo real.
Pedidos do dia com geocoding via BrasilAPI + Nominatim.
"""

import logging
from datetime import datetime, timedelta, timezone, time
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.driver import Driver
from app.models.delivery import Delivery, DeliveryStatus
from app.models.order import Order, OrderStatus
from app.models.customer import Customer
from app.models.auth_models import BRAZIL_TZ
from app.services.geocoding_service import geocode_address

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== Schemas ====================

class LocationData(BaseModel):
    latitude: float
    longitude: float
    timestamp: Optional[datetime] = None


class TagConfig(BaseModel):
    """Configuração visual de uma tag."""
    color: str
    icon: str
    label: str
    category: str


class DriverLocation(BaseModel):
    id: str
    name: str
    phone: Optional[str] = None
    status: str
    location: Optional[LocationData] = None
    active_deliveries: int = 0
    tags: List[str] = []
    tag_config: Optional[TagConfig] = None


class OrderMapItem(BaseModel):
    id: str
    order_number: Optional[int] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    status: str  # "pending", "in_route", "completed"
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    driver_name: Optional[str] = None
    created_at: Optional[datetime] = None
    items_summary: Optional[str] = None


class DeliveryLocation(BaseModel):
    id: str
    order_id: str
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    status: str
    location: Optional[LocationData] = None
    address: Optional[str] = None
    driver_id: Optional[str] = None
    driver_name: Optional[str] = None
    tags: List[str] = []
    tag_config: Optional[TagConfig] = None


class CustomerLocation(BaseModel):
    phone: str
    name: Optional[str] = None
    latitude: float
    longitude: float
    address: Optional[str] = None
    timestamp: datetime
    tags: List[str] = []
    tag_config: Optional[TagConfig] = None
    order_count: int = 0


class FiltersData(BaseModel):
    """Filtros disponíveis para o mapa."""
    available_tags: List[str]
    tag_configs: dict


class MapDataResponse(BaseModel):
    drivers: List[DriverLocation]
    orders: List[OrderMapItem]
    deliveries: List[DeliveryLocation]
    customer_locations: List[CustomerLocation]
    filters: FiltersData
    updated_at: datetime


# ==================== Helpers ====================

def _map_order_status(status: str) -> Optional[str]:
    """Mapeia status do pedido para categoria visual do mapa."""
    if status in (OrderStatus.PENDING.value, OrderStatus.PAID.value, OrderStatus.PREPARING.value):
        return "pending"
    elif status == OrderStatus.DISPATCHED.value:
        return "in_route"
    elif status == OrderStatus.DELIVERED.value:
        return "completed"
    return None  # CANCELLED não aparece no mapa


def _format_address(delivery_address: Optional[dict]) -> Optional[str]:
    """Formata endereço para exibição no mapa."""
    if not delivery_address or not isinstance(delivery_address, dict):
        return None
    parts = []
    if delivery_address.get("street"):
        parts.append(delivery_address["street"])
    if delivery_address.get("number"):
        parts.append(str(delivery_address["number"]))
    if delivery_address.get("bairro"):
        parts.append(delivery_address["bairro"])
    return ", ".join(parts) if parts else None


def _get_today_boundaries() -> tuple:
    """Retorna (inicio, fim) do dia atual em horário brasileiro, convertido para UTC."""
    now_br = datetime.now(BRAZIL_TZ)
    start_of_day_br = datetime.combine(now_br.date(), time.min, tzinfo=BRAZIL_TZ)
    end_of_day_br = datetime.combine(now_br.date(), time.max, tzinfo=BRAZIL_TZ)
    return (
        start_of_day_br.astimezone(timezone.utc),
        end_of_day_br.astimezone(timezone.utc),
    )

class GeocodeRequest(BaseModel):
    """Request para geocodificação."""
    cep: Optional[str] = None
    address: Optional[dict] = None


class GeocodeResponse(BaseModel):
    """Response de geocodificação."""
    cep: Optional[str]
    logradouro: Optional[str]
    bairro: Optional[str]
    cidade: Optional[str]
    estado: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    source: Optional[str]
    accuracy: Optional[str]


# ==================== Endpoints ====================

@router.get("/map-data", response_model=MapDataResponse)
async def get_map_data(
    db: AsyncSession = Depends(get_db),
    include_offline_drivers: bool = Query(False, description="Incluir entregadores offline"),
    today_only: bool = Query(True, description="Mostrar apenas pedidos de hoje"),
    hours_back: int = Query(24, description="Horas para buscar localizacoes de clientes"),
):
    """
    Retorna dados para o mapa em tempo real.
    Inclui: entregadores ativos, entregas em andamento, localizacoes de clientes.
    Com sistema de tags e geocoding automático.
    """
    try:
        # Importar funções de tags
        from app.models.location_tag import (
            get_tag_for_driver, 
            get_tag_for_customer, 
            get_tag_for_delivery,
            get_tag_config,
            get_all_tag_configs
        )
        from app.services.geocoding_service import GeocodingService
        from app.models.customer import Customer
        from sqlalchemy import func
        from app.database import redis_manager
        
        # Inicializar serviço de geocoding
        geocoding_service = GeocodingService(db, redis_manager)
        
        # 1. Buscar entregadores
        drivers = await _fetch_drivers(db, include_offline_drivers)

        # 2. Buscar pedidos do dia com coordenadas (mantido para compatibilidade do MapDataResponse e OrderMapItem)
        orders = await _fetch_today_orders(db, today_only)

        # 3. Buscar entregas ativas e locais do cliente dependem de config (a logica principal do update passa pelo geo service)
        deliveries = await _fetch_active_deliveries(db, geocoding_service)

        # 4. Buscar localizações de clientes recentes
        customer_locations = await get_recent_customer_locations(db, hours_back, geocoding_service)
        
        all_tag_configs = get_all_tag_configs()
        filters = FiltersData(
            available_tags=list(all_tag_configs.keys()),
            tag_configs=all_tag_configs
        )

        return MapDataResponse(
            drivers=drivers,
            orders=orders,
            deliveries=deliveries,
            customer_locations=customer_locations,
            filters=filters,
            updated_at=datetime.now(timezone.utc),
        )

    except Exception as e:
        logger.error(f"Erro ao buscar dados do mapa: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def _fetch_drivers(db: AsyncSession, include_offline: bool) -> List[DriverLocation]:
    """Busca entregadores para o mapa."""
    from app.models.location_tag import get_tag_for_driver, get_tag_config
    driver_query = select(Driver)
    if not include_offline:
        driver_query = driver_query.where(Driver.is_active == True)

    result = await db.execute(driver_query)
    drivers_db = result.scalars().all()

    drivers = []
    for d in drivers_db:
        loc = None
        if d.current_location:
            loc = LocationData(
                latitude=d.current_location.get("latitude"),
                longitude=d.current_location.get("longitude"),
                timestamp=d.current_location.get("timestamp"),
            )

        # Contar entregas ativas
        active_count_query = select(Delivery).where(
            and_(
                Delivery.driver_id == d.id,
                Delivery.status.in_([
                    DeliveryStatus.ASSIGNED.value,
                    DeliveryStatus.PICKED_UP.value,
                    DeliveryStatus.IN_TRANSIT.value,
                ])
            )
        )
        active_result = await db.execute(active_count_query)
        active_count = len(active_result.scalars().all())
        
        # Determinar tag
        tag = get_tag_for_driver(d)
        tag_cfg = get_tag_config(tag)

        drivers.append(DriverLocation(
            id=str(d.id),
            name=d.name,
            phone=d.phone,
            status=d.status or "offline",
            location=loc,
            active_deliveries=active_count,
            tags=[tag],
            tag_config=TagConfig(**tag_cfg) if tag_cfg else None,
        ))

    return drivers


async def _fetch_today_orders(db: AsyncSession, today_only: bool) -> List[OrderMapItem]:
    """Busca pedidos do dia para manter compatibilidade com a struct de resposta."""
    query = (
        select(Order, Customer)
        .outerjoin(Customer, Order.customer_id == Customer.id)
        .where(Order.status != OrderStatus.CANCELLED.value)
    )

    if today_only:
        day_start, day_end = _get_today_boundaries()
        query = query.where(
            and_(
                Order.created_at >= day_start,
                Order.created_at <= day_end,
            )
        )

    query = query.order_by(Order.created_at.desc())
    result = await db.execute(query)
    rows = result.all()

    orders = []
    for order, customer in rows:
        map_status = _map_order_status(order.status)
        if map_status is None:
            continue

        lat, lng = None, None
        addr = order.delivery_address or {}

        # 1. Coordenadas já salvas no delivery_address
        if addr.get("location"):
            lat = addr.get("location").get("latitude")
            lng = addr.get("location").get("longitude")

        # 2. Coordenadas da delivery (se existir)
        driver_name = None
        if lat is None or lng is None or map_status == "in_route":
            delivery_result = await db.execute(
                select(Delivery).where(Delivery.order_id == order.id)
            )
            delivery = delivery_result.scalar_one_or_none()
            if delivery:
                if (lat is None or lng is None) and delivery.delivery_destination_lat and delivery.delivery_destination_lng:
                    lat = delivery.delivery_destination_lat
                    lng = delivery.delivery_destination_lng
                driver_name = delivery.driver_name

        orders.append(OrderMapItem(
            id=str(order.id),
            order_number=order.order_number,
            customer_name=customer.name if customer else None,
            customer_phone=customer.phone if customer else None,
            status=map_status,
            address=_format_address(addr),
            latitude=lat,
            longitude=lng,
            driver_name=driver_name,
            created_at=order.created_at,
        ))

    return orders

async def _fetch_active_deliveries(db: AsyncSession, geocoding_service=None) -> List[DeliveryLocation]:
    """Busca entregas ativas para compatibilidade."""
    from app.models.location_tag import get_tag_for_delivery, get_tag_config
    
    delivery_query = (
        select(Delivery, Order, Customer)
        .join(Order, Delivery.order_id == Order.id)
        .outerjoin(Customer, Order.customer_id == Customer.id)
        .where(
            Delivery.status.in_([
                DeliveryStatus.PENDING.value,
                DeliveryStatus.ASSIGNED.value,
                DeliveryStatus.PICKED_UP.value,
                DeliveryStatus.IN_TRANSIT.value,
                DeliveryStatus.ARRIVED.value,
            ])
        )
    )

    result = await db.execute(delivery_query)
    deliveries_db = result.all()

    deliveries = []
    for delivery, order, customer in deliveries_db:
        loc = None
        if delivery.last_location:
            loc = LocationData(
                latitude=delivery.last_location.get("lat") or delivery.last_location.get("latitude"),
                longitude=delivery.last_location.get("lng") or delivery.last_location.get("longitude"),
                timestamp=delivery.last_location.get("timestamp"),
            )
        elif order.delivery_address:
            # Usar endereco do pedido se tiver coordenadas
            addr = order.delivery_address
            if addr.get("location"):
                loc = LocationData(
                    latitude=addr["location"].get("latitude"),
                    longitude=addr["location"].get("longitude"),
                )
        
        # Se não tem localização, tentar geocodificar pelo CEP
        if not loc and order.delivery_address and order.delivery_address.get("cep") and geocoding_service:
            cep = order.delivery_address.get("cep")
            geo_data = await geocoding_service.geocode_by_cep(cep)
            
            if geo_data and geo_data.get("latitude") and geo_data.get("longitude"):
                loc = LocationData(
                    latitude=geo_data["latitude"],
                    longitude=geo_data["longitude"],
                )
        
        # Determinar tag
        tag = get_tag_for_delivery(delivery)
        tag_cfg = get_tag_config(tag)

        deliveries.append(DeliveryLocation(
            id=str(delivery.id),
            order_id=str(delivery.order_id),
            customer_name=customer.name if customer else None,
            customer_phone=customer.phone if customer else None,
            status=delivery.status,
            location=loc,
            address=delivery.bairro or (order.delivery_address.get("formatted") if order.delivery_address else None),
            driver_id=str(delivery.driver_id) if delivery.driver_id else None,
            driver_name=delivery.driver_name,
            tags=[tag],
            tag_config=TagConfig(**tag_cfg) if tag_cfg else None,
        ))

    return deliveries


async def get_recent_customer_locations(
    db: AsyncSession,
    hours_back: int = 24,
    geocoding_service=None
) -> List[CustomerLocation]:
    """
    Busca localizacoes de clientes recentes do EventLog.
    """
    from app.models.event_log import EventLog
    from app.models.customer import Customer
    from app.models.location_tag import get_tag_for_customer, get_tag_config
    from sqlalchemy import func

    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)

        query = select(EventLog).where(
            and_(
                EventLog.event_type == "location_received",
                EventLog.created_at >= cutoff,
            )
        ).order_by(EventLog.created_at.desc()).limit(100)

        result = await db.execute(query)
        events = result.scalars().all()

        locations = []
        seen_phones = set()

        for event in events:
            payload = event.payload or {}
            phone = payload.get("phone")

            # Evitar duplicatas (pegar apenas a mais recente por telefone)
            if phone in seen_phones:
                continue
            seen_phones.add(phone)

            if payload.get("latitude") and payload.get("longitude"):
                # Buscar dados do cliente e contar pedidos
                customer_query = select(Customer).where(Customer.phone == phone)
                customer_result = await db.execute(customer_query)
                customer = customer_result.scalar_one_or_none()
                
                order_count = 0
                if customer:
                    order_count_query = select(func.count(Order.id)).where(
                        Order.customer_id == customer.id
                    )
                    order_count_result = await db.execute(order_count_query)
                    order_count = order_count_result.scalar() or 0
                
                # Determinar tag
                tag = get_tag_for_customer(customer, order_count)
                tag_cfg = get_tag_config(tag)
                
                locations.append(CustomerLocation(
                    phone=phone,
                    name=payload.get("name"),
                    latitude=payload["latitude"],
                    longitude=payload["longitude"],
                    address=payload.get("address"),
                    timestamp=event.created_at,
                    tags=[tag],
                    tag_config=TagConfig(**tag_cfg) if tag_cfg else None,
                    order_count=order_count,
                ))

        return locations

    except Exception as e:
        logger.warning(f"Erro ao buscar localizacoes de clientes: {e}")
        return []


@router.post("/driver/{driver_id}/location")
async def update_driver_location(
    driver_id: UUID,
    location: LocationData,
    db: AsyncSession = Depends(get_db),
):
    """
    Atualiza a localizacao de um entregador.
    """
    try:
        result = await db.execute(select(Driver).where(Driver.id == driver_id))
        driver = result.scalar_one_or_none()

        if not driver:
            raise HTTPException(status_code=404, detail="Entregador nao encontrado")

        driver.current_location = {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "timestamp": (location.timestamp or datetime.now(timezone.utc)).isoformat(),
        }

        await db.commit()

        # Emitir via WebSocket
        try:
            from app.api.websocket import manager
            await manager.broadcast(
                {
                    "type": "driver_location_update",
                    "driver_id": str(driver_id),
                    "location": {
                        "latitude": location.latitude,
                        "longitude": location.longitude,
                        "timestamp": driver.current_location["timestamp"],
                    }
                },
                filter_fn=lambda m: m.user_role.value in ("admin", "operator", "owner"),
            )
        except Exception as e:
            logger.warning(f"Erro ao emitir WebSocket: {e}")

        return {"status": "updated", "driver_id": str(driver_id)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar localizacao: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/drivers/active", response_model=List[DriverLocation])
async def get_active_drivers(
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna apenas entregadores ativos com localizacao.
    """
    result = await db.execute(
        select(Driver).where(
            and_(
                Driver.is_active == True,
                Driver.current_location.isnot(None),
            )
        )
    )
    drivers = result.scalars().all()

    return [
        DriverLocation(
            id=str(d.id),
            name=d.name,
            phone=d.phone,
            status=d.status or "online",
            location=LocationData(
                latitude=d.current_location.get("latitude"),
                longitude=d.current_location.get("longitude"),
                timestamp=d.current_location.get("timestamp"),
            ) if d.current_location else None,
        )
        for d in drivers
    ]


@router.post("/geocode", response_model=GeocodeResponse)
async def geocode_address(
    request: GeocodeRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Geocodifica um CEP ou endereço completo.
    
    Exemplos:
    - POST /api/locations/geocode {"cep": "80010-000"}
    - POST /api/locations/geocode {"address": {"street": "Rua XV de Novembro", "cidade": "Curitiba", "estado": "PR"}}
    
    Retorna coordenadas geográficas + endereço enriquecido.
    """
    from app.services.geocoding_service import GeocodingService
    
    try:
        service = GeocodingService(db, redis_manager)
        
        result = None
        
        if request.cep:
            result = await service.geocode_by_cep(request.cep)
        elif request.address:
            result = await service.geocode_by_address(request.address)
        else:
            raise HTTPException(
                status_code=400,
                detail="CEP ou endereço necessário"
            )
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail="Não foi possível geocodificar o endereço"
            )
        
        return GeocodeResponse(**result)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao geocodificar: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tags")
async def get_available_tags():
    """
    Retorna todas as tags disponíveis com suas configurações visuais.
    
    Útil para o frontend construir filtros e legendas do mapa.
    """
    from app.models.location_tag import get_all_tag_configs, get_tags_by_category
    
    return {
        "tags": get_all_tag_configs(),
        "categories": get_tags_by_category()
    }
