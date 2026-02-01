# GPS Auto-Arrived + WhatsApp "1 minuto"

## Visão Geral

Quando o motorista está em rota (`in_transit`) e se aproxima do endereço do cliente (~500m), o sistema:

1. **Auto-atualiza** o status da entrega para `arrived`
2. **Envia WhatsApp** ao cliente: *"📍 Seu gás está a 1 minuto da sua casa! Pedido #X – o entregador está chegando. 🔥"*

Similar ao que a Uber faz ao avisar que o motorista está chegando.

## Componentes

### Backend (gas-automation)

- **Migration** `20260201_add_delivery_destination_coords.py`:
  - `delivery_destination_lat`, `delivery_destination_lng`: coordenadas do endereço (geocoding)
  - `arrived_whatsapp_sent`: flag para não reenviar WhatsApp

- **Serviço** `app/services/geocoding_service.py`:
  - Geocoding via Nominatim (OpenStreetMap) – gratuito, sem API key
  - Função `haversine_distance_km()` para calcular distância

- **Endpoint** `PUT /api/drivers/me/location`:
  - Após salvar a localização, executa em background:
    - Busca entrega `in_transit` do driver
    - Geocodifica o endereço se ainda não tiver coordenadas
    - Se distância < 500m: atualiza para `arrived`, envia WhatsApp

### Mobile (gas-automation-mobile)

- **locationTracker.ts**: intervalo de envio reduzido de 30s para **15 segundos** para detecção mais rápida de proximidade

## Fluxo

1. Motorista marca entrega como "Em rota" (`in_transit`)
2. App envia GPS a cada 15s para `PUT /drivers/me/location`
3. Backend, ao receber cada atualização:
   - Verifica se há entrega in_transit
   - Geocodifica endereço (se necessário)
   - Calcula distância (Haversine)
   - Se < 500m: `arrived` + WhatsApp

## Configuração

- **Raio de proximidade**: 500m (`ARRIVED_PROXIMITY_KM = 0.5` em `drivers.py`)
- **Geocoding**: Nominatim (cidade padrão: Curitiba)
- **WhatsApp**: via WAHA (mesma integração existente)

## Teste

1. Criar pedido com endereço completo
2. Atribuir ao motorista e marcar como "Em rota"
3. Simular GPS próximo ao endereço (ou usar dispositivo real)
4. Verificar: status mudou para "Chegou" e cliente recebeu WhatsApp
