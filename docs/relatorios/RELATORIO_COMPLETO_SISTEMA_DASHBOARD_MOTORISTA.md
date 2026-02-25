# RELATÓRIO EXECUTIVO E TÉCNICO COMPLETO
## Sistema Gas Automation - Dashboard do Motorista

**Data:** 28 de Janeiro de 2026  
**Versão do Sistema:** 1.0  
**Objetivo:** Documentação completa para recriação do Dashboard do Motorista

---

## 📋 SUMÁRIO EXECUTIVO

### Visão Geral do Sistema

O **Gas Automation** é um sistema completo de gestão de entregas de gás, desenvolvido para automatizar todo o ciclo de vida de pedidos, desde a criação até a entrega final. O sistema possui múltiplos dashboards especializados para diferentes perfis de usuário:

- **Dashboard do Operador**: Gestão de pedidos, conversas, clientes
- **Dashboard do Admin**: Gestão completa do sistema, usuários, configurações
- **Dashboard do Owner**: Visão executiva, relatórios financeiros, análises
- **Dashboard do Motorista**: Foco na operação de campo, entregas, rastreamento

### Problema Identificado

O **Dashboard do Motorista** atual apresenta problemas funcionais que impedem seu uso adequado em produção. Este relatório fornece todas as informações necessárias para uma recriação completa e funcional do dashboard.

### Escopo do Relatório

Este documento cobre:
1. Arquitetura técnica completa do sistema
2. Modelos de dados e relacionamentos
3. APIs e endpoints disponíveis
4. Fluxos de negócio críticos
5. Especificações detalhadas do Dashboard do Motorista
6. Problemas conhecidos e limitações
7. Requisitos para recriação

---

## 🏗️ ARQUITETURA TÉCNICA

### Stack Tecnológico

#### Backend
- **Framework**: FastAPI (Python 3.8+)
- **ORM**: SQLAlchemy (async)
- **Banco de Dados**: PostgreSQL
- **Migrações**: Alembic
- **Validação**: Pydantic
- **Autenticação**: JWT (OAuth2PasswordBearer)
- **WebSocket**: FastAPI WebSocket + Redis Pub/Sub
- **Eventos**: Redis Streams
- **Integrações**: WAHA (WhatsApp HTTP API), Firebird (exportação)

#### Frontend
- **Framework**: React 18+
- **Roteamento**: React Router v6
- **Estado**: React Hooks (useState, useEffect, useCallback)
- **HTTP Client**: Fetch API nativo
- **Notificações**: react-hot-toast
- **Estilização**: Tailwind CSS
- **Icons**: Lucide React + Emojis

#### Infraestrutura
- **Containerização**: Docker + Docker Compose
- **Monitoramento**: Prometheus + Grafana
- **Cache/Mensageria**: Redis
- **Servidor Web**: Uvicorn (ASGI)

### Arquitetura de Camadas

```
┌─────────────────────────────────────────┐
│         Frontend (React)                │
│  - Pages (DriverDashboard, etc)         │
│  - Components (DriverHeader, etc)       │
│  - Utils (driverApi.js)                 │
│  - Hooks (useWebSocketDriver)           │
└──────────────┬──────────────────────────┘
               │ HTTP/REST + WebSocket
┌──────────────▼──────────────────────────┐
│         Backend (FastAPI)               │
│  - API Routes (drivers.py, cargas.py)   │
│  - Services (driver_time_tracking)      │
│  - Models (Driver, Delivery, Carga)     │
│  - Schemas (Pydantic)                   │
│  - Auth (JWT)                           │
└──────────────┬──────────────────────────┘
               │ SQL + Redis
┌──────────────▼──────────────────────────┐
│      PostgreSQL + Redis                 │
│  - Dados persistentes                   │
│  - Eventos/Streams                      │
│  - Pub/Sub (WebSocket bridge)          │
└─────────────────────────────────────────┘
```

### Padrões de Design

- **Repository Pattern**: Models SQLAlchemy encapsulam lógica de dados
- **Service Layer**: Services contêm lógica de negócio
- **Dependency Injection**: FastAPI Depends para injeção de dependências
- **Event-Driven**: Redis Streams para eventos assíncronos
- **Real-time Updates**: WebSocket para atualizações em tempo real

---

## 📊 MODELOS DE DADOS

### Modelo: Driver (Entregador)

**Tabela**: `drivers`

```python
class Driver(BaseModel):
    id: UUID (PK)
    name: str (100) - Nome completo
    phone: str (20, UNIQUE, INDEX) - Telefone (usado como username)
    email: str (100, nullable) - Email opcional
    vehicle_type: str (50, nullable) - Tipo de veículo
    license_plate: str (10, nullable) - Placa do veículo
    status: str (20, INDEX) - Status atual
        Valores: "offline", "available", "busy", "break"
    current_location: JSON (nullable) - GPS atual
        Formato: {"latitude": float, "longitude": float, "timestamp": str}
    rating: float (default: 5.0) - Avaliação média (0-5)
    total_deliveries: int (default: 0) - Total de entregas
    is_active: bool (default: True) - Ativo no sistema
    last_online: datetime (nullable) - Última vez online
    created_at: datetime
    updated_at: datetime
```

**Relacionamentos**:
- `time_logs`: List[DriverTimeLog] - Logs de tempo trabalhado
- `cargas`: List[CargaVeiculo] - Cargas do veículo

**Métodos Importantes**:
- `go_online()` - Coloca online
- `go_offline()` - Coloca offline
- `start_delivery()` - Marca como ocupado
- `finish_delivery()` - Volta para disponível
- `is_available` (property) - Verifica se está disponível

### Modelo: Delivery (Entrega)

**Tabela**: `deliveries`

```python
class Delivery(BaseModel):
    id: UUID (PK)
    order_id: UUID (FK -> orders.id, UNIQUE) - Pedido relacionado
    driver_id: UUID (nullable, INDEX) - ID do entregador
    driver_name: str (100, nullable) - Nome do entregador
    driver_phone: str (20, nullable) - Telefone do entregador
    status: str (50, INDEX) - Status atual
        Valores: "pending", "assigned", "picked_up", "in_transit", 
                 "arrived", "delivered", "failed", "returned"
    bairro: str (100, nullable, INDEX) - Bairro de destino
    estimated_minutes: int (nullable, default: 40) - Previsão em minutos
    actual_delivery_minutes: int (nullable) - Tempo real de entrega
    assigned_at: datetime (nullable) - Quando foi alocado
    picked_up_at: datetime (nullable) - Quando retirou produtos
    in_transit_at: datetime (nullable) - Quando saiu para entrega
    arrived_at: datetime (nullable) - Quando chegou no destino
    delivered_at: datetime (nullable) - Quando entregou
    notes: text (nullable) - Observações
    failure_reason: str (500, nullable) - Motivo da falha
    last_location: JSONB (nullable) - Última localização GPS
    created_at: datetime
    updated_at: datetime
```

**Relacionamentos**:
- `order`: Order - Pedido relacionado (1:1)

**Métodos Importantes**:
- `update_status(new_status)` - Atualiza status e timestamp correspondente
- `is_active` (property) - Verifica se está em andamento
- `is_completed` (property) - Verifica se foi finalizada

### Modelo: DriverTimeLog (Log de Tempo)

**Tabela**: `driver_time_logs`

```python
class DriverTimeLog(Base):
    id: UUID (PK)
    driver_id: UUID (FK -> drivers.id, CASCADE)
    status: str (20) - Status do período
        Valores: "available", "offline", "busy", "break"
    started_at: datetime (timezone) - Início do período
    ended_at: datetime (timezone, nullable) - Fim do período
    duration_minutes: int (nullable) - Duração calculada
    date: date (INDEX) - Data do log
    extra_data: JSONB (nullable) - Metadados extras
    created_at: datetime
```

**Métodos Importantes**:
- `finalize()` - Finaliza o log calculando duração (limita a 16h máximo)

### Modelo: CargaVeiculo (Carga do Veículo)

**Tabela**: `cargas_veiculo`

```python
class CargaVeiculo(BaseModel):
    id: UUID (PK)
    driver_id: UUID (FK -> drivers.id, INDEX) - Motorista responsável
    data_saida: datetime (nullable) - Data/hora da saída
    data_retorno: datetime (nullable) - Data/hora do retorno
    status: str (20, INDEX) - Status atual
        Valores: "criada", "em_rota", "finalizada"
    observacoes: str (500, nullable) - Observações gerais
    created_at: datetime
    updated_at: datetime
```

**Relacionamentos**:
- `driver`: Driver - Motorista responsável
- `itens`: List[CargaItem] - Itens da carga

### Modelo: CargaItem (Item da Carga)

**Tabela**: `carga_itens`

```python
class CargaItem(BaseModel):
    id: UUID (PK)
    carga_id: UUID (FK -> cargas_veiculo.id)
    produto_id: UUID (FK -> products.id)
    qtd_saida: int (default: 0) - Quantidade que saiu (cheios)
    qtd_retorno_cheio: int (default: 0) - Quantidade que retornou cheia
    qtd_retorno_vazio: int (default: 0) - Quantidade de vazios retornados
    qtd_vendida: int (default: 0) - Quantidade efetivamente vendida
    created_at: datetime
    updated_at: datetime
```

**Métodos Importantes**:
- `qtd_pendente` (property) - Calcula quantidade não contabilizada
- `validar_acerto()` - Valida se acerto está correto

### Modelo: Order (Pedido)

**Tabela**: `orders`

```python
class Order(BaseModel):
    id: UUID (PK)
    order_number: int (UNIQUE, INDEX) - Número do pedido
    customer_id: UUID (FK -> customers.id, NOT NULL) - Cliente
    status: str (50, INDEX) - Status atual
        Valores: "pending", "paid", "preparing", "dispatched", 
                 "delivered", "cancelled"
    total_amount: Decimal - Valor total
    delivery_address: JSONB - Endereço de entrega
    items: List[OrderItem] - Itens do pedido
    delivery: Delivery - Entrega relacionada (1:1)
    created_at: datetime
    updated_at: datetime
```

---

## 🔌 APIs E ENDPOINTS

### Base URL
```
Backend: http://192.168.10.156:8000/api
Frontend: http://192.168.10.156:3000 (ou porta configurada)
```

### Autenticação

**Endpoint**: `POST /api/auth/login`

**Request**:
```json
{
  "email": "driver@example.com",
  "password": "senha123"
}
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "role": "driver",
  "user": {
    "id": "...",
    "username": "11999999999",
    "email": "driver@example.com",
    "role": "driver"
  }
}
```

**Headers Necessários**:
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

### Endpoints do Driver

#### 1. Obter Perfil do Driver Logado

**Endpoint**: `GET /api/drivers/me`

**Headers**: `Authorization: Bearer {token}`

**Response Model**: `DriverResponse`
```json
{
  "id": "uuid",
  "name": "João Silva",
  "phone": "11999999999",
  "email": "joao@example.com",
  "vehicle_type": "moto",
  "license_plate": "ABC1234",
  "status": "available",
  "current_location": {
    "latitude": -23.5505,
    "longitude": -46.6333,
    "timestamp": "2026-01-28T10:00:00"
  },
  "rating": 4.8,
  "total_deliveries": 150,
  "is_active": true,
  "last_online": "2026-01-28T10:00:00Z",
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-28T10:00:00Z"
}
```

**Permissões**: `role = "driver"`

#### 2. Atualizar Status do Driver

**Endpoint**: `PUT /api/drivers/me/status`

**Request**:
```json
{
  "status": "available"  // "offline", "available", "busy", "break"
}
```

**Response**: `DriverResponse` (mesmo formato do GET /me)

**Efeitos Colaterais**:
- Atualiza `last_online` se status for "available" ou "busy"
- Cria log em `DriverTimeLog` via `DriverTimeTrackingService`

#### 3. Atualizar Localização GPS

**Endpoint**: `PUT /api/drivers/me/location`

**Request**:
```json
{
  "latitude": -23.5505,
  "longitude": -46.6333
}
```

**Response**: `DriverResponse`

#### 4. Obter Estatísticas do Driver

**Endpoint**: `GET /api/drivers/me/stats`

**Response Model**: `DriverStats`
```json
{
  "driver_id": "uuid",
  "driver_name": "João Silva",
  "total_deliveries": 150,
  "today_deliveries": 5,
  "week_deliveries": 25,
  "month_deliveries": 80,
  "rating": 4.8,
  "average_delivery_time_minutes": 35.5,
  "success_rate": 98.5,
  "status": "available"
}
```

**Cálculos**:
- `today_deliveries`: Conta entregas com `delivered_at >= hoje 00:00` e `status = "delivered"`
- `week_deliveries`: Conta entregas da semana atual
- `month_deliveries`: Conta entregas do mês atual
- `average_delivery_time_minutes`: Média de `actual_delivery_minutes` das entregas entregues
- `success_rate`: (entregas entregues / total de entregas) * 100

#### 5. Obter Entregas do Driver

**Endpoint**: `GET /api/drivers/me/deliveries?status={status}`

**Query Parameters**:
- `status` (opcional): `"pending"`, `"active"`, `"completed"`, ou `null` para todas

**Response**: `List[dict]`
```json
[
  {
    "id": "uuid",
    "order_id": "uuid",
    "order_number": 1234,
    "status": "assigned",
    "bairro": "Centro",
    "delivery_address": {
      "street": "Rua Exemplo",
      "number": "123",
      "complement": "Apto 45",
      "bairro": "Centro",
      "city": "São Paulo",
      "cep": "01234-567"
    },
    "estimated_minutes": 40,
    "assigned_at": "2026-01-28T10:00:00Z",
    "picked_up_at": null,
    "in_transit_at": null,
    "arrived_at": null,
    "delivered_at": null,
    "notes": null,
    "order_total": 150.00,
    "order_items": [
      {
        "product_code": "GAS001",
        "product_name": "Gás P13",
        "quantity": 2
      }
    ]
  }
]
```

**Lógica de Filtros**:
- `status=pending`: Entregas com `status = "pending"` (sem driver alocado)
- `status=active`: Entregas do driver com status em `["assigned", "picked_up", "in_transit", "arrived"]`
- `status=completed`: Entregas do driver com status em `["delivered", "failed", "returned"]`
- Sem `status`: Todas as entregas do driver

#### 6. Atualizar Status da Entrega

**Endpoint**: `PUT /api/drivers/deliveries/{delivery_id}/status`

**Request**:
```json
{
  "status": "picked_up",  // "picked_up", "in_transit", "arrived", "delivered"
  "notes": "Observações opcionais"
}
```

**Response**:
```json
{
  "id": "uuid",
  "status": "picked_up",
  "message": "Status atualizado com sucesso"
}
```

**Efeitos Colaterais**:
- Atualiza `Delivery.status` e timestamp correspondente
- Se `status = "picked_up"`: Atualiza `Order.status = "dispatched"` e `Order.dispatched_at`
- Se `status = "delivered"`: 
  - Atualiza `Order.status = "delivered"` e `Order.delivered_at`
  - Atualiza `Driver.status = "available"`
  - Incrementa `Driver.total_deliveries`

**Validações**:
- Driver deve ser o dono da entrega (`delivery.driver_id == driver.id`)
- Status deve ser válido e seguir ordem lógica

#### 7. Reportar Problema na Entrega

**Endpoint**: `POST /api/drivers/deliveries/{delivery_id}/problem`

**Request**:
```json
{
  "problem_type": "customer_absent",  // "customer_absent", "wrong_address", "product_issue", "payment_issue", "other"
  "description": "Cliente não estava em casa"
}
```

**Response**:
```json
{
  "id": "uuid",
  "status": "failed",
  "message": "Problema reportado com sucesso. Operador será notificado."
}
```

**Efeitos Colaterais**:
- Marca `Delivery.status = "failed"`
- Salva `Delivery.failure_reason = "[problem_type] description"`
- TODO: Notificar operador via WebSocket
- TODO: Criar log de evento

#### 8. Obter Resumo de Tempo Trabalhado

**Endpoint**: `GET /api/drivers/me/time-summary?period={period}`

**Query Parameters**:
- `period`: `"today"`, `"week"`, `"month"`

**Response Model**: `DriverTimeSummary`
```json
{
  "driver_id": "uuid",
  "driver_name": "João Silva",
  "current_status": "available",
  "rating": 4.8,
  "period": {
    "start": "2026-01-28",
    "end": "2026-01-28"
  },
  "by_status": {
    "available": {
      "minutes": 240,
      "hours": 4.0,
      "count": 3
    },
    "busy": {
      "minutes": 180,
      "hours": 3.0,
      "count": 5
    },
    "break": {
      "minutes": 30,
      "hours": 0.5,
      "count": 1
    }
  },
  "total_minutes": 450,
  "total_hours": 7.5
}
```

**Cálculos**:
- Agrupa `DriverTimeLog` por `status`
- Soma `duration_minutes` para cada status
- Calcula `total_minutes` e `total_hours`
- Conta períodos (`count`) por status

### Endpoints de Carga do Veículo

#### 9. Obter Carga Atual do Motorista

**Endpoint**: `GET /api/cargas/driver/{driver_id}/atual`

**Response Model**: `CargaAtualResponse`
```json
{
  "id": "uuid",
  "driver_id": "uuid",
  "driver_nome": "João Silva",
  "status": "criada",  // "criada", "em_rota", "finalizada"
  "data_saida": null,
  "data_retorno": null,
  "observacoes": null,
  "itens": [
    {
      "id": "uuid",
      "produto_id": "uuid",
      "produto_nome": "Gás P13",
      "produto_codigo": "GAS001",
      "qtd_saida": 10,
      "qtd_retorno_cheio": 0,
      "qtd_retorno_vazio": 0,
      "qtd_vendida": 0,
      "qtd_pendente": 10
    }
  ],
  "total_itens": 1,
  "total_produtos": 10,
  "created_at": "2026-01-28T08:00:00Z",
  "updated_at": "2026-01-28T08:00:00Z"
}
```

**Lógica**:
- Busca carga com `status != "finalizada"` do driver
- Retorna `null` se não houver carga ativa

#### 10. Registrar Saída com Carga

**Endpoint**: `POST /api/cargas/{carga_id}/saida`

**Response**: `CargaResponse`

**Efeitos Colaterais**:
- Atualiza `CargaVeiculo.status = "em_rota"`
- Atualiza `CargaVeiculo.data_saida = datetime.now()`

#### 11. Realizar Acerto da Carga

**Endpoint**: `POST /api/cargas/{carga_id}/acerto`

**Request**:
```json
{
  "itens": [
    {
      "produto_id": "uuid",
      "qtd_retorno_cheio": 2,
      "qtd_retorno_vazio": 5,
      "qtd_vendida": 3
    }
  ],
  "observacoes": "Tudo certo"
}
```

**Response**: `CargaResponse`

**Validações**:
- `qtd_vendida + qtd_retorno_cheio <= qtd_saida` para cada item
- `qtd_retorno_vazio` pode ser maior que `qtd_saida` (vazios de entregas anteriores)

**Efeitos Colaterais**:
- Atualiza `CargaItem` com valores de acerto
- Atualiza `CargaVeiculo.status = "finalizada"`
- Atualiza `CargaVeiculo.data_retorno = datetime.now()`

---

## 🔄 FLUXOS DE NEGÓCIO

### Fluxo 1: Login e Autenticação do Motorista

```
1. Motorista acessa /driver/login
2. Informa email e senha
3. POST /api/auth/login
4. Backend valida credenciais
5. Backend verifica se role = "driver"
6. Backend retorna JWT token
7. Frontend salva token no localStorage
8. Frontend redireciona para /driver/dashboard
```

**Validações**:
- Email e senha obrigatórios
- Usuário deve existir e estar ativo
- Role deve ser "driver"
- Token JWT expira em tempo configurado (padrão: 24h)

### Fluxo 2: Carregamento do Dashboard

```
1. DriverDashboard monta
2. useEffect dispara fetchData()
3. Paralelo:
   - GET /api/drivers/me (perfil)
   - GET /api/drivers/me/stats (estatísticas)
   - GET /api/drivers/me/deliveries?status=active (entregas ativas)
   - GET /api/drivers/me/deliveries?status=pending (entregas disponíveis)
4. WebSocket conecta (useWebSocketDriver)
5. Estado atualizado com dados recebidos
6. Auto-refresh a cada 30 segundos
```

**Tratamento de Erros**:
- Se 401: Limpa localStorage e redireciona para login
- Se erro de rede: Mostra mensagem de erro
- Se dados incompletos: Mostra loading ou estado vazio

### Fluxo 3: Mudança de Status do Motorista

```
1. Motorista clica no status no header
2. Seleciona novo status (offline/available/busy/break)
3. PUT /api/drivers/me/status { status: "available" }
4. Backend atualiza Driver.status
5. Backend atualiza Driver.last_online (se aplicável)
6. Backend chama DriverTimeTrackingService.start_time_log()
7. Backend finaliza log anterior (se houver)
8. Backend cria novo DriverTimeLog
9. Response retorna Driver atualizado
10. Frontend atualiza estado local
11. WebSocket broadcast para operadores (se implementado)
```

### Fluxo 4: Aceitar e Gerenciar Entrega

```
1. Motorista vê entrega disponível (status=pending)
2. Clica no card da entrega
3. Navega para /driver/delivery/{delivery_id}
4. DeliveryDetail carrega dados da entrega
5. Motorista atualiza status:
   
   a) RETIRAR PRODUTOS:
      - PUT /api/drivers/deliveries/{id}/status { status: "picked_up" }
      - Backend atualiza Delivery.status = "picked_up"
      - Backend atualiza Delivery.picked_up_at
      - Backend atualiza Order.status = "dispatched"
      - Backend atualiza Order.dispatched_at
   
   b) SAIR PARA ENTREGA:
      - PUT /api/drivers/deliveries/{id}/status { status: "in_transit" }
      - Backend atualiza Delivery.status = "in_transit"
      - Backend atualiza Delivery.in_transit_at
   
   c) CHEGAR NO LOCAL:
      - PUT /api/drivers/deliveries/{id}/status { status: "arrived" }
      - Backend atualiza Delivery.status = "arrived"
      - Backend atualiza Delivery.arrived_at
   
   d) ENTREGAR:
      - PUT /api/drivers/deliveries/{id}/status { status: "delivered" }
      - Backend atualiza Delivery.status = "delivered"
      - Backend atualiza Delivery.delivered_at
      - Backend calcula actual_delivery_minutes
      - Backend atualiza Order.status = "delivered"
      - Backend atualiza Order.delivered_at
      - Backend atualiza Driver.status = "available"
      - Backend incrementa Driver.total_deliveries
      - Frontend redireciona para dashboard após 2s
```

**Validações**:
- Driver deve ser dono da entrega
- Status deve seguir ordem lógica
- Não pode pular etapas

### Fluxo 5: Reportar Problema na Entrega

```
1. Motorista clica em "Reportar Problema"
2. Modal abre com formulário
3. Seleciona tipo de problema
4. Preenche descrição
5. POST /api/drivers/deliveries/{id}/problem
6. Backend marca Delivery.status = "failed"
7. Backend salva Delivery.failure_reason
8. TODO: Notificar operador via WebSocket
9. TODO: Criar EventLog
10. Response confirma problema reportado
11. Frontend mostra mensagem de sucesso
12. Frontend atualiza estado da entrega
```

### Fluxo 6: Gerenciar Carga do Veículo

```
1. Motorista acessa /driver/carga/acerto
2. GET /api/cargas/driver/{driver_id}/atual
3. Se carga existe e status = "criada":
   - Mostra botão "Registrar Saída"
   - POST /api/cargas/{carga_id}/saida
   - Backend atualiza status = "em_rota" e data_saida
   
4. Se carga existe e status = "em_rota":
   - Mostra formulário de acerto
   - Lista itens com qtd_saida
   - Motorista preenche:
     * qtd_retorno_cheio
     * qtd_retorno_vazio
     * qtd_vendida
   - POST /api/cargas/{carga_id}/acerto
   - Backend valida: qtd_vendida + qtd_retorno_cheio <= qtd_saida
   - Backend atualiza CargaItem
   - Backend atualiza CargaVeiculo.status = "finalizada"
   - Backend atualiza CargaVeiculo.data_retorno
```

---

## 📱 ESPECIFICAÇÕES DO DASHBOARD DO MOTORISTA

### Estrutura de Páginas

#### 1. DriverLogin (`/driver/login`)

**Componente**: `frontend/src/pages/driver/DriverLogin.jsx`

**Funcionalidades**:
- Formulário de login (email, senha)
- Validação de campos
- Chamada para `driverApi.login()`
- Redirecionamento para `/driver/dashboard` após login bem-sucedido
- Tratamento de erros (usuário não é driver, credenciais inválidas)

**Estados**:
- `loading`: boolean
- `error`: string

#### 2. DriverDashboard (`/driver/dashboard`)

**Componente**: `frontend/src/pages/driver/DriverDashboard.jsx`

**Estrutura Visual**:
```
┌─────────────────────────────────────┐
│  DriverHeader (fixo no topo)        │
├─────────────────────────────────────┤
│  📊 Estatísticas Hoje               │
│  [StatsCard - 3 cards]               │
├─────────────────────────────────────┤
│  ⏱️ Meu Tempo Trabalhado            │
│  [MyTimePanel]                      │
├─────────────────────────────────────┤
│  🚚 Entregas em Andamento (N)       │
│  [DeliveryCard...]                  │
├─────────────────────────────────────┤
│  📦 Entregas Disponíveis (N)       │
│  [DeliveryCard...]                  │
└─────────────────────────────────────┘
│  Bottom Navigation (fixo)            │
│  [Início] [Acerto] [Histórico] [Perfil]
└─────────────────────────────────────┘
```

**Componentes Utilizados**:
- `DriverHeader`: Header com nome, status, rating
- `StatsCard`: Cards de estatísticas (entregas hoje, rating, tempo médio)
- `MyTimePanel`: Painel de tempo trabalhado
- `DeliveryCard`: Card de entrega (reutilizado)

**Estados**:
- `driver`: DriverResponse | null
- `stats`: DriverStats | null
- `activeDeliveries`: Delivery[]
- `pendingDeliveries`: Delivery[]
- `loading`: boolean
- `error`: string
- `refreshing`: boolean

**Funcionalidades**:
- Carregamento inicial de dados (paralelo)
- Auto-refresh a cada 30 segundos
- Refresh manual (botão)
- WebSocket para atualizações em tempo real
- Navegação para detalhes da entrega
- Mudança de status do motorista

**WebSocket Events**:
- `delivery_assigned`: Nova entrega alocada
- `delivery_updated`: Entrega atualizada
- `operator_message`: Mensagem do operador

#### 3. DeliveryDetail (`/driver/delivery/:id`)

**Componente**: `frontend/src/pages/driver/DeliveryDetail.jsx`

**Estrutura Visual**:
```
┌─────────────────────────────────────┐
│  Header com voltar                  │
├─────────────────────────────────────┤
│  Pedido #1234                       │
│  Status: 🟦 Alocado                 │
├─────────────────────────────────────┤
│  📍 Endereço                        │
│  Rua Exemplo, 123                   │
│  [Abrir no Maps] [Ligar]           │
├─────────────────────────────────────┤
│  📦 Itens                           │
│  • 2x Gás P13                       │
│  • 1x Gás P45                       │
├─────────────────────────────────────┤
│  💰 Total: R$ 150,00                │
├─────────────────────────────────────┤
│  ⏱️ Tempo Estimado: 40 min         │
├─────────────────────────────────────┤
│  [Próxima Ação: Retirei os Produtos]│
│  [Reportar Problema]               │
└─────────────────────────────────────┘
```

**Funcionalidades**:
- Carregar detalhes da entrega
- Mostrar endereço completo
- Botão "Abrir no Maps" (Google Maps)
- Botão "Ligar para Cliente" (tel:)
- Atualizar status da entrega (próxima ação)
- Reportar problema
- Validação de status (não pode pular etapas)

**Estados**:
- `delivery`: Delivery | null
- `loading`: boolean
- `updating`: boolean
- `error`: string
- `showProblemModal`: boolean

#### 4. AcertoCarga (`/driver/carga/acerto`)

**Componente**: `frontend/src/pages/driver/AcertoCarga.jsx`

**Funcionalidades**:
- Buscar carga atual do motorista
- Registrar saída (se status = "criada")
- Formulário de acerto (se status = "em_rota")
- Validação de quantidades
- Submissão do acerto

**Estrutura do Formulário**:
```
┌─────────────────────────────────────┐
│  Carga do Veículo                   │
│  Status: Em Rota                    │
├─────────────────────────────────────┤
│  Produto: Gás P13                   │
│  Saída: 10                          │
│  ┌─────────────────────────────┐   │
│  │ Retorno Cheio: [__]         │   │
│  │ Retorno Vazio: [__]         │   │
│  │ Vendida: [__]               │   │
│  └─────────────────────────────┘   │
│  Pendente: 10                        │
├─────────────────────────────────────┤
│  Observações: [textarea]             │
│  [Finalizar Acerto]                  │
└─────────────────────────────────────┘
```

#### 5. DeliveryHistory (`/driver/history`)

**Componente**: `frontend/src/pages/driver/DeliveryHistory.jsx`

**Funcionalidades**:
- Listar entregas finalizadas do motorista
- Filtrar por período (hoje, semana, mês)
- Mostrar detalhes de cada entrega
- Navegar para detalhes

#### 6. DriverProfile (`/driver/profile`)

**Componente**: `frontend/src/pages/driver/DriverProfile.jsx`

**Funcionalidades**:
- Mostrar perfil do motorista
- Editar informações (se permitido)
- Alterar senha
- Logout

### Componentes Reutilizáveis

#### DriverHeader

**Arquivo**: `frontend/src/components/driver/DriverHeader.jsx`

**Props**:
- `driver`: DriverResponse
- `onStatusChange`: (status: string) => Promise<void>
- `wsConnected`: boolean

**Funcionalidades**:
- Exibir nome e foto do motorista
- Dropdown de status (offline/available/busy/break)
- Indicador de conexão WebSocket
- Rating e total de entregas

**Estados**:
- `showStatusMenu`: boolean

#### StatsCard

**Arquivo**: `frontend/src/components/driver/StatsCard.jsx`

**Props**:
- `stats`: DriverStats

**Funcionalidades**:
- Exibir 3 cards:
  1. Entregas hoje
  2. Rating
  3. Tempo médio de entrega

#### DeliveryCard

**Arquivo**: `frontend/src/components/driver/DeliveryCard.jsx`

**Props**:
- `delivery`: Delivery
- `onAction`: () => void
- `isPending`: boolean (opcional)

**Funcionalidades**:
- Exibir número do pedido
- Status com cor e ícone
- Endereço resumido
- Lista de itens
- Valor total
- Tempo estimado
- Timestamp de alocação (se não pendente)

**Cores por Status**:
- `pending`: Amarelo (bg-yellow-100)
- `assigned`: Azul (bg-blue-100)
- `picked_up`: Laranja (bg-orange-100)
- `in_transit`: Azul (bg-blue-100)
- `arrived`: Roxo (bg-purple-100)
- `delivered`: Verde (bg-green-100)

#### MyTimePanel

**Arquivo**: `frontend/src/components/driver/MyTimePanel.jsx`

**Props**: Nenhuma (usa driverApi internamente)

**Funcionalidades**:
- Buscar resumo de tempo trabalhado
- Filtrar por período (hoje, semana, mês)
- Exibir tempo total trabalhado
- Breakdown por status (available, busy, break, offline)
- Barras de progresso por status
- Percentuais de tempo por status

**Estados**:
- `period`: "today" | "week" | "month"
- `timeData`: DriverTimeSummary | null
- `loading`: boolean

### WebSocket Integration

**Hook**: `frontend/src/hooks/useWebSocketDriver.js`

**Funcionalidades**:
- Conectar ao WebSocket do backend
- Escutar eventos específicos do driver
- Callbacks para eventos:
  - `onDeliveryAssigned`
  - `onDeliveryUpdated`
  - `onOperatorMessage`
- Retornar status de conexão

**URL WebSocket**:
```
ws://192.168.10.156:8000/ws/driver
```

**Autenticação**:
- Token JWT enviado como query parameter: `?token={jwt_token}`

**Eventos Recebidos**:
- `delivery_assigned`: Nova entrega alocada para o driver
- `delivery_updated`: Entrega atualizada
- `operator_message`: Mensagem do operador

**Eventos Enviados**:
- (Nenhum no momento)

### API Client

**Arquivo**: `frontend/src/utils/driverApi.js`

**Funções Principais**:
- `driverLogin(username, email, password)`
- `getDriverProfile()`
- `getDriverStats()`
- `updateDriverStatus(status)`
- `updateDriverLocation(latitude, longitude)`
- `getDriverDeliveries(status)`
- `updateDeliveryStatus(deliveryId, status, notes)`
- `reportDeliveryProblem(deliveryId, problemType, description)`
- `getCargaAtual()`
- `registrarSaidaCarga(cargaId)`
- `realizarAcertoCarga(cargaId, itens, observacoes)`

**Base URL**:
```javascript
const API_BASE = import.meta.env.VITE_API_URL || 'http://192.168.10.156:8000/api'
```

**Headers Padrão**:
```javascript
{
  'Authorization': `Bearer ${localStorage.getItem('token')}`,
  'Content-Type': 'application/json'
}
```

---

## ⚠️ PROBLEMAS CONHECIDOS E LIMITAÇÕES

### Problemas Críticos Identificados

#### 1. **Falta de Alocação Automática de Entregas**

**Problema**: O sistema não possui endpoint para o motorista "aceitar" uma entrega disponível (`status=pending`). O motorista apenas vê entregas disponíveis, mas não consegue se alocar a elas.

**Impacto**: Motorista não consegue iniciar entregas.

**Solução Necessária**:
- Criar endpoint `POST /api/drivers/deliveries/{delivery_id}/accept`
- Atualizar `Delivery.driver_id` e `Delivery.status = "assigned"`
- Validar que motorista está `available`
- Validar que entrega está `pending`

#### 2. **Falta de Integração com Mapa/GPS**

**Problema**: O componente `DeliveryDetail` tem botão "Abrir no Maps", mas não há integração real com GPS ou rastreamento em tempo real.

**Impacto**: Motorista precisa usar app externo para navegação.

**Solução Necessária**:
- Integrar Google Maps API ou similar
- Mostrar rota no mapa
- Rastreamento em tempo real (opcional)

#### 3. **WebSocket Não Implementado Completamente**

**Problema**: O hook `useWebSocketDriver` existe, mas o backend pode não estar enviando eventos corretamente para drivers.

**Impacto**: Atualizações em tempo real não funcionam.

**Solução Necessária**:
- Verificar implementação do WebSocket no backend
- Garantir que eventos são broadcastados para drivers
- Testar conexão e reconexão automática

#### 4. **Falta de Validação de Status na UI**

**Problema**: O `DeliveryDetail` permite atualizar status, mas não valida se o status anterior permite a transição.

**Impacto**: Motorista pode pular etapas ou fazer transições inválidas.

**Solução Necessária**:
- Validar transições de status no frontend
- Desabilitar botões de ações inválidas
- Mostrar mensagens claras sobre próximas ações

#### 5. **MyTimePanel com URL Hardcoded**

**Problema**: O componente `MyTimePanel.jsx` tem URL hardcoded:
```javascript
const response = await fetch(
  `http://192.168.10.156:8000/api/drivers/me/time-summary?period=${period}`,
  ...
)
```

**Impacto**: Não funciona em ambientes diferentes.

**Solução Necessária**:
- Usar `driverApi` ou `buildApiEndpoint` do `api.js`
- Usar variável de ambiente para URL base

#### 6. **Falta de Tratamento de Erros Robusto**

**Problema**: Muitos componentes não tratam todos os casos de erro possíveis.

**Impacto**: UX ruim quando ocorrem erros.

**Solução Necessária**:
- Adicionar try/catch em todas as chamadas de API
- Mostrar mensagens de erro amigáveis
- Implementar retry automático para erros de rede
- Logging de erros para debug

#### 7. **Falta de Loading States Consistentes**

**Problema**: Alguns componentes não mostram loading states adequados.

**Impacto**: Usuário não sabe se sistema está processando.

**Solução Necessária**:
- Adicionar spinners/loading em todas as operações assíncronas
- Desabilitar botões durante operações
- Mostrar feedback visual imediato

#### 8. **Bottom Navigation Não Funcional**

**Problema**: A navegação inferior no `DriverDashboard` pode não estar funcionando corretamente para todas as rotas.

**Impacto**: Motorista não consegue navegar entre páginas.

**Solução Necessária**:
- Verificar rotas no `App.jsx`
- Garantir que todas as páginas existem
- Adicionar indicador de página ativa

### Limitações Conhecidas

1. **Sem Filtros Avançados**: Não há filtros por bairro, data, etc. nas entregas
2. **Sem Histórico Detalhado**: `DeliveryHistory` pode não estar implementado completamente
3. **Sem Notificações Push**: Apenas WebSocket (requer app aberto)
4. **Sem Offline Mode**: Sistema não funciona sem internet
5. **Sem Sincronização de Dados**: Dados podem ficar desatualizados se WebSocket falhar

---

## ✅ REQUISITOS PARA RECRIAÇÃO DO DASHBOARD

### Funcionalidades Obrigatórias

#### 1. Autenticação e Autorização
- ✅ Login com email/senha
- ✅ Validação de role "driver"
- ✅ Token JWT com expiração
- ✅ Logout e limpeza de sessão
- ✅ Redirecionamento automático se não autenticado

#### 2. Dashboard Principal
- ✅ Exibir perfil do motorista (nome, foto, rating)
- ✅ Toggle de status (offline/available/busy/break)
- ✅ Estatísticas do dia (entregas, rating, tempo médio)
- ✅ Tempo trabalhado (hoje, semana, mês)
- ✅ Lista de entregas ativas
- ✅ Lista de entregas disponíveis
- ✅ Auto-refresh a cada 30 segundos
- ✅ Refresh manual

#### 3. Gestão de Entregas
- ✅ Aceitar entrega disponível (NOVO - precisa implementar)
- ✅ Ver detalhes da entrega
- ✅ Atualizar status da entrega (picked_up, in_transit, arrived, delivered)
- ✅ Validar transições de status
- ✅ Reportar problema na entrega
- ✅ Ligar para cliente
- ✅ Abrir endereço no Maps
- ✅ Ver histórico de entregas

#### 4. Gestão de Carga
- ✅ Ver carga atual do veículo
- ✅ Registrar saída com carga
- ✅ Realizar acerto da carga
- ✅ Validar quantidades do acerto

#### 5. WebSocket e Tempo Real
- ✅ Conectar ao WebSocket
- ✅ Receber notificações de novas entregas
- ✅ Receber atualizações de entregas
- ✅ Receber mensagens do operador
- ✅ Reconexão automática se desconectar

### Melhorias Recomendadas

#### 1. UX/UI
- 🎨 Design moderno e responsivo (mobile-first)
- 🎨 Animações suaves para transições
- 🎨 Feedback visual imediato em todas as ações
- 🎨 Estados de loading consistentes
- 🎨 Mensagens de erro amigáveis
- 🎨 Confirmações para ações críticas

#### 2. Funcionalidades Adicionais
- 📍 Rastreamento GPS em tempo real
- 📍 Integração com Google Maps para navegação
- 📍 Notificações push (se possível)
- 📍 Modo offline básico (cache de dados)
- 📍 Filtros avançados (bairro, data, status)
- 📍 Busca de entregas
- 📍 Compartilhamento de localização com operador

#### 3. Performance
- ⚡ Lazy loading de componentes
- ⚡ Cache de dados no frontend
- ⚡ Debounce em buscas/filtros
- ⚡ Otimização de re-renders (React.memo, useMemo)
- ⚡ Code splitting por rota

#### 4. Testes e Qualidade
- 🧪 Testes unitários de componentes
- 🧪 Testes de integração de APIs
- 🧪 Testes E2E críticos
- 🧪 Validação de tipos (TypeScript recomendado)

### Estrutura de Arquivos Recomendada

```
frontend/src/
├── pages/driver/
│   ├── DriverLogin.jsx
│   ├── DriverDashboard.jsx
│   ├── DeliveryDetail.jsx
│   ├── DeliveryHistory.jsx
│   ├── AcertoCarga.jsx
│   └── DriverProfile.jsx
├── components/driver/
│   ├── DriverHeader.jsx
│   ├── StatsCard.jsx
│   ├── DeliveryCard.jsx
│   ├── MyTimePanel.jsx
│   ├── DeliveryStatusStepper.jsx (NOVO)
│   ├── ProblemReportModal.jsx (NOVO)
│   └── MapView.jsx (NOVO - opcional)
├── hooks/
│   ├── useWebSocketDriver.js
│   ├── useDriverData.js (NOVO)
│   └── useLocation.js (NOVO - opcional)
├── utils/
│   ├── driverApi.js
│   ├── api.js
│   └── validation.js (NOVO)
└── constants/
    ├── deliveryStatus.js (NOVO)
    └── driverStatus.js (NOVO)
```

### Checklist de Implementação

#### Fase 1: Core (Crítico)
- [ ] Login funcional
- [ ] Dashboard carrega dados básicos
- [ ] Lista de entregas ativas funciona
- [ ] Lista de entregas disponíveis funciona
- [ ] Aceitar entrega (NOVO)
- [ ] Ver detalhes da entrega
- [ ] Atualizar status da entrega
- [ ] WebSocket conecta e recebe eventos

#### Fase 2: Melhorias (Importante)
- [ ] Tempo trabalhado funciona corretamente
- [ ] Acerto de carga completo
- [ ] Histórico de entregas
- [ ] Perfil do motorista
- [ ] Tratamento de erros robusto
- [ ] Loading states consistentes

#### Fase 3: Polimento (Desejável)
- [ ] Design moderno e responsivo
- [ ] Animações e transições
- [ ] Integração com Maps
- [ ] Notificações push
- [ ] Modo offline básico
- [ ] Testes automatizados

---

## 🔗 INTEGRAÇÕES EXTERNAS

### WAHA (WhatsApp HTTP API)

**Uso**: Envio de notificações WhatsApp para clientes

**Endpoints Utilizados**:
- Envio de mensagens
- Status de mensagens

**Não usado diretamente no Dashboard do Motorista**, mas eventos de entrega podem disparar notificações.

### Firebird

**Uso**: Exportação de pedidos entregues

**Não usado diretamente no Dashboard do Motorista**, mas pedidos entregues são exportados automaticamente.

### Google Maps (Recomendado)

**Uso Futuro**: Navegação e rastreamento

**API Necessária**: Google Maps JavaScript API ou React Native Maps

**Funcionalidades**:
- Mostrar rota do motorista para endereço de entrega
- Rastreamento em tempo real (opcional)
- Geocoding de endereços

---

## 📝 NOTAS TÉCNICAS IMPORTANTES

### Compatibilidade Python 3.8

O backend usa Python 3.8, então:
- ❌ Não use `list[...]`, `dict[...]`, `tuple[...]` (type hints)
- ✅ Use `List[...]`, `Dict[...]`, `Tuple[...]` do `typing`
- ❌ Não use `type | None`
- ✅ Use `Optional[type]` ou `Union[type, None]`

### Autenticação JWT

- Token expira em tempo configurado (padrão: 24h)
- Token deve ser enviado em todas as requisições: `Authorization: Bearer {token}`
- Se token expirar (401), limpar localStorage e redirecionar para login

### WebSocket

- URL: `ws://192.168.10.156:8000/ws/driver?token={jwt_token}`
- Reconexão automática recomendada
- Tratar desconexões graciosamente

### Estados de Entrega

Ordem lógica obrigatória:
```
pending → assigned → picked_up → in_transit → arrived → delivered
                                    ↓
                                 failed/returned
```

Não permitir pular etapas.

### Validações de Carga

Ao fazer acerto:
- `qtd_vendida + qtd_retorno_cheio <= qtd_saida` (para cada item)
- `qtd_retorno_vazio` pode ser maior (vazios de entregas anteriores)

### Time Tracking

- Logs são criados automaticamente ao mudar status
- Log anterior é finalizado antes de criar novo
- Duração máxima limitada a 16h por log (prevenir métricas infladas)

---

## 🎯 CONCLUSÃO

Este relatório fornece uma visão completa e detalhada do sistema Gas Automation, com foco especial no Dashboard do Motorista. Todas as informações necessárias para uma recriação funcional estão documentadas:

1. ✅ Arquitetura técnica completa
2. ✅ Modelos de dados detalhados
3. ✅ APIs e endpoints documentados
4. ✅ Fluxos de negócio mapeados
5. ✅ Especificações do dashboard atual
6. ✅ Problemas conhecidos identificados
7. ✅ Requisitos para recriação definidos

**Próximos Passos Recomendados**:
1. Revisar este relatório completamente
2. Identificar funcionalidades críticas faltantes
3. Criar mockups/wireframes do novo dashboard
4. Implementar funcionalidades core primeiro
5. Adicionar melhorias e polimento depois
6. Testar extensivamente antes de deploy

**Contato para Dúvidas**:
- Documentação do backend: `backend/app/api/drivers.py`
- Documentação do frontend: `frontend/src/pages/driver/`
- Schemas: `backend/app/schemas/driver.py`

---

**Documento gerado em**: 28 de Janeiro de 2026  
**Versão**: 1.0  
**Autor**: Sistema de Documentação Automática
