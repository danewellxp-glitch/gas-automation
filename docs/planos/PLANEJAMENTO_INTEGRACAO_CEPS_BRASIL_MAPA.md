# 📍 Planejamento: Integração API CEPs Brasil + Sistema de Tags no Mapa

**Data:** 13/02/2026  
**Objetivo:** Melhorar o mapa do painel do operador com geocoding automático via API CEPs Brasil e implementar sistema de tags para categorização e filtros visuais

---

## 🎯 Visão Geral

### Problema Atual
- Endereços sem coordenadas geográficas (latitude/longitude)
- Impossível exibir clientes, entregas e pedidos no mapa
- Falta de categorização visual (tags) para diferentes entidades
- Dificuldade em filtrar e identificar tipos de localização

### Solução Proposta
1. **Geocoding Automático**: Usar API CEPs Brasil para converter CEPs em coordenadas
2. **Sistema de Tags**: Categorizar visualmente entidades no mapa (clientes, entregadores, entregas, pedidos)
3. **Filtros Interativos**: Permitir mostrar/ocultar categorias específicas
4. **Enriquecimento de Dados**: Adicionar informações de bairro, cidade, estado automaticamente

---

## 📊 APIs CEPs Brasil Disponíveis

### 1. **ViaCEP** (Recomendado)
- ✅ **Gratuito** e sem limite de requisições
- ✅ **Sem autenticação** necessária
- ✅ Retorna: logradouro, bairro, cidade, estado, DDD
- ❌ Não retorna coordenadas geográficas

**Endpoint:**
```
GET https://viacep.com.br/ws/{cep}/json/
```

**Resposta:**
```json
{
  "cep": "01310-100",
  "logradouro": "Avenida Paulista",
  "bairro": "Bela Vista",
  "localidade": "São Paulo",
  "uf": "SP"
}
```

### 2. **BrazilCEP** (Biblioteca Python)
- ✅ Integração Python simplificada
- ✅ Suporta múltiplas APIs (ViaCEP, OpenCEP, ApiCEP)
- ✅ Async/await nativo
- ❌ Não retorna coordenadas geográficas

**Instalação:**
```bash
pip install brazilcep
```

**Uso:**
```python
from brazilcep import get_address_from_cep, WebServiceException

try:
    address = await get_address_from_cep('01310-100')
    print(address)
except WebServiceException as e:
    print(f"Erro: {e}")
```

### 3. **CEPAberto** (Geocoding com Coordenadas)
- ✅ **RETORNA LATITUDE/LONGITUDE** ⭐
- ⚠️ Requer token de acesso (gratuito com limite)
- ✅ Dados completos: endereço + coordenadas

**Endpoint:**
```
GET https://www.cepaberto.com/api/v3/cep?cep={cep}
Header: Authorization: Token token=YOUR_TOKEN
```

**Resposta:**
```json
{
  "cep": "01310100",
  "logradouro": "Avenida Paulista",
  "bairro": "Bela Vista",
  "cidade": {"nome": "São Paulo"},
  "estado": {"sigla": "SP"},
  "latitude": "-23.561414",
  "longitude": "-46.656139"
}
```

### 4. **Nominatim (OpenStreetMap)** - Fallback
- ✅ Gratuito
- ✅ Geocoding de endereços completos
- ⚠️ Limite de 1 req/segundo
- ✅ Não requer autenticação

**Endpoint:**
```
GET https://nominatim.openstreetmap.org/search?format=json&q={endereco_completo}&country=brazil
```

---

## 🏗️ Arquitetura da Solução

### Camada 1: Backend - Serviço de Geocoding

```
backend/app/services/geocoding_service.py
├── GeocodingService
│   ├── geocode_by_cep(cep: str) -> dict
│   ├── geocode_by_address(address: dict) -> dict
│   ├── _try_cepaberto(cep: str)
│   ├── _try_viacep(cep: str)
│   └── _try_nominatim(address_str: str)
```

**Estratégia de Fallback:**
1. **CEPAberto** (se token disponível) → Retorna coordenadas + endereço
2. **ViaCEP** → Retorna apenas endereço
3. **Nominatim** → Geocoding do endereço completo para obter coordenadas
4. **Cache Redis** → Armazenar resultados por 30 dias

### Camada 2: Backend - Sistema de Tags

```
backend/app/models/location_tag.py
├── LocationTag (Enum)
│   ├── CUSTOMER_NEW = "customer_new"
│   ├── CUSTOMER_RECURRING = "customer_recurring"
│   ├── DRIVER_AVAILABLE = "driver_available"
│   ├── DRIVER_BUSY = "driver_busy"
│   ├── DRIVER_OFFLINE = "driver_offline"
│   ├── DELIVERY_PENDING = "delivery_pending"
│   ├── DELIVERY_IN_TRANSIT = "delivery_in_transit"
│   ├── DELIVERY_ARRIVED = "delivery_arrived"
│   ├── ORDER_PENDING_PAYMENT = "order_pending_payment"
│   └── ORDER_CONFIRMED = "order_confirmed"
```

**Cores e Ícones por Tag:**
```python
TAG_CONFIG = {
    "customer_new": {
        "color": "#3B82F6",  # Azul
        "icon": "user-plus",
        "label": "Cliente Novo"
    },
    "customer_recurring": {
        "color": "#10B981",  # Verde
        "icon": "user-check",
        "label": "Cliente Recorrente"
    },
    "driver_available": {
        "color": "#22C55E",  # Verde claro
        "icon": "truck",
        "label": "Entregador Disponível"
    },
    "driver_busy": {
        "color": "#F59E0B",  # Laranja
        "icon": "truck-loading",
        "label": "Entregador em Entrega"
    },
    "delivery_in_transit": {
        "color": "#8B5CF6",  # Roxo
        "icon": "package",
        "label": "Em Trânsito"
    }
}
```

### Camada 3: Banco de Dados - Schema Updates

#### 3.1. Adicionar coordenadas aos modelos existentes

**Tabela `customers`:**
```sql
ALTER TABLE customers ADD COLUMN IF NOT EXISTS location JSONB;
-- Estrutura: {"latitude": -23.561414, "longitude": -46.656139, "accuracy": "cep", "updated_at": "2026-02-13T..."}

CREATE INDEX IF NOT EXISTS ix_customers_location ON customers USING GIN(location);
```

**Tabela `orders`:**
```sql
-- delivery_address já existe como JSONB, adicionar coordenadas nele
-- Estrutura: {...endereço existente..., "location": {"latitude": ..., "longitude": ...}}
```

**Tabela `drivers`:**
```sql
-- current_location já existe como JSON
-- Mantém estrutura atual
```

#### 3.2. Criar tabela de cache de geocoding

```sql
CREATE TABLE IF NOT EXISTS geocoding_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cep VARCHAR(10) UNIQUE NOT NULL,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    logradouro VARCHAR(255),
    bairro VARCHAR(100),
    cidade VARCHAR(100),
    estado VARCHAR(2),
    source VARCHAR(50), -- 'cepaberto', 'viacep', 'nominatim'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX ix_geocoding_cache_cep ON geocoding_cache(cep);
CREATE INDEX ix_geocoding_cache_location ON geocoding_cache(latitude, longitude);
```

### Camada 4: API - Endpoints Aprimorados

#### 4.1. Atualizar `/api/locations/map-data`

**Resposta Aprimorada:**
```json
{
  "drivers": [
    {
      "id": "uuid",
      "name": "João Silva",
      "location": {"latitude": -25.4, "longitude": -49.2},
      "tags": ["driver_available"],
      "tag_config": {
        "color": "#22C55E",
        "icon": "truck",
        "label": "Disponível"
      }
    }
  ],
  "deliveries": [
    {
      "id": "uuid",
      "order_id": "uuid",
      "customer_name": "Maria Santos",
      "location": {"latitude": -25.5, "longitude": -49.3},
      "address": "Rua X, 123 - Bairro Y",
      "tags": ["delivery_in_transit", "priority_high"],
      "tag_config": {...}
    }
  ],
  "customer_locations": [
    {
      "phone": "5541999999999",
      "name": "Pedro Costa",
      "location": {"latitude": -25.6, "longitude": -49.4},
      "tags": ["customer_recurring"],
      "order_count": 15,
      "last_order_date": "2026-02-10"
    }
  ],
  "filters": {
    "available_tags": ["driver_available", "customer_new", ...],
    "tag_configs": {...}
  }
}
```

#### 4.2. Novo endpoint `/api/locations/geocode`

```python
@router.post("/geocode")
async def geocode_address(
    cep: Optional[str] = None,
    address: Optional[dict] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Geocodifica um CEP ou endereço completo.
    Retorna coordenadas + endereço enriquecido.
    """
    service = GeocodingService(db)
    
    if cep:
        result = await service.geocode_by_cep(cep)
    elif address:
        result = await service.geocode_by_address(address)
    else:
        raise HTTPException(400, "CEP ou endereço necessário")
    
    return result
```

#### 4.3. Novo endpoint `/api/locations/tags`

```python
@router.get("/tags")
async def get_available_tags():
    """
    Retorna todas as tags disponíveis com configurações.
    """
    return {
        "tags": TAG_CONFIG,
        "categories": {
            "customers": ["customer_new", "customer_recurring"],
            "drivers": ["driver_available", "driver_busy", "driver_offline"],
            "deliveries": ["delivery_pending", "delivery_in_transit", "delivery_arrived"]
        }
    }
```

### Camada 5: Frontend - Componentes React

#### 5.1. Atualizar `DeliveryMap.jsx`

**Novos recursos:**
- Marcadores coloridos por tag
- Clustering de marcadores próximos
- Popups com informações detalhadas
- Filtros interativos por tag

```jsx
// Estrutura básica
const DeliveryMap = ({ drivers, deliveries, customerLocations, filters }) => {
  const [activeFilters, setActiveFilters] = useState(['all'])
  const [mapCenter, setMapCenter] = useState([-25.4284, -49.2733]) // Curitiba
  
  // Filtrar marcadores baseado em tags
  const filteredMarkers = useMemo(() => {
    return filterByTags(allMarkers, activeFilters)
  }, [allMarkers, activeFilters])
  
  return (
    <div className="relative">
      {/* Painel de filtros */}
      <TagFilterPanel 
        tags={availableTags}
        active={activeFilters}
        onChange={setActiveFilters}
      />
      
      {/* Mapa com marcadores */}
      <MapContainer center={mapCenter} zoom={12}>
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        
        {/* Marcadores de entregadores */}
        {filteredMarkers.drivers.map(driver => (
          <Marker 
            key={driver.id}
            position={[driver.location.latitude, driver.location.longitude]}
            icon={createIconByTag(driver.tags[0])}
          >
            <Popup>
              <DriverPopup driver={driver} />
            </Popup>
          </Marker>
        ))}
        
        {/* Marcadores de entregas */}
        {filteredMarkers.deliveries.map(delivery => (
          <Marker 
            key={delivery.id}
            position={[delivery.location.latitude, delivery.location.longitude]}
            icon={createIconByTag(delivery.tags[0])}
          >
            <Popup>
              <DeliveryPopup delivery={delivery} />
            </Popup>
          </Marker>
        ))}
        
        {/* Heat map de clientes */}
        <HeatmapLayer 
          points={customerLocations}
          radius={20}
          blur={15}
        />
      </MapContainer>
    </div>
  )
}
```

#### 5.2. Criar `TagFilterPanel.jsx`

```jsx
const TagFilterPanel = ({ tags, active, onChange }) => {
  return (
    <div className="absolute top-4 right-4 z-1000 bg-white rounded-lg shadow-lg p-4 w-64">
      <h3 className="font-semibold mb-3">Filtros do Mapa</h3>
      
      <div className="space-y-2">
        {Object.entries(tags).map(([key, config]) => (
          <label key={key} className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={active.includes(key)}
              onChange={(e) => {
                if (e.target.checked) {
                  onChange([...active, key])
                } else {
                  onChange(active.filter(t => t !== key))
                }
              }}
              className="rounded text-primary-600"
            />
            <span 
              className="w-3 h-3 rounded-full" 
              style={{ backgroundColor: config.color }}
            />
            <span className="text-sm">{config.label}</span>
          </label>
        ))}
      </div>
    </div>
  )
}
```

#### 5.3. Criar `MarkerIcons.jsx`

```jsx
import L from 'leaflet'

export const createIconByTag = (tag, tagConfig) => {
  const color = tagConfig?.color || '#3B82F6'
  
  return L.divIcon({
    className: 'custom-marker',
    html: `
      <div style="
        background-color: ${color};
        width: 32px;
        height: 32px;
        border-radius: 50% 50% 50% 0;
        border: 3px solid white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        transform: rotate(-45deg);
        display: flex;
        align-items: center;
        justify-content: center;
      ">
        <i class="fas fa-${tagConfig?.icon || 'map-pin'}" 
           style="transform: rotate(45deg); color: white; font-size: 14px;">
        </i>
      </div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 32],
    popupAnchor: [0, -32]
  })
}
```

---

## 🔧 Implementação Passo a Passo

### **Fase 1: Backend - Serviço de Geocoding** (2-3 horas)

#### 1.1. Instalar dependências
```bash
cd backend
pip install brazilcep httpx
```

#### 1.2. Criar arquivo de configuração
```python
# backend/app/config.py
class Settings:
    # ... configurações existentes ...
    
    # Geocoding
    CEPABERTO_TOKEN: Optional[str] = os.getenv("CEPABERTO_TOKEN")
    GEOCODING_CACHE_TTL: int = 30 * 24 * 60 * 60  # 30 dias
    GEOCODING_RATE_LIMIT: int = 10  # req/segundo
```

#### 1.3. Criar serviço de geocoding
```python
# backend/app/services/geocoding_service.py

import httpx
from typing import Optional, Dict
from brazilcep import get_address_from_cep, WebServiceException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import redis_manager
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class GeocodingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.redis = redis_manager
        
    async def geocode_by_cep(self, cep: str) -> Optional[Dict]:
        """
        Geocodifica um CEP usando estratégia de fallback.
        
        Returns:
            {
                "cep": "80010-000",
                "logradouro": "Rua XV de Novembro",
                "bairro": "Centro",
                "cidade": "Curitiba",
                "estado": "PR",
                "latitude": -25.428954,
                "longitude": -49.273386,
                "source": "cepaberto",
                "accuracy": "street"
            }
        """
        # Limpar CEP
        cep_clean = ''.join(filter(str.isdigit, cep))
        
        # 1. Verificar cache Redis
        cache_key = f"geocoding:cep:{cep_clean}"
        cached = await self.redis.get(cache_key)
        if cached:
            logger.info(f"Geocoding cache HIT: {cep_clean}")
            return cached
        
        # 2. Verificar cache DB
        db_cached = await self._get_from_db_cache(cep_clean)
        if db_cached:
            await self.redis.set(cache_key, db_cached, ttl=settings.GEOCODING_CACHE_TTL)
            return db_cached
        
        # 3. Tentar CEPAberto (com coordenadas)
        if settings.CEPABERTO_TOKEN:
            result = await self._try_cepaberto(cep_clean)
            if result:
                await self._save_to_cache(cep_clean, result)
                return result
        
        # 4. Tentar ViaCEP (sem coordenadas)
        viacep_result = await self._try_viacep(cep_clean)
        if viacep_result:
            # 5. Tentar obter coordenadas via Nominatim
            address_str = f"{viacep_result['logradouro']}, {viacep_result['bairro']}, {viacep_result['localidade']}, {viacep_result['uf']}, Brasil"
            coords = await self._try_nominatim(address_str)
            
            if coords:
                result = {
                    **viacep_result,
                    "latitude": coords["latitude"],
                    "longitude": coords["longitude"],
                    "source": "viacep+nominatim",
                    "accuracy": "neighborhood"
                }
            else:
                result = {
                    **viacep_result,
                    "latitude": None,
                    "longitude": None,
                    "source": "viacep",
                    "accuracy": "cep_only"
                }
            
            await self._save_to_cache(cep_clean, result)
            return result
        
        logger.warning(f"Geocoding falhou para CEP: {cep_clean}")
        return None
    
    async def _try_cepaberto(self, cep: str) -> Optional[Dict]:
        """Tenta geocodificar via CEPAberto (retorna coordenadas)."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"https://www.cepaberto.com/api/v3/cep?cep={cep}",
                    headers={"Authorization": f"Token token={settings.CEPABERTO_TOKEN}"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "cep": data["cep"],
                        "logradouro": data.get("logradouro"),
                        "bairro": data.get("bairro"),
                        "cidade": data["cidade"]["nome"],
                        "estado": data["estado"]["sigla"],
                        "latitude": float(data["latitude"]),
                        "longitude": float(data["longitude"]),
                        "source": "cepaberto",
                        "accuracy": "street"
                    }
        except Exception as e:
            logger.warning(f"CEPAberto falhou: {e}")
        
        return None
    
    async def _try_viacep(self, cep: str) -> Optional[Dict]:
        """Tenta buscar endereço via ViaCEP (sem coordenadas)."""
        try:
            address = await get_address_from_cep(cep)
            return {
                "cep": address["cep"],
                "logradouro": address.get("logradouro"),
                "bairro": address.get("bairro"),
                "cidade": address.get("localidade"),
                "estado": address.get("uf"),
            }
        except WebServiceException as e:
            logger.warning(f"ViaCEP falhou: {e}")
        
        return None
    
    async def _try_nominatim(self, address_str: str) -> Optional[Dict]:
        """Tenta obter coordenadas via Nominatim (OpenStreetMap)."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={
                        "q": address_str,
                        "format": "json",
                        "limit": 1,
                        "countrycodes": "br"
                    },
                    headers={"User-Agent": "GasAutomation/1.0"}
                )
                
                if response.status_code == 200:
                    results = response.json()
                    if results:
                        return {
                            "latitude": float(results[0]["lat"]),
                            "longitude": float(results[0]["lon"])
                        }
        except Exception as e:
            logger.warning(f"Nominatim falhou: {e}")
        
        return None
    
    async def _get_from_db_cache(self, cep: str) -> Optional[Dict]:
        """Busca no cache do banco de dados."""
        from app.models.geocoding_cache import GeocodingCache
        from sqlalchemy import select
        
        result = await self.db.execute(
            select(GeocodingCache).where(GeocodingCache.cep == cep)
        )
        cache = result.scalar_one_or_none()
        
        if cache:
            return {
                "cep": cache.cep,
                "logradouro": cache.logradouro,
                "bairro": cache.bairro,
                "cidade": cache.cidade,
                "estado": cache.estado,
                "latitude": float(cache.latitude) if cache.latitude else None,
                "longitude": float(cache.longitude) if cache.longitude else None,
                "source": cache.source,
                "accuracy": "cached"
            }
        
        return None
    
    async def _save_to_cache(self, cep: str, data: Dict):
        """Salva resultado no cache (Redis + DB)."""
        from app.models.geocoding_cache import GeocodingCache
        
        # Redis
        cache_key = f"geocoding:cep:{cep}"
        await self.redis.set(cache_key, data, ttl=settings.GEOCODING_CACHE_TTL)
        
        # DB
        cache_obj = GeocodingCache(
            cep=cep,
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            logradouro=data.get("logradouro"),
            bairro=data.get("bairro"),
            cidade=data.get("cidade"),
            estado=data.get("estado"),
            source=data.get("source")
        )
        
        self.db.add(cache_obj)
        await self.db.commit()
```

#### 1.4. Criar modelo de cache
```python
# backend/app/models/geocoding_cache.py

from sqlalchemy import Index, String, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import BaseModel

class GeocodingCache(BaseModel):
    __tablename__ = "geocoding_cache"
    
    cep: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    latitude: Mapped[float] = mapped_column(Numeric(10, 8), nullable=True)
    longitude: Mapped[float] = mapped_column(Numeric(11, 8), nullable=True)
    logradouro: Mapped[str] = mapped_column(String(255), nullable=True)
    bairro: Mapped[str] = mapped_column(String(100), nullable=True)
    cidade: Mapped[str] = mapped_column(String(100), nullable=True)
    estado: Mapped[str] = mapped_column(String(2), nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=True)
    
    __table_args__ = (
        Index("ix_geocoding_cache_location", "latitude", "longitude"),
    )
```

---

### **Fase 2: Backend - Sistema de Tags** (2 horas)

#### 2.1. Criar enums de tags
```python
# backend/app/models/location_tag.py

from enum import Enum

class LocationTag(str, Enum):
    # Clientes
    CUSTOMER_NEW = "customer_new"
    CUSTOMER_RECURRING = "customer_recurring"
    CUSTOMER_VIP = "customer_vip"
    
    # Entregadores
    DRIVER_AVAILABLE = "driver_available"
    DRIVER_BUSY = "driver_busy"
    DRIVER_OFFLINE = "driver_offline"
    DRIVER_ON_BREAK = "driver_on_break"
    
    # Entregas
    DELIVERY_PENDING = "delivery_pending"
    DELIVERY_IN_TRANSIT = "delivery_in_transit"
    DELIVERY_ARRIVED = "delivery_arrived"
    DELIVERY_DELAYED = "delivery_delayed"
    
    # Pedidos
    ORDER_PENDING_PAYMENT = "order_pending_payment"
    ORDER_CONFIRMED = "order_confirmed"
    ORDER_PREPARING = "order_preparing"

TAG_CONFIG = {
    # Clientes
    LocationTag.CUSTOMER_NEW: {
        "color": "#3B82F6",
        "icon": "user-plus",
        "label": "Cliente Novo",
        "category": "customers"
    },
    LocationTag.CUSTOMER_RECURRING: {
        "color": "#10B981",
        "icon": "user-check",
        "label": "Cliente Recorrente",
        "category": "customers"
    },
    LocationTag.CUSTOMER_VIP: {
        "color": "#F59E0B",
        "icon": "crown",
        "label": "Cliente VIP",
        "category": "customers"
    },
    
    # Entregadores
    LocationTag.DRIVER_AVAILABLE: {
        "color": "#22C55E",
        "icon": "truck",
        "label": "Disponível",
        "category": "drivers"
    },
    LocationTag.DRIVER_BUSY: {
        "color": "#EF4444",
        "icon": "truck-loading",
        "label": "Em Entrega",
        "category": "drivers"
    },
    LocationTag.DRIVER_OFFLINE: {
        "color": "#6B7280",
        "icon": "truck",
        "label": "Offline",
        "category": "drivers"
    },
    
    # Entregas
    LocationTag.DELIVERY_IN_TRANSIT: {
        "color": "#8B5CF6",
        "icon": "package",
        "label": "Em Trânsito",
        "category": "deliveries"
    },
    LocationTag.DELIVERY_ARRIVED: {
        "color": "#06B6D4",
        "icon": "map-pin",
        "label": "Chegou",
        "category": "deliveries"
    },
    LocationTag.DELIVERY_DELAYED: {
        "color": "#DC2626",
        "icon": "clock",
        "label": "Atrasada",
        "category": "deliveries"
    },
}

def get_tag_for_driver(driver) -> str:
    """Determina tag baseada no status do driver."""
    if driver.status == "available":
        return LocationTag.DRIVER_AVAILABLE
    elif driver.status == "busy":
        return LocationTag.DRIVER_BUSY
    else:
        return LocationTag.DRIVER_OFFLINE

def get_tag_for_customer(customer, order_count: int) -> str:
    """Determina tag baseada no histórico do cliente."""
    if order_count == 0:
        return LocationTag.CUSTOMER_NEW
    elif order_count >= 10:
        return LocationTag.CUSTOMER_VIP
    else:
        return LocationTag.CUSTOMER_RECURRING

def get_tag_for_delivery(delivery) -> str:
    """Determina tag baseada no status da entrega."""
    if delivery.status == "in_transit":
        return LocationTag.DELIVERY_IN_TRANSIT
    elif delivery.status == "arrived":
        return LocationTag.DELIVERY_ARRIVED
    else:
        return LocationTag.DELIVERY_PENDING
```

#### 2.2. Atualizar `/api/locations/map-data`
```python
# backend/app/api/locations.py (modificações)

from app.models.location_tag import get_tag_for_driver, get_tag_for_customer, get_tag_for_delivery, TAG_CONFIG
from app.services.geocoding_service import GeocodingService

@router.get("/map-data", response_model=MapDataResponse)
async def get_map_data(
    db: AsyncSession = Depends(get_db),
    include_offline_drivers: bool = Query(False),
    hours_back: int = Query(24),
):
    try:
        geocoding_service = GeocodingService(db)
        
        # ... código existente de busca de drivers, deliveries, customers ...
        
        # Enriquecer drivers com tags
        for d in drivers:
            tag = get_tag_for_driver(d)
            d.tags = [tag]
            d.tag_config = TAG_CONFIG[tag]
        
        # Enriquecer deliveries com tags e geocoding
        for delivery in deliveries:
            # Tag
            tag = get_tag_for_delivery(delivery)
            delivery.tags = [tag]
            delivery.tag_config = TAG_CONFIG[tag]
            
            # Geocoding se não tiver coordenadas
            if not delivery.location and delivery.address:
                cep = extract_cep_from_address(delivery.address)
                if cep:
                    geo_data = await geocoding_service.geocode_by_cep(cep)
                    if geo_data and geo_data.get("latitude"):
                        delivery.location = {
                            "latitude": geo_data["latitude"],
                            "longitude": geo_data["longitude"]
                        }
        
        # Enriquecer customer_locations com tags
        for customer in customer_locations:
            # Contar pedidos do cliente
            order_count_query = select(func.count(Order.id)).where(
                Order.customer_id == customer.customer_id
            )
            order_count_result = await db.execute(order_count_query)
            order_count = order_count_result.scalar() or 0
            
            tag = get_tag_for_customer(customer, order_count)
            customer.tags = [tag]
            customer.tag_config = TAG_CONFIG[tag]
            customer.order_count = order_count
        
        return MapDataResponse(
            drivers=drivers,
            deliveries=deliveries,
            customer_locations=customer_locations,
            filters={
                "available_tags": list(TAG_CONFIG.keys()),
                "tag_configs": TAG_CONFIG
            },
            updated_at=datetime.now(timezone.utc)
        )
    
    except Exception as e:
        logger.error(f"Erro ao buscar dados do mapa: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

---

### **Fase 3: Frontend - Componentes de Mapa** (3-4 horas)

#### 3.1. Instalar dependências
```bash
cd frontend
npm install react-leaflet leaflet leaflet.markercluster
```

#### 3.2. Criar `TagFilterPanel.jsx`
```jsx
// frontend/src/components/map/TagFilterPanel.jsx

import { useState, useMemo } from 'react'
import { Filter, X } from 'lucide-react'

export default function TagFilterPanel({ tagConfigs, activeTags, onToggle, onReset }) {
  const [isOpen, setIsOpen] = useState(true)
  
  // Agrupar tags por categoria
  const tagsByCategory = useMemo(() => {
    const grouped = {}
    Object.entries(tagConfigs).forEach(([key, config]) => {
      const category = config.category || 'other'
      if (!grouped[category]) grouped[category] = []
      grouped[category].push({ key, ...config })
    })
    return grouped
  }, [tagConfigs])
  
  const categoryLabels = {
    customers: '👥 Clientes',
    drivers: '🚚 Entregadores',
    deliveries: '📦 Entregas'
  }
  
  return (
    <div className="absolute top-4 right-4 z-[1000] bg-white rounded-lg shadow-xl w-72">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5 text-primary-600" />
          <h3 className="font-semibold text-gray-900">Filtros do Mapa</h3>
        </div>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="text-gray-400 hover:text-gray-600"
        >
          {isOpen ? <X className="w-5 h-5" /> : <Filter className="w-5 h-5" />}
        </button>
      </div>
      
      {/* Body */}
      {isOpen && (
        <div className="p-4 space-y-4 max-h-96 overflow-y-auto">
          {Object.entries(tagsByCategory).map(([category, tags]) => (
            <div key={category}>
              <h4 className="text-sm font-medium text-gray-700 mb-2">
                {categoryLabels[category] || category}
              </h4>
              <div className="space-y-1.5">
                {tags.map(tag => (
                  <label key={tag.key} className="flex items-center gap-2 cursor-pointer group">
                    <input
                      type="checkbox"
                      checked={activeTags.includes(tag.key)}
                      onChange={() => onToggle(tag.key)}
                      className="rounded text-primary-600 focus:ring-primary-500"
                    />
                    <span 
                      className="w-3 h-3 rounded-full ring-1 ring-gray-200 group-hover:ring-2" 
                      style={{ backgroundColor: tag.color }}
                    />
                    <span className="text-sm text-gray-700 group-hover:text-gray-900">
                      {tag.label}
                    </span>
                  </label>
                ))}
              </div>
            </div>
          ))}
          
          {/* Reset */}
          <button
            onClick={onReset}
            className="w-full py-2 px-3 text-sm text-primary-600 hover:bg-primary-50 rounded-md border border-primary-200"
          >
            Mostrar Todos
          </button>
        </div>
      )}
    </div>
  )
}
```

#### 3.3. Atualizar `DeliveryMap.jsx` com tags
```jsx
// frontend/src/components/map/DeliveryMap.jsx (modificações principais)

import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import MarkerClusterGroup from 'react-leaflet-cluster'
import { useMemo, useState } from 'react'
import TagFilterPanel from './TagFilterPanel'
import { createIconByTag } from '../../utils/mapIcons'

export default function DeliveryMap({ 
  drivers, 
  deliveries, 
  customerLocations,
  filters,
  height = '600px' 
}) {
  const [activeTags, setActiveTags] = useState(Object.keys(filters.tag_configs))
  
  // Filtrar marcadores por tags ativas
  const filteredData = useMemo(() => {
    return {
      drivers: drivers.filter(d => 
        d.tags?.some(tag => activeTags.includes(tag))
      ),
      deliveries: deliveries.filter(d => 
        d.tags?.some(tag => activeTags.includes(tag))
      ),
      customers: customerLocations.filter(c => 
        c.tags?.some(tag => activeTags.includes(tag))
      )
    }
  }, [drivers, deliveries, customerLocations, activeTags])
  
  // Toggle tag
  const handleToggleTag = (tag) => {
    setActiveTags(prev => 
      prev.includes(tag) 
        ? prev.filter(t => t !== tag)
        : [...prev, tag]
    )
  }
  
  // Reset filtros
  const handleReset = () => {
    setActiveTags(Object.keys(filters.tag_configs))
  }
  
  // Centro padrão (Curitiba)
  const mapCenter = [-25.4284, -49.2733]
  
  return (
    <div className="relative rounded-lg overflow-hidden shadow-lg" style={{ height }}>
      {/* Painel de filtros */}
      <TagFilterPanel
        tagConfigs={filters.tag_configs}
        activeTags={activeTags}
        onToggle={handleToggleTag}
        onReset={handleReset}
      />
      
      {/* Mapa */}
      <MapContainer
        center={mapCenter}
        zoom={12}
        style={{ height: '100%', width: '100%' }}
        scrollWheelZoom={true}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        />
        
        {/* Cluster de entregadores */}
        <MarkerClusterGroup>
          {filteredData.drivers.map(driver => (
            driver.location && (
              <Marker
                key={`driver-${driver.id}`}
                position={[driver.location.latitude, driver.location.longitude]}
                icon={createIconByTag(driver.tags[0], driver.tag_config)}
              >
                <Popup>
                  <div className="p-2">
                    <h3 className="font-semibold text-lg">{driver.name}</h3>
                    <p className="text-sm text-gray-600">{driver.phone}</p>
                    <div className="mt-2 flex items-center gap-2">
                      <span 
                        className="px-2 py-1 rounded text-xs font-medium text-white"
                        style={{ backgroundColor: driver.tag_config?.color }}
                      >
                        {driver.tag_config?.label}
                      </span>
                      <span className="text-xs text-gray-500">
                        {driver.active_deliveries} entregas ativas
                      </span>
                    </div>
                  </div>
                </Popup>
              </Marker>
            )
          ))}
        </MarkerClusterGroup>
        
        {/* Cluster de entregas */}
        <MarkerClusterGroup>
          {filteredData.deliveries.map(delivery => (
            delivery.location && (
              <Marker
                key={`delivery-${delivery.id}`}
                position={[delivery.location.latitude, delivery.location.longitude]}
                icon={createIconByTag(delivery.tags[0], delivery.tag_config)}
              >
                <Popup>
                  <div className="p-2">
                    <h3 className="font-semibold">Pedido #{delivery.order_id}</h3>
                    <p className="text-sm">{delivery.customer_name}</p>
                    <p className="text-xs text-gray-600 mt-1">{delivery.address}</p>
                    <div className="mt-2">
                      <span 
                        className="px-2 py-1 rounded text-xs font-medium text-white"
                        style={{ backgroundColor: delivery.tag_config?.color }}
                      >
                        {delivery.tag_config?.label}
                      </span>
                    </div>
                  </div>
                </Popup>
              </Marker>
            )
          ))}
        </MarkerClusterGroup>
        
        {/* Cluster de clientes */}
        <MarkerClusterGroup>
          {filteredData.customers.map(customer => (
            customer.location && (
              <Marker
                key={`customer-${customer.phone}`}
                position={[customer.location.latitude, customer.location.longitude]}
                icon={createIconByTag(customer.tags[0], customer.tag_config)}
              >
                <Popup>
                  <div className="p-2">
                    <h3 className="font-semibold">{customer.name}</h3>
                    <p className="text-sm text-gray-600">{customer.phone}</p>
                    <p className="text-xs text-gray-500 mt-1">
                      {customer.order_count} pedidos realizados
                    </p>
                    <div className="mt-2">
                      <span 
                        className="px-2 py-1 rounded text-xs font-medium text-white"
                        style={{ backgroundColor: customer.tag_config?.color }}
                      >
                        {customer.tag_config?.label}
                      </span>
                    </div>
                  </div>
                </Popup>
              </Marker>
            )
          ))}
        </MarkerClusterGroup>
      </MapContainer>
    </div>
  )
}
```

#### 3.4. Criar utilitário de ícones
```jsx
// frontend/src/utils/mapIcons.js

import L from 'leaflet'

export const createIconByTag = (tag, tagConfig) => {
  const color = tagConfig?.color || '#3B82F6'
  const iconName = tagConfig?.icon || 'map-pin'
  
  // Ícones FontAwesome ou alternativa
  const iconHtml = `
    <div class="relative">
      <div style="
        background-color: ${color};
        width: 36px;
        height: 36px;
        border-radius: 50% 50% 50% 0;
        border: 3px solid white;
        box-shadow: 0 3px 10px rgba(0,0,0,0.4);
        transform: rotate(-45deg);
        display: flex;
        align-items: center;
        justify-content: center;
      ">
        <span style="
          transform: rotate(45deg);
          color: white;
          font-size: 16px;
          font-weight: bold;
        ">
          ${getIconSymbol(iconName)}
        </span>
      </div>
    </div>
  `
  
  return L.divIcon({
    className: 'custom-map-marker',
    html: iconHtml,
    iconSize: [36, 36],
    iconAnchor: [18, 36],
    popupAnchor: [0, -36]
  })
}

function getIconSymbol(iconName) {
  const symbols = {
    'user-plus': '👤',
    'user-check': '✓',
    'crown': '👑',
    'truck': '🚚',
    'truck-loading': '📦',
    'package': '📦',
    'map-pin': '📍',
    'clock': '⏰'
  }
  
  return symbols[iconName] || '📍'
}
```

---

### **Fase 4: Testes e Refinamentos** (2 horas)

#### 4.1. Testes Backend
```bash
# Testar serviço de geocoding
curl http://localhost:8000/api/locations/geocode \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"cep": "80010-000"}'

# Testar mapa com tags
curl http://localhost:8000/api/locations/map-data
```

#### 4.2. Testes Frontend
- Verificar renderização de marcadores com cores corretas
- Testar filtros de tags (mostrar/ocultar categorias)
- Validar popups com informações completas
- Testar clustering de marcadores próximos

#### 4.3. Refinamentos
- Ajustar cores e ícones para melhor visibilidade
- Otimizar consultas de banco de dados
- Adicionar loading states
- Implementar error handling robusto

---

## 📊 Métricas e Monitoramento

### KPIs de Sucesso
- **Taxa de Geocoding**: % de endereços com coordenadas válidas (meta: >90%)
- **Cache Hit Rate**: % de requisições atendidas por cache (meta: >70%)
- **Tempo de Resposta**: API `/map-data` (meta: <2s)
- **Precisão de Localização**: Accuracy "street" vs "neighborhood" (meta: >60% street-level)

### Logs e Alertas
```python
# Adicionar métricas ao serviço
logger.info(f"Geocoding: {source} | Accuracy: {accuracy} | Cache: {from_cache} | Time: {elapsed}ms")
```

---

## 🚀 Melhorias Futuras

### Fase 2.0
1. **Roteamento Inteligente**: Sugerir melhor entregador baseado em proximidade
2. **Heatmaps**: Visualizar densidade de pedidos por região
3. **Zonas de Entrega**: Delimitar áreas de cobertura
4. **Histórico de Rotas**: Replay de entregas anteriores

### Fase 3.0
1. **Machine Learning**: Prever tempo de entrega por região
2. **Otimização de Rotas**: Algoritmo de múltiplas entregas
3. **Integração Google Maps**: Directions API para rotas em tempo real
4. **Notificações Push**: Alertas de proximidade para clientes

---

## ✅ Checklist de Implementação

### Backend
- [ ] Instalar `brazilcep` e `httpx`
- [ ] Criar `GeocodingService` com fallback estratégico
- [ ] Criar modelo `GeocodingCache`
- [ ] Migração: adicionar coluna `location` em `customers`
- [ ] Criar enums e config de `LocationTag`
- [ ] Atualizar endpoint `/api/locations/map-data` com tags
- [ ] Criar endpoint `/api/locations/geocode`
- [ ] Criar endpoint `/api/locations/tags`
- [ ] Adicionar testes unitários

### Frontend
- [ ] Instalar `react-leaflet` e `leaflet.markercluster`
- [ ] Criar `TagFilterPanel` component
- [ ] Criar utilitário `mapIcons.js`
- [ ] Atualizar `DeliveryMap` com clustering e filtros
- [ ] Adicionar CSS customizado para marcadores
- [ ] Testar responsividade em mobile
- [ ] Adicionar loading states e error boundaries

### DevOps
- [ ] Adicionar variável `CEPABERTO_TOKEN` no `.env`
- [ ] Atualizar `docker-compose.yml` se necessário
- [ ] Documentar API no README
- [ ] Criar migration Alembic para cache de geocoding

---

## 📝 Notas Importantes

1. **Rate Limiting**: Nominatim tem limite de 1 req/segundo. Implementar queue se necessário.
2. **HTTPS**: Leaflet requer HTTPS para geolocation. Configurar SSL em produção.
3. **CEPAberto Token**: Obter em https://www.cepaberto.com/ (gratuito até 10k req/mês)
4. **Privacidade**: Não armazenar localização exata de clientes por mais de 30 dias (LGPD)

---

## 🎉 Resultado Final

Após implementação completa, o mapa terá:
✅ Geocoding automático de todos os endereços  
✅ Marcadores coloridos e categorizados por tags  
✅ Filtros interativos por tipo de entidade  
✅ Clustering inteligente de marcadores próximos  
✅ Popups informativos com ações rápidas  
✅ Performance otimizada com cache em 3 camadas (Redis + DB + API)  
✅ Fallback robusto entre múltiplas APIs de geocoding
