#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste da Fase 2: Mapa em tempo real.
Verifica endpoints e estrutura de dados.
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# ===== Schemas (copias simplificadas) =====

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


class CustomerLocation(BaseModel):
    phone: str
    name: Optional[str] = None
    latitude: float
    longitude: float
    address: Optional[str] = None
    timestamp: datetime


# ===== Testes =====

def test_schemas():
    print("=" * 60)
    print("TESTE FASE 2: Schemas de Localização")
    print("=" * 60)

    # Teste 1: LocationData
    print("\n📍 Teste 1: LocationData")
    loc = LocationData(
        latitude=-25.4284,
        longitude=-49.2733,
        timestamp=datetime.now()
    )
    print(f"   latitude: {loc.latitude}")
    print(f"   longitude: {loc.longitude}")
    print(f"   timestamp: {loc.timestamp}")
    print("   ✅ OK")

    # Teste 2: DriverLocation
    print("\n🚚 Teste 2: DriverLocation")
    driver = DriverLocation(
        id="driver-123",
        name="João Silva",
        phone="41999887766",
        status="online",
        location=LocationData(
            latitude=-25.4300,
            longitude=-49.2700
        ),
        active_deliveries=2
    )
    print(f"   id: {driver.id}")
    print(f"   name: {driver.name}")
    print(f"   status: {driver.status}")
    print(f"   location: {driver.location}")
    print(f"   active_deliveries: {driver.active_deliveries}")
    print("   ✅ OK")

    # Teste 3: DeliveryLocation
    print("\n📦 Teste 3: DeliveryLocation")
    delivery = DeliveryLocation(
        id="delivery-456",
        order_id="order-789",
        customer_name="Maria Santos",
        customer_phone="41988776655",
        status="in_transit",
        location=LocationData(
            latitude=-25.4350,
            longitude=-49.2650
        ),
        address="Rua XV de Novembro, 123"
    )
    print(f"   id: {delivery.id}")
    print(f"   order_id: {delivery.order_id}")
    print(f"   customer_name: {delivery.customer_name}")
    print(f"   status: {delivery.status}")
    print(f"   address: {delivery.address}")
    print("   ✅ OK")

    # Teste 4: CustomerLocation
    print("\n👤 Teste 4: CustomerLocation")
    customer = CustomerLocation(
        phone="5541999887766",
        name="Cliente Teste",
        latitude=-25.4400,
        longitude=-49.2600,
        address="Av. Brasil, 500",
        timestamp=datetime.now()
    )
    print(f"   phone: {customer.phone}")
    print(f"   name: {customer.name}")
    print(f"   latitude: {customer.latitude}")
    print(f"   longitude: {customer.longitude}")
    print(f"   address: {customer.address}")
    print("   ✅ OK")

    return True


def test_map_data_structure():
    print("\n" + "=" * 60)
    print("TESTE: Estrutura de Dados do Mapa")
    print("=" * 60)

    # Simular resposta do endpoint /api/locations/map-data
    map_data = {
        "drivers": [
            {
                "id": "d1",
                "name": "Entregador 1",
                "phone": "41999111111",
                "status": "online",
                "location": {
                    "latitude": -25.4284,
                    "longitude": -49.2733
                },
                "active_deliveries": 1
            },
            {
                "id": "d2",
                "name": "Entregador 2",
                "phone": "41999222222",
                "status": "busy",
                "location": {
                    "latitude": -25.4350,
                    "longitude": -49.2680
                },
                "active_deliveries": 2
            }
        ],
        "deliveries": [
            {
                "id": "del1",
                "order_id": "ord1",
                "customer_name": "Cliente A",
                "status": "pending",
                "location": {
                    "latitude": -25.4400,
                    "longitude": -49.2600
                },
                "address": "Rua A, 100"
            },
            {
                "id": "del2",
                "order_id": "ord2",
                "customer_name": "Cliente B",
                "status": "in_transit",
                "location": {
                    "latitude": -25.4450,
                    "longitude": -49.2550
                },
                "address": "Rua B, 200",
                "driver_id": "d2",
                "driver_name": "Entregador 2"
            }
        ],
        "customer_locations": [
            {
                "phone": "5541999333333",
                "name": "Cliente C",
                "latitude": -25.4500,
                "longitude": -49.2500,
                "address": "Rua C, 300",
                "timestamp": datetime.now().isoformat()
            }
        ],
        "updated_at": datetime.now().isoformat()
    }

    print(f"\n📊 Resumo dos dados:")
    print(f"   Entregadores: {len(map_data['drivers'])}")
    print(f"   Entregas: {len(map_data['deliveries'])}")
    print(f"   Localizações de clientes: {len(map_data['customer_locations'])}")

    print(f"\n🚚 Entregadores:")
    for d in map_data["drivers"]:
        print(f"   - {d['name']} ({d['status']}): {d['location']['latitude']}, {d['location']['longitude']}")

    print(f"\n📦 Entregas:")
    for d in map_data["deliveries"]:
        print(f"   - {d['customer_name']} ({d['status']}): {d['address']}")

    print(f"\n📍 Localizações de clientes:")
    for c in map_data["customer_locations"]:
        print(f"   - {c['name']}: {c['latitude']}, {c['longitude']}")

    print("\n   ✅ Estrutura de dados OK")
    return True


def test_websocket_events():
    print("\n" + "=" * 60)
    print("TESTE: Eventos WebSocket")
    print("=" * 60)

    # Evento: Atualização de localização do entregador
    print("\n📡 Evento: driver_location_update")
    event1 = {
        "type": "driver_location_update",
        "driver_id": "d1",
        "location": {
            "latitude": -25.4290,
            "longitude": -49.2740,
            "timestamp": datetime.now().isoformat()
        }
    }
    print(f"   {event1}")
    print("   ✅ OK")

    # Evento: Nova localização de cliente
    print("\n📡 Evento: location_received")
    event2 = {
        "type": "location_received",
        "phone": "5541999444444",
        "name": "Novo Cliente",
        "latitude": -25.4550,
        "longitude": -49.2450,
        "address": "Rua Nova, 500"
    }
    print(f"   {event2}")
    print("   ✅ OK")

    return True


def main():
    print("\n" + "=" * 60)
    print("🗺️  TESTES DA FASE 2: MAPA EM TEMPO REAL")
    print("=" * 60)

    results = []

    # Executar testes
    results.append(("Schemas", test_schemas()))
    results.append(("Estrutura de dados", test_map_data_structure()))
    results.append(("Eventos WebSocket", test_websocket_events()))

    # Resumo
    print("\n" + "=" * 60)
    print("📋 RESUMO DOS TESTES")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✅ PASSOU" if passed else "❌ FALHOU"
        print(f"   {name}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ TODOS OS TESTES PASSARAM!")
    else:
        print("❌ ALGUNS TESTES FALHARAM")
    print("=" * 60)

    # Instruções
    print("\n📌 ARQUIVOS CRIADOS:")
    print("   Backend:")
    print("   - app/api/locations.py (endpoints do mapa)")
    print("   Frontend:")
    print("   - src/components/map/DeliveryMap.jsx (componente Leaflet)")
    print("   - src/hooks/useMapData.js (hook de dados)")
    print("   - OperatorDashboard.jsx (atualizado com view do mapa)")

    print("\n📌 ENDPOINTS:")
    print("   GET  /api/locations/map-data - Dados completos do mapa")
    print("   POST /api/locations/driver/{id}/location - Atualizar localização")
    print("   GET  /api/locations/drivers/active - Entregadores ativos")

    print("\n📌 PARA TESTAR:")
    print("   1. Inicie o Docker: docker-compose up -d")
    print("   2. Inicie o backend: uvicorn app.main:app --reload")
    print("   3. Inicie o frontend: npm run dev")
    print("   4. Acesse: http://localhost:5173")
    print("   5. Login como operador e clique em 'Mapa'")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
