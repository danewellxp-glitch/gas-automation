# 📊 ANÁLISE COMPLETA DO SISTEMA - GAS AUTOMATION

**Para:** IA Gestora - Design de Role "Driver/Entregador"  
**Data:** 21 de Janeiro de 2026  
**Versão do Sistema:** 1.0.0 (Fase 3 - Escala Avançada Completa)  
**Objetivo:** Fornecer contexto completo para desenhar funcionalidades da role de entregador/driver

---

## 📋 **ÍNDICE**

1. [Visão Geral do Negócio](#visão-geral-do-negócio)
2. [Stack Tecnológica](#stack-tecnológica)
3. [Arquitetura do Sistema](#arquitetura-do-sistema)
4. [Modelos de Dados](#modelos-de-dados)
5. [Roles Existentes](#roles-existentes)
6. [Fluxo de Pedidos Atual](#fluxo-de-pedidos-atual)
7. [Funcionalidades Implementadas](#funcionalidades-implementadas)
8. [Driver/Entregador - Estado Atual](#driverentregador---estado-atual)
9. [Gaps e Oportunidades](#gaps-e-oportunidades)
10. [Requisitos Técnicos](#requisitos-técnicos)
11. [Métricas e KPIs](#métricas-e-kpis)

---

## 🎯 **VISÃO GERAL DO NEGÓCIO**

### **O que é o Gas Automation?**

Sistema completo de **automação de pedidos de gás via WhatsApp** com gerenciamento de entregas, pagamentos e rastreamento em tempo real.

### **Produtos Comercializados:**

| Código | Produto | Descrição | Preço Típico |
|--------|---------|-----------|--------------|
| **P13** | Botijão 13kg | Gás residencial padrão | R$ 80-100 |
| **P20** | Botijão 20kg | Gás comercial médio | R$ 120-150 |
| **P45** | Botijão 45kg | Gás industrial | R$ 250-300 |

### **Volume Operacional Atual:**

```
Capacidade máxima: 50.000+ pedidos/semana
Usuários simultâneos: 500+
Instâncias backend: Múltiplas (escala horizontal)
Taxa de mensagens WebSocket: ~3/s (otimizado com batching)
Latência média: 5-10ms
Tráfego de rede: 0.6MB/h (98% menos que versão original)
```

### **Áreas de Cobertura:**

- Sistema suporta **múltiplos bairros** e **regiões**
- Alocação de entregadores **por bairro**
- Filtros de broadcast por **bairro/região** implementados

---

## 🛠️ **STACK TECNOLÓGICA**

### **Backend:**

```yaml
Framework: FastAPI 0.109.0 (Python 3.11)
ORM: SQLAlchemy 2.0 (Async)
Database: PostgreSQL 15 (UUID-based IDs)
Cache/Queue: Redis 7 (Pub/Sub para WebSocket)
Migrations: Alembic
API Docs: Swagger UI (OpenAPI 3.0)
WebSocket: Nativo FastAPI (Uvicorn com compressão)
Authentication: JWT (Bearer tokens)
```

### **Frontend:**

```yaml
Framework: React 18
Build: Vite
State Management: Context API + useState
Networking: Axios
WebSocket: Native WebSocket API + BroadcastChannel
UI: CSS puro (sem framework)
```

### **Infraestrutura:**

```yaml
Containers: Docker + Docker Compose
Reverse Proxy: Traefik 2.11
Monitoring: Prometheus + Grafana
Object Storage: MinIO (S3-compatible)
AI/Chatbot: Ollama (local LLM)
WhatsApp: WAHA (WhatsApp API gateway)
```

### **Observabilidade (Fase 3):**

```yaml
Métricas: 20+ custom Prometheus metrics
Dashboard: Grafana (8 painéis)
Alertas: 20 regras (Prometheus Alert Manager)
Logs: Docker logs + aplicação
Uptime: System uptime tracking
```

---

## 🏗️ **ARQUITETURA DO SISTEMA**

### **Arquitetura Geral:**

```
┌─────────────────────────────────────────────────────┐
│                  CLIENTES                            │
│  (WhatsApp, Web Dashboard, Mobile Apps)              │
└────────────────┬─────────────────────────────────────┘
                 │
         ┌───────▼────────┐
         │   Traefik       │ (API Gateway)
         │   Load Balancer │
         └───────┬─────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
┌───▼───┐   ┌───▼───┐   ┌───▼───┐
│Backend│   │Backend│   │Backend│ (Escala Horizontal)
│   1   │   │   2   │   │   N   │
└───┬───┘   └───┬───┘   └───┬───┘
    │            │            │
    └────────────┼────────────┘
                 │
        ┌────────▼─────────┐
        │  Redis Pub/Sub   │ (Comunicação entre instâncias)
        └────────┬─────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
┌───▼──────┐ ┌──▼──────┐ ┌──▼────────┐
│PostgreSQL│ │  Redis  │ │ MinIO     │
│(Dados)   │ │ (Cache) │ │ (Files)   │
└──────────┘ └─────────┘ └───────────┘
```

### **Fluxo de WebSocket (Tempo Real):**

```
┌──────────┐     WebSocket      ┌──────────┐
│ Cliente  │◄──────────────────►│ Backend  │
└──────────┘                     └─────┬────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
            ┌───────▼───────┐  ┌──────▼──────┐  ┌───────▼────────┐
            │ Event Batcher │  │  Redis Pub  │  │ Message Store  │
            │ (Agrupamento) │  │  (Broadcast)│  │ (Persistência) │
            └───────────────┘  └─────────────┘  └────────────────┘

Features:
✅ Event batching (90% menos mensagens)
✅ Redis Pub/Sub (múltiplas instâncias)
✅ Persistência (replay em reconexão)
✅ Filtros por role/bairro/região
✅ Rate limiting (10 broadcasts/segundo)
✅ Heartbeat monitor (limpa conexões mortas)
```

---

## 📊 **MODELOS DE DADOS**

### **1. User (Usuário do Sistema)**

```python
Model: User
Table: users
ID Type: Integer (sequencial)

Campos Principais:
- id: int (PK)
- username: str (unique)
- email: str (unique)
- full_name: str
- hashed_password: str
- role: str (enum: "user", "admin", "operator", "owner", "manager")
- is_active: bool
- created_at: datetime
- updated_at: datetime

Roles Existentes:
1. user: Cliente final (acesso básico)
2. admin: Administrador total
3. operator: Operador (atendimento, gestão de pedidos)
4. owner: Dono (visão executiva, relatórios)
5. manager: Gerente regional (visão de região)
```

### **2. Customer (Cliente)**

```python
Model: Customer
Table: customers
ID Type: UUID

Campos Principais:
- id: UUID (PK)
- phone: str (unique, ex: 5511999999999)
- name: str
- email: str (opcional)
- cpf_cnpj: str (opcional)
- addresses: JSONB array [{street, number, complement, bairro, city, cep}]
- default_address_index: int
- is_active: bool
- total_orders: int
- last_order_at: datetime
- created_at, updated_at

Relacionamentos:
- orders: List[Order] (one-to-many)
```

### **3. Product (Produto)**

```python
Model: Product
Table: products
ID Type: UUID

Produtos Padrão:
- P13: Botijão 13kg
- P20: Botijão 20kg
- P45: Botijão 45kg

Campos:
- id: UUID (PK)
- code: str (unique, ex: "P13")
- name: str
- description: str
- price: Decimal(10, 2)
- stock_quantity: int
- is_active: bool
- category: str (opcional)
```

### **4. Order (Pedido)**

```python
Model: Order
Table: orders
ID Type: UUID

Status Enum: OrderStatus
- PENDING: "pending" (aguardando pagamento)
- PAID: "paid" (pago, aguardando preparo)
- PREPARING: "preparing" (em preparação)
- DISPATCHED: "dispatched" (saiu para entrega)
- DELIVERED: "delivered" (entregue)
- CANCELLED: "cancelled" (cancelado)

Campos Principais:
- id: UUID (PK)
- customer_id: UUID (FK → customers)
- order_number: int (sequencial único, para exibição)
- status: str (OrderStatus enum)
- payment_method: str (pix, credit_card, debit_card, cash, boleto)
- total_amount: Decimal(10, 2)
- delivery_address: JSONB (snapshot do endereço)
- delivery_bairro: str (índice para alocação de entregador)
- notes: str (observações)
- paid_at: datetime
- dispatched_at: datetime
- delivered_at: datetime
- cancelled_at: datetime
- cancellation_reason: str

Relacionamentos:
- customer: Customer
- items: List[OrderItem] (one-to-many)
- payments: List[Payment] (one-to-many)
- delivery: Delivery (one-to-one, nullable)

Índices:
- ix_orders_status_created (status, created_at)
- ix_orders_customer_status (customer_id, status)
- ix_orders_bairro_status (delivery_bairro, status)
```

### **5. OrderItem (Item do Pedido)**

```python
Model: OrderItem
Table: order_items
ID Type: UUID

Campos:
- id: UUID (PK)
- order_id: UUID (FK → orders)
- product_code: str (P13, P20, P45)
- product_name: str (snapshot)
- quantity: int
- unit_price: Decimal(10, 2) (snapshot)
- subtotal: Decimal(10, 2) (quantity * unit_price)

Nota: Armazena snapshot dos dados do produto no momento do pedido
```

### **6. Payment (Pagamento)**

```python
Model: Payment
Table: payments
ID Type: UUID

Status Enum: PaymentStatus
- PENDING: "pending"
- PROCESSING: "processing"
- PAID: "paid"
- FAILED: "failed"
- REFUNDED: "refunded"

Campos:
- id: UUID (PK)
- order_id: UUID (FK → orders)
- amount: Decimal(10, 2)
- payment_method: str
- status: str (PaymentStatus enum)
- provider: str (asaas, stripe, manual, etc.)
- provider_transaction_id: str
- provider_payment_url: str
- paid_at: datetime
- metadata: JSONB (dados adicionais)
```

### **7. Delivery (Entrega)** ⭐

```python
Model: Delivery
Table: deliveries
ID Type: UUID

Status Enum: DeliveryStatus
- PENDING: "pending" (aguardando alocação)
- ASSIGNED: "assigned" (entregador alocado)
- PICKED_UP: "picked_up" (retirado para entrega)
- IN_TRANSIT: "in_transit" (em trânsito)
- ARRIVED: "arrived" (chegou no destino)
- DELIVERED: "delivered" (entregue)
- FAILED: "failed" (falha na entrega)
- RETURNED: "returned" (devolvido)

Campos Principais:
- id: UUID (PK)
- order_id: UUID (FK → orders, unique)
- driver_id: UUID (nullable, FK futura → drivers)
- driver_name: str (nome do entregador)
- driver_phone: str (telefone do entregador)
- status: str (DeliveryStatus enum)
- bairro: str (bairro de destino)
- estimated_minutes: int (previsão, default: 40)
- actual_delivery_minutes: int (tempo real)
- assigned_at: datetime
- picked_up_at: datetime
- in_transit_at: datetime
- arrived_at: datetime
- delivered_at: datetime
- notes: str
- failure_reason: str
- last_location: JSONB ({lat, lng, timestamp})

Relacionamento:
- order: Order (one-to-one)

Índices:
- ix_deliveries_status_bairro (status, bairro)
- ix_deliveries_driver_status (driver_id, status)
```

### **8. Driver (Entregador)** ⭐⭐⭐ FOCO

```python
Model: Driver
Table: drivers
ID Type: UUID

Status Enum: DriverStatus
- OFFLINE: "offline" (fora do sistema)
- AVAILABLE: "available" (disponível para entregas)
- BUSY: "busy" (em entrega)
- BREAK: "break" (em pausa)

Campos Atuais:
- id: UUID (PK)
- name: str (nome completo)
- phone: str (unique, telefone)
- email: str (opcional)
- vehicle_type: str (moto, carro, etc.)
- license_plate: str (placa do veículo)
- status: str (DriverStatus enum)
- current_location: JSON ({latitude, longitude, timestamp})
- rating: float (avaliação média 0-5, default: 5.0)
- total_deliveries: int (contador de entregas)
- is_active: bool (ativo no sistema)
- last_online: datetime

Métodos:
- go_online() → Disponível
- go_offline() → Offline
- start_delivery() → Ocupado
- finish_delivery() → Disponível + incrementa contador
- is_available → bool property

Índices:
- ix_drivers_status_active (status, is_active)
- ix_drivers_phone (phone)
```

### **9. EventLog (Log de Eventos)**

```python
Model: EventLog
Table: event_logs
ID Type: UUID

Tipos de Eventos:
- ORDER_CREATED
- ORDER_STATUS_CHANGED
- PAYMENT_RECEIVED
- DELIVERY_ASSIGNED
- DELIVERY_STATUS_CHANGED
- USER_ACTION

Campos:
- id: UUID (PK)
- event_type: str (EventTypes enum)
- actor_type: str (user, system, driver, customer)
- actor_id: UUID
- entity_type: str (order, delivery, payment)
- entity_id: UUID
- description: str
- metadata: JSONB
- timestamp: datetime
```

---

## 👥 **ROLES EXISTENTES**

### **Hierarquia de Permissões:**

```
┌─────────────────────────────────────────────────┐
│  ADMIN (Administrador Total)                    │
│  ✓ Acesso completo ao sistema                   │
│  ✓ Gerenciar usuários e roles                   │
│  ✓ Configurações globais                        │
│  ✓ Relatórios completos                         │
└─────────────────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
┌───────▼────────┐    ┌─────────▼────────┐
│  OWNER (Dono)  │    │  MANAGER         │
│  ✓ Dashboard   │    │  (Gerente)       │
│    executivo   │    │  ✓ Visão regional│
│  ✓ Métricas    │    │  ✓ Equipe da     │
│  ✓ Relatórios  │    │    região        │
└────────────────┘    └──────────────────┘
        │
┌───────▼─────────────────────────────────────────┐
│  OPERATOR (Operador)                            │
│  ✓ Gerenciar pedidos                            │
│  ✓ Atendimento ao cliente                       │
│  ✓ Alocação de entregas (por bairro)            │
│  ✓ Dashboard operacional                        │
└─────────────────────────────────────────────────┘
        │
┌───────▼─────────────────────────────────────────┐
│  USER (Cliente/Usuário)                         │
│  ✓ Fazer pedidos                                │
│  ✓ Acompanhar status                            │
│  ✓ Histórico de pedidos                         │
└─────────────────────────────────────────────────┘
```

### **Role Faltante: DRIVER (Entregador)** 🚀

**Posição na Hierarquia:**

```
┌─────────────────────────────────────────────────┐
│  OPERATOR (Operador)                            │
│  Aloca entregas → Monitora entregas             │
└────────────────┬────────────────────────────────┘
                 │
        ┌────────▼─────────┐
        │  DRIVER          │ ← NOVA ROLE A CRIAR
        │  (Entregador)    │
        │                  │
        │  Recebe          │
        │  Atualiza status │
        │  Reporta         │
        └──────────────────┘
```

---

## 🔄 **FLUXO DE PEDIDOS ATUAL**

### **Ciclo de Vida Completo:**

```
1. CLIENTE FAZ PEDIDO (WhatsApp/Web)
   ↓
   Status: PENDING
   ↓

2. PAGAMENTO
   ↓
   Status: PAID
   Payment.status = "paid"
   Order.paid_at = now()
   ↓

3. PREPARAÇÃO
   ↓
   Status: PREPARING
   (Operador separa produtos)
   ↓

4. ALOCAÇÃO DE ENTREGADOR
   ↓
   Delivery.status = ASSIGNED
   Delivery.driver_id = UUID do driver
   Delivery.assigned_at = now()
   ↓

5. RETIRADA PARA ENTREGA
   ↓
   Order.status = DISPATCHED
   Delivery.status = PICKED_UP
   Order.dispatched_at = now()
   Delivery.picked_up_at = now()
   ↓

6. EM TRÂNSITO
   ↓
   Delivery.status = IN_TRANSIT
   Delivery.in_transit_at = now()
   (GPS tracking atualiza current_location)
   ↓

7. CHEGADA
   ↓
   Delivery.status = ARRIVED
   Delivery.arrived_at = now()
   ↓

8. ENTREGA CONCLUÍDA
   ↓
   Order.status = DELIVERED
   Delivery.status = DELIVERED
   Order.delivered_at = now()
   Delivery.delivered_at = now()
   Driver.total_deliveries += 1
   Driver.status = AVAILABLE
```

### **Fluxos Alternativos:**

**Cancelamento:**
```
PENDING/PAID → CANCELLED
Order.cancelled_at = now()
Order.cancellation_reason = "motivo"
```

**Falha na Entrega:**
```
IN_TRANSIT → FAILED
Delivery.status = FAILED
Delivery.failure_reason = "motivo"
Order.status pode voltar para PREPARING
```

**Devolução:**
```
FAILED → RETURNED
Delivery.status = RETURNED
Produto retorna ao estoque
```

---

## ⚙️ **FUNCIONALIDADES IMPLEMENTADAS**

### **Backend APIs Disponíveis:**

```yaml
Endpoints Principais:
- POST /api/auth/login - Autenticação JWT
- POST /api/auth/register - Cadastro de usuário
- GET /api/users - Listar usuários (admin)
- PUT /api/users/{id}/role - Alterar role (admin)
  
- POST /api/orders - Criar pedido
- GET /api/orders - Listar pedidos (paginado, filtros)
- GET /api/orders/{id} - Detalhes do pedido
- PUT /api/orders/{id}/status - Atualizar status
- DELETE /api/orders/{id} - Cancelar pedido
  
- GET /api/customers - Listar clientes
- POST /api/customers - Criar cliente
- GET /api/products - Listar produtos
  
- POST /webhooks/waha - Receber mensagens WhatsApp
- POST /webhooks/asaas - Notificações de pagamento
  
- WS /ws/dashboard - WebSocket tempo real
  - Eventos: new_order, order_update, new_message, metrics_update
  - Filtros: por role, bairro, região
  - Features: batching, persistência, replay
```

### **Features Tempo Real (WebSocket):**

```yaml
✅ Broadcast filtrado por role
✅ Broadcast por bairro/região
✅ Rate limiting (10 broadcasts/segundo)
✅ Heartbeat monitor (limpa conexões mortas)
✅ Event batching (90% menos mensagens)
✅ Redis Pub/Sub (múltiplas instâncias)
✅ Persistência + replay (reconexão inteligente)
✅ Compressão automática (permessage-deflate)
```

### **Monitoring & Observabilidade:**

```yaml
Prometheus Metrics (20+ customizadas):
- websocket_connections_total (por role, instância)
- websocket_messages_sent_total
- websocket_broadcast_duration_seconds (p95, p99)
- event_batcher_batch_size
- redis_pubsub_messages_published
- system_uptime_seconds

Grafana Dashboard (8 painéis):
- Conexões WebSocket
- Taxa de mensagens
- Latência
- Event batching
- Redis Pub/Sub
- Taxa de erros
- Uptime

Alertas (20 regras):
- Conexões altas
- Taxa de erro alta
- Latência alta
- System down
```

---

## 🚗 **DRIVER/ENTREGADOR - ESTADO ATUAL**

### **O que JÁ EXISTE:**

#### **1. Modelo de Dados Completo** ✅

```python
Driver Model (backend/app/models/driver.py):
- Campos: id, name, phone, email, vehicle_type, license_plate
- Status: offline, available, busy, break
- Localização: current_location (JSON GPS)
- Estatísticas: rating, total_deliveries
- Ativo: is_active, last_online
```

#### **2. Service Layer** ✅

```python
DriverService (backend/app/services/driver_service.py):
- list_all() - Listar todos
- list_available() - Listar disponíveis
- get_by_id() - Buscar por ID
- create() - Criar novo entregador
- update() - Atualizar dados
- delete() - Remover entregador
- go_online() - Marcar como disponível
- go_offline() - Marcar como offline
- update_location() - Atualizar GPS
- get_nearby_drivers() - Buscar próximos (placeholder)
```

#### **3. Integração com Delivery** ✅

```python
Delivery Model já referencia Driver:
- driver_id: UUID (FK para drivers)
- driver_name: str (snapshot)
- driver_phone: str (snapshot)
```

### **O que NÃO EXISTE (GAPS):**

#### **1. API Endpoints** ❌

```
Falta criar:
- GET /api/drivers - Listar entregadores
- POST /api/drivers - Criar entregador
- GET /api/drivers/{id} - Detalhes
- PUT /api/drivers/{id} - Atualizar
- DELETE /api/drivers/{id} - Remover
- PUT /api/drivers/{id}/status - Mudar status (online/offline)
- PUT /api/drivers/{id}/location - Atualizar GPS
- GET /api/drivers/available - Listar disponíveis
- GET /api/drivers/{id}/deliveries - Histórico de entregas
- GET /api/drivers/{id}/stats - Estatísticas
```

#### **2. Dashboard do Entregador** ❌

```
Frontend não existe:
- Tela de login do entregador
- Dashboard com:
  - Entregas pendentes
  - Entregas em andamento
  - Histórico
  - Estatísticas (total, avaliação)
  - Botão online/offline
  - Mapa de rota (opcional)
```

#### **3. Mobile App/PWA** ❌

```
Não existe aplicativo mobile específico para entregador
Ideal: PWA (Progressive Web App) para usar no celular
```

#### **4. Funcionalidades Avançadas** ❌

```
Não implementado:
- Push notifications (entrega alocada)
- Tracking GPS em tempo real (broadcasting)
- Cálculo de rotas otimizadas
- Estimativa de tempo de chegada
- Prova de entrega (foto, assinatura)
- Chat com cliente
- Chat com operador
- Avaliação do entregador pelo cliente
- Sistema de bonificações/gamificação
```

#### **5. WebSocket para Driver** ❌

```
Falta:
- Eventos específicos para entregadores:
  - delivery_assigned (nova entrega alocada)
  - delivery_updated (mudança de status)
  - customer_message (mensagem do cliente)
  - operator_message (mensagem do operador)

- Filtros WebSocket para role "driver" não implementados
```

---

## 🎯 **GAPS E OPORTUNIDADES**

### **Funcionalidades Críticas (MVP):**

```
1. AUTENTICAÇÃO E PERFIL
   - Login específico para entregador
   - Perfil com dados pessoais e veículo
   - Alternar status (online/offline)
   - Ver estatísticas próprias

2. GERENCIAMENTO DE ENTREGAS
   - Ver entregas disponíveis (por bairro)
   - Aceitar/rejeitar entrega
   - Ver detalhes da entrega (endereço, cliente, itens)
   - Atualizar status (retirou, em trânsito, entregue)
   - Reportar problemas (cliente ausente, endereço errado)

3. NAVEGAÇÃO
   - Ver endereço de entrega
   - Botão "Abrir no Maps" (Google Maps/Waze)
   - (Opcional) Mapa integrado

4. COMUNICAÇÃO
   - Ver telefone do cliente
   - Botão "Ligar para cliente"
   - (Opcional) Chat com cliente
   - (Opcional) Chat com operador

5. HISTÓRICO
   - Ver entregas realizadas
   - Ver entregas em andamento
   - Filtros por data
```

### **Funcionalidades Desejáveis (Fase 2):**

```
1. TRACKING GPS
   - Atualização automática de localização (cada 30s)
   - Broadcasting para operador/cliente via WebSocket
   - Estimativa de tempo de chegada (ETA)

2. PROVA DE ENTREGA
   - Tirar foto do produto entregue
   - Coletar assinatura digital
   - Upload via MinIO (S3)
   - Anexar à entrega

3. AVALIAÇÃO E FEEDBACK
   - Cliente avalia entregador (1-5 estrelas)
   - Entregador vê sua avaliação média
   - Comentários opcionais

4. NOTIFICAÇÕES PUSH
   - Nova entrega disponível
   - Entrega alocada
   - Mensagem do operador
   - Alerta de atraso

5. GAMIFICAÇÃO
   - Ranking de entregadores
   - Badges/conquistas
   - Bônus por performance
   - Meta de entregas diárias/semanais
```

### **Funcionalidades Avançadas (Futuro):**

```
1. OTIMIZAÇÃO DE ROTAS
   - Múltiplas entregas agrupadas
   - Rota otimizada (menor distância)
   - Sequenciamento automático

2. PREVISÃO DE DEMANDA
   - ML para prever picos
   - Sugestão de horários online
   - Alertas de demanda alta

3. INTEGRAÇÃO FINANCEIRA
   - Controle de ganhos
   - Pagamentos automáticos
   - Relatórios fiscais

4. GESTÃO DE EQUIPE
   - Supervisores de entregadores
   - Áreas/territórios fixos
   - Escalas de trabalho
```

---

## 🔧 **REQUISITOS TÉCNICOS**

### **Backend (FastAPI):**

```python
Criar Router: backend/app/api/drivers.py

Endpoints Mínimos:
@router.get("/drivers")  # Listar (admin/operator)
@router.post("/drivers")  # Criar (admin)
@router.get("/drivers/{id}")  # Detalhes
@router.put("/drivers/{id}")  # Atualizar
@router.delete("/drivers/{id}")  # Remover (admin)
@router.put("/drivers/{id}/status")  # Online/Offline
@router.put("/drivers/{id}/location")  # Atualizar GPS
@router.get("/drivers/{id}/deliveries")  # Histórico
@router.get("/drivers/me")  # Perfil próprio (driver logado)
@router.put("/drivers/me/status")  # Alterar próprio status

Schemas Pydantic:
- DriverCreate (name, phone, email, vehicle_type, license_plate)
- DriverUpdate (campos opcionais)
- DriverResponse (todos os campos)
- DriverStatusUpdate (status: online/offline/break)
- DriverLocationUpdate (latitude, longitude)
- DriverDeliveryHistory (lista de deliveries)
- DriverStats (total_deliveries, rating, today_deliveries)
```

### **Frontend (React):**

```javascript
Páginas a Criar:

1. /driver/login
   - Login específico para entregador
   - Usar mesmo JWT endpoint (/api/auth/login)
   - Verificar role === "driver"

2. /driver/dashboard
   - Status toggle (online/offline/pausa)
   - Entregas disponíveis (por bairro)
   - Entregas em andamento
   - Botão "Aceitar entrega"

3. /driver/delivery/{id}
   - Detalhes da entrega
   - Endereço completo
   - Itens do pedido
   - Telefone do cliente
   - Botões de ação:
     - "Retirei os produtos"
     - "Em trânsito"
     - "Cheguei"
     - "Entregue"
     - "Problema"
   - Mapa (opcional)

4. /driver/history
   - Lista de entregas realizadas
   - Filtros (hoje, semana, mês)
   - Detalhes ao clicar

5. /driver/profile
   - Dados pessoais
   - Veículo
   - Estatísticas
   - Editar perfil

Hooks React:
- useDriverStatus (online/offline)
- useDriverLocation (GPS tracking)
- useDriverDeliveries (lista de entregas)
- useWebSocketDriver (eventos em tempo real)

Componentes:
- DriverHeader (nome, status, stats)
- DeliveryCard (card de entrega)
- DeliveryMap (mapa de rota)
- StatusToggle (switch online/offline)
- DeliveryActions (botões de ação)
```

### **WebSocket:**

```python
Modificar backend/app/api/websocket.py:

1. Adicionar filtro para role "driver"
2. Eventos específicos:
   - delivery_assigned (nova entrega)
   - delivery_updated (mudança em entrega do driver)
   - operator_message (mensagem do operador)

Exemplo:
async def emit_delivery_assigned(delivery_data: dict):
    driver_id = delivery_data.get("driver_id")
    await manager.broadcast(
        message={
            "type": "delivery_assigned",
            "data": delivery_data,
            "timestamp": datetime.now().isoformat()
        },
        filter_fn=lambda m: (
            m.user_role == UserRole.DRIVER and 
            m.user_id == driver_id
        )
    )
```

### **Database Migration:**

```bash
# Tabela drivers JÁ EXISTE, mas pode precisar de campos adicionais

Campos a considerar adicionar:
- cpf: str (CPF do entregador)
- birth_date: date (data de nascimento)
- cnh_number: str (número da CNH)
- cnh_category: str (categoria da CNH: A, B, AB)
- bank_account: JSONB (dados bancários para pagamento)
- emergency_contact: JSONB (contato de emergência)
- work_schedule: JSONB (horários de trabalho)
- max_deliveries_per_day: int (limite diário)
- current_deliveries_count: int (entregas ativas no momento)
- bairros_coverage: ARRAY[str] (bairros que atende)

Criar migration:
alembic revision --autogenerate -m "add_driver_extended_fields"
alembic upgrade head
```

---

## 📊 **MÉTRICAS E KPIs**

### **Métricas para o Entregador:**

```
Visualizar no Dashboard do Driver:
- Total de entregas (hoje, semana, mês, total)
- Avaliação média (estrelas 1-5)
- Tempo médio de entrega
- Taxa de sucesso (% entregas concluídas)
- Ganhos do dia/semana/mês (se houver sistema de pagamento)
- Ranking (posição entre entregadores)
```

### **Métricas para o Operador/Admin:**

```
Adicionar no Dashboard Operacional:
- Entregadores online agora
- Entregadores ocupados
- Entregadores disponíveis (por bairro)
- Entregas pendentes de alocação
- Entregas em andamento
- Tempo médio de entrega por entregador
- Taxa de falha por entregador
- Avaliação média por entregador
```

### **Métricas Prometheus (adicionar):**

```python
# backend/app/metrics.py (adicionar)

driver_online_total = Gauge(
    'driver_online_total',
    'Total de entregadores online',
    ['status', 'instance_id']
)

driver_deliveries_total = Counter(
    'driver_deliveries_total',
    'Total de entregas por entregador',
    ['driver_id', 'status', 'instance_id']
)

driver_delivery_duration_seconds = Histogram(
    'driver_delivery_duration_seconds',
    'Tempo de entrega em segundos',
    ['driver_id', 'instance_id'],
    buckets=[300, 600, 900, 1200, 1800, 2400, 3600]  # 5min a 1h
)

driver_rating = Gauge(
    'driver_rating',
    'Avaliação do entregador',
    ['driver_id', 'instance_id']
)
```

---

## 🎬 **PRÓXIMOS PASSOS RECOMENDADOS**

### **Fase 1: MVP (1-2 semanas)**

```
1. Backend API para Driver
   - Criar endpoints REST
   - Adicionar role "driver" ao UserRole enum
   - Implementar autenticação/autorização
   - Testar com Postman/Thunder Client

2. Frontend Dashboard Básico
   - Tela de login
   - Dashboard principal (status, entregas disponíveis)
   - Tela de detalhes da entrega
   - Ações básicas (aceitar, atualizar status)

3. WebSocket para Driver
   - Eventos de entrega alocada
   - Broadcast filtrado por driver_id

4. Testes
   - Criar entregador
   - Alocar entrega
   - Atualizar status
   - Verificar WebSocket
```

### **Fase 2: Funcionalidades Essenciais (2-3 semanas)**

```
1. GPS Tracking
   - Atualização automática de localização
   - Broadcasting para operador/cliente

2. Histórico e Estatísticas
   - Página de histórico
   - Dashboard de stats

3. Comunicação
   - Botão de ligação para cliente
   - (Opcional) Chat integrado

4. Melhorias UX
   - Notificações
   - Feedback visual
   - Carregamento otimizado
```

### **Fase 3: Features Avançadas (3-4 semanas)**

```
1. Prova de Entrega
   - Upload de fotos
   - Assinatura digital

2. Avaliação
   - Sistema de rating
   - Feedback do cliente

3. Mobile PWA
   - Otimização mobile
   - Instalável como app

4. Gamificação
   - Ranking
   - Badges
   - Metas
```

---

## 📚 **DOCUMENTAÇÃO DE REFERÊNCIA**

### **Arquivos Relevantes:**

```
Backend:
- backend/app/models/driver.py (Modelo Driver)
- backend/app/models/delivery.py (Modelo Delivery)
- backend/app/models/order.py (Modelo Order)
- backend/app/services/driver_service.py (Service Driver)
- backend/app/services/delivery_service.py (Service Delivery)
- backend/app/api/websocket.py (WebSocket)
- backend/app/api/orders.py (API Orders)
- backend/app/auth.py (Autenticação)

Frontend:
- frontend/src/pages/owner/OwnerDashboard.jsx (exemplo de dashboard)
- frontend/src/services/api.js (serviços de API)
- frontend/src/hooks/useSharedWebSocket.js (WebSocket hook)

Documentação:
- FASE_1_IMPLEMENTADA.md (WebSocket escalável)
- FASE_2_IMPLEMENTADA.md (Otimizações)
- FASE_3_COMPLETA.md (Escala avançada)
- GUIA_ACESSO_GRAFANA.md (Monitoring)
```

### **URLs de Acesso:**

```
Backend API: http://192.168.10.156:8000
API Docs: http://192.168.10.156:8000/docs
Frontend: http://192.168.10.156:3001
Grafana: http://192.168.10.156:3002
Prometheus: http://192.168.10.156:9090
pgAdmin: http://192.168.10.156:5050
```

---

## 🎯 **RESUMO EXECUTIVO PARA IA GESTORA**

### **Contexto:**

- Sistema de pedidos de gás via WhatsApp **em produção**
- Stack moderno: FastAPI + React + PostgreSQL + Redis
- **Fase 3 completa**: Sistema escalável (50k+ pedidos/semana)
- Modelo de Driver **JÁ EXISTE** no banco
- Service layer **JÁ IMPLEMENTADO**

### **Gap Principal:**

**Falta implementar a interface e funcionalidades específicas do entregador:**
- Endpoints API REST
- Dashboard frontend
- WebSocket events para driver
- Mobile-friendly UI
- Funcionalidades operacionais

### **Oportunidade:**

Criar uma **experiência completa para o entregador** que:
1. Facilite o trabalho diário
2. Aumente a eficiência de entrega
3. Melhore a satisfação do cliente
4. Forneça dados para otimização

### **Prioridades:**

1. **MVP rápido** (1-2 semanas): Login + Dashboard + Entregas + Status
2. **Features essenciais** (2-3 semanas): GPS + Histórico + Comunicação
3. **Experiência completa** (3-4 semanas): Prova + Avaliação + Gamificação

---

## 📞 **INFORMAÇÕES ADICIONAIS**

**Stack Completo:**
- Backend: Python 3.11 + FastAPI + SQLAlchemy + PostgreSQL + Redis
- Frontend: React 18 + Vite + Axios + WebSocket
- Infra: Docker + Traefik + Prometheus + Grafana
- Capacidade: 50.000+ pedidos/semana, 500+ users simultâneos

**Estado Atual:**
- ✅ Sistema em produção
- ✅ Websocket escalável (Fase 3 completa)
- ✅ Modelo Driver implementado
- ✅ Service Layer pronto
- ❌ Interface do entregador faltando

**Objetivo:**
Desenhar e implementar uma solução completa e moderna para os entregadores,
aproveitando toda a infraestrutura já existente.

---

**Documento criado em:** 21 de Janeiro de 2026  
**Para uso com:** IA Gestora - Design de Funcionalidades Driver  
**Validade:** Sistema em constante evolução

---

**PRONTO PARA ANÁLISE E DESIGN!** 🚀
