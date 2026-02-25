# Resumo do sistema Gas Automation (para contexto em Claude AI)

Use este texto como contexto ao perguntar ao Claude. Copie e cole antes da sua dúvida.

---

## O que é o sistema

**Gas Automation** é um sistema de automação de pedidos de gás via WhatsApp para distribuidoras. O cliente pede pelo WhatsApp (bot com fluxo guiado), a operação valida/despacha no painel, o entregador atualiza status em tempo real, e há integrações com pagamentos (Asaas) e ERP (Firebird).

---

## Arquitetura (alto nível)

```
Cliente (WhatsApp) → WAHA (WhatsApp HTTP API) → Webhook → Backend (FastAPI)
                                                              ↓
                                                    Flow Engine (máquina de estados)
                                                              ↓
                                                    PostgreSQL + Redis
                                                              ↓
                    Asaas (pagamentos) | WebSocket | Firebird (ERP opcional)
                                                              ↓
                    Dashboards: Admin, Owner, Operador, Driver (React)
```

- **Infra**: Docker Compose, Traefik (gateway), PostgreSQL 15, Redis (cache + Pub/Sub para WebSocket), Prometheus/Grafana, MinIO (opcional).
- **Backend**: Python 3.x, FastAPI, SQLAlchemy (async), Alembic (migrations), Pydantic.
- **Frontend**: React, Vite, TailwindCSS, WebSocket para tempo real.
- **WhatsApp**: integração via **WAHA** (WhatsApp HTTP API); webhook recebe mensagens, backend responde (texto, botões, imagens).

---

## Fluxo principal (pedido via WhatsApp)

1. Cliente manda mensagem no WhatsApp conectado ao WAHA.
2. WAHA envia webhook para o backend (`/webhooks/waha` ou similar).
3. **Flow Engine** carrega o contexto da conversa no Redis (estado + dados do pedido em andamento).
4. **State machine**: estados como `start`, `awaiting_product`, `awaiting_quantity`, `confirming_address`, `awaiting_payment`, `awaiting_pix`, `confirming_order`, `order_confirmed`, `tracking_order`, `talking_to_human`.
5. Handlers em `app/core/handlers.py` processam cada estado e retornam respostas (texto/botões).
6. Contexto é salvo no Redis (TTL configurável). Pedido confirmado vira registro em PostgreSQL (orders, customers, etc.).
7. Resposta é enviada de volta ao cliente via WAHA (API do WAHA).

---

## Pedidos e entregas

- **Status do pedido**: `pending` → `paid` → `preparing` → `dispatched` → `delivered` (ou `cancelled`).
- **Cargas**: entidade “carga” para agrupar entregas; entregador (driver) recebe “carga” com várias entregas.
- **Driver**: painel próprio (driver); atualiza status da entrega, time tracking (logs de tempo), pode receber notificações (FCM/push).
- **Locations**: endpoint de localização (ex.: coordenadas do entregador ou destino) com possível webhook.

---

## Perfis (RBAC)

| Role      | Uso principal                                      |
|-----------|----------------------------------------------------|
| `admin`   | Administração total (usuários, sistema, debug)     |
| `owner`   | Visão executiva (KPIs, relatórios, dashboard dono) |
| `operator`| Operação diária (pedidos, conversas, despacho)     |
| `driver`  | Entregas e atualização de status                   |

Autenticação: JWT; senha com hash; pode haver flags de “primeiro acesso” / “troca de senha obrigatória”.

---

## Principais módulos do backend (FastAPI)

- **api/webhooks.py**: webhook WAHA (mensagens recebidas), possivelmente webhook Asaas (pagamentos).
- **api/orders.py**, **api/customers.py**, **api/products.py**: CRUD e listagens.
- **api/drivers.py**, **api/cargas.py**: entregadores e cargas.
- **api/chats.py**, **api/chatbot.py**: conversas e chatbot (pode usar Ollama local).
- **api/auth.py**: login, JWT, usuários.
- **api/owner_dashboard.py**: dados para dashboard do dono (KPIs, resumos).
- **api/websocket.py**: conexões WebSocket com filtros por role/bairro, heartbeat, rate limiting; **Redis WebSocket Bridge** para múltiplas instâncias.
- **core/flow_engine.py**: orquestra o fluxo WhatsApp (estado → handler → resposta).
- **core/state_machine.py**: definição dos estados da conversa.
- **core/handlers.py**: lógica de cada estado (produto, quantidade, endereço, pagamento, confirmação, etc.).
- **integrations/waha.py**: cliente HTTP para WAHA (enviar mensagem, botões, etc.).
- **integrations/asaas.py**: cobranças e status de pagamento.
- **integrations/firebird.py**: conexão ao banco Firebird (ERP legado); exportação de vendas/entregas quando habilitado.
- **services/**: order_service, delivery_service, driver_service, customer_service, product_service, payment_service, firebird_export_service, geocoding_service, etc.

---

## Banco de dados (PostgreSQL)

- **Principais entidades**: users (auth), customers, orders, order_items, products, drivers, deliveries, cargas, driver_time_logs, payments (Asaas), event_log, error_events, promotions, tipos_preco, vasilhames (embalagens/recursos), etc.
- Migrations: Alembic em `backend/alembic/versions/`.
- Async: SQLAlchemy com `asyncpg`.

---

## Configuração (variáveis de ambiente)

- **Segurança**: `SECRET_KEY`, `JWT_SECRET_KEY`, `METRICS_TOKEN` (Protege `/metrics`).
- **Banco**: `DATABASE_URL` (PostgreSQL).
- **Redis**: `REDIS_URL`.
- **WAHA**: `WAHA_URL`, `WAHA_API_KEY`, `WAHA_SESSION_NAME`.
- **Asaas**: `ASAAS_API_KEY`, `ASAAS_WEBHOOK_TOKEN` (se usar).
- **Firebird**: `FIREBIRD_HOST`, `FIREBIRD_DATABASE`, `FIREBIRD_USER`, `FIREBIRD_PASSWORD`, e opções de export (tabelas, IDs de estabelecimento, etc.).
- **Ollama**: `OLLAMA_URL`, `OLLAMA_MODEL` (chatbot).
- **MinIO**: opcional para arquivos.

Config carregada em `backend/app/config.py` (Pydantic Settings).

---

## Escalabilidade e tempo real

- WebSocket com **filtros** (por role, bairro) e **deduplicação** por usuário.
- **Event batching** para reduzir mensagens em pico.
- **Redis Pub/Sub** como bridge para múltiplas instâncias do backend (WebSocket escalável).
- Paginação nos endpoints para não carregar tudo de uma vez.
- Meta: suportar alta demanda (ex.: 9.000+ pedidos/semana); há docs de verificação de capacidade.

---

## URLs típicas (desenvolvimento)

- Frontend: `http://localhost:3001`
- Backend API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- WAHA: `http://localhost:3000`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3002`

---

## Documentação interna (no repositório)

- `docs/relatorios/`, `docs/resumos/`, `docs/planos/`, `docs/configuracao/`, etc.
- Ex.: relatório executivo, escalabilidade, configuração de webhook WAHA, verificações de capacidade.

---

## Resumo em uma frase

Sistema de pedidos de gás via WhatsApp (WAHA) com backend FastAPI, fluxo conversacional por máquina de estados, pedidos/entregas/cargas/drivers em PostgreSQL, WebSocket em tempo real com Redis, integrações Asaas e Firebird, e dashboards React para admin, dono, operador e entregador.

---

*Use o texto acima como contexto e em seguida escreva sua dúvida para o Claude.*
