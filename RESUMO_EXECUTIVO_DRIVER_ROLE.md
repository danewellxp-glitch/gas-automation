# 🚗 RESUMO EXECUTIVO - ROLE DE DRIVER/ENTREGADOR

**Para:** IA Gestora  
**Objetivo:** Design rápido de funcionalidades para role de entregador  
**Sistema:** Gas Automation v1.0.0 (Produção)  
**Data:** 21 de Janeiro de 2026

---

## ⚡ **TL;DR (Too Long; Didn't Read)**

```
SISTEMA: Pedidos de gás via WhatsApp (B2C)
PRODUTOS: Botijões P13 (13kg), P20 (20kg), P45 (45kg)
CAPACIDADE: 50.000+ pedidos/semana, 500+ users simultâneos
STACK: FastAPI + React + PostgreSQL + Redis + Docker

JÁ TEM:
✅ Modelo Driver completo no banco
✅ Service layer implementado
✅ WebSocket escalável (tempo real)
✅ Sistema de entregas funcionando

FALTA:
❌ API REST para entregadores
❌ Dashboard do entregador
❌ WebSocket events para driver
❌ Mobile-friendly UI
❌ Funcionalidades operacionais

OBJETIVO:
🎯 Criar interface completa para o entregador gerenciar suas entregas
```

---

## 📊 **DADOS IMPORTANTES**

### **Modelo de Driver (JÁ EXISTE)**

```typescript
interface Driver {
  id: UUID
  name: string
  phone: string (unique)
  email?: string
  vehicle_type?: string  // "moto", "carro"
  license_plate?: string
  
  status: "offline" | "available" | "busy" | "break"
  current_location?: {
    latitude: number
    longitude: number
    timestamp: datetime
  }
  
  rating: number  // 0-5
  total_deliveries: number
  is_active: boolean
  last_online?: datetime
}
```

### **Modelo de Delivery (JÁ EXISTE)**

```typescript
interface Delivery {
  id: UUID
  order_id: UUID
  driver_id?: UUID  // FK para Driver
  driver_name?: string
  driver_phone?: string
  
  status: "pending" | "assigned" | "picked_up" | 
          "in_transit" | "arrived" | "delivered" | 
          "failed" | "returned"
  
  bairro: string
  estimated_minutes: number  // default: 40
  actual_delivery_minutes?: number
  
  // Timestamps de cada etapa
  assigned_at?: datetime
  picked_up_at?: datetime
  in_transit_at?: datetime
  arrived_at?: datetime
  delivered_at?: datetime
  
  notes?: string
  failure_reason?: string
  last_location?: {lat, lng, timestamp}
}
```

### **Fluxo de Status da Entrega**

```
PENDING → ASSIGNED → PICKED_UP → IN_TRANSIT → ARRIVED → DELIVERED
                                              ↘
                                               FAILED → RETURNED
```

---

## 🎯 **O QUE PRECISA SER CRIADO**

### **1. Backend API (FastAPI)**

```python
# Criar: backend/app/api/drivers.py

Endpoints Mínimos (MVP):
GET    /api/drivers/me              # Perfil do driver logado
PUT    /api/drivers/me/status       # Online/Offline/Break
PUT    /api/drivers/me/location     # Atualizar GPS
GET    /api/drivers/me/deliveries   # Minhas entregas
GET    /api/drivers/me/deliveries/pending    # Disponíveis
GET    /api/drivers/me/deliveries/active     # Em andamento
PUT    /api/deliveries/{id}/status  # Atualizar status da entrega
POST   /api/deliveries/{id}/problem # Reportar problema

Endpoints Admin/Operator:
GET    /api/drivers                 # Listar todos
POST   /api/drivers                 # Criar novo
PUT    /api/drivers/{id}            # Editar
DELETE /api/drivers/{id}            # Remover
GET    /api/drivers/available       # Listar disponíveis
GET    /api/drivers/{id}/stats      # Estatísticas
```

### **2. Frontend React**

```javascript
Páginas a Criar:

/driver/login
  - Login específico para entregador
  - Usa JWT endpoint existente
  - Verifica role === "driver"

/driver/dashboard
  - Toggle de status (online/offline/pausa)
  - Contador de entregas (hoje, total)
  - Avaliação média
  - Lista de entregas disponíveis (por bairro)
  - Lista de entregas em andamento

/driver/delivery/{id}
  - Detalhes completos da entrega
  - Endereço do cliente
  - Telefone do cliente
  - Itens do pedido
  - Botões de ação:
    ✓ "Retirei os produtos" (ASSIGNED → PICKED_UP)
    ✓ "Saí para entrega" (PICKED_UP → IN_TRANSIT)
    ✓ "Cheguei no local" (IN_TRANSIT → ARRIVED)
    ✓ "Entregue" (ARRIVED → DELIVERED)
    ✓ "Reportar Problema"
  - Botão "Abrir no Maps"

/driver/history
  - Histórico de entregas
  - Filtros (hoje, semana, mês)
  - Detalhes ao clicar

/driver/profile
  - Dados pessoais
  - Veículo
  - Estatísticas (entregas, avaliação)
  - Editar dados
```

### **3. WebSocket Events**

```javascript
// Adicionar em backend/app/api/websocket.py

Eventos para Driver:
- delivery_assigned: Nova entrega alocada
- delivery_updated: Mudança em entrega do driver
- operator_message: Mensagem do operador

Filtro:
filter_fn=lambda m: (
    m.user_role == UserRole.DRIVER and 
    m.user_id == driver_id
)
```

### **4. Métricas**

```python
# Adicionar em backend/app/metrics.py

driver_online_total
driver_deliveries_total
driver_delivery_duration_seconds
driver_rating
```

---

## 🎨 **FUNCIONALIDADES POR PRIORIDADE**

### **🔴 CRÍTICAS (MVP - 1 semana)**

1. **Autenticação**
   - Login como driver
   - JWT authentication
   - Verificação de role

2. **Status Online/Offline**
   - Toggle no dashboard
   - Atualiza Driver.status
   - Salva last_online

3. **Ver Entregas Disponíveis**
   - Lista entregas com status PENDING do seu bairro
   - Detalhes: endereço, cliente, itens
   - Botão "Aceitar Entrega"

4. **Gerenciar Entrega Ativa**
   - Ver detalhes completos
   - Atualizar status (retirou, saiu, chegou, entregue)
   - Ver telefone e ligar
   - Abrir no Maps

5. **Estatísticas Básicas**
   - Total de entregas (hoje, total)
   - Avaliação média

### **🟡 IMPORTANTES (Fase 2 - 2 semanas)**

6. **GPS Tracking**
   - Atualização automática de localização (30s)
   - Broadcasting via WebSocket para operador
   - ETA (Estimated Time of Arrival)

7. **Histórico**
   - Lista de entregas passadas
   - Filtros por data
   - Busca

8. **Notificações**
   - Push quando entrega alocada
   - Sons/alertas

9. **Reportar Problemas**
   - Cliente ausente
   - Endereço errado
   - Produto danificado
   - Outros

10. **Chat/Comunicação**
    - Ver mensagens do operador
    - Enviar mensagens

### **🟢 DESEJÁVEIS (Fase 3 - 3 semanas)**

11. **Prova de Entrega**
    - Tirar foto do produto
    - Coletar assinatura digital
    - Upload via MinIO

12. **Avaliação**
    - Cliente avalia entregador
    - Ver avaliações recebidas
    - Comentários

13. **Gamificação**
    - Ranking de entregadores
    - Badges/conquistas
    - Metas diárias
    - Bônus por performance

14. **PWA Mobile**
    - Instalável como app
    - Offline-first
    - Notificações push

15. **Rotas Otimizadas**
    - Múltiplas entregas
    - Melhor sequência
    - Menor distância

---

## 💡 **DECISÕES DE DESIGN SUGERIDAS**

### **UX/UI:**

```
✅ Mobile-first design (entregador usa celular)
✅ Botões grandes e touch-friendly
✅ Cores por status (verde=ok, amarelo=atenção, vermelho=problema)
✅ Ações principais sempre visíveis
✅ Mínimo de cliques para ações frequentes
✅ Feedback visual imediato
✅ Modo escuro (opcional)
```

### **Fluxo de Trabalho:**

```
1. ENTREGADOR CHEGA AO TRABALHO
   - Abre app
   - Faz login
   - Liga status "Online"
   - Sistema mostra entregas disponíveis

2. VÊ ENTREGA DISPONÍVEL
   - Lista mostra: endereço, bairro, itens
   - Clica para ver detalhes
   - Aceita a entrega
   - Status muda para ASSIGNED

3. VAI BUSCAR OS PRODUTOS
   - Dashboard mostra "Entrega ativa"
   - Clica em "Retirei os produtos"
   - Status muda para PICKED_UP

4. SAI PARA ENTREGA
   - Clica "Saí para entrega"
   - Status muda para IN_TRANSIT
   - GPS tracking ativado

5. CHEGOU NO CLIENTE
   - Clica "Cheguei no local"
   - Status muda para ARRIVED
   - Pode ligar para cliente

6. ENTREGA CONCLUÍDA
   - Clica "Entregue"
   - (Opcional) Tira foto/assinatura
   - Status muda para DELIVERED
   - Status do driver volta para AVAILABLE
   - Notificação de próxima entrega (se houver)

7. FIM DO EXPEDIENTE
   - Clica status "Offline"
   - Ver resumo do dia
```

### **Segurança:**

```
✅ JWT authentication em todos os endpoints
✅ Driver só vê suas próprias entregas
✅ Verificar driver_id em todas as ações
✅ Rate limiting nos endpoints
✅ Logs de auditoria (EventLog)
```

### **Performance:**

```
✅ Paginação nas listas
✅ Lazy loading de imagens
✅ Cache de dados frequentes
✅ WebSocket para atualizações em tempo real
✅ Compressão de imagens
```

---

## 🔧 **STACK TÉCNICO**

```yaml
Backend:
  Framework: FastAPI (Python 3.11)
  ORM: SQLAlchemy 2.0 (Async)
  Database: PostgreSQL 15
  Cache: Redis 7
  WebSocket: Uvicorn native
  Auth: JWT Bearer tokens

Frontend:
  Framework: React 18
  Build: Vite
  Networking: Axios
  WebSocket: Native + BroadcastChannel
  UI: CSS puro (ou Tailwind se preferir)

Infra:
  Containers: Docker Compose
  Monitoring: Prometheus + Grafana
  Storage: MinIO (S3-compatible)
```

---

## 📱 **EXEMPLO DE TELAS**

### **Dashboard do Driver:**

```
┌─────────────────────────────────────┐
│  [📍] João Silva         [⚙️]       │
│  Status: 🟢 ONLINE  [▼]             │
├─────────────────────────────────────┤
│  📊 HOJE                            │
│  ├─ Entregas: 8                     │
│  ├─ Avaliação: ⭐ 4.8              │
│  └─ Tempo médio: 32 min             │
├─────────────────────────────────────┤
│  📦 ENTREGAS DISPONÍVEIS (3)        │
│  ┌─────────────────────────────┐  │
│  │ Rua ABC, 123 - Centro       │  │
│  │ 2x P13                      │  │
│  │ 📍 2.5 km                   │  │
│  │          [ACEITAR] ──────►  │  │
│  └─────────────────────────────┘  │
├─────────────────────────────────────┤
│  🚚 ENTREGA EM ANDAMENTO            │
│  ┌─────────────────────────────┐  │
│  │ ⏱️ EM TRÂNSITO              │  │
│  │ Rua XYZ, 456 - Bairro Alto  │  │
│  │ 1x P20, 1x P13              │  │
│  │ Cliente: Maria (11) 99999   │  │
│  │                             │  │
│  │  [📞 LIGAR] [🗺️ MAPS]      │  │
│  │  [📍 CHEGUEI] ──────────►   │  │
│  └─────────────────────────────┘  │
└─────────────────────────────────────┘
```

### **Detalhes da Entrega:**

```
┌─────────────────────────────────────┐
│  ← Voltar    Pedido #1234           │
├─────────────────────────────────────┤
│  📦 ITENS                           │
│  ├─ 1x Botijão P13 (13kg)           │
│  └─ 2x Botijão P20 (20kg)           │
│                                     │
│  📍 ENDEREÇO                        │
│  Rua das Flores, 789                │
│  Apto 302 - Torre A                 │
│  Jardim Paulista, São Paulo         │
│  CEP: 01234-567                     │
│                                     │
│  👤 CLIENTE                         │
│  Maria Silva                        │
│  📞 (11) 99999-9999                 │
│                                     │
│  💰 PAGAMENTO                       │
│  Pix - Já Pago ✅                   │
│  Total: R$ 250,00                   │
│                                     │
│  📝 OBSERVAÇÕES                     │
│  "Favor tocar campainha 2x"         │
├─────────────────────────────────────┤
│  [📞 LIGAR CLIENTE]                 │
│  [🗺️ ABRIR NO MAPS]                │
│                                     │
│  [✅ ENTREGUE]                      │
│  [⚠️ REPORTAR PROBLEMA]             │
└─────────────────────────────────────┘
```

---

## 📈 **MÉTRICAS DE SUCESSO**

### **Para o Negócio:**

```
KPI 1: Tempo médio de entrega
  Meta: < 40 minutos
  Medição: actual_delivery_minutes

KPI 2: Taxa de sucesso
  Meta: > 95%
  Medição: (DELIVERED / total) * 100

KPI 3: Avaliação média
  Meta: > 4.5 estrelas
  Medição: AVG(rating)

KPI 4: Entregas por entregador/dia
  Meta: 15-20 entregas
  Medição: COUNT(deliveries WHERE date = today)
```

### **Para o Entregador:**

```
- Ver minhas estatísticas em tempo real
- Comparar com meta diária
- Ver minha posição no ranking
- Acompanhar ganhos (se houver sistema de pagamento)
```

---

## ⚠️ **PONTOS DE ATENÇÃO**

1. **GPS e Bateria**
   - Tracking constante consome bateria
   - Oferecer opção de atualização manual
   - Modo "economia de bateria"

2. **Internet Instável**
   - Modo offline básico
   - Queue de ações pendentes
   - Retry automático

3. **Segurança de Dados**
   - Não expor dados sensíveis de outros entregadores
   - Não expor todos os endereços (só da entrega alocada)
   - Logs de acesso

4. **Usabilidade**
   - Testar em tela pequena (5-6 polegadas)
   - Testar sob sol forte (contraste)
   - Testar com luvas (touch)

---

## 🚀 **QUICK START PARA IMPLEMENTAÇÃO**

### **Passo 1: Backend (2-3 dias)**

```bash
# 1. Adicionar role "driver" ao enum
# backend/app/api/websocket.py
class UserRole(str, Enum):
    # ... existing
    DRIVER = "driver"  # ← ADICIONAR

# 2. Criar router de drivers
# backend/app/api/drivers.py
# (usar DriverService já existente)

# 3. Registrar router
# backend/app/main.py
from app.api import drivers
app.include_router(drivers.router, prefix="/api/drivers", tags=["Drivers"])

# 4. Criar schemas Pydantic
# backend/app/schemas/driver.py

# 5. Testar com Postman
```

### **Passo 2: Frontend (3-5 dias)**

```bash
# 1. Criar páginas
frontend/src/pages/driver/
  ├── Login.jsx
  ├── Dashboard.jsx
  ├── DeliveryDetail.jsx
  ├── History.jsx
  └── Profile.jsx

# 2. Criar componentes
frontend/src/components/driver/
  ├── StatusToggle.jsx
  ├── DeliveryCard.jsx
  ├── DeliveryActions.jsx
  └── StatsCard.jsx

# 3. Criar hooks
frontend/src/hooks/
  ├── useDriverStatus.js
  ├── useDriverDeliveries.js
  └── useDriverLocation.js

# 4. Criar serviços
frontend/src/services/
  └── driverApi.js

# 5. Adicionar rotas
# frontend/src/App.jsx
<Route path="/driver/*" element={<DriverLayout />}>
  <Route path="login" element={<DriverLogin />} />
  <Route path="dashboard" element={<DriverDashboard />} />
  {/* ... */}
</Route>
```

### **Passo 3: WebSocket (1 dia)**

```python
# backend/app/api/websocket.py

async def emit_delivery_assigned(delivery_data: dict):
    driver_id = delivery_data.get("driver_id")
    await manager.broadcast(
        message={
            "type": "delivery_assigned",
            "data": delivery_data
        },
        filter_fn=lambda m: (
            m.user_role == UserRole.DRIVER and 
            str(m.user_id) == str(driver_id)
        )
    )
```

### **Passo 4: Testes (2 dias)**

```bash
# 1. Criar driver no banco
# 2. Fazer login
# 3. Ligar status online
# 4. Alocar entrega (via operador)
# 5. Verificar WebSocket
# 6. Atualizar status
# 7. Concluir entrega
# 8. Verificar estatísticas
```

---

## 📞 **CONTATO E SUPORTE**

**Documentação Completa:**
- `ANALISE_COMPLETA_SISTEMA_PARA_IA_GESTORA.md`

**Código Fonte:**
- Backend: `/backend/app/models/driver.py`
- Service: `/backend/app/services/driver_service.py`

**Sistema em Produção:**
- API: http://192.168.10.156:8000
- Docs: http://192.168.10.156:8000/docs

---

**PRONTO PARA IMPLEMENTAÇÃO!** 🚀

Este resumo fornece todas as informações necessárias para a IA Gestora desenhar
funcionalidades completas, práticas e eficientes para o papel de entregador/driver.
