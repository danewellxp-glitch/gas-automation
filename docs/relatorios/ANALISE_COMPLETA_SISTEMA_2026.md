# Análise Completa do Sistema Gas Automation - 2026

**Data de Atualização:** 13 de Fevereiro de 2026  
**Versão do Sistema:** 1.0.0  
**Propósito:** Documentação técnica completa para compreensão do sistema por inteligência artificial ou desenvolvedores

---

## Índice

1. [Visão Geral Executiva](#1-visão-geral-executiva)
2. [Arquitetura do Sistema](#2-arquitetura-do-sistema)
3. [Stack Tecnológica Completa](#3-stack-tecnológica-completa)
4. [Fluxo de Dados End-to-End](#4-fluxo-de-dados-end-to-end)
5. [Componentes Principais](#5-componentes-principais)
6. [Processamento de Mensagens (Redis Streams)](#6-processamento-de-mensagens-redis-streams)
7. [Flow Engine e Máquina de Estados](#7-flow-engine-e-máquina-de-estados)
8. [Modelos de Dados](#8-modelos-de-dados)
9. [Integrações Externas](#9-integrações-externas)
10. [Observabilidade e Monitoramento](#10-observabilidade-e-monitoramento)
11. [Segurança e Autenticação](#11-segurança-e-autenticação)
12. [WebSocket e Tempo Real](#12-websocket-e-tempo-real)
13. [Estrutura de Código](#13-estrutura-de-código)
14. [Configuração e Deploy](#14-configuração-e-deploy)
15. [Pontos Críticos e Melhores Práticas](#15-pontos-críticos-e-melhores-práticas)

---

## 1. Visão Geral Executiva

### 1.1 O Que É Este Sistema

O **Gas Automation** é um sistema SaaS completo de automação de pedidos de gás liquefeito de petróleo (GLP) via WhatsApp. O sistema processa aproximadamente **9.000 pedidos por semana** e automatiza todo o ciclo de vida de um pedido, desde a recepção da mensagem do cliente até a entrega e integração com sistemas fiscais.

### 1.2 Problema Que Resolve

**Antes:**
- Clientes precisavam ligar para fazer pedidos
- Operadores anotavam manualmente em papel ou planilhas
- Alto risco de erros de digitação
- Falta de rastreamento em tempo real
- Integração manual com sistemas fiscais
- Dificuldade em gerenciar múltiplos entregadores
- Duplicação de pedidos por race conditions

**Depois:**
- Clientes fazem pedidos via WhatsApp de forma automatizada
- Sistema gerencia todo o fluxo conversacional com IA
- Operadores têm dashboards em tempo real
- Entregadores recebem pedidos automaticamente
- Integração automática com sistemas fiscais (Firebird)
- Rastreamento completo de entregas
- Processamento distribuído sem duplicações (Redis Streams)

### 1.3 Domínio de Negócio

**Produtos:**
- P13: Botija de 13kg
- P20: Botija de 20kg
- P45: Botija de 45kg

**Tipos de Operação:**
- **Troca:** Cliente troca vasilhame vazio por cheio (desconto aplicado)
- **Venda:** Cliente compra vasilhame novo (paga caução)
- **Retira:** Cliente busca na loja (sem entrega)

**Métodos de Pagamento:**
- PIX (descontinuado no fluxo atual)
- Cartão de Crédito/Débito
- Dinheiro
- Boleto

**Bairros Atendidos:**
- Alto Boqueirão, Boqueirão, Ganchinho, Hauer, Sítio Cercado, Umbará, Xaxim

**Status de Pedidos:**
- `pending` → `paid` → `preparing` → `dispatched` → `delivered` (ou `cancelled`)

---

## 2. Arquitetura do Sistema

### 2.1 Padrão Arquitetural

**Arquitetura Híbrida:**
- **Backend Principal:** FastAPI monolítico modular (não é microserviços puro)
- **Microserviços Especializados:** Opcionais (sync-service, inventory-service, notification-service)
- **Frontend:** React SPA (Single Page Application)
- **Comunicação:** REST API + WebSocket para tempo real
- **Processamento de Mensagens:** Redis Streams com Consumer Groups (substitui BackgroundTask)
- **Infraestrutura:** Docker Compose com Traefik como API Gateway

### 2.2 Diagrama de Arquitetura Completo

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENTE                                 │
│                    (WhatsApp Mobile)                            │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                         WAHA                                    │
│              (WhatsApp HTTP API Server)                         │
│              Porta: 3000                                        │
│              - Recebe mensagens WhatsApp                        │
│              - Envia webhooks para backend                      │
│              - Gerencia sessão WhatsApp                         │
└───────────────────────────┬─────────────────────────────────────┘
                            │ Webhook HTTP POST
                            │ (event: message)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                            │
│                    Porta: 8000                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  /webhooks/waha                                           │  │
│  │  - Valida assinatura HMAC                                 │  │
│  │  - Resolve LID (@lid → @c.us)                            │  │
│  │  - Deduplicação (Redis SET NX)                           │  │
│  │  - Adiciona ao Redis Stream                               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Redis Stream: stream:messages                           │  │
│  │  Consumer Group: gas-workers                             │  │
│  │  - Distribui mensagens entre workers                     │  │
│  │  - Garante processamento único                           │  │
│  │  - Retry automático (até 3x)                             │  │
│  │  - DLQ para falhas                                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Message Stream Consumer                                  │  │
│  │  - Processa mensagens do stream                          │  │
│  │  - Lock distribuído por telefone                         │  │
│  │  - Chama Flow Engine                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Flow Engine (State Machine)                             │  │
│  │  - Gerencia estados da conversa                           │  │
│  │  - NLP para detecção de intenção                         │  │
│  │  - Handlers específicos por estado                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Order Service                                            │  │
│  │  - Cria pedidos (idempotente)                            │  │
│  │  - Validações de negócio                                 │  │
│  │  - Integração com Firebird                               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  PostgreSQL                                              │  │
│  │  - Orders, Customers, Messages                           │  │
│  │  - Event Logs (auditoria)                                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  WebSocket Manager                                        │  │
│  │  - Notifica dashboards em tempo real                     │  │
│  │  - Redis Pub/Sub para escala horizontal                  │  │
│  │  - Event Batching para performance                       │  │
│  └──────────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                             │
│                    Porta: 3001                                  │
│  - Dashboard Admin/Owner/Operator/Driver                        │
│  - WebSocket para atualizações em tempo real                   │
│  - Filtros por role/bairro                                     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│              STACK DE OBSERVABILIDADE                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Prometheus   │  │  Grafana     │  │ Alertmanager│          │
│  │ (Métricas)   │  │ (Dashboards) │  │ (Alertas)    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐                            │
│  │ Loki         │  │ Promtail     │                            │
│  │ (Logs)       │  │ (Log Ship)   │                            │
│  └──────────────┘  └──────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 Componentes de Infraestrutura

**Serviços Docker:**
- `backend` - API FastAPI principal
- `frontend` - React SPA
- `postgres` - Banco de dados PostgreSQL 15
- `redis` - Cache e mensageria (Streams, Pub/Sub)
- `waha` - WhatsApp HTTP API
- `prometheus` - Coleta de métricas
- `grafana` - Dashboards
- `alertmanager` - Gerenciamento de alertas
- `loki` - Agregação de logs
- `promtail` - Coleta de logs
- `traefik` - API Gateway (opcional)

---

## 3. Stack Tecnológica Completa

### 3.1 Backend

**Framework:**
- FastAPI 0.115.0 (Python 3.11+)
- Uvicorn (ASGI server)
- Pydantic (validação de dados)
- SQLAlchemy 2.0 (ORM assíncrono)
- Alembic (migrações)

**Banco de Dados:**
- PostgreSQL 15 (banco principal)
- Redis 7 (cache, streams, pub/sub)

**Processamento de Mensagens:**
- Redis Streams (substitui BackgroundTask)
- Consumer Groups para distribuição
- Dead Letter Queue (DLQ) para falhas

**IA/NLP:**
- Ollama (modelo local: qwen2.5:3b)
- Detecção de intenção e extração de entidades

**Autenticação:**
- JWT (JSON Web Tokens)
- Argon2 (hash de senhas)

**Observabilidade:**
- Prometheus (métricas)
- Grafana (visualização)
- Loki (logs)
- Promtail (coleta de logs)
- Alertmanager (alertas)

**Integrações:**
- Datadog (opcional)
- New Relic (opcional)

### 3.2 Frontend

**Framework:**
- React 18+
- Vite (build tool)
- TailwindCSS (estilização)
- React Router (roteamento)

**Tempo Real:**
- WebSocket nativo
- Reconexão automática
- Heartbeat

### 3.3 Infraestrutura

**Containerização:**
- Docker
- Docker Compose

**API Gateway:**
- Traefik (opcional)

**Monitoramento:**
- Prometheus
- Grafana
- Alertmanager
- Loki + Promtail

---

## 4. Fluxo de Dados End-to-End

### 4.1 Fluxo Completo de uma Mensagem

```
1. Cliente envia mensagem no WhatsApp
   ↓
2. WAHA recebe mensagem e envia webhook para /webhooks/waha
   ↓
3. Webhook Handler:
   - Valida assinatura HMAC (se configurado)
   - Resolve LID (@lid → @c.us) se necessário
   - Verifica deduplicação (Redis SET NX)
   - Adiciona mensagem ao Redis Stream (stream:messages)
   - Retorna 200 OK imediatamente
   ↓
4. Message Stream Consumer (worker):
   - Lê mensagem do stream via XREADGROUP
   - Adquire lock distribuído por telefone (Redis SETNX)
   - Processa mensagem:
     a. Carrega contexto da conversa (Redis)
     b. Chama Flow Engine
     c. Flow Engine determina estado atual
     d. Handler específico processa mensagem
     e. Atualiza contexto (Redis + PostgreSQL)
     f. Gera resposta
   - Envia resposta via WAHA API
   - Faz XACK no stream (confirma processamento)
   - Libera lock
   ↓
5. Se falhar:
   - Não faz XACK (mensagem fica pendente)
   - Redis redeliver após timeout
   - Após 3 tentativas → move para DLQ
   ↓
6. DLQ Alerter:
   - Monitora stream:dlq
   - Envia alertas (email/webhook)
   ↓
7. WebSocket:
   - Emite eventos para dashboards
   - Operadores veem atualizações em tempo real
```

### 4.2 Fluxo de Criação de Pedido

```
1. Cliente completa fluxo conversacional:
   START → ASKING_CUSTOMER_TYPE → COLLECTING_NAME → ...
   → CONFIRMING_ORDER
   ↓
2. Handler handle_confirming_order:
   - Valida dados do contexto
   - Chama create_order() (idempotente)
   ↓
3. create_order():
   - Verifica se pedido já existe (order_id no contexto)
   - Lock distribuído por customer_id
   - Valida regras de negócio
   - Cria Order no PostgreSQL
   - Cria EventLog (auditoria)
   - Retorna Order
   ↓
4. Handler continua:
   - Atualiza contexto com order_id
   - Envia confirmação para cliente
   - Emite evento WebSocket (novo pedido)
   ↓
5. Dashboards recebem evento:
   - Admin/Owner: vêem no dashboard executivo
   - Operator: vêem na lista de pedidos pendentes
```

### 4.3 Fluxo de Processamento Distribuído (Redis Streams)

```
┌─────────────────────────────────────────────────────────────┐
│  Webhook recebe mensagem                                    │
│  → XADD stream:messages {message_data}                     │
│  → Retorna 200 OK                                           │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Worker 1                    Worker 2                      │
│  ┌──────────────────┐        ┌──────────────────┐         │
│  │ XREADGROUP       │        │ XREADGROUP       │         │
│  │ gas-workers      │        │ gas-workers      │         │
│  │ consumer: w1     │        │ consumer: w2     │         │
│  └────────┬─────────┘        └────────┬─────────┘         │
│           │                           │                    │
│           │ Mensagem 1                │ Mensagem 2        │
│           │                           │                    │
│           ▼                           ▼                    │
│  ┌──────────────────┐        ┌──────────────────┐         │
│  │ Processa         │        │ Processa         │         │
│  │ → XACK           │        │ → XACK           │         │
│  └──────────────────┘        └──────────────────┘         │
└─────────────────────────────────────────────────────────────┘

Garantias:
- Cada mensagem é processada por apenas 1 worker
- Se worker falhar, Redis redeliver para outro worker
- Após 3 tentativas → DLQ
```

---

## 5. Componentes Principais

### 5.1 Backend (`backend/app/`)

**API Routes (`api/`):**
- `webhooks.py` - Recebe webhooks do WAHA
- `orders.py` - CRUD de pedidos
- `customers.py` - CRUD de clientes
- `products.py` - CRUD de produtos
- `chats.py` - Gerenciamento de conversas
- `websocket.py` - WebSocket para tempo real
- `auth.py` - Autenticação JWT
- `dlq.py` - API para monitorar Dead Letter Queue
- `alerts.py` - Webhook para receber alertas do Alertmanager

**Core (`core/`):**
- `flow_engine.py` - Motor principal do fluxo conversacional
- `state_machine.py` - Máquina de estados
- `handlers.py` - Handlers específicos por estado
- `message_store.py` - Armazenamento de mensagens
- `redis_websocket_bridge.py` - Bridge Redis para escala horizontal
- `secure_logging.py` - Logging seguro (sanitiza dados sensíveis)

**Services (`services/`):**
- `message_stream_consumer.py` - Consumer de Redis Streams
- `waha_poller.py` - Poller de fallback (quando webhooks falham)
- `dlq_alerter.py` - Monitora DLQ e envia alertas
- `order_service.py` - Lógica de negócio para pedidos
- `customer_service.py` - Lógica de negócio para clientes
- `delivery_service.py` - Lógica de negócio para entregas
- `driver_service.py` - Lógica de negócio para entregadores

**Integrations (`integrations/`):**
- `waha.py` - Cliente WAHA (envio de mensagens, resolução de LID)
- `datadog.py` - Integração com Datadog (opcional)
- `newrelic.py` - Integração com New Relic (opcional)

**Utils (`utils/`):**
- `structured_logging.py` - Logging estruturado com message_id/trace_id

**Models (`models/`):**
- `order.py` - Modelo Order
- `customer.py` - Modelo Customer
- `product.py` - Modelo Product
- `delivery.py` - Modelo Delivery
- `driver.py` - Modelo Driver
- `event_log.py` - Modelo EventLog (auditoria)

**Database (`database.py`):**
- `RedisManager` - Gerenciamento de Redis
  - `acquire_phone_lock()` - Lock distribuído por telefone
  - `release_phone_lock()` - Libera lock
  - `check_message_processed()` - Deduplicação
  - `add_message_to_stream()` - Adiciona ao Redis Stream
  - `publish()` - Redis Pub/Sub

**Metrics (`metrics.py`):**
- Métricas Prometheus customizadas:
  - `stream_messages_added_total`
  - `stream_messages_processed_total`
  - `stream_messages_dlq_total`
  - `stream_processing_duration_seconds`
  - `stream_lag`
  - `stream_retry_count`
  - `stream_consumer_running`
  - `websocket_connections_total`
  - E muitas outras...

### 5.2 Frontend (`frontend/`)

**Estrutura:**
- `src/components/` - Componentes React
- `src/pages/` - Páginas/rotas
- `src/services/` - Serviços (API calls, WebSocket)
- `src/context/` - Context API
- `src/hooks/` - Custom hooks

**Dashboards:**
- Admin Dashboard - Administração completa
- Owner Dashboard - KPIs e relatórios executivos
- Operator Dashboard - Operação diária (pedidos, conversas)
- Driver Dashboard - Entregas e tracking

---

## 6. Processamento de Mensagens (Redis Streams)

### 6.1 Por Que Redis Streams?

**Problema Anterior:**
- BackgroundTask do FastAPI não é distribuído
- Múltiplos workers processavam a mesma mensagem
- Race conditions causavam duplicação de pedidos
- Sem retry automático
- Sem dead letter queue

**Solução:**
- Redis Streams com Consumer Groups
- Cada mensagem processada por apenas 1 worker
- Retry automático (até 3 tentativas)
- Dead Letter Queue para falhas
- Observabilidade completa (métricas Prometheus)

### 6.2 Arquitetura do Stream

**Stream:** `stream:messages`
**Consumer Group:** `gas-workers`
**DLQ:** `stream:dlq`

**Formato da Mensagem no Stream:**
```json
{
  "message": {
    "key": {
      "remoteJid": "5511999999999@c.us",
      "fromMe": false,
      "id": "MSG123"
    },
    "message": {
      "conversation": "Olá, quero fazer um pedido"
    },
    "messageTimestamp": 1234567890,
    "pushName": "João Silva"
  },
  "original_chat_id": "7185547411514@lid",  // Se era LID
  "timestamp": "1234567890.123"
}
```

### 6.3 Consumer Process

```python
# 1. Ler mensagens do stream
events = await redis.xreadgroup(
    groupname="gas-workers",
    consumername="worker-1",
    streams={"stream:messages": ">"},
    count=10,
    block=5000
)

# 2. Para cada mensagem:
for msg_id, msg_data in events:
    # 3. Processar
    success = await process_message(msg_id, msg_data)
    
    # 4. Se sucesso:
    if success:
        await redis.xack("stream:messages", "gas-workers", msg_id)
    else:
        # 5. Se falhou, verificar tentativas
        retry_count = get_retry_count(msg_id)
        if retry_count >= 3:
            # Mover para DLQ
            await move_to_dlq(msg_id, msg_data)
            await redis.xack("stream:messages", "gas-workers", msg_id)
        # Senão, deixa pendente para retry automático
```

### 6.4 Dead Letter Queue (DLQ)

**Quando vai para DLQ:**
- Mensagem falhou após 3 tentativas
- Erro não recuperável

**Monitoramento:**
- DLQ Alerter monitora `stream:dlq`
- Envia alertas (email/webhook)
- API `/api/dlq/stats` para inspecionar

---

## 7. Flow Engine e Máquina de Estados

### 7.1 Estados da Conversa

```python
class ConversationState(Enum):
    START = "start"
    ASKING_CUSTOMER_TYPE = "asking_customer_type"
    COLLECTING_NAME = "collecting_name"
    COLLECTING_DOCUMENT = "collecting_document"
    AWAITING_PRODUCT = "awaiting_product"
    AWAITING_QUANTITY = "awaiting_quantity"
    AWAITING_ADDRESS = "awaiting_address"
    CONFIRMING_ADDRESS = "confirming_address"
    AWAITING_PAYMENT = "awaiting_payment"
    AWAITING_PIX = "awaiting_pix"
    CONFIRMING_ORDER = "confirming_order"
    ORDER_CONFIRMED = "order_confirmed"
    TRACKING_ORDER = "tracking_order"
    TALKING_TO_HUMAN = "talking_to_human"
```

### 7.2 Fluxo Típico

```
START
  ↓ (cliente diz "menu" ou "pedido")
ASKING_CUSTOMER_TYPE
  ↓ (cliente escolhe: novo/existente)
COLLECTING_NAME (se novo)
  ↓
COLLECTING_DOCUMENT (se novo)
  ↓
AWAITING_PRODUCT
  ↓ (cliente escolhe produto)
AWAITING_QUANTITY
  ↓ (cliente informa quantidade)
AWAITING_ADDRESS
  ↓ (cliente informa endereço)
CONFIRMING_ADDRESS
  ↓ (cliente confirma)
AWAITING_PAYMENT
  ↓ (cliente escolhe método)
CONFIRMING_ORDER
  ↓ (cliente confirma)
ORDER_CONFIRMED
  ↓
START (volta ao início)
```

### 7.3 Flow Engine

**Responsabilidades:**
- Gerencia estados da conversa
- Roteia mensagens para handlers corretos
- Usa NLP para detecção de intenção no estado START
- Extrai entidades inline nos estados intermediários

**Handlers:**
- Cada estado tem um handler específico
- Handlers são funções async que recebem contexto e mensagem
- Retornam `ProcessedMessage` com respostas e novo estado

---

## 8. Modelos de Dados

### 8.1 Principais Tabelas

**Orders:**
- `id` (UUID)
- `order_number` (int, único)
- `customer_id` (UUID, FK)
- `status` (pending, paid, preparing, dispatched, delivered, cancelled)
- `total_amount` (Decimal)
- `payment_method` (string)
- `address` (JSONB)
- `created_at`, `updated_at`

**Customers:**
- `id` (UUID)
- `phone` (string, único)
- `name` (string)
- `document` (string, CPF)
- `address` (JSONB)
- `waha_chat_id` (string, pode ser @lid)

**Products:**
- `id` (UUID)
- `name` (string)
- `code` (string, P13, P20, P45)
- `price` (Decimal)
- `active` (boolean)

**Deliveries:**
- `id` (UUID)
- `order_id` (UUID, FK)
- `driver_id` (UUID, FK)
- `status` (pending, in_transit, delivered, cancelled)
- `started_at`, `completed_at`

**EventLogs:**
- `id` (UUID)
- `event_type` (string)
- `entity_type` (string)
- `entity_id` (UUID)
- `actor_type` (string)
- `actor_id` (string)
- `payload` (JSONB)
- `created_at`

### 8.2 Índices Importantes

- `uq_orders_customer_pending` - Evita pedidos duplicados pendentes
- `processed_messages.waha_message_id` - Deduplicação de mensagens
- `customers.phone` - Busca rápida por telefone
- `orders.customer_id` - Busca pedidos do cliente

---

## 9. Integrações Externas

### 9.1 WAHA (WhatsApp HTTP API)

**Endpoints Usados:**
- `POST /api/sendText` - Enviar mensagem de texto
- `POST /api/sendButtons` - Enviar botões
- `GET /api/contacts` - Resolver LID para número real
- `GET /api/sessions/{session}/status` - Status da sessão

**LID Resolution:**
- WAHA usa Linked IDs (@lid) para grupos
- Sistema resolve para números reais (@c.us)
- Cache em Redis (TTL 24h)
- Fallback para banco de dados

### 9.2 Firebird (ERP Legado)

**Sync Service:**
- Sincroniza pedidos entregues para Firebird
- Exporta dados fiscais
- Configurável via variáveis de ambiente

### 9.3 Asaas (Pagamentos)

**Status:** Descontinuado no fluxo atual, mas código existe

### 9.4 Ollama (IA Local)

**Uso:**
- Detecção de intenção no estado START
- Extração de entidades (produto, quantidade, endereço)
- Modelo: qwen2.5:3b

---

## 10. Observabilidade e Monitoramento

### 10.1 Métricas Prometheus

**Stream Metrics:**
- `stream_messages_added_total` - Mensagens adicionadas ao stream
- `stream_messages_processed_total{status}` - Mensagens processadas (success/error)
- `stream_messages_dlq_total` - Mensagens na DLQ
- `stream_processing_duration_seconds` - Tempo de processamento
- `stream_lag` - Mensagens pendentes
- `stream_retry_count` - Distribuição de retries
- `stream_consumer_running` - Status do consumer

**WebSocket Metrics:**
- `websocket_connections_total` - Conexões ativas
- `websocket_messages_sent_total` - Mensagens enviadas
- `websocket_messages_received_total` - Mensagens recebidas

**Sistema:**
- `gas_automation_system_info` - Informações do sistema
- Muitas outras...

### 10.2 Dashboards Grafana

**Redis Streams Dashboard:**
- Mensagens adicionadas/processadas
- Taxa de sucesso vs erro
- Lag do stream
- Tempo de processamento (p50, p95, p99)
- Mensagens na DLQ
- Distribuição de retries

### 10.3 Alertas (Alertmanager)

**Alertas Críticos:**
- `StreamConsumerDown` - Consumer parado
- `MessagesInDLQ` - Mensagens na DLQ
- `RedisDown` - Redis inacessível
- `PostgreSQLDown` - PostgreSQL inacessível
- `WAHASessionDown` - Sessão WhatsApp desconectada

**Alertas de Aviso:**
- `HighStreamLag` - Lag alto
- `HighStreamErrorRate` - Taxa de erro alta
- `HighRetryRate` - Muitos retries
- `HighProcessingTime` - Tempo alto

### 10.4 Logs (Loki)

**Estrutura:**
- Logs estruturados com `message_id`, `trace_id`, `phone`
- Coletados pelo Promtail
- Armazenados no Loki
- Visualizados no Grafana

**Query Exemplo:**
```
{job="backend"} |= "message_id=ABC123"
```

---

## 11. Segurança e Autenticação

### 11.1 Autenticação

**JWT Tokens:**
- Access tokens (expiração: 30min)
- Refresh tokens (não implementado ainda)
- Secret key mínimo 32 caracteres

**Roles (RBAC):**
- `admin` - Administração total
- `owner` - Visão executiva
- `operator` - Operação diária
- `driver` - Entregas

### 11.2 Segurança de Webhooks

**WAHA Webhooks:**
- Validação HMAC-SHA256 (se `WAHA_WEBHOOK_SECRET` configurado)
- Header: `X-WAHA-Signature`

### 11.3 Proteção de Dados

**Secure Logging:**
- Sanitiza dados sensíveis automaticamente
- Remove CPF, telefones, senhas dos logs

**Rate Limiting:**
- SlowAPI para rate limiting
- 100 requests/min por IP (configurável)

---

## 12. WebSocket e Tempo Real

### 12.1 Arquitetura WebSocket

**Componentes:**
- `WebSocketManager` - Gerencia conexões
- `RedisWebSocketBridge` - Bridge para escala horizontal
- `EventBatcher` - Agrupa eventos para performance

**Otimizações:**
- Filtros por role/bairro
- Deduplicação por usuário
- Heartbeat para detectar desconexões
- Rate limiting
- Batching de eventos

### 12.2 Eventos WebSocket

**Tipos:**
- `new_order` - Novo pedido criado
- `order_updated` - Pedido atualizado
- `new_message` - Nova mensagem
- `customer_updated` - Cliente atualizado
- `delivery_updated` - Entrega atualizada

---

## 13. Estrutura de Código

### 13.1 Backend (`backend/app/`)

```
app/
├── api/              # Rotas FastAPI
├── core/             # Lógica central (Flow Engine, State Machine)
├── services/         # Serviços de negócio
├── models/           # Modelos SQLAlchemy
├── schemas/          # Schemas Pydantic
├── integrations/     # Integrações externas
├── utils/            # Utilitários
├── auth.py           # Autenticação
├── config.py         # Configurações
├── database.py       # Database (PostgreSQL + Redis)
├── metrics.py        # Métricas Prometheus
└── main.py           # Aplicação principal
```

### 13.2 Frontend (`frontend/src/`)

```
src/
├── components/       # Componentes React
├── pages/            # Páginas/rotas
├── services/         # Serviços (API, WebSocket)
├── context/          # Context API
├── hooks/            # Custom hooks
└── App.jsx           # Componente raiz
```

---

## 14. Configuração e Deploy

### 14.1 Variáveis de Ambiente Essenciais

**Segurança:**
- `SECRET_KEY` (mínimo 32 chars)
- `JWT_SECRET_KEY` (mínimo 32 chars)
- `METRICS_TOKEN` (protege `/metrics`)
- `WAHA_WEBHOOK_SECRET` (validação HMAC)

**Banco/Cache:**
- `DATABASE_URL` (PostgreSQL)
- `REDIS_URL` (Redis)

**Integrações:**
- `WAHA_API_KEY`
- `WAHA_URL`
- `OLLAMA_URL`
- `FIREBIRD_HOST`, `FIREBIRD_DATABASE`, etc.

**DLQ Alertas:**
- `DLQ_ALERT_EMAIL`
- `DLQ_ALERT_WEBHOOK_URL`

### 14.2 Docker Compose

**Perfis:**
- `monitoring` - Stack de observabilidade
- `microservices` - Microserviços opcionais
- `gateway` - Traefik
- `storage` - MinIO
- `tools` - Ferramentas (pgAdmin, etc)

**Iniciar:**
```bash
# Todos os serviços
docker-compose up -d

# Com observabilidade
docker-compose --profile monitoring up -d
```

### 14.3 Migrações

**Alembic:**
```bash
cd backend
alembic upgrade head
```

**Migrações Importantes:**
- `20260213_add_idempotency_and_lid.py` - Idempotência e LID

---

## 15. Pontos Críticos e Melhores Práticas

### 15.1 Anti-Duplicação

**Camadas de Proteção:**
1. **Deduplicação de Mensagens:** Redis SET NX por `message_id`
2. **Lock Distribuído:** Redis SETNX por telefone
3. **Idempotência de Pedidos:** `order_id` no contexto + unique constraint
4. **Redis Streams:** Garante processamento único por mensagem

### 15.2 Escalabilidade

**WebSocket:**
- Redis Pub/Sub para múltiplas instâncias
- Event Batching para reduzir volume
- Filtros por role/bairro

**Processamento:**
- Redis Streams distribui carga entre workers
- Consumer Groups garantem processamento único

### 15.3 Observabilidade

**Sempre Use:**
- Logging estruturado com `message_id` e `trace_id`
- Métricas Prometheus para monitoramento
- Alertas para problemas críticos

### 15.4 Troubleshooting

**Mensagens não chegam:**
1. Verificar se WAHA está rodando
2. Verificar se webhook está configurado
3. Verificar logs do backend
4. Verificar se WAHA Poller está ativo (fallback)

**Pedidos duplicados:**
1. Verificar se locks estão funcionando
2. Verificar se deduplicação está ativa
3. Verificar logs para race conditions

**Performance:**
1. Verificar métricas Prometheus
2. Verificar lag do stream
3. Verificar tempo de processamento

---

## Conclusão

Este sistema é uma solução completa e robusta para automação de pedidos via WhatsApp, com:

- **Processamento distribuído** sem duplicações (Redis Streams)
- **Observabilidade completa** (Prometheus, Grafana, Loki)
- **Escalabilidade horizontal** (múltiplos workers, Redis Pub/Sub)
- **Resiliência** (retry automático, DLQ, fallbacks)
- **Segurança** (JWT, HMAC, rate limiting)
- **Tempo real** (WebSocket otimizado)

Para mais detalhes sobre componentes específicos, consulte os arquivos de código e documentação adicional no diretório `docs/`.
