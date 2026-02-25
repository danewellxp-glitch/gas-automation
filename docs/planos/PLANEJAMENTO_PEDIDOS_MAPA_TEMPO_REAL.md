# 📍 Planejamento: Sistema de Pedidos em Tempo Real no Mapa

**Data:** 13/02/2026  
**Objetivo:** Implementar visualização de pedidos em tempo real no mapa do operador com geocoding automático, tags visuais e reset diário

---

## 🎯 Visão Geral

### Problema Atual
- Pedidos não aparecem automaticamente no mapa
- Endereços dos clientes não estão geocodificados
- Falta sistema de visualização em tempo real (live updates)
- Não há diferenciação visual por status do pedido
- Dados antigos acumulam no mapa (sem reset diário)

### Solução Proposta
1. **Geocoding Automático**: Ao criar pedido, geocodificar endereço via API CEPs Brasil
2. **Live Updates**: Usar WebSocket para atualizar mapa em tempo real
3. **Tags Visuais**: Marcadores coloridos por status (Pendente/Em Rota/Concluído)
4. **Reset Diário**: Limpar visualizações de pedidos antigos automaticamente
5. **Integração com Flow Engine**: Capturar pedidos do bot WhatsApp automaticamente

---

## 📊 Arquitetura do Sistema

```
┌─────────────────────────────────────────────┐
│     WhatsApp Bot (Flow Engine V2)          │
│  - Cliente faz pedido via WhatsApp          │
│  - Bot coleta: endereço, CEP, produtos      │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│   API Orders (create_order)                 │
│  1. Recebe pedido do bot                    │
│  2. Geocodifica endereço via GeocodingService│
│  3. Salva coordenadas em Order.delivery_address│
│  4. Emite WebSocket event: "order_created"  │
└─────────────────┬───────────────────────────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
┌──────────────┐    ┌──────────────────┐
│ PostgreSQL   │    │ WebSocket        │
│ - Orders     │    │ - Live broadcast │
│ - Coordinates│    │ - Role: operator │
└──────────────┘    └─────────┬────────┘
                              │
                              ▼
                    ┌──────────────────────┐
                    │ Frontend (React)     │
                    │ - Operador Dashboard │
                    │ - DeliveryMap        │
                    │ - Live markers       │
                    └──────────────────────┘
```

---

## 🏗️ Implementação Detalhada

### **FASE 1: Geocoding Automático ao Criar Pedido** (2-3h)

#### 1.1. Atualizar modelo `Order`

**Objetivo:** Adicionar campo `location` no `delivery_address` (JSONB)

```python
# backend/app/models/order.py (já existe delivery_address como JSONB)

# Estrutura atual:
delivery_address: {
    "street": "Rua XV de Novembro",
    "number": "123",
    "complement": "Apto 201",
    "bairro": "Centro",
    "city": "Curitiba",
    "state": "PR",
    "cep": "80010-000",
    "formatted": "..."
}

# Nova estrutura (adicionar):
delivery_address: {
    ...campos existentes...,
    "location": {
        "latitude": -25.4325731,
        "longitude": -49.2696439,
        "accuracy": "street",
        "source": "viacep+nominatim",
        "geocoded_at": "2026-02-13T20:00:00Z"
    }
}
```

**Não requer migration** - campo `delivery_address` já é JSONB, basta adicionar a chave `location`.

#### 1.2. Modificar `create_order` para geocodificar automaticamente

**Arquivo:** `backend/app/api/orders.py`

```python
@router.post("", response_model=OrderResponse, status_code=201)
async def create_order(
    data: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cria pedido + geocodifica endereço automaticamente."""
    
    # ... validações existentes ...
    
    # NOVO: Geocodificar endereço
    delivery_addr_dict = None
    if data.delivery_address:
        delivery_addr_dict = dict(data.delivery_address.model_dump())
        
        # Geocodificar via API CEPs Brasil
        from app.services.geocoding_service import GeocodingService
        geocoding_service = GeocodingService(db, redis_manager)
        
        # Tentar por CEP primeiro
        geo_result = None
        if data.delivery_address.cep:
            geo_result = await geocoding_service.geocode_by_cep(
                data.delivery_address.cep
            )
        
        # Se falhar, tentar por endereço completo
        if not geo_result or not geo_result.get("latitude"):
            geo_result = await geocoding_service.geocode_by_address({
                "street": data.delivery_address.street,
                "number": data.delivery_address.number,
                "bairro": data.delivery_address.bairro,
                "cidade": data.delivery_address.city,
                "estado": data.delivery_address.state,
                "cep": data.delivery_address.cep,
            })
        
        # Adicionar coordenadas ao endereço
        if geo_result and geo_result.get("latitude"):
            delivery_addr_dict["location"] = {
                "latitude": geo_result["latitude"],
                "longitude": geo_result["longitude"],
                "accuracy": geo_result.get("accuracy", "approximate"),
                "source": geo_result.get("source", "unknown"),
                "geocoded_at": datetime.now(timezone.utc).isoformat()
            }
            logger.info(f"Pedido geocodificado: {geo_result['latitude']}, {geo_result['longitude']}")
        else:
            logger.warning(f"Não foi possível geocodificar pedido #{order_number}")
    
    # Criar pedido com coordenadas
    order = Order(
        customer_id=data.customer_id,
        # ... outros campos ...
        delivery_address=delivery_addr_dict,  # Agora com location
        delivery_bairro=delivery_bairro,
    )
    
    # ... restante da lógica ...
    
    # Emitir WebSocket (já existe)
    await emit_order_created_event(order, db)
    
    return order
```

#### 1.3. Atualizar `emit_order_created_event`

**Arquivo:** `backend/app/api/orders.py`

```python
async def emit_order_created_event(order: Order, db: AsyncSession):
    """Emite evento de pedido criado via WebSocket."""
    from app.api.websocket import manager as ws_manager
    from app.models.location_tag import get_tag_for_order, get_tag_config
    
    # Determinar tag baseada no status
    tag = get_tag_for_order(order)
    tag_config = get_tag_config(tag)
    
    # Preparar dados do pedido para o mapa
    order_data = {
        "type": "order_created",
        "order_id": str(order.id),
        "order_number": order.order_number,
        "customer_name": order.customer.name if order.customer else None,
        "customer_phone": order.customer.phone if order.customer else None,
        "status": order.status,
        "total_amount": float(order.total_amount),
        "delivery_address": order.delivery_address,
        "location": order.delivery_address.get("location") if order.delivery_address else None,
        "bairro": order.delivery_bairro,
        "tags": [tag],
        "tag_config": tag_config,
        "created_at": order.created_at.isoformat(),
    }
    
    # Broadcast para operadores (e admin)
    if order.delivery_bairro:
        await ws_manager.broadcast_to_neighborhood(order_data, order.delivery_bairro)
    else:
        await ws_manager.broadcast_to_role(order_data, UserRole.OPERATOR)
    
    await ws_manager.broadcast_to_role(order_data, UserRole.ADMIN)
```

---

### **FASE 2: API de Pedidos para o Mapa** (1-2h)

#### 2.1. Criar endpoint `/api/orders/map-data`

**Objetivo:** Retornar pedidos do dia atual com coordenadas e tags

**Arquivo:** `backend/app/api/orders.py`

```python
from app.models.location_tag import get_tag_for_order, get_tag_config, TAG_CONFIG

class OrderMapLocation(BaseModel):
    """Pedido para exibição no mapa."""
    id: str
    order_number: int
    customer_name: Optional[str]
    customer_phone: Optional[str]
    status: str
    location: Optional[LocationData]
    address: Optional[str]
    bairro: Optional[str]
    total_amount: float
    tags: List[str] = []
    tag_config: Optional[dict] = None
    created_at: datetime
    delivered_at: Optional[datetime] = None


class OrdersMapDataResponse(BaseModel):
    """Response do mapa de pedidos."""
    orders: List[OrderMapLocation]
    total_count: int
    by_status: dict  # {"pending": 5, "dispatched": 3, ...}
    filters: dict
    updated_at: datetime


@router.get("/map-data", response_model=OrdersMapDataResponse)
async def get_orders_map_data(
    db: AsyncSession = Depends(get_db),
    date: Optional[str] = Query(None, description="Data YYYY-MM-DD (padrão: hoje)"),
    status_filter: Optional[List[str]] = Query(None, description="Filtrar por status"),
    bairro_filter: Optional[str] = Query(None, description="Filtrar por bairro"),
):
    """
    Retorna pedidos do dia para exibição no mapa.
    
    Features:
    - Apenas pedidos com coordenadas geocodificadas
    - Filtrável por status e bairro
    - Tags visuais por status
    - Reset diário (padrão: pedidos de hoje)
    """
    from datetime import date as date_obj
    from sqlalchemy import func, and_
    
    # Determinar data (padrão: hoje)
    target_date = date_obj.today()
    if date:
        try:
            target_date = date_obj.fromisoformat(date)
        except ValueError:
            raise HTTPException(400, detail="Data inválida. Use formato YYYY-MM-DD")
    
    # Query base: pedidos do dia
    start_of_day = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    end_of_day = datetime.combine(target_date, datetime.max.time()).replace(tzinfo=timezone.utc)
    
    query = select(Order, Customer).join(
        Customer, Order.customer_id == Customer.id
    ).where(
        and_(
            Order.created_at >= start_of_day,
            Order.created_at <= end_of_day,
            # Apenas pedidos com coordenadas
            Order.delivery_address.isnot(None),
        )
    )
    
    # Filtros opcionais
    if status_filter:
        query = query.where(Order.status.in_(status_filter))
    
    if bairro_filter:
        query = query.where(Order.delivery_bairro == bairro_filter)
    
    # Executar query
    result = await db.execute(query)
    orders_db = result.all()
    
    # Processar pedidos
    orders = []
    status_count = {}
    
    for order, customer in orders_db:
        # Verificar se tem coordenadas
        location = None
        if order.delivery_address and order.delivery_address.get("location"):
            loc_data = order.delivery_address["location"]
            location = LocationData(
                latitude=loc_data["latitude"],
                longitude=loc_data["longitude"],
                timestamp=loc_data.get("geocoded_at")
            )
        
        # Se não tem coordenadas, pular (ou tentar geocodificar aqui)
        if not location:
            continue
        
        # Determinar tag
        tag = get_tag_for_order(order)
        tag_cfg = get_tag_config(tag)
        
        # Formatar endereço
        address_str = order.delivery_address.get("formatted") if order.delivery_address else None
        
        orders.append(OrderMapLocation(
            id=str(order.id),
            order_number=order.order_number,
            customer_name=customer.name,
            customer_phone=customer.phone,
            status=order.status,
            location=location,
            address=address_str,
            bairro=order.delivery_bairro,
            total_amount=float(order.total_amount),
            tags=[tag],
            tag_config=tag_cfg,
            created_at=order.created_at,
            delivered_at=order.delivered_at,
        ))
        
        # Contar por status
        status_count[order.status] = status_count.get(order.status, 0) + 1
    
    return OrdersMapDataResponse(
        orders=orders,
        total_count=len(orders),
        by_status=status_count,
        filters={
            "available_statuses": [s.value for s in OrderStatus],
            "available_tags": list(TAG_CONFIG.keys()),
            "date": target_date.isoformat()
        },
        updated_at=datetime.now(timezone.utc)
    )
```

#### 2.2. Integrar com endpoint `/api/locations/map-data`

**Objetivo:** Retornar pedidos junto com drivers, deliveries e customer_locations

**Arquivo:** `backend/app/api/locations.py`

```python
# Adicionar import
from app.api.orders import get_orders_map_data

# Modificar MapDataResponse
class MapDataResponse(BaseModel):
    drivers: List[DriverLocation]
    deliveries: List[DeliveryLocation]
    customer_locations: List[CustomerLocation]
    orders: List[OrderMapLocation]  # NOVO
    filters: FiltersData
    updated_at: datetime

# Modificar endpoint
@router.get("/map-data", response_model=MapDataResponse)
async def get_map_data(...):
    # ... código existente ...
    
    # NOVO: Buscar pedidos do dia
    orders_data = await get_orders_map_data(db)
    
    return MapDataResponse(
        drivers=drivers,
        deliveries=deliveries,
        customer_locations=customer_locations,
        orders=orders_data.orders,  # NOVO
        filters=filters,
        updated_at=datetime.now(timezone.utc),
    )
```

---

### **FASE 3: Sistema de Reset Diário** (1h)

#### 3.1. Criar job agendado para reset

**Arquivo:** `backend/app/services/daily_reset_service.py` (NOVO)

```python
"""
Serviço de Reset Diário do Mapa.
Limpa pedidos antigos e reseta visualizações.
"""

import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class DailyResetService:
    """Gerencia reset diário do mapa."""
    
    @staticmethod
    async def reset_daily_map(db: AsyncSession):
        """
        Reset diário do mapa.
        
        Actions:
        1. Limpar cache de visualizações antigas
        2. Emitir evento WebSocket de reset
        3. Arquivar métricas do dia anterior
        """
        logger.info("🔄 Iniciando reset diário do mapa...")
        
        # 1. Emitir evento de reset via WebSocket
        from app.api.websocket import manager as ws_manager
        
        reset_event = {
            "type": "map_reset",
            "reason": "daily_reset",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "Mapa resetado - novo dia iniciado"
        }
        
        await ws_manager.broadcast(reset_event, roles=["operator", "admin", "owner"])
        
        # 2. Limpar cache Redis (opcional)
        # from app.database import redis_manager
        # await redis_manager.delete_pattern("map:orders:*")
        
        # 3. Arquivar métricas (opcional)
        # await archive_previous_day_metrics(db)
        
        logger.info("✅ Reset diário do mapa concluído")
        
        return True


async def archive_previous_day_metrics(db: AsyncSession):
    """Arquiva métricas do dia anterior (opcional)."""
    from app.models.order import Order
    from sqlalchemy import func
    
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    start_of_day = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    # Contar pedidos do dia anterior
    count_query = select(func.count(Order.id)).where(
        and_(
            Order.created_at >= start_of_day,
            Order.created_at <= end_of_day,
        )
    )
    
    result = await db.execute(count_query)
    total = result.scalar()
    
    logger.info(f"📊 Dia anterior: {total} pedidos")
    
    # Aqui você pode salvar em uma tabela de métricas diárias
    # ou enviar para sistema de analytics
    
    return total
```

#### 3.2. Configurar scheduler (APScheduler)

**Arquivo:** `backend/app/main.py`

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.daily_reset_service import DailyResetService

# Criar scheduler global
scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def startup_event():
    """Inicializar serviços no startup."""
    # ... código existente ...
    
    # NOVO: Configurar reset diário às 00:00
    from app.database import get_db
    
    async def daily_reset_job():
        """Job de reset diário."""
        async for db in get_db():
            try:
                await DailyResetService.reset_daily_map(db)
            except Exception as e:
                logger.error(f"Erro no reset diário: {e}")
            finally:
                await db.close()
    
    # Agendar para 00:00 todos os dias
    scheduler.add_job(
        daily_reset_job,
        trigger="cron",
        hour=0,
        minute=0,
        id="daily_map_reset",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("📅 Scheduler de reset diário iniciado")


@app.on_event("shutdown")
async def shutdown_event():
    """Desligar scheduler."""
    scheduler.shutdown()
    logger.info("📅 Scheduler desligado")
```

**Adicionar dependência:**
```bash
# requirements.txt
apscheduler==3.10.4
```

---

### **FASE 4: WebSocket Live Updates** (1-2h)

#### 4.1. Eventos WebSocket para pedidos

**Arquivo:** `backend/app/api/websocket.py`

Adicionar novos tipos de eventos:

```python
# Eventos existentes + novos:
EVENT_TYPES = [
    "order_created",         # NOVO
    "order_status_updated",  # NOVO
    "order_geocoded",        # NOVO
    "map_reset",             # NOVO
    "delivery_assigned",     # Existente
    "driver_location_update", # Existente
    # ... outros eventos ...
]
```

#### 4.2. Atualizar status do pedido com broadcast

**Arquivo:** `backend/app/api/orders.py`

```python
@router.patch("/{order_id}/status")
async def update_order_status(
    order_id: UUID,
    status_update: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(["admin", "operator"]),
):
    """Atualiza status do pedido + emite WebSocket."""
    
    # ... lógica de atualização ...
    
    order.update_status(status_update.status, current_user.id)
    await db.commit()
    
    # NOVO: Emitir WebSocket de atualização
    from app.api.websocket import manager as ws_manager
    from app.models.location_tag import get_tag_for_order, get_tag_config
    
    tag = get_tag_for_order(order)
    tag_config = get_tag_config(tag)
    
    update_event = {
        "type": "order_status_updated",
        "order_id": str(order.id),
        "order_number": order.order_number,
        "old_status": old_status,  # Salvar antes
        "new_status": order.status,
        "tags": [tag],
        "tag_config": tag_config,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    
    await ws_manager.broadcast(update_event, roles=["operator", "admin", "owner"])
    
    return order
```

---

### **FASE 5: Frontend - Mapa Integrado** (4-5h)

#### 5.1. Atualizar `useMapData` hook

**Arquivo:** `frontend/src/hooks/useMapData.js`

```javascript
import { useState, useEffect, useCallback } from 'react'
import { useWebSocket } from './useWebSocket'

export default function useMapData({ 
  autoRefresh = true, 
  refreshInterval = 30000,
  includeOrders = true  // NOVO
}) {
  const [drivers, setDrivers] = useState([])
  const [deliveries, setDeliveries] = useState([])
  const [customerLocations, setCustomerLocations] = useState([])
  const [orders, setOrders] = useState([])  // NOVO
  const [filters, setFilters] = useState({})
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  
  // WebSocket connection
  const { lastMessage } = useWebSocket('/ws/operator')
  
  const fetchMapData = useCallback(async () => {
    try {
      setIsLoading(true)
      const response = await fetch('/api/locations/map-data')
      const data = await response.json()
      
      setDrivers(data.drivers || [])
      setDeliveries(data.deliveries || [])
      setCustomerLocations(data.customer_locations || [])
      setOrders(data.orders || [])  // NOVO
      setFilters(data.filters || {})
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }, [])
  
  // Live updates via WebSocket
  useEffect(() => {
    if (!lastMessage) return
    
    const event = JSON.parse(lastMessage.data)
    
    switch (event.type) {
      case 'order_created':
        // Adicionar novo pedido ao mapa
        setOrders(prev => [...prev, event])
        break
        
      case 'order_status_updated':
        // Atualizar status do pedido existente
        setOrders(prev => prev.map(order => 
          order.order_id === event.order_id 
            ? { ...order, status: event.new_status, tags: event.tags, tag_config: event.tag_config }
            : order
        ))
        break
        
      case 'map_reset':
        // Reset diário - recarregar tudo
        fetchMapData()
        break
        
      case 'driver_location_update':
        // Atualizar localização do driver
        setDrivers(prev => prev.map(d => 
          d.id === event.driver_id 
            ? { ...d, location: event.location }
            : d
        ))
        break
    }
  }, [lastMessage, fetchMapData])
  
  // Auto-refresh
  useEffect(() => {
    fetchMapData()
    
    if (autoRefresh) {
      const interval = setInterval(fetchMapData, refreshInterval)
      return () => clearInterval(interval)
    }
  }, [autoRefresh, refreshInterval, fetchMapData])
  
  return {
    drivers,
    deliveries,
    customerLocations,
    orders,  // NOVO
    filters,
    isLoading,
    error,
    refresh: fetchMapData
  }
}
```

#### 5.2. Atualizar `DeliveryMap.jsx`

**Arquivo:** `frontend/src/components/map/DeliveryMap.jsx`

```jsx
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import MarkerClusterGroup from 'react-leaflet-cluster'
import { useMemo, useState, useEffect } from 'react'
import TagFilterPanel from './TagFilterPanel'
import { createIconByTag } from '../../utils/mapIcons'

export default function DeliveryMap({ 
  drivers, 
  deliveries, 
  customerLocations,
  orders = [],  // NOVO
  filters,
  height = '600px',
  onOrderClick  // NOVO
}) {
  const [activeTags, setActiveTags] = useState(Object.keys(filters.tag_configs || {}))
  const [showOrders, setShowOrders] = useState(true)  // NOVO
  
  // Filtrar dados por tags ativas
  const filteredData = useMemo(() => {
    return {
      drivers: drivers.filter(d => d.tags?.some(tag => activeTags.includes(tag))),
      deliveries: deliveries.filter(d => d.tags?.some(tag => activeTags.includes(tag))),
      customers: customerLocations.filter(c => c.tags?.some(tag => activeTags.includes(tag))),
      orders: showOrders ? orders.filter(o => o.tags?.some(tag => activeTags.includes(tag))) : []
    }
  }, [drivers, deliveries, customerLocations, orders, activeTags, showOrders])
  
  // Auto-center no primeiro pedido novo
  const AutoCenter = () => {
    const map = useMap()
    
    useEffect(() => {
      if (filteredData.orders.length > 0) {
        const firstOrder = filteredData.orders[0]
        if (firstOrder.location) {
          map.setView([firstOrder.location.latitude, firstOrder.location.longitude], 13)
        }
      }
    }, [filteredData.orders, map])
    
    return null
  }
  
  return (
    <div className="relative" style={{ height }}>
      {/* Painel de filtros */}
      <TagFilterPanel
        tagConfigs={filters.tag_configs || {}}
        activeTags={activeTags}
        onToggle={(tag) => {
          setActiveTags(prev => 
            prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag]
          )
        }}
        onReset={() => setActiveTags(Object.keys(filters.tag_configs || {}))}
      />
      
      {/* Toggle de pedidos */}
      <div className="absolute top-4 left-4 z-[1000] bg-white rounded-lg shadow-lg p-3">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={showOrders}
            onChange={(e) => setShowOrders(e.target.checked)}
            className="rounded text-primary-600"
          />
          <span className="text-sm font-medium">Mostrar Pedidos ({orders.length})</span>
        </label>
      </div>
      
      {/* Mapa */}
      <MapContainer
        center={[-25.4284, -49.2733]}
        zoom={12}
        style={{ height: '100%', width: '100%' }}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; OpenStreetMap'
        />
        
        <AutoCenter />
        
        {/* Marcadores de PEDIDOS */}
        <MarkerClusterGroup>
          {filteredData.orders.map(order => (
            order.location && (
              <Marker
                key={`order-${order.id}`}
                position={[order.location.latitude, order.location.longitude]}
                icon={createIconByTag(order.tags[0], order.tag_config)}
                eventHandlers={{
                  click: () => onOrderClick?.(order)
                }}
              >
                <Popup>
                  <OrderPopup order={order} />
                </Popup>
              </Marker>
            )
          ))}
        </MarkerClusterGroup>
        
        {/* Marcadores de ENTREGADORES */}
        {/* ... (código existente) ... */}
        
        {/* Marcadores de ENTREGAS */}
        {/* ... (código existente) ... */}
      </MapContainer>
      
      {/* Resumo */}
      <MapSummary 
        drivers={filteredData.drivers}
        deliveries={filteredData.deliveries}
        orders={filteredData.orders}
      />
    </div>
  )
}

// Componente de Popup do Pedido
function OrderPopup({ order }) {
  const statusLabels = {
    pending: 'Aguardando Pagamento',
    paid: 'Pago',
    preparing: 'Em Preparação',
    dispatched: 'Em Rota',
    delivered: 'Concluído',
    cancelled: 'Cancelado'
  }
  
  return (
    <div className="p-2 min-w-[200px]">
      <h3 className="font-semibold text-lg">Pedido #{order.order_number}</h3>
      <p className="text-sm text-gray-600">{order.customer_name}</p>
      <p className="text-xs text-gray-500">{order.customer_phone}</p>
      
      <div className="mt-2 space-y-1">
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-600">Status:</span>
          <span 
            className="px-2 py-0.5 rounded text-xs font-medium text-white"
            style={{ backgroundColor: order.tag_config?.color }}
          >
            {statusLabels[order.status]}
          </span>
        </div>
        
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-600">Valor:</span>
          <span className="text-sm font-semibold text-green-600">
            R$ {order.total_amount.toFixed(2)}
          </span>
        </div>
        
        <div className="text-xs text-gray-500 mt-2">
          <p>{order.address}</p>
          <p>{order.bairro}</p>
        </div>
      </div>
    </div>
  )
}

// Componente de Resumo
function MapSummary({ drivers, deliveries, orders }) {
  return (
    <div className="absolute bottom-4 right-4 z-[1000] bg-white rounded-lg shadow-lg p-4">
      <div className="grid grid-cols-3 gap-3 text-center">
        <div>
          <p className="text-2xl font-bold text-blue-600">{drivers.length}</p>
          <p className="text-xs text-gray-500">Entregadores</p>
        </div>
        <div>
          <p className="text-2xl font-bold text-purple-600">{deliveries.length}</p>
          <p className="text-xs text-gray-500">Entregas</p>
        </div>
        <div>
          <p className="text-2xl font-bold text-green-600">{orders.length}</p>
          <p className="text-xs text-gray-500">Pedidos Hoje</p>
        </div>
      </div>
    </div>
  )
}
```

---

## 🎨 Tags Visuais para Pedidos

### Tags de Status de Pedido:

| Status       | Tag                      | Cor       | Ícone         | Quando Exibir |
|--------------|--------------------------|-----------|---------------|---------------|
| `pending`    | `order_pending_payment`  | #FBBF24 (Amarelo) | 💰 dollar-sign | Aguardando pagamento |
| `paid`       | `order_confirmed`        | #10B981 (Verde) | ✓ check-circle | Pagamento confirmado |
| `preparing`  | `order_preparing`        | #F97316 (Laranja) | 🍴 shopping-bag | Em preparação |
| `dispatched` | `order_in_transit`       | #8B5CF6 (Roxo) | 🚚 truck | Em rota (saiu para entrega) |
| `delivered`  | `order_delivered`        | #22C55E (Verde Claro) | ✅ check | Entregue com sucesso |
| `cancelled`  | `order_cancelled`        | #DC2626 (Vermelho) | ❌ x-circle | Cancelado |

**Implementar em:** `backend/app/models/location_tag.py`

```python
# Adicionar ao LocationTag enum:
ORDER_PENDING_PAYMENT = "order_pending_payment"
ORDER_CONFIRMED = "order_confirmed"
ORDER_PREPARING = "order_preparing"
ORDER_IN_TRANSIT = "order_in_transit"
ORDER_DELIVERED = "order_delivered"
ORDER_CANCELLED = "order_cancelled"

# Adicionar ao TAG_CONFIG:
LocationTag.ORDER_IN_TRANSIT: {
    "color": "#8B5CF6",
    "icon": "truck",
    "label": "Em Rota",
    "category": "orders"
},
# ... (adicionar todas as tags de pedido)

# Atualizar get_tag_for_order():
def get_tag_for_order(order) -> str:
    status = getattr(order, 'status', 'pending').lower()
    
    if status == 'pending':
        return LocationTag.ORDER_PENDING_PAYMENT
    elif status == 'paid':
        return LocationTag.ORDER_CONFIRMED
    elif status == 'preparing':
        return LocationTag.ORDER_PREPARING
    elif status == 'dispatched':
        return LocationTag.ORDER_IN_TRANSIT
    elif status == 'delivered':
        return LocationTag.ORDER_DELIVERED
    elif status == 'cancelled':
        return LocationTag.ORDER_CANCELLED
    else:
        return LocationTag.ORDER_CONFIRMED
```

---

## 📊 Fluxo Completo (End-to-End)

```
1. CLIENTE FAZ PEDIDO VIA WHATSAPP
   ↓
2. FLOW ENGINE V2 CAPTURA:
   - Nome, telefone, endereço, CEP
   - Produtos e quantidades
   - Forma de pagamento
   ↓
3. API CREATE_ORDER É CHAMADA:
   - Valida dados
   - Geocodifica endereço via GeocodingService
   - Salva pedido com coordenadas (delivery_address.location)
   - Emite WebSocket "order_created"
   ↓
4. WEBSOCKET BROADCAST:
   - Envia para: operadores + admin
   - Payload: order_id, location, tags, tag_config
   ↓
5. FRONTEND (OPERADOR DASHBOARD):
   - useMapData() recebe evento WebSocket
   - Adiciona marcador no mapa em tempo real
   - Marcador colorido por status (tag)
   ↓
6. OPERADOR VISUALIZA:
   - Pedido aparece instantaneamente no mapa
   - Cor: Amarelo (Pendente Pagamento)
   - Popup: Detalhes do pedido
   ↓
7. STATUS MUDA (ex: PAID → DISPATCHED):
   - API update_order_status()
   - Emite WebSocket "order_status_updated"
   - Frontend atualiza cor do marcador (Amarelo → Roxo)
   ↓
8. ENTREGA CONCLUÍDA (DELIVERED):
   - Marcador fica verde
   - Mantém no mapa até o reset diário
   ↓
9. RESET DIÁRIO (00:00):
   - Scheduler executa daily_reset_job()
   - Emite WebSocket "map_reset"
   - Frontend limpa pedidos antigos
   - Novo dia começa com mapa limpo
```

---

## ✅ Checklist de Implementação

### Backend
- [ ] Modificar `create_order()` para geocodificar automaticamente
- [ ] Atualizar `emit_order_created_event()` com tags
- [ ] Criar endpoint `/api/orders/map-data`
- [ ] Integrar pedidos no endpoint `/api/locations/map-data`
- [ ] Adicionar tags de pedidos em `location_tag.py`
- [ ] Atualizar `get_tag_for_order()` com novos status
- [ ] Criar `DailyResetService`
- [ ] Configurar APScheduler no `main.py`
- [ ] Adicionar eventos WebSocket de pedidos
- [ ] Atualizar `update_order_status()` com broadcast
- [ ] Testar geocoding automático
- [ ] Testar WebSocket live updates

### Frontend
- [ ] Atualizar `useMapData` hook com orders
- [ ] Adicionar listener WebSocket para `order_created`
- [ ] Adicionar listener WebSocket para `order_status_updated`
- [ ] Adicionar listener WebSocket para `map_reset`
- [ ] Atualizar `DeliveryMap.jsx` com marcadores de pedidos
- [ ] Criar componente `OrderPopup`
- [ ] Adicionar toggle "Mostrar Pedidos"
- [ ] Implementar auto-center no primeiro pedido
- [ ] Atualizar `MapSummary` com contador de pedidos
- [ ] Testar filtros de tags com pedidos
- [ ] Testar atualização em tempo real

### DevOps
- [ ] Adicionar `apscheduler` ao `requirements.txt`
- [ ] Reiniciar backend após mudanças
- [ ] Configurar timezone do servidor (UTC)
- [ ] Testar scheduler às 00:00 (ou usar trigger manual)
- [ ] Monitorar logs de geocoding
- [ ] Monitorar logs de reset diário

---

## 🚀 Estimativas de Tempo

| Fase | Descrição | Tempo Estimado |
|------|-----------|----------------|
| 1 | Geocoding Automático | 2-3h |
| 2 | API de Pedidos para Mapa | 1-2h |
| 3 | Sistema de Reset Diário | 1h |
| 4 | WebSocket Live Updates | 1-2h |
| 5 | Frontend - Mapa Integrado | 4-5h |
| **TOTAL** | **Implementação Completa** | **9-13 horas** |

---

## 📈 Melhorias Futuras

### Fase 2.0
1. **Filtro por Período**: Visualizar pedidos de dias anteriores
2. **Heatmap de Pedidos**: Densidade de pedidos por região
3. **Rotas Otimizadas**: Sugerir melhor sequência de entregas
4. **Estatísticas em Tempo Real**: Ticket médio, tempo médio de entrega
5. **Notificações Push**: Alertar operador sobre novos pedidos

### Fase 3.0
1. **Machine Learning**: Prever tempo de entrega por região
2. **Alocação Automática**: Sugerir melhor entregador por proximidade
3. **Replay de Entregas**: Visualizar rotas históricas
4. **Integração Google Maps**: Rotas em tempo real
5. **Dashboard Analytics**: Gráficos de performance diária/semanal

---

## 🎉 Resultado Final

Após implementação completa, o **Mapa do Operador** terá:

✅ **Pedidos em Tempo Real**: Aparecem instantaneamente ao serem criados  
✅ **Geocoding Automático**: Endereços convertidos em coordenadas  
✅ **Tags Visuais por Status**: Cores diferenciadas (Pendente/Em Rota/Concluído)  
✅ **Live Updates**: WebSocket atualiza marcadores sem refresh  
✅ **Reset Diário**: Mapa limpo automaticamente às 00:00  
✅ **Filtros Interativos**: Mostrar/ocultar por status e categoria  
✅ **Popups Informativos**: Detalhes completos do pedido ao clicar  
✅ **Performance Otimizada**: Cache em 3 camadas + clustering de marcadores

---

## 📝 Considerações Importantes

### Privacidade (LGPD)
- ⚠️ Coordenadas de clientes são dados sensíveis
- ✅ Armazenar apenas em `Order.delivery_address` (necessário para entrega)
- ✅ Não compartilhar coordenadas fora do sistema
- ✅ Limpar pedidos antigos após 90 dias (conforme política de retenção)

### Performance
- ✅ Usar clustering de marcadores para muitos pedidos
- ✅ Limitar query a pedidos do dia atual (ou últimos 7 dias)
- ✅ Cache Redis para coordenadas geocodificadas
- ✅ Índices no banco: `orders(created_at, status)`

### Segurança
- ✅ Apenas operadores/admin podem ver mapa completo
- ✅ WebSocket autenticado por token
- ✅ Rate limiting na API de geocoding (evitar abuso)

---

**Pronto para implementar?** 🚀

Este planejamento detalha **TUDO** necessário para colocar os pedidos no mapa em tempo real com geocoding automático e reset diário!
