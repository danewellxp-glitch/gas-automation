# Documento completo do sistema Gas Automation (contexto para Claude AI)

Use este texto como contexto completo ao perguntar ao Claude. Copie e cole antes da sua dúvida.

---

## 1. Visão geral do sistema

**Gas Automation** é um sistema de automação de pedidos de gás para distribuidoras. O fluxo principal é:

1. **Cliente** envia mensagens no **WhatsApp** (conectado via WAHA).
2. **WAHA** envia webhook para o **backend** (FastAPI).
3. **Flow Engine** (máquina de estados) processa a mensagem, carrega/salva contexto no **Redis**, e devolve respostas (texto, botões).
4. **Pedido confirmado** vira registro em **PostgreSQL** (orders, order_items, customers, deliveries).
5. **Operação** (operador/admin/owner) usa **frontend React** com **WebSocket** para ver pedidos e conversas em tempo real.
6. **Entregador (driver)** tem painel próprio: recebe cargas, atualiza status de entrega, time tracking, acerto de carga.
7. **Integrações opcionais**: Firebird (ERP legado, leitura + exportação de vendas), Asaas (pagamentos – atualmente descontinuado no fluxo).

**Stack:** Backend Python/FastAPI, PostgreSQL (async SQLAlchemy + Alembic), Redis (estado de conversa + Pub/Sub WebSocket), Frontend React/Vite/Tailwind, WAHA (WhatsApp HTTP API), Docker Compose, Traefik, Prometheus/Grafana, MinIO opcional.

---

## 2. Arquitetura de alto nível

```
[Cliente WhatsApp] → [WAHA] → POST /webhooks/waha → [Backend FastAPI]
                                                           │
                                    ┌──────────────────────┼──────────────────────┐
                                    ▼                      ▼                      ▼
                            [Flow Engine]           [PostgreSQL]              [Redis]
                            (state machine)         (orders, customers,        (chat:{phone},
                            + handlers                 products, deliveries,      Pub/Sub WS)
                                                       drivers, cargas, etc.)
                                    │                      │                      │
                                    └──────────────────────┼──────────────────────┘
                                                           │
                    ┌─────────────────────────────────────┼─────────────────────────────────────┐
                    ▼                    ▼                  ▼                    ▼                 ▼
              [WAHA sendText/      [Asaas]            [Firebird]         [WebSocket]        [Event log /
               sendButtons]       (descontinuado)      (leitura +         (filtros por        Error events]
                                                      export)            role/bairro)
                    │                                                                              │
                    ▼                                                                              ▼
              [Cliente recebe                                                                 [Prometheus /
               resposta WhatsApp]                                                             Grafana]
```

---

## 3. Backend – Estrutura de pastas e responsabilidades

- **`app/main.py`** – FastAPI app, lifespan (Redis, WAHA ensure_session), CORS, rate limit, montagem de rotas, health, métricas, exception handler global.
- **`app/config.py`** – Settings (Pydantic), variáveis de ambiente: `SECRET_KEY`, `JWT_SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, `WAHA_*`, `ASAAS_*`, `FIREBIRD_*`, `OLLAMA_*`, `supported_bairros`, `manual_order_creation_enabled`, etc.
- **`app/database.py`** – Engine async PostgreSQL, `AsyncSessionLocal`, `get_db`, `RedisManager` (get/set conversation state, order lock, rate limit, publish/subscribe para WebSocket).
- **`app/auth.py`** – Autenticação (JWT), `get_current_user`, `get_current_user_ws` (WebSocket), hash de senha, criação de usuário.
- **`app/api/`** – Rotas HTTP (veja seção 5).
- **`app/core/`** – Flow engine, state machine, handlers, Redis WebSocket bridge, event batcher, message store.
- **`app/integrations/`** – WAHA, Asaas, Firebird, FCM, MinIO, Ollama.
- **`app/models/`** – SQLAlchemy (Customer, Order, OrderItem, Delivery, Driver, Product, CargaVeiculo, CargaItem, User, etc.).
- **`app/schemas/`** – Pydantic (webhooks, orders, customers, etc.).
- **`app/services/`** – Lógica de negócio (order_service, delivery_service, driver_service, firebird_export_service, event_publisher, etc.).

---

## 4. Fluxo WhatsApp (Flow Engine) – Detalhado

### 4.1 Entrada

- **Webhook:** `POST /webhooks/waha`
- Body: evento WAHA com `event`, `session`, `payload`. Para `event == "message"`:
  - Ignora se `fromMe == true`.
  - Extrai `chat_id` (pode ser `@lid` ou `@c.us`), `body`/`_data`, `pushName`, `id` da mensagem.
- **Schemas:** `WAHAWebhookPayload`, `WAHAMessage` (`app/schemas/webhook.py`). Em `WAHAMessage`: propriedades `phone`, `text`, `button_id`, `location`.
- Processamento é em **background** (`BackgroundTasks`) para não bloquear o webhook. Função: `process_whatsapp_message(message: WAHAMessage)`.

### 4.2 Processamento da mensagem

1. **Localização:** Se `message.location` existe, chama `process_location_message(phone, location)` – salva no contexto, emite WebSocket, responde confirmação. Fim.
2. **Conteúdo:** `content = text or button_id or ""`. Se vazio, trata como `"menu"`.
3. **WebSocket:** Emite `emit_new_message(phone, content, "incoming")` para operadores.
4. **EventLog:** Persiste `message_received` no PostgreSQL.
5. **Flow Engine:** `flow_engine.process_message(phone, content, message_id)`.

### 4.3 Flow Engine (`app/core/flow_engine.py`)

- **get_context(phone):** Lê `chat:{phone}` do Redis; se não existir, cria `ConversationContext(phone=phone)` com estado `START`.
- **process_message(phone, message, message_id):**
  - Carrega contexto, incrementa `message_count`.
  - **Comandos globais** (em qualquer estado): `menu`/`inicio`/`voltar`/`0` → reset + menu principal com botões (Fazer Pedido, Meus Pedidos, Atendente). `cancelar` → cancela pedido no DB se existir e status permitir, depois reset. `ajuda`/`help`/`?` → texto de ajuda. `atendente`/`humano` → estado `TALKING_TO_HUMAN` e mensagem de transferência.
  - Handler do estado atual: mapeamento `ConversationState` → função em `handlers.py`.
  - Chama o handler; handler retorna `ProcessedMessage(context, responses, new_state, success, error)`.
  - Salva contexto no Redis (`set_conversation_state`), marca mensagem como lida no WAHA (se `message_id`), retorna resultado.
- **send_responses(phone, responses):** Para cada `MessageResponse`: se tem imagem → `waha_client.send_image`; se tem botões → `send_buttons`; senão → `send_text`. Também persiste `message_sent` no EventLog.

### 4.4 State Machine (`app/core/state_machine.py`)

- **ConversationState (enum):**  
  `START`, `AWAITING_PRODUCT`, `AWAITING_QUANTITY`, `CONFIRMING_ADDRESS`, `AWAITING_ADDRESS`, `AWAITING_PAYMENT`, `PROCESSING_PAYMENT`, `AWAITING_PIX`, `CONFIRMING_ORDER`, `ORDER_CONFIRMED`, `TRACKING_ORDER`, `TALKING_TO_HUMAN`, `IDLE`.
- **StateTransition.VALID_TRANSITIONS:** dicionário estado → lista de estados permitidos (ex.: de `START` pode ir para `AWAITING_PRODUCT`, `TRACKING_ORDER`, `TALKING_TO_HUMAN`).
- **ConversationContext (dataclass):**  
  `phone`, `state`, `customer_id`, `customer_name`, `order_id`, `selected_product`, `selected_quantity`, `address`, `address_confirmed`, `payment_method`, `payment_id`, `asaas_payment_id`, `last_message_at`, `message_count`, `retry_count`, `last_intent`, `ai_confidence`. Métodos: `to_dict()`, `from_dict()`, `transition_to()`, `reset()`, `increment_retry()`.

### 4.5 Handlers (`app/core/handlers.py`) – Resumo por estado

- **handle_start:** Busca/cria cliente (`get_or_create_customer`), lista produtos ativos do DB, mensagem de boas-vindas + botões de produtos. Próximo estado: `AWAITING_PRODUCT`.
- **handle_awaiting_product:** Extrai código do produto (`extract_product_code`: P13/P20/P45, peso ou opção). Valida produto no DB. Pede quantidade com botões (1/2/3). Próximo: `AWAITING_QUANTITY`.
- **handle_awaiting_quantity:** Extrai quantidade (1–10). Se cliente tem endereço → mostra resumo e “Endereço está correto?” (Sim/Alterar). Se não tem endereço → pede endereço. Próximo: `CONFIRMING_ADDRESS` ou `AWAITING_ADDRESS`.
- **handle_confirming_address:** “Sim/correto” → confirma endereço e mostra totais + botões de pagamento (Pix descontinuado, Dinheiro, Cartão). “Alterar” → volta a pedir endereço. Próximo: `AWAITING_PAYMENT` ou `AWAITING_ADDRESS`.
- **handle_awaiting_address:** Valida texto mínimo, extrai bairro de `supported_bairros`, salva em `context.address` e atualiza `Customer.address`. Mostra totais e opções de pagamento. Próximo: `AWAITING_PAYMENT`.
- **handle_awaiting_payment:** Pix → mensagem “descontinuado”, mantém em `AWAITING_PAYMENT`. Dinheiro → `create_order(context, total)`, preenche `context.order_id`, emite `emit_new_order` via WebSocket, mensagem de confirmação. Próximo: `ORDER_CONFIRMED`. Cartão → pergunta “Confirmar?” (Confirmar/Voltar). Próximo: `CONFIRMING_ORDER`.
- **handle_awaiting_pix:** Sempre redireciona para “Pix descontinuado” e botões Dinheiro/Cartão. Próximo: `AWAITING_PAYMENT`.
- **handle_confirming_order:** “Confirmar” → cria pedido, emite WebSocket, confirmação. “Voltar” → volta para `handle_awaiting_payment`. Próximo: `ORDER_CONFIRMED` ou mantém.
- **handle_order_confirmed:** Se mensagem fala de status/pedido → delega para `handle_tracking_order`. Senão → reset e `handle_start`.
- **handle_tracking_order:** Busca últimos 5 pedidos do cliente no DB, formata com status e emoji, retorna texto. Próximo: `START`.
- **handle_talking_to_human:** Emite `emit_new_message` com texto “ATENDIMENTO HUMANO SOLICITADO” + mensagem para operadores; responde ao cliente que um atendente responderá. Próximo: `TALKING_TO_HUMAN`.

Funções auxiliares: `get_or_create_customer(phone)` (PostgreSQL + opcional Firebird), `get_product(code)`, `extract_product_code`, `extract_quantity`, `format_currency`, `create_order(context, total)` (Order + OrderItem, delivery_address, delivery_bairro).

---

## 5. Backend – Rotas (APIs)

Prefixos e tags conforme `main.py`:

| Prefixo            | Arquivo          | Descrição |
|--------------------|------------------|-----------|
| `/webhooks`        | webhooks.py      | POST /waha (webhook WAHA), GET /health |
| `/api/orders`      | orders.py        | CRUD pedidos, atualização de status (com side effects: notificação cliente via event_publisher, WebSocket para operadores, exportação Firebird em background quando status → delivered), listagem paginada, rejeição |
| `/api/products`    | products.py      | CRUD produtos |
| `/api/customers`   | customers.py     | CRUD clientes |
| `/ws`              | websocket.py     | Conexão WebSocket com auth, filtros por role/bairro, heartbeat, Redis bridge |
| `/api` (chats)     | chats.py         | Conversas, mensagens |
| `/api/auth`        | auth.py          | POST /login (email/senha), /register, troca de senha, etc. |
| `/api` (users)     | users.py         | Usuários, audit logs |
| `/api` (admin_*)   | admin_*.py       | Admin: users, errors, system health, debug |
| `/api` (owner)     | owner_dashboard.py | Dashboard executivo: KPIs financeiros, operacionais, pagamento, gráficos, filtros por período |
| `/api/chatbot`     | chatbot.py       | Chatbot (Ollama, etc.) |
| `/api/drivers`     | drivers.py       | CRUD entregadores, status, localização, push token |
| `/api/cargas`      | cargas.py        | Cargas de veículo, itens, acerto |
| `/api/images`      | images.py        | Upload/gestão de imagens |
| `/api/tipos-preco` | tipos_preco.py   | Tipos de preço (varejo, atacado, etc.) |
| `/api/vasilhames`  | vasilhames.py    | Vasilhames por cliente |
| `/api/locations`   | locations.py     | GET /map-data (entregadores ativos, entregas em andamento, localizações de clientes vindas de EventLog `location_received`); webhook para receber/atualizar localização (ex. driver) |
| `/api/exports`     | exports.py       | Exportação de arquivos (pedidos, etc.) |
| `/api/firebird`    | firebird_schema.py | Schema Firebird (consulta) |
| `/api/rpa`         | rpa.py           | RPA Gasmaster |
| `/api/daily-summary` | daily_summary.py | Resumo diário |
| `/api/promotions`  | promotions.py    | Promoções |
| `/api/whatsapp`    | whatsapp_broadcast.py | Broadcast WhatsApp |

Outros em `main.py`: GET `/`, GET `/health`, GET `/api/info`, GET `/metrics` (header `X-Metrics-Token`), GET `/api/audit-logs*`, e endpoints de estatísticas de dashboard.

---

## 6. Modelos de dados (PostgreSQL) – Principais

- **User (auth):** id, username, email, full_name, hashed_password, role, is_active, must_change_password, temp_password_issued_at, created_at, updated_at. (SQLModel em auth_models.)
- **Customer:** id, firebird_id, asaas_customer_id, phone (unique), name, email, cpf_cnpj, address (JSONB), notes, tipo_preco_id. Relacionamentos: orders, vasilhames, tipo_preco.
- **Product:** id, code (unique), firebird_code, name, description, weight_kg, price, is_active. Constantes: DEFAULT_PRODUCT_CODES (P13, P20, P45), WEIGHT_TO_CODE, OPTION_TO_CODE.
- **Order:** id, customer_id, order_number (sequencial), status (pending/paid/preparing/dispatched/delivered/cancelled), payment_method, asaas_payment_id, tipo_operacao (troca/venda/retira), firebird_* (trade_id, export_status, etc.), file_export_*, total_amount, delivery_address (JSONB), delivery_bairro, notes, paid_at, dispatched_at, delivered_at, cancelled_at, cancellation_reason, approved_by. Relacionamentos: customer, items (OrderItem), payments, delivery.
- **OrderItem:** order_id, product_code, product_name, quantity, unit_price, subtotal.
- **Delivery:** order_id (unique), driver_id, driver_name, driver_phone, status (pending/assigned/picked_up/in_transit/arrived/delivered/failed/returned), bairro, estimated_minutes, actual_delivery_minutes, timestamps por etapa, notes, failure_reason, last_location (JSONB), delivery_destination_lat/lng, arrived_whatsapp_sent.
- **Driver:** id, name, phone, email, vehicle_type, license_plate, status (offline/available/busy/break), current_location (JSON), rating, total_deliveries, is_active, push_token, last_online. Relacionamentos: time_logs, cargas.
- **CargaVeiculo:** driver_id, data_saida, data_retorno, status (criada/em_rota/finalizada), observacoes. Relacionamento: itens (CargaItem).
- **CargaItem:** carga_id, produto_id, qtd_saida, qtd_retorno_cheio, qtd_retorno_vazio, qtd_vendida.
- **EventLog:** event_type, entity_type, payload (JSON).
- **Error_event:** serviço, tipo, mensagem, detalhes (central de erros).

Migrações: Alembic em `backend/alembic/versions/` (initial_schema, asaas_payment_id, driver_time_logs, tipo_operacao, tipos_preco, drivers_and_cargas, firebird_export_fields, vasilhames, approved_by, error_events, file_export_fields, user_password_flags, delivery_destination_coords, etc.).

---

## 7. Integrações

### 7.1 WAHA (`app/integrations/waha.py`)

- **WAHAClient:** base_url, session_name, api_key. Métodos: get_session_status, start_session, ensure_session_ready, get_qr_code; send_text, send_buttons (fallback para texto se falhar), send_list, send_image, send_document; mark_as_read; resolve_lid (LID → @c.us), _format_phone, _get_chat_id. Uso de httpx.AsyncClient.
- Mensagens enviadas com `chatId` em formato @c.us (LID resolvido quando necessário).

### 7.2 Firebird (`app/integrations/firebird.py`)

- Cliente somente leitura para sincronização. Conexão via `fdb`. Config: host, database, user, password, charset. Métodos de leitura (clientes, produtos, etc.). Exportação de vendas é feita por serviço (firebird_export_service) ao marcar pedido como delivered (se firebird_export_on_delivered).

### 7.3 Asaas

- Configurado em settings; uso no fluxo de pagamento foi descontinuado (handlers retornam mensagem “Pix descontinuado” e não criam cobrança).

---

## 8. WebSocket (tempo real)

- **Router:** `/ws` (ex.: conexão com query params para role, bairro).
- **ScalableConnectionManager:** Conexões com metadados (user_id, user_role, bairro, region). Broadcast com filtro opcional (`filter_fn`), rate limiting (ex.: 10 broadcasts/segundo), heartbeat para desconectar inativos. Redis Pub/Sub para múltiplas instâncias (redis_websocket_bridge). EventBatcher para agrupar eventos.
- **Funções de emissão usadas no código:**  
  - `emit_new_order(order_data)` – chamada ao criar pedido nos handlers (dinheiro/cartão); envia para operadores/admins.  
  - `emit_new_message(phone, message, direction, customer_data=None)` – mensagem recebida no webhook WAHA, localização recebida, e quando cliente pede “atendente” (TALKING_TO_HUMAN).  
  Ambas publicam para Redis quando o bridge está ativo.
- **Autenticação WebSocket:** `get_current_user_ws` (token/query).

---

## 9. Autenticação e perfis

- **Login:** POST `/api/auth/login` com email e senha. Retorna JWT (access_token, token_type, role, email, must_change_password, user).
- **Roles:** admin, owner, operator, driver, user. Redirecionamento no frontend: driver → /driver/dashboard, admin → /admin, owner → /owner, operator/user → /operador.
- **Proteção de rotas:** `get_current_user` (JWT). Owner dashboard verifica owner ou admin. Rotas de driver exigem role driver.

---

## 10. Frontend (React)

- **Rotas (App.jsx):** `/` → redirect login ou dashboard por role; `/login`; `/change-password`; `/dashboard` (Layout: Dashboard, pedidos, chats); `/operador` (OperatorDashboard); `/admin` (AdminDashboard); `/owner` (OwnerDashboard); `/driver/login`, `/driver/dashboard`, `/driver/delivery/:id`, `/driver/history`, `/driver/profile`, `/driver/carga/acerto`. ProtectedRoute por role. Fallback `*` → login.
- **Auth:** AuthProvider, useAuth, token em armazenamento, envio em headers para API.
- **API base:** Configurada por variável (ex.: VITE_API_URL). Serviços em `services/api.js`, `driverApi.js`, etc.
- **WebSocket:** Hooks como useSharedWebSocket, useWebSocketDriver para painéis em tempo real.

---

## 11. Configuração (variáveis de ambiente)

- **Obrigatórias (exemplo):** SECRET_KEY, JWT_SECRET_KEY (min 32 caracteres), DATABASE_URL, REDIS_URL.
- **WAHA:** WAHA_URL, WAHA_API_KEY, WAHA_SESSION_NAME. Opcional: WHATSAPP_HOOK_URL (quando backend não está no mesmo host que WAHA).
- **Asaas:** ASAAS_API_KEY, ASAAS_WEBHOOK_TOKEN (se usar).
- **Firebird:** FIREBIRD_HOST, FIREBIRD_DATABASE, FIREBIRD_USER, FIREBIRD_PASSWORD (e opções de export em config).
- **Ollama:** OLLAMA_URL, OLLAMA_MODEL.
- **Outros:** METRICS_TOKEN, supported_bairros (config), default_delivery_time_minutes, manual_order_creation_enabled, cors_origins, access_token_expire_minutes.

---

## 12. Infra e deploy

- **Docker Compose:** Serviços: traefik (gateway), postgres, redis, backend (FastAPI), frontend (build/serve), waha, prometheus, grafana, minio (opcional), postgres-backup, sync-service, notification-service, inventory-service (conforme compose).
- **Portas típicas:** Backend 8000, Frontend 3001, WAHA 3000, Prometheus 9090, Grafana 3002, Postgres 5433 no host.

---

## 13. Resumo em uma frase

Sistema de pedidos de gás via WhatsApp (WAHA) com backend FastAPI, fluxo conversacional por máquina de estados (Redis + handlers por estado), persistência em PostgreSQL (orders, customers, products, deliveries, drivers, cargas), WebSocket escalável com Redis Pub/Sub e filtros por role/bairro, integrações Firebird (leitura e exportação) e Asaas (descontinuado no fluxo), dashboards React para admin, owner, operador e driver, e observabilidade com Prometheus/Grafana.

---

*Use o texto acima como contexto completo e em seguida escreva sua dúvida para o Claude.*
