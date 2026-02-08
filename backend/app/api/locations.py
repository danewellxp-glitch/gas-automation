"""
API de Localizacoes - Mapa em tempo real.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, redis_manager
from app.models.driver import Driver
from app.models.delivery import Delivery, DeliveryStatus
from app.models.order import Order

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== Schemas ====================

class LocationData(BaseModel):
    latitude: float
    longitude: float
    timestamp: Optional[datetime] = None


class DriverLocation(BaseModel):
    id: str
    name: str
    phone: Optional[str] = None
    status: str
    location: Optional[LocationData] = None
    active_deliveries: int = 0


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


class CustomerLocation(BaseModel):
    phone: str
    name: Optional[str] = None
    latitude: float
    longitude: float
    address: Optional[str] = None
    timestamp: datetime


class MapDataResponse(BaseModel):
    drivers: List[DriverLocation]
    deliveries: List[DeliveryLocation]
    customer_locations: List[CustomerLocation]
    updated_at: datetime


# ==================== Endpoints ====================

@router.get("/map-data", response_model=MapDataResponse)
async def get_map_data(
    db: AsyncSession = Depends(get_db),
    include_offline_drivers: bool = Query(False, description="Incluir entregadores offline"),
    hours_back: int = Query(24, description="Horas para buscar localizacoes de clientes"),
):
    """
    Retorna dados para o mapa em tempo real.
    Inclui: entregadores ativos, entregas em andamento, localizacoes de clientes.
    """
    try:
        # 1. Buscar entregadores
        driver_query = select(Driver)
        if not include_offline_drivers:
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

            drivers.append(DriverLocation(
                id=str(d.id),
                name=d.name,
                phone=d.phone,
                status=d.status or "offline",
                location=loc,
                active_deliveries=active_count,
            ))

        # 2. Buscar entregas em andamento
        from sqlalchemy.orm import selectinload
        from app.models.customer import Customer

        delivery_query = select(Delivery, Order, Customer).join(
            Order, Delivery.order_id == Order.id
        ).join(
            Customer, Order.customer_id == Customer.id
        ).where(
            Delivery.status.in_([
                DeliveryStatus.PENDING.value,
                DeliveryStatus.ASSIGNED.value,
                DeliveryStatus.PICKED_UP.value,
                DeliveryStatus.IN_TRANSIT.value,
                DeliveryStatus.ARRIVED.value,
            ])
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
            ))

        # 3. Buscar localizacoes de clientes recentes (do Redis/EventLog)
        customer_locations = await get_recent_customer_locations(db, hours_back)

        return MapDataResponse(
            drivers=drivers,
            deliveries=deliveries,
            customer_locations=customer_locations,
            updated_at=datetime.now(timezone.utc),
        )

    except Exception as e:
        logger.error(f"Erro ao buscar dados do mapa: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def get_recent_customer_locations(
    db: AsyncSession,
    hours_back: int = 24
) -> List[CustomerLocation]:
    """
    Busca localizacoes de clientes recentes do EventLog.
    """
    from app.models.event_log import EventLog

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
                locations.append(CustomerLocation(
                    phone=phone,
                    name=payload.get("name"),
                    latitude=payload["latitude"],
                    longitude=payload["longitude"],
                    address=payload.get("address"),
                    timestamp=event.created_at,
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
                roles=["admin", "operator", "owner"],
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
