# Relatório Executivo - Sistema Gas Automation

**Data:** 28 de Janeiro de 2026  
**Versão do Sistema:** 1.0.0  
**Propósito:** Documentação executiva e lógica para compreensão do sistema por inteligência artificial

---

## 1. PROPÓSITO E DOMÍNIO DE NEGÓCIO

### 1.1 O Que É Este Sistema

O **Gas Automation** é um sistema completo de automação de pedidos de gás liquefeito de petróleo (GLP) via WhatsApp. O sistema permite que clientes façam pedidos de botijas de gás através de conversas no WhatsApp, automatizando todo o processo desde a recepção do pedido até a entrega e integração com sistemas fiscais.

### 1.2 Problema Que Resolve

**Antes:** Clientes precisavam ligar para fazer pedidos, operadores anotavam manualmente, havia risco de erros, falta de rastreamento e necessidade de integração manual com sistemas fiscais.

**Depois:** Clientes fazem pedidos via WhatsApp de forma automatizada, o sistema gerencia todo o fluxo, operadores têm dashboards em tempo real, entregadores recebem pedidos automaticamente, e há integração automática com sistemas fiscais.

### 1.3 Domínio de Negócio

- **Produtos:** Botijas de gás P13 (13kg), P20 (20kg), P45 (45kg)
- **Operações:** Troca (cliente tem vasilhame vazio), Venda (cliente compra vasilhame novo), Retira (cliente busca na loja)
- **Pagamentos:** PIX, Cartão de Crédito/Débito, Boleto, Dinheiro
- **Entregas:** Sistema de roteamento por bairro, atribuição de entregadores, rastreamento em tempo real
- **Integração Fiscal:** Exportação para sistema Firebird (ERP legado) para emissão de notas fiscais

---

## 2. ARQUITETURA GERAL

### 2.1 Padrão Arquitetural

**Arquitetura de Microserviços com Backend Monolítico Modular:**

- **Backend Principal:** FastAPI monolítico com módulos bem definidos
- **Microserviços Especializados:** 
  - `sync-service`: Sincronização com Firebird
  - `inventory-service`: Gestão de estoque
  - `notification-service`: Notificações (email, SMS)
- **Frontend:** React (JSX) com Vite
- **Comunicação:** REST API + WebSocket para tempo real
- **Infraestrutura:** Docker Compose, Traefik (API Gateway), Prometheus/Grafana (monitoramento)

### 2.2 Stack Tecnológica

**Backend:**
- Python 3.11+
- FastAPI (framework web assíncrono)
- SQLAlchemy (ORM) + Alembic (migrations)
- PostgreSQL (banco principal)
- Redis (cache, sessões, pub/sub para WebSocket)
- Pydantic (validação de dados)

**Frontend:**
- React (JSX)
- Vite (build tool)
- TailwindCSS (estilização)
- Axios (HTTP client)

**Integrações:**
- WAHA (WhatsApp HTTP API) - comunicação WhatsApp
- Asaas - gateway de pagamento (PIX, cartão, boleto)
- Ollama - IA local para chatbot (opcional)
- Firebird - sistema ERP legado (somente leitura para sincronização)

**Infraestrutura:**
- Docker & Docker Compose
- Traefik (reverse proxy, load balancer)
- Prometheus (métricas)
- Grafana (dashboards)
- MinIO (armazenamento de imagens, opcional)

---

## 3. COMPONENTES PRINCIPAIS

### 3.1 Backend Principal (`backend/app/`)

#### 3.1.1 API Routes (`api/`)
- **`webhooks.py`**: Recebe eventos do WhatsApp (WAHA) e Asaas
- **`orders.py`**: CRUD de pedidos
- **`customers.py`**: Gerenciamento de clientes
- **`products.py`**: Catálogo de produtos
- **`drivers.py`**: Gerenciamento de entregadores
- **`cargas.py`**: Gestão de cargas (rotas de entrega)
- **`websocket.py`**: WebSocket para atualizações em tempo real
- **`auth.py`**: Autenticação JWT e RBAC
- **`users.py`**: Gerenciamento de usuários do sistema
- **`chatbot.py`**: Endpoints para chatbot com IA
- **`exports.py`**: Exportação de dados (CSV, relatórios)
- **`firebird_schema.py`**: Endpoints para explorar schema Firebird
- **`rpa.py`**: Automação RPA para sistema Gasmaster (calibração)

#### 3.1.2 Core (`core/`)
- **`flow_engine.py`**: Motor principal de processamento de mensagens WhatsApp
- **`state_machine.py`**: Máquina de estados da conversa (START → AWAITING_PRODUCT → ... → ORDER_CONFIRMED)
- **`handlers.py`**: Handlers específicos para cada estado da conversa
- **`business_rules.py`**: Regras de negócio centralizadas
- **`redis_websocket_bridge.py`**: Bridge Redis para escala horizontal de WebSocket
- **`event_batcher.py`**: Agrupamento de eventos para otimização
- **`message_store.py`**: Armazenamento de mensagens para replay

#### 3.1.3 Models (`models/`)
- **`order.py`**: Order, OrderItem (pedidos e itens)
- **`customer.py`**: Customer (clientes)
- **`product.py`**: Product (produtos)
- **`driver.py`**: Driver (entregadores)
- **`delivery.py`**: Delivery (entregas)
- **`payment.py`**: Payment (pagamentos)
- **`auth_models.py`**: User, Role, Conversation, Message, AuditLog
- **`carga.py`**: Carga (rotas de entrega)
- **`vasilhame.py`**: Vasilhame (controle de vasilhames)
- **`tipo_preco.py`**: TipoPreco (tipos de preço: troca/venda)

#### 3.1.4 Services (`services/`)
- **`order_service.py`**: Lógica de negócio para pedidos
- **`customer_service.py`**: Lógica de negócio para clientes
- **`delivery_service.py`**: Lógica de negócio para entregas
- **`driver_service.py`**: Lógica de negócio para entregadores
- **`product_service.py`**: Lógica de negócio para produtos
- **`payment_service.py`**: Integração com Asaas
- **`enhanced_chatbot_service.py`**: Chatbot com IA (Ollama/Claude)
- **`order_bot_service.py`**: Bot especializado em criação de pedidos
- **`firebird_export_service.py`**: Exportação de pedidos para Firebird
- **`file_export_service.py`**: Exportação alternativa para arquivos
- **`rpa_gasmaster_service.py`**: Automação RPA para calibração

#### 3.1.5 Integrations (`integrations/`)
- **`waha.py`**: Cliente WAHA (WhatsApp HTTP API)
- **`asaas.py`**: Cliente Asaas (pagamentos)
- **`firebird.py`**: Cliente Firebird (ERP legado, somente leitura)
- **`ollama.py`**: Cliente Ollama (IA local)
- **`minio_client.py`**: Cliente MinIO (armazenamento)

### 3.2 Microserviços (`backend/services/`)

#### 3.2.1 Sync Service
- **Propósito:** Sincronização bidirecional com Firebird
- **Funcionalidades:**
  - Sincronização de produtos (catálogo)
  - Sincronização de clientes
  - Exportação de pedidos para Firebird (TRADE/TRADEITEM)
  - Sincronização de estoque
  - Agendamento automático configurável

#### 3.2.2 Inventory Service
- **Propósito:** Gestão de estoque independente
- **Funcionalidades:**
  - Controle de estoque por produto
  - Alertas de estoque baixo
  - Histórico de movimentações

#### 3.2.3 Notification Service
- **Propósito:** Envio de notificações
- **Funcionalidades:**
  - Email (SendGrid)
  - SMS (Twilio)
  - Notificações push (futuro)

### 3.3 Frontend (`frontend/`)

- **Componentes React:** Dashboards, formulários, listas
- **Páginas:**
  - Dashboard do Owner (visão executiva)
  - Dashboard do Operador (gestão de pedidos)
  - Dashboard do Entregador (app mobile)
  - Painel Admin (gestão de usuários)
- **WebSocket Client:** Conexão para atualizações em tempo real

---

## 4. FLUXOS PRINCIPAIS

### 4.1 Fluxo de Pedido via WhatsApp

```
1. Cliente envia mensagem no WhatsApp
   ↓
2. WAHA recebe mensagem e envia webhook para /webhooks/waha
   ↓
3. Flow Engine processa mensagem:
   - Carrega contexto do Redis (estado atual da conversa)
   - Identifica estado atual (START, AWAITING_PRODUCT, etc.)
   - Chama handler específico do estado
   ↓
4. Handler processa mensagem:
   - Extrai informações (produto, quantidade, endereço)
   - Valida dados
   - Atualiza contexto
   - Gera resposta
   ↓
5. Flow Engine salva novo contexto no Redis
   ↓
6. Resposta é enviada via WAHA para WhatsApp
   ↓
7. Quando pedido completo:
   - Cria Order no PostgreSQL
   - Cria Payment no Asaas (se PIX/cartão)
   - Envia link de pagamento
   ↓
8. Quando pagamento confirmado (webhook Asaas):
   - Atualiza Order.status = "paid"
   - Notifica operadores via WebSocket
   ↓
9. Operador aprova pedido:
   - Atribui entregador
   - Order.status = "preparing"
   ↓
10. Entregador inicia entrega:
    - Order.status = "dispatched"
    - Cria Delivery
    ↓
11. Entregador finaliza entrega:
    - Order.status = "delivered"
    - Exporta para Firebird (se habilitado)
```

### 4.2 Fluxo de Autenticação e Autorização

```
1. Usuário faz login em /api/auth/login
   ↓
2. Sistema valida credenciais
   ↓
3. Gera JWT token com claims (role, user_id)
   ↓
4. Cliente armazena token
   ↓
5. Em cada requisição:
   - Cliente envia token no header Authorization
   - get_current_user() valida token
   - Verifica permissões baseadas em role (RBAC)
   ↓
6. Roles disponíveis:
   - admin: Acesso total
   - owner: Proprietário, visão executiva
   - operator: Operador, gestão de pedidos
   - driver: Entregador, apenas suas entregas
```

### 4.3 Fluxo de Sincronização Firebird

```
1. Sync Service roda periodicamente (cron)
   ↓
2. Sincronização de Produtos:
   - Lê produtos do Firebird
   - Compara com PostgreSQL
   - Atualiza/cria produtos
   ↓
3. Sincronização de Clientes:
   - Lê clientes do Firebird
   - Sincroniza com PostgreSQL
   ↓
4. Exportação de Pedidos:
   - Busca pedidos com status "delivered" e firebird_export_status != "exported"
   - Cria registro em TRADE (Firebird)
   - Cria itens em TRADEITEM
   - Atualiza Order.firebird_export_status = "exported"
```

### 4.4 Fluxo de WebSocket (Tempo Real)

```
1. Cliente conecta em /ws
   ↓
2. Autenticação via token JWT
   ↓
3. Cliente é adicionado ao WebSocketManager
   ↓
4. Quando evento ocorre (novo pedido, atualização, etc.):
   - Sistema chama manager.broadcast(evento)
   ↓
5. WebSocketManager:
   - Envia evento para todos os clientes conectados
   - Se escala horizontal: publica no Redis Pub/Sub
   - Redis Bridge em outras instâncias recebe e distribui
   ↓
6. Clientes recebem atualização em tempo real
```

---

## 5. MODELOS DE DADOS PRINCIPAIS

### 5.1 Order (Pedido)
- **Campos principais:**
  - `order_number`: Número sequencial para exibição
  - `status`: pending → paid → preparing → dispatched → delivered
  - `tipo_operacao`: troca/venda/retira
  - `total_amount`: Valor total
  - `payment_method`: Método de pagamento
  - `delivery_address`: Endereço (JSON)
  - `firebird_trade_id`: ID no Firebird (se exportado)
- **Relacionamentos:**
  - `customer`: Cliente que fez o pedido
  - `items`: Itens do pedido (OrderItem)
  - `payments`: Pagamentos associados
  - `delivery`: Entrega associada

### 5.2 Customer (Cliente)
- **Campos principais:**
  - `phone`: Telefone (chave única)
  - `name`: Nome
  - `cpf_cnpj`: CPF/CNPJ
  - `addresses`: Endereços (JSON array)
  - `asaas_customer_id`: ID no Asaas
- **Relacionamentos:**
  - `orders`: Pedidos do cliente

### 5.3 Product (Produto)
- **Campos principais:**
  - `code`: Código (P13, P20, P45)
  - `name`: Nome
  - `price_troca`: Preço com troca
  - `price_venda`: Preço sem troca
  - `active`: Ativo/inativo

### 5.4 Driver (Entregador)
- **Campos principais:**
  - `name`: Nome
  - `phone`: Telefone
  - `available`: Disponível/indisponível
  - `bairros`: Bairros atendidos (JSON array)

### 5.5 Delivery (Entrega)
- **Campos principais:**
  - `order_id`: Pedido associado
  - `driver_id`: Entregador
  - `status`: Em andamento/concluída
  - `started_at`: Início da entrega
  - `completed_at`: Conclusão

---

## 6. INTEGRAÇÕES EXTERNAS

### 6.1 WAHA (WhatsApp HTTP API)
- **Propósito:** Comunicação WhatsApp
- **Operações:**
  - Receber mensagens (webhook)
  - Enviar mensagens de texto
  - Enviar botões interativos
  - Enviar imagens
- **Configuração:** `WAHA_URL`, `WAHA_API_KEY`, `WAHA_SESSION_NAME`

### 6.2 Asaas (Gateway de Pagamento)
- **Propósito:** Processamento de pagamentos
- **Operações:**
  - Criar cliente
  - Criar cobrança (PIX, cartão, boleto)
  - Receber webhook de confirmação de pagamento
- **Configuração:** `ASAAS_API_KEY`, `ASAAS_API_URL`

### 6.3 Firebird (ERP Legado)
- **Propósito:** Sincronização e exportação fiscal
- **Operações:**
  - Leitura de produtos, clientes, estoque
  - Escrita de pedidos (TRADE/TRADEITEM)
- **Configuração:** `FIREBIRD_HOST`, `FIREBIRD_DATABASE`, `FIREBIRD_USER`, `FIREBIRD_PASSWORD`
- **Importante:** Somente leitura para sincronização, escrita apenas para exportação de pedidos

### 6.4 Ollama (IA Local)
- **Propósito:** Chatbot inteligente (opcional)
- **Operações:**
  - Processar mensagens com IA
  - Gerar respostas contextuais
- **Configuração:** `OLLAMA_URL`, `OLLAMA_MODEL`

---

## 7. SEGURANÇA E AUTENTICAÇÃO

### 7.1 Autenticação
- **Método:** JWT (JSON Web Tokens)
- **Fluxo:** Login → Token JWT → Token em cada requisição
- **Validação:** Middleware `get_current_user()` valida token e extrai usuário

### 7.2 Autorização (RBAC)
- **Roles:**
  - `admin`: Acesso total ao sistema
  - `owner`: Proprietário, dashboards executivos, relatórios
  - `operator`: Operador, gestão de pedidos, aprovações
  - `driver`: Entregador, apenas suas entregas, atualização de status
- **Implementação:** Decorators e verificações baseadas em role

### 7.3 Auditoria
- **Tabela:** `audit_logs`
- **Registra:** Ações importantes (criação de pedidos, alterações de status, etc.)
- **Campos:** `user_id`, `action`, `resource_type`, `resource_id`, `details`, `timestamp`

---

## 8. ESCALABILIDADE E PERFORMANCE

### 8.1 Escala Horizontal (WebSocket)
- **Problema:** WebSocket é stateful, não funciona bem com múltiplas instâncias
- **Solução:** Redis Pub/Sub Bridge
  - Cada instância publica eventos no Redis
  - Outras instâncias recebem e distribuem para seus clientes WebSocket
  - Permite múltiplas instâncias do backend

### 8.2 Otimizações
- **Event Batching:** Agrupa eventos para reduzir overhead
- **Message Store:** Armazena mensagens para replay (útil em reconexões)
- **Redis Cache:** Cache de conversas e estados
- **Índices no Banco:** Índices estratégicos em campos frequentemente consultados

### 8.3 Monitoramento
- **Prometheus:** Métricas customizadas (conexões WebSocket, latência, etc.)
- **Grafana:** Dashboards visuais
- **Health Checks:** `/health` endpoint para load balancers

---

## 9. ESTADOS E FLUXOS DE CONVERSA

### 9.1 Estados da Conversa (State Machine)

1. **START**: Estado inicial, apresenta menu
2. **AWAITING_PRODUCT**: Aguardando cliente escolher produto (P13, P20, P45)
3. **AWAITING_QUANTITY**: Aguardando quantidade
4. **CONFIRMING_ADDRESS**: Confirmando endereço existente
5. **AWAITING_ADDRESS**: Aguardando novo endereço
6. **AWAITING_PAYMENT**: Aguardando escolha de método de pagamento
7. **AWAITING_PIX**: Aguardando pagamento PIX
8. **CONFIRMING_ORDER**: Confirmando pedido antes de criar
9. **ORDER_CONFIRMED**: Pedido criado, aguardando pagamento
10. **TRACKING_ORDER**: Cliente rastreando pedido
11. **TALKING_TO_HUMAN**: Conversa com operador humano

### 9.2 Transições de Estado

```
START → AWAITING_PRODUCT (cliente escolheu fazer pedido)
AWAITING_PRODUCT → AWAITING_QUANTITY (produto selecionado)
AWAITING_QUANTITY → CONFIRMING_ADDRESS (quantidade informada)
CONFIRMING_ADDRESS → AWAITING_ADDRESS (endereço não encontrado)
CONFIRMING_ADDRESS → AWAITING_PAYMENT (endereço confirmado)
AWAITING_ADDRESS → AWAITING_PAYMENT (novo endereço informado)
AWAITING_PAYMENT → AWAITING_PIX (PIX escolhido)
AWAITING_PAYMENT → CONFIRMING_ORDER (outro método)
AWAITING_PIX → ORDER_CONFIRMED (pagamento confirmado)
CONFIRMING_ORDER → ORDER_CONFIRMED (pedido criado)
ORDER_CONFIRMED → TRACKING_ORDER (cliente quer rastrear)
```

---

## 10. COMANDOS E FUNCIONALIDADES ESPECIAIS

### 10.1 Comandos Globais (funcionam em qualquer estado)
- **`menu`**: Volta ao início
- **`pedir`**: Inicia fluxo de pedido
- **`rastrear`**: Rastreia pedido
- **`atendente`**: Fala com operador humano
- **`cancelar`**: Cancela pedido atual

### 10.2 Funcionalidades Especiais
- **Chatbot com IA:** Responde perguntas gerais quando não está em fluxo de pedido
- **Validação de Bairro:** Verifica se entrega no bairro informado
- **Cálculo Automático:** Calcula total baseado em produto, quantidade e tipo de operação
- **Link de Pagamento:** Gera link PIX/cartão automaticamente via Asaas
- **Notificações em Tempo Real:** Operadores recebem notificações via WebSocket

---

## 11. DEPLOY E INFRAESTRUTURA

### 11.1 Docker Compose
- **Serviços:**
  - `backend`: API principal (FastAPI)
  - `frontend`: Interface React
  - `postgres`: Banco de dados PostgreSQL
  - `redis`: Cache e pub/sub
  - `waha`: Servidor WAHA (WhatsApp)
  - `traefik`: Reverse proxy
  - `prometheus`: Métricas
  - `grafana`: Dashboards
  - `sync-service`: Sincronização Firebird
  - `inventory-service`: Gestão de estoque
  - `notification-service`: Notificações

### 11.2 Variáveis de Ambiente Importantes
- `SECRET_KEY`: Chave secreta para JWT
- `DATABASE_URL`: URL do PostgreSQL
- `REDIS_URL`: URL do Redis
- `WAHA_URL`, `WAHA_API_KEY`: Configuração WAHA
- `ASAAS_API_KEY`: Chave API Asaas
- `FIREBIRD_*`: Configuração Firebird (se habilitado)
- `OLLAMA_URL`: URL do Ollama (se habilitado)

---

## 12. PONTOS DE ATENÇÃO PARA DESENVOLVIMENTO

### 12.1 Arquitetura
- Backend é monolítico mas bem modularizado
- Microserviços são opcionais e podem ser desabilitados
- WebSocket requer Redis para escala horizontal

### 12.2 Banco de Dados
- PostgreSQL é fonte da verdade
- Firebird é somente leitura (exceto exportação de pedidos)
- Redis é cache/sessão, não é persistente

### 12.3 Integrações
- WAHA é obrigatório (sem ele não há WhatsApp)
- Asaas é opcional (pode usar outros gateways)
- Firebird é opcional (pode exportar para arquivos)
- Ollama é opcional (pode usar chatbot rule-based)

### 12.4 Estados e Contexto
- Contexto de conversa fica no Redis (TTL de 30 minutos)
- Se Redis cair, conversas em andamento são perdidas
- Estado da conversa é gerenciado pela máquina de estados

---

## 13. RESUMO EXECUTIVO

**O Gas Automation é um sistema completo de automação de pedidos de gás via WhatsApp que:**

1. **Recebe pedidos** através de conversas automatizadas no WhatsApp
2. **Processa pagamentos** via gateway Asaas (PIX, cartão, boleto)
3. **Gerencia entregas** com atribuição automática de entregadores
4. **Integra com ERP** exportando pedidos para sistema Firebird fiscal
5. **Fornece dashboards** em tempo real para diferentes perfis de usuário
6. **Escala horizontalmente** usando Redis para distribuir eventos WebSocket
7. **Monitora operações** com Prometheus e Grafana

**Tecnologias principais:** Python/FastAPI, React, PostgreSQL, Redis, Docker, WhatsApp (WAHA), Asaas, Firebird.

**Arquitetura:** Backend monolítico modular + microserviços opcionais + frontend React + infraestrutura containerizada.

---

**Fim do Relatório**
