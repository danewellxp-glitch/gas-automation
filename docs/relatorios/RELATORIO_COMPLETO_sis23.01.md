# 📋 Relatório Completo do Projeto - Gas Automation System

**Data:** 23 de Janeiro de 2026  
**Versão do Sistema:** 1.0.0  
**Status:** Em Desenvolvimento Ativo (73% Completo)

---

## 📌 Sumário Executivo

O **Gas Automation System** é uma plataforma completa de automação de pedidos de gás via WhatsApp, integrada com sistema ERP legado (Firebird), gateway de pagamento (Asaas), e dashboard administrativo em tempo real. O sistema permite que clientes façam pedidos através de conversas no WhatsApp, com processamento automático via IA (Ollama) e acompanhamento em tempo real por operadores, administradores e entregadores.

### Principais Características

- 🤖 **Chatbot Inteligente**: Processa pedidos via WhatsApp com IA local (Ollama)
- 💬 **Atendimento Híbrido**: Bot automático + escalação para atendentes humanos
- 📦 **Gestão de Pedidos**: Ciclo completo de pedido (criação → pagamento → entrega)
- 👥 **Multi-Role**: 4 tipos de usuários (admin, owner, operator, driver)
- 🔄 **Integração ERP**: Sincronização bidirecional com Firebird
- 💳 **Pagamentos**: Integração com Asaas (PIX, cartão, boleto)
- 📊 **Dashboard em Tempo Real**: WebSocket para atualizações instantâneas
- 🚚 **Sistema de Entrega**: Rastreamento de entregadores e entregas
- 📈 **Monitoramento**: Prometheus + Grafana para métricas
- 🐳 **Docker-Ready**: Infraestrutura containerizada completa

---

## 🏗️ Arquitetura do Sistema

### Visão Geral

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENTE (WhatsApp)                        │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              WAHA (WhatsApp HTTP API)                       │
│              Porta: 3000                                     │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              BACKEND (FastAPI)                               │
│              Porta: 8000                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Flow Engine  │  │   Services   │  │ Integrations │     │
│  │  (Estado)     │  │  (Negócio)   │  │  (Externas)  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└───────┬──────────────────┬──────────────────┬──────────────┘
        │                  │                  │
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  PostgreSQL  │  │    Redis     │  │   Firebird    │
│  (Principal) │  │   (Cache)    │  │   (Legado)    │
└──────────────┘  └──────────────┘  └──────────────┘
        │                  │
        ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│              FRONTEND (React + Vite)                        │
│              Porta: 3001                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Admin      │  │   Operator   │  │    Driver    │     │
│  │  Dashboard   │  │   Dashboard  │  │  Dashboard   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### Componentes Principais

1. **WAHA (WhatsApp HTTP API)**: Recebe mensagens do WhatsApp e envia para o backend via webhook
2. **Backend FastAPI**: Processa mensagens, gerencia pedidos, integra com serviços externos
3. **Flow Engine**: Máquina de estados que gerencia o fluxo de conversação
4. **PostgreSQL**: Banco de dados principal (pedidos, clientes, usuários)
5. **Redis**: Cache de conversas, sessões, e bridge para WebSocket horizontal
6. **Firebird**: Sistema ERP legado (somente leitura para sincronização)
7. **Frontend React**: Dashboards para diferentes roles de usuário
8. **Ollama**: IA local para análise de intenções e processamento de linguagem natural

---

## 🛠️ Stack Tecnológica

### Backend

| Tecnologia | Versão | Uso |
|------------|--------|-----|
| **Python** | 3.11+ | Linguagem principal |
| **FastAPI** | Latest | Framework web assíncrono |
| **SQLAlchemy** | 2.0+ | ORM para PostgreSQL |
| **Alembic** | Latest | Migrações de banco |
| **Pydantic** | 2.0+ | Validação de dados |
| **Redis** | 7+ | Cache e mensageria |
| **fdb** | Latest | Cliente Firebird |
| **Ollama** | Latest | IA local |
| **Prometheus Client** | Latest | Métricas |

### Frontend

| Tecnologia | Versão | Uso |
|------------|--------|-----|
| **React** | 18+ | Framework UI |
| **Vite** | Latest | Build tool |
| **TailwindCSS** | Latest | Estilização |
| **Axios** | Latest | HTTP client |
| **React Router** | Latest | Roteamento |
| **WebSocket** | Native | Comunicação em tempo real |

### Infraestrutura

| Tecnologia | Versão | Uso |
|------------|--------|-----|
| **Docker** | Latest | Containerização |
| **Docker Compose** | Latest | Orquestração |
| **Traefik** | 2.11+ | API Gateway / Load Balancer |
| **PostgreSQL** | 15 | Banco de dados |
| **Redis** | 7 | Cache |
| **MinIO** | Latest | Object Storage (S3-compatible) |
| **Prometheus** | Latest | Coleta de métricas |
| **Grafana** | Latest | Visualização de métricas |

### Integrações Externas

- **WAHA**: WhatsApp HTTP API (devlikeapro/waha)
- **Asaas**: Gateway de pagamento (PIX, cartão, boleto)
- **Firebird**: Sistema ERP legado (somente leitura)
- **Ollama**: IA local para processamento de linguagem natural

---

## 📦 Funcionalidades Principais

### 1. Sistema de Pedidos via WhatsApp

#### Fluxo de Conversação

O sistema utiliza uma **máquina de estados** para gerenciar o fluxo de conversação:

```
START → AWAITING_PRODUCT → AWAITING_QUANTITY → CONFIRMING_ADDRESS 
→ AWAITING_ADDRESS → AWAITING_PAYMENT → AWAITING_PIX 
→ CONFIRMING_ORDER → ORDER_CONFIRMED → TRACKING_ORDER
```

**Estados Principais:**

- **START**: Início da conversa, saudação
- **AWAITING_PRODUCT**: Aguardando cliente escolher produto (P13, P20, P45)
- **AWAITING_QUANTITY**: Aguardando quantidade desejada
- **CONFIRMING_ADDRESS**: Confirmando endereço cadastrado
- **AWAITING_ADDRESS**: Solicitando novo endereço
- **AWAITING_PAYMENT**: Escolhendo método de pagamento
- **AWAITING_PIX**: Aguardando confirmação de pagamento PIX
- **CONFIRMING_ORDER**: Revisão final do pedido
- **ORDER_CONFIRMED**: Pedido confirmado
- **TRACKING_ORDER**: Acompanhamento de pedido
- **TALKING_TO_HUMAN**: Escalado para atendente humano

#### Processamento de Mensagens

1. **Recepção**: WAHA recebe mensagem do WhatsApp
2. **Webhook**: Envia para `/webhooks/waha` no backend
3. **Flow Engine**: Processa mensagem baseado no estado atual
4. **IA (Ollama)**: Analisa intenção quando necessário
5. **Handler**: Executa lógica específica do estado
6. **Resposta**: Envia resposta via WAHA para WhatsApp
7. **Persistência**: Salva contexto no Redis e eventos no PostgreSQL

### 2. Sistema de Autenticação e Autorização (RBAC)

#### Roles de Usuário

| Role | Descrição | Permissões |
|------|-----------|------------|
| **admin** | Administrador | Acesso total, gerencia usuários e roles |
| **owner** | Proprietário | Visão executiva, relatórios, métricas |
| **operator** | Operador | Atende pedidos, cria pedidos manualmente |
| **driver** | Entregador | Visualiza entregas, atualiza status |

#### Autenticação

- **JWT Tokens**: Tokens com expiração configurável
- **Bcrypt**: Hash de senhas
- **Protected Routes**: Rotas protegidas por role
- **Session Management**: Gerenciamento de sessão via Redis

#### Endpoints de Autenticação

```
POST /api/auth/login      # Login (retorna JWT)
POST /api/auth/logout     # Logout
GET  /api/auth/me         # Usuário atual
POST /api/auth/refresh    # Renovar token
```

### 3. Gestão de Pedidos

#### Status de Pedidos

| Status | Descrição |
|--------|-----------|
| `pending` | Aguardando pagamento |
| `paid` | Pago, aguardando preparo |
| `preparing` | Em preparação |
| `dispatched` | Saiu para entrega |
| `delivered` | Entregue |
| `cancelled` | Cancelado |

#### Endpoints de Pedidos

```
GET    /api/orders              # Listar pedidos (paginado)
POST   /api/orders              # Criar pedido (auth required)
GET    /api/orders/{id}         # Detalhes do pedido
GET    /api/orders/pending      # Pedidos pendentes
POST   /api/orders/{id}/approve # Aprovar pedido
POST   /api/orders/{id}/reject  # Rejeitar pedido
PUT    /api/orders/{id}/status  # Atualizar status
```

### 4. Sistema de Clientes

- **Cadastro Automático**: Clientes criados automaticamente no primeiro contato
- **Histórico**: Todos os pedidos vinculados ao cliente
- **Endereços**: Múltiplos endereços por cliente
- **Busca**: Busca por telefone, nome, ou ID

### 5. Sistema de Produtos

- **Catálogo**: Produtos sincronizados do Firebird
- **Estoque**: Níveis de estoque em tempo real
- **Preços**: Preços com e sem troca
- **Ativação/Desativação**: Controle de disponibilidade

### 6. Sistema de Entregas

- **Rastreamento**: Status de entrega em tempo real
- **Entregadores**: Gestão de entregadores (drivers)
- **Histórico**: Histórico completo de entregas
- **Tempo de Entrega**: Tracking de tempo de entrega

### 7. Sistema de Pagamentos

- **Integração Asaas**: Gateway de pagamento completo
- **Métodos Suportados**: PIX, cartão de crédito, cartão de débito, boleto, dinheiro
- **Webhooks**: Recebimento de confirmações de pagamento
- **Status**: Rastreamento de status de pagamento

### 8. Dashboard em Tempo Real

- **WebSocket**: Comunicação bidirecional em tempo real
- **Event Batching**: Agrupamento de eventos para performance
- **Redis Bridge**: Escala horizontal via Redis Pub/Sub
- **Métricas**: Métricas Prometheus integradas

---

## 🗄️ Estrutura de Dados

### Modelos Principais

#### User (Usuários)
```python
- id: int (PK)
- username: str (unique)
- email: str (unique)
- full_name: str
- hashed_password: str
- role: str (admin, owner, operator, driver, user)
- is_active: bool
- created_at: datetime
- updated_at: datetime
```

#### Customer (Clientes)
```python
- id: UUID (PK)
- phone: str (unique, indexed)
- name: str
- addresses: JSONB (array de endereços)
- created_at: datetime
- updated_at: datetime
```

#### Order (Pedidos)
```python
- id: UUID (PK)
- customer_id: UUID (FK)
- order_number: int (unique, sequential)
- status: str (pending, paid, preparing, dispatched, delivered, cancelled)
- payment_method: str (pix, credit_card, debit_card, cash, boleto)
- total_amount: Decimal
- delivery_address: JSONB
- notes: str
- delivered_at: datetime
- created_at: datetime
- updated_at: datetime
```

#### Delivery (Entregas)
```python
- id: UUID (PK)
- order_id: UUID (FK)
- driver_id: UUID (FK)
- status: str
- started_at: datetime
- completed_at: datetime
- location: JSONB
```

#### Product (Produtos)
```python
- id: UUID (PK)
- code: str (unique)
- name: str
- description: str
- price_with_exchange: Decimal
- price_without_exchange: Decimal
- stock_quantity: int
- is_active: bool
- firebird_id: int (FK para Firebird)
```

### Relacionamentos

```
User (1) ──< (N) Conversation
Customer (1) ──< (N) Order
Order (1) ──< (1) Delivery
Order (N) ──< (N) OrderItem
Product (1) ──< (N) OrderItem
Driver (1) ──< (N) Delivery
```

---

## 🔐 Autenticação e Segurança

### Autenticação JWT

- **Algoritmo**: HS256
- **Expiração**: Configurável (padrão: 24 horas)
- **Refresh Token**: Suportado
- **Secret Key**: Configurável via variável de ambiente

### Segurança

- **CORS**: Configurado com whitelist de origens
- **Rate Limiting**: Implementado via SlowAPI
- **Password Hashing**: Bcrypt com salt
- **SQL Injection**: Protegido via SQLAlchemy ORM
- **XSS**: Protegido via React (sanitização automática)
- **CSRF**: Protegido via tokens JWT

### Variáveis de Ambiente Críticas

```bash
SECRET_KEY              # Chave secreta para sessões (mínimo 32 caracteres)
JWT_SECRET_KEY          # Chave para assinatura JWT
DATABASE_URL            # URL de conexão PostgreSQL
REDIS_URL               # URL de conexão Redis
WAHA_API_KEY            # Chave de API do WAHA
ASAAS_API_KEY           # Chave de API do Asaas
FIREBIRD_HOST           # Host do Firebird
FIREBIRD_DATABASE       # Database do Firebird
FIREBIRD_PASSWORD       # Senha do Firebird
```

---

## 🔌 Integrações

### 1. WAHA (WhatsApp HTTP API)

**Propósito**: Interface com WhatsApp

**Funcionalidades**:
- Recebe mensagens do WhatsApp
- Envia mensagens para WhatsApp
- Gerencia sessões WhatsApp
- Suporta imagens, áudios, documentos

**Configuração**:
```yaml
WAHA_URL: http://waha:3000
WAHA_API_KEY: <chave>
WAHA_SESSION_NAME: default
```

### 2. Firebird (ERP Legado)

**Propósito**: Sincronização com sistema ERP legado

**Funcionalidades**:
- Leitura de produtos
- Leitura de clientes
- Sincronização de estoque
- Exportação de pedidos (futuro)

**Modo**: Somente leitura (para evitar conflitos)

**Configuração**:
```yaml
FIREBIRD_HOST: <host>
FIREBIRD_DATABASE: <caminho_do_arquivo>
FIREBIRD_USER: SYSDBA
FIREBIRD_PASSWORD: <senha>
FIREBIRD_CHARSET: UTF8
```

### 3. Asaas (Gateway de Pagamento)

**Propósito**: Processamento de pagamentos

**Funcionalidades**:
- Criação de cobranças PIX
- Processamento de cartão
- Geração de boletos
- Webhooks de confirmação

**Configuração**:
```yaml
ASAAS_API_KEY: <chave>
ASAAS_API_URL: https://api.asaas.com/v3
ASAAS_WEBHOOK_TOKEN: <token>
```

### 4. Ollama (IA Local)

**Propósito**: Análise de intenções e processamento de linguagem natural

**Funcionalidades**:
- Análise de intenção de mensagens
- Identificação de produtos mencionados
- Extração de informações (quantidade, endereço)
- Respostas contextuais

**Configuração**:
```yaml
OLLAMA_URL: http://ollama:11434
OLLAMA_MODEL: qwen2.5:3b
OLLAMA_TIMEOUT: 30
AI_CONFIDENCE_THRESHOLD: 0.7
```

### 5. MinIO (Object Storage)

**Propósito**: Armazenamento de imagens e arquivos

**Funcionalidades**:
- Upload de imagens
- Armazenamento S3-compatible
- URLs públicas para acesso

**Configuração**:
```yaml
MINIO_ENDPOINT: minio:9000
MINIO_ROOT_USER: minioadmin
MINIO_ROOT_SECRET_KEY: minioadmin123
```

---

## 🎨 Frontend

### Estrutura de Páginas

#### 1. Login (`/login`)
- Autenticação de usuários
- Redirecionamento baseado em role

#### 2. Admin Dashboard (`/admin`)
- Gerenciamento de usuários
- Edição de roles
- Logs de auditoria
- Configurações do sistema

#### 3. Operator Dashboard (`/operador`)
- Lista de pedidos pendentes
- Criação manual de pedidos
- Atendimento de conversas
- Aprovação/rejeição de pedidos

#### 4. Owner Dashboard (`/owner`)
- Visão executiva
- Métricas e KPIs
- Gráficos de receita
- Estatísticas de pedidos

#### 5. Driver Dashboard (`/driver`)
- Lista de entregas atribuídas
- Atualização de status de entrega
- Histórico de entregas
- Tracking de tempo

### Componentes Principais

- **ProtectedRoute**: Proteção de rotas por role
- **Layout**: Layout comum com navegação
- **WebSocket Hook**: Hook para comunicação em tempo real
- **Pagination**: Componente de paginação reutilizável

### Estado Global

- **AuthContext**: Contexto de autenticação
- **WebSocket**: Conexão WebSocket compartilhada
- **LocalStorage**: Persistência de token e role

---

## 🚀 Infraestrutura

### Docker Compose

O projeto utiliza Docker Compose para orquestração de serviços:

**Serviços Principais**:
- `backend`: API FastAPI
- `frontend`: Aplicação React
- `postgres`: Banco de dados PostgreSQL
- `redis`: Cache e mensageria
- `waha`: WhatsApp HTTP API
- `ollama`: IA local
- `traefik`: API Gateway
- `minio`: Object Storage
- `prometheus`: Coleta de métricas
- `grafana`: Visualização de métricas

**Perfis**:
- `gateway`: Traefik
- `storage`: MinIO
- `microservices`: Notification Service, Inventory Service
- `monitoring`: Prometheus, Grafana
- `tools`: pgAdmin, Redis Commander

### Rede

- **Network**: `gas_network` (bridge)
- **Isolamento**: Serviços isolados por rede Docker

### Volumes

- `postgres_data`: Dados do PostgreSQL
- `redis_data`: Dados do Redis
- `waha_data`: Sessões do WAHA
- `ollama_data`: Modelos da IA
- `minio_data`: Arquivos do MinIO
- `prometheus_data`: Métricas do Prometheus
- `grafana_data`: Dashboards do Grafana

---

## 📊 Monitoramento e Observabilidade

### Prometheus

**Métricas Coletadas**:
- Requisições HTTP (total, por endpoint, por status)
- Tempo de resposta
- Conexões WebSocket ativas
- Eventos processados
- Uptime do sistema
- Uso de recursos

**Endpoint**: `GET /metrics` (requer header `X-Metrics-Token`)

### Grafana

**Dashboards**:
- Visão geral do sistema
- Métricas de performance
- Análise de erros
- Uso de recursos

**Acesso**: `http://grafana.localhost:3002`

### Health Checks

```
GET /health              # Health check geral
GET /health/db           # Status do banco de dados
GET /health/redis        # Status do Redis
GET /health/waha         # Status do WAHA
```

---

## 🔄 Fluxo de Pedido Completo

### 1. Cliente Inicia Conversa

```
Cliente → WhatsApp → WAHA → Webhook → Backend
```

### 2. Flow Engine Processa

```
Flow Engine → Carrega Contexto (Redis) → Identifica Estado → Executa Handler
```

### 3. Coleta de Informações

```
Estado: AWAITING_PRODUCT
Cliente escolhe: "P13"
→ Estado: AWAITING_QUANTITY
Cliente informa: "2"
→ Estado: CONFIRMING_ADDRESS
Cliente confirma endereço
→ Estado: AWAITING_PAYMENT
Cliente escolhe: "PIX"
```

### 4. Criação de Pedido

```
Handler → OrderService → Cria Order (status: pending)
→ PaymentService → Cria cobrança Asaas
→ Envia QR Code PIX para cliente
```

### 5. Pagamento

```
Asaas → Webhook → Backend
→ PaymentService → Atualiza Order (status: paid)
→ Notifica operador via WebSocket
```

### 6. Preparação

```
Operador → Aprova pedido
→ OrderService → Atualiza (status: preparing)
→ Notifica cliente via WhatsApp
```

### 7. Entrega

```
Operador → Atribui entregador
→ DeliveryService → Cria Delivery
→ OrderService → Atualiza (status: dispatched)
→ Driver atualiza status em tempo real
→ OrderService → Atualiza (status: delivered)
```

---

## 🧪 Testes

### Estrutura de Testes

```
backend/
  tests/
    __init__.py
    conftest.py          # Fixtures e configuração
    test_auth.py         # Testes de autenticação
    test_orders.py        # Testes de pedidos
    test_customers.py    # Testes de clientes
    test_flow_engine.py  # Testes do flow engine
    test_integrations.py # Testes de integrações
```

### Executar Testes

```bash
cd backend
pytest -v                    # Todos os testes
pytest tests/test_auth.py   # Testes específicos
pytest --cov=app --cov-report=html  # Com coverage
```

---

## 📝 Desenvolvimento

### Setup Local

1. **Clonar repositório**
```bash
git clone <repo-url>
cd gas-automation
```

2. **Configurar variáveis de ambiente**
```bash
cp .env.example .env
# Editar .env com suas configurações
```

3. **Iniciar serviços**
```bash
docker-compose up -d
```

4. **Executar migrações**
```bash
cd backend
alembic upgrade head
```

5. **Criar usuário admin**
```bash
python create_user.py
```

### Desenvolvimento Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Desenvolvimento Frontend

```bash
cd frontend
npm install
npm run dev
```

### Estrutura de Código

```
backend/
  app/
    api/              # Endpoints REST
    auth.py
    orders.py
    customers.py
    ...
    core/             # Lógica de negócio
      flow_engine.py
      state_machine.py
      handlers.py
    models/           # Modelos SQLAlchemy
    schemas/          # Schemas Pydantic
    services/         # Serviços de negócio
    integrations/     # Integrações externas
    workers/          # Background workers
  alembic/            # Migrações
  tests/              # Testes

frontend/
  src/
    pages/            # Páginas React
    components/       # Componentes reutilizáveis
    hooks/            # Custom hooks
    services/         # Serviços (API, WebSocket)
    context/          # Context API
    utils/            # Utilitários
```

---

## 🐛 Troubleshooting

### Problemas Comuns

#### 1. WAHA não conecta ao WhatsApp
- Verificar se QR Code foi escaneado
- Verificar logs: `docker-compose logs waha`
- Verificar variável `WAHA_API_KEY`

#### 2. Erro de conexão com Firebird
- Verificar se Firebird está acessível
- Verificar credenciais em `.env`
- Verificar se biblioteca `fdb` está instalada

#### 3. WebSocket não conecta
- Verificar se Redis está rodando
- Verificar CORS no backend
- Verificar URL do WebSocket no frontend

#### 4. Erro de autenticação
- Verificar `SECRET_KEY` e `JWT_SECRET_KEY`
- Verificar se token não expirou
- Verificar role do usuário

---

## 📚 Documentação Adicional

### Documentos Importantes

- `README.md`: Guia de início rápido
- `ORGANIZACAO_DOCUMENTOS.md`: Sistema de organização de docs
- `docs/`: Documentação organizada por categoria
  - `relatorios/`: Relatórios e análises
  - `resumos/`: Resumos executivos
  - `planos/`: Planos e roadmaps
  - `guias/`: Guias e tutoriais
  - `correcoes/`: Correções e soluções

### APIs Documentadas

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

## 🎯 Roadmap e Status

### Status Atual (73% Completo)

✅ **Completo**:
- Autenticação e autorização (RBAC)
- Flow Engine e máquina de estados
- Integração WAHA (WhatsApp)
- Integração Firebird (somente leitura)
- Dashboard multi-role
- Sistema de pedidos básico
- WebSocket em tempo real
- Docker e infraestrutura

🟡 **Em Progresso**:
- Testes automatizados
- Integração completa com Asaas
- Sistema de entregas completo
- Sincronização bidirecional Firebird

❌ **Planejado**:
- Notificações push
- Relatórios avançados
- App mobile para entregadores
- Integração com outros gateways de pagamento

---

## 👥 Contribuição

### Como Contribuir

1. Criar branch: `git checkout -b feature/nova-funcionalidade`
2. Fazer alterações e commits
3. Push: `git push origin feature/nova-funcionalidade`
4. Abrir Pull Request

### Padrões de Código

- **Python**: PEP 8, type hints, docstrings
- **JavaScript/React**: ESLint, Prettier
- **Commits**: Conventional Commits
- **Testes**: Cobertura mínima de 70%

---

## 📞 Suporte e Contato

### Informações do Projeto

- **Nome**: Gas Automation System
- **Versão**: 1.0.0
- **Licença**: Proprietary
- **Repositório**: [URL do repositório]

### Equipe

- **Desenvolvimento**: [Equipe de desenvolvimento]
- **Arquitetura**: [Arquiteto responsável]
- **DevOps**: [Equipe DevOps]

---

## 📄 Licença

Proprietary - All rights reserved

---

**Última Atualização**: 23 de Janeiro de 2026  
**Versão do Documento**: 1.0  
**Autor**: Sistema de Documentação Automática

---

## 🔗 Links Úteis

- **API Docs**: http://localhost:8000/docs
- **Grafana**: http://localhost:3002
- **Prometheus**: http://localhost:9090
- **Traefik Dashboard**: http://traefik.localhost:8080
- **MinIO Console**: http://minio.localhost:9001

---

**Este documento serve como referência completa para entender o sistema Gas Automation. Para informações específicas, consulte a documentação técnica nos arquivos do projeto ou a documentação da API em `/docs`.**
