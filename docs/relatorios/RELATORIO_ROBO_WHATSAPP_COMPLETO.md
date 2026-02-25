# Relatório Completo do Robô WhatsApp - Gas Automation

**Data:** 04/02/2026  
**Objetivo:** Documentação completa para facilitar mudanças nos textos e na lógica de resposta ao cliente, permitindo melhor coleta de dados para filtrar clientes, identificar cadastrados etc.  
**Uso:** Base para auxílio do Claude na reformulação do fluxo.

---

## 1. Visão Geral da Arquitetura

### 1.1 Fluxo de Dados (Visão Alto Nível)

```
WhatsApp → WAHA → Webhook (/webhooks/waha) → process_whatsapp_message() 
    → FlowEngine.process_message() → Handler por estado → send_responses() → WAHA → WhatsApp
```

### 1.2 Componentes Principais

| Componente | Arquivo | Responsabilidade |
|------------|---------|------------------|
| **Webhook WAHA** | `backend/app/api/webhooks.py` | Recebe mensagens do WhatsApp via POST, despacha para processamento em background |
| **Flow Engine** | `backend/app/core/flow_engine.py` | Orquestra o fluxo, carrega/salva contexto Redis, delega para handlers |
| **Handlers** | `backend/app/core/handlers.py` | Lógica de resposta por estado da conversa |
| **State Machine** | `backend/app/core/state_machine.py` | Estados e transições válidas |
| **WAHA Client** | `backend/app/integrations/waha.py` | Envia mensagens (texto, botões, imagem) para o WhatsApp |
| **Schemas Webhook** | `backend/app/schemas/webhook.py` | Modelo WAHAMessage (phone, text, button_id, location) |

---

## 2. Entrada de Mensagens (Webhook)

### 2.1 Endpoint e Configuração

- **URL:** `POST /webhooks/waha`
- **Variável de ambiente:** `WHATSAPP_HOOK_URL` (ex: `http://backend:8000/webhooks/waha`)
- **Segurança:** Header `X-WAHA-Signature` com HMAC-SHA256 (quando `WAHA_WEBHOOK_SECRET` configurado)

### 2.2 Eventos Tratados

| Evento | Ação |
|--------|------|
| `message` | Processa mensagem em background |
| `message.ack` | Apenas log |
| `session.status` | Apenas log |

### 2.3 Extração de Dados da Mensagem

O payload do WAHA é normalizado em `WAHAMessage`:

```python
# Dados extraídos (schemas/webhook.py)
message.phone        # chatId completo: "5541999999999@c.us" ou "7185547411514@lid"
message.text         # Texto da mensagem OU body de conversation
message.button_id    # ID do botão clicado (ex: "fazer_pedido", "P13")
message.location     # {latitude, longitude, address, name} se for localização
```

**Formatos de `phone`:**
- `5541999999999@c.us` – número direto
- `7185547411514@lid` – Linked ID (WhatsApp Business); o WAHA resolve para @c.us na hora de enviar

### 2.4 Fluxo em `process_whatsapp_message()` (webhooks.py)

1. **Localização:** Se `location` presente → `process_location_message()` e retorna
2. **Conteúdo:** `content = text or button_id or "menu"` (mensagem vazia vira "menu")
3. **WebSocket:** Emite `emit_new_message(phone, content, "incoming")` para painel operador
4. **EventLog:** Salva `event_type="message_received"` no PostgreSQL
5. **Flow Engine:** `flow_engine.process_message(phone, content, message_id)`
6. **Respostas:** `flow_engine.send_responses(phone, result.responses)`

---

## 3. Fluxo de Estados (State Machine)

### 3.1 Estados Definidos

| Estado | Descrição |
|--------|-----------|
| `START` | Início da conversa |
| `AWAITING_PRODUCT` | Aguardando escolha de produto |
| `AWAITING_QUANTITY` | Aguardando quantidade |
| `CONFIRMING_ADDRESS` | Confirmando endereço |
| `AWAITING_ADDRESS` | Aguardando novo endereço |
| `AWAITING_PAYMENT` | Aguardando método de pagamento |
| `AWAITING_PIX` | (Legado) Aguardando Pix |
| `CONFIRMING_ORDER` | Confirmando pedido (cartão) |
| `ORDER_CONFIRMED` | Pedido confirmado |
| `TRACKING_ORDER` | Rastreamento de pedido |
| `TALKING_TO_HUMAN` | Atendimento humano |
| `IDLE` | Inativo |

### 3.2 Contexto da Conversa (Redis)

Chave: `chat:{phone}`  
TTL: 1800 segundos (30 min) – `redis_conversation_ttl`

**Campos do `ConversationContext`:**

| Campo | Tipo | Uso |
|-------|------|-----|
| `phone` | str | Identificador |
| `state` | str | Estado atual |
| `customer_id` | str | UUID do Customer (PostgreSQL) |
| `customer_name` | str | Nome do cliente |
| `order_id` | str | ID do pedido em andamento |
| `selected_product` | str | Código (P13, P20, P45) |
| `selected_quantity` | int | Quantidade escolhida |
| `address` | dict | `{full_address, bairro, location?, formatted?}` |
| `address_confirmed` | bool | Endereço confirmado |
| `payment_method` | str | cash, credit_card, pix |
| `retry_count` | int | Tentativas de reentrada |
| `last_message_at` | datetime | Última interação |

---

## 4. Linkagem com Banco de Dados

### 4.1 PostgreSQL (Tabelas Principais)

| Tabela | Uso no Robô |
|--------|--------------|
| **customers** | Cliente por telefone; nome, endereço, firebird_id, cpf_cnpj |
| **products** | Catálogo (P13, P20, P45); preços e nomes |
| **orders** | Pedidos criados; status, total, endereço |
| **order_items** | Itens do pedido (produto, quantidade, preço) |
| **event_logs** | Log de mensagens recebidas/enviadas (`entity_type="chat"`) |

### 4.2 Fluxo de Cliente

**Função:** `get_or_create_customer(phone)` em `handlers.py`

1. Busca `Customer` no PostgreSQL por `phone`
2. Se não encontrar, busca no **Firebird** via `firebird_client.get_customer_by_phone(phone)`
3. Se encontrar no Firebird: cria Customer no PostgreSQL com nome, email, cpf_cnpj, endereço, firebird_id
4. Se não encontrar em nenhum: cria Customer só com `phone` (cliente vazio)

**Importante:** O cliente é criado na primeira interação (handle_start), logo quando entra no fluxo de pedido.

### 4.3 Identificação Atual de Cliente

- **Identificador:** `phone` (telefone WhatsApp, ex: 5541999999999)
- **Dados disponíveis no início:** 
  - Se veio do Firebird: nome, email, cpf_cnpj, endereço completo
  - Se novo: apenas phone
- **Nome:** Usado nas saudações; se vazio, usa "cliente"

### 4.4 Produtos

- Origem: tabela `products` (PostgreSQL), sincronizada do Firebird
- Códigos: P13, P20, P45 (constantes em `handlers.py` e `product.py`)
- Detecção na mensagem: `extract_product_code()` – busca códigos, pesos (13, 20, 45) ou opções numéricas (1, 2, 3)

### 4.5 Endereço

- **Bairros suportados** (`config.py`): Alto Boqueirão, Boqueirão, Ganchinho, Hauer, Sítio Cercado, Umbará, Xaxim
- Extração: procura substring do bairro no texto digitado
- Estrutura salva: `{full_address, bairro}` – atualiza `Customer.address` no banco

### 4.6 EventLog (Mensagens)

- `message_received`: `payload={"phone": phone, "message": content}`
- `message_sent`: `payload={"phone": phone, "message": response.text}`
- `location_received`: `payload={phone, latitude, longitude, address, name}`

---

## 5. Textos e Lógica de Resposta por Estado

### 5.1 Comandos Globais (em qualquer estado)

| Comando | Textos de Resposta |
|---------|--------------------|
| `menu`, `inicio`, `voltar`, `0` | Menu principal com botões Fazer Pedido, Meus Pedidos, Atendente |
| `cancelar` | Cancela pedido ou informa que não há pedido |
| `ajuda`, `help`, `?` | Lista comandos e produtos |
| `atendente`, `humano`, `pessoa`, `atendimento` | Transfere para atendente humano |

**Texto do Menu Principal:**
```
🏠 *Menu Principal*

Olá! Bem-vindo à *Distribuidora de Gás*! 🔥

Como posso ajudar?
[Fazer Pedido] [Meus Pedidos] [Atendente]
```

### 5.2 handle_start (Primeira Interação)

- Busca/cria cliente via `get_or_create_customer()`
- **Cliente novo:** "👋 *Olá! Bem-vindo à Distribuidora de Gás!* Sou o assistente virtual..."
- **Cliente retornando:** "👋 *Olá, {nome}!* Que bom ter você de volta!"
- Lista produtos do banco com preços e botões
- Transição: → AWAITING_PRODUCT

### 5.3 handle_awaiting_product

- Aceita: P13, P20, P45, "13", "20", "45", "1", "2", "3" ou clique em botão
- Se inválido (3 tentativas): mostra botões P13, P20, P45 com preços fixos
- Se válido: confirma produto, pede quantidade com botões 1, 2, 3 botijões
- Transição: → AWAITING_QUANTITY

### 5.4 handle_awaiting_quantity

- Aceita: números 1–10 ou botões qty_1, qty_2, qty_3
- Se cliente tem endereço: mostra resumo e pede confirmação
- Se não tem endereço: pede endereço completo (exemplo: "Rua das Flores, 123 - Boqueirão")
- Transição: → CONFIRMING_ADDRESS ou AWAITING_ADDRESS

### 5.5 handle_confirming_address

- "Sim", "correto", "confirmar" → vai para pagamento
- "Alterar", "não" → pede novo endereço
- Transição: → AWAITING_PAYMENT ou AWAITING_ADDRESS

### 5.6 handle_awaiting_address

- Valida: endereço mínimo 10 caracteres
- Extrai bairro da lista `supported_bairros`
- Salva em `Customer.address` e segue para pagamento
- Transição: → AWAITING_PAYMENT

### 5.7 handle_awaiting_payment

- **Pix:** mensagem de descontinuado; volta às opções
- **Dinheiro:** cria pedido, confirma, emite WebSocket
- **Cartão:** pede confirmação (handle_confirming_order)
- Botões: Dinheiro, Cartão (Pix descontinuado)
- Transição: → ORDER_CONFIRMED ou CONFIRMING_ORDER

### 5.8 handle_confirming_order (Cartão)

- "Confirmar" → cria pedido, confirma
- "Voltar" → volta para escolha de pagamento

### 5.9 handle_order_confirmed

- Se mensagem contém "status" ou "pedido" → chama handle_tracking_order
- Caso contrário → reset e handle_start (novo pedido)

### 5.10 handle_tracking_order

- Busca últimos 5 pedidos do cliente no PostgreSQL
- Mostra status (emoji + label) e total
- Labels: Aguardando pagamento, Pago, Em preparação, Saiu para entrega, Entregue, Cancelado

### 5.11 handle_talking_to_human

- Emite WebSocket com dados do cliente (id, name, phone, bairro)
- Mensagem: "👤 Você está em atendimento humano. Um de nossos atendentes responderá em breve. Digite *menu* para voltar."

---

## 6. Pontos de Atenção para Reformulação

### 6.1 Lacunas Atuais

1. **Botões do menu não tratados corretamente:**
   - "Meus Pedidos" (`ver_pedido`): ao clicar, cai em AWAITING_PRODUCT e pede produto de novo
   - "Atendente" (`falar_atendente`): não é reconhecido como comando global; o comando global aceito é só "atendente"
   - **Sugestão:** incluir `ver_pedido` e `falar_atendente` nos comandos globais ou no handler do menu

2. **Coleta de dados do cliente limitada:**
   - Nome só vem do Firebird; cliente novo fica sem nome
   - CPF/CNPJ não são pedidos no fluxo
   - E-mail não é pedido
   - **Sugestão:** adicionar passos para capturar nome, CPF/CNPJ (e e-mail se fizer sentido) para clientes novos

3. **Endereço pouco estruturado:**
   - Apenas `full_address` e `bairro`; não há campos rua, número, complemento, CEP
   - **Sugestão:** perguntas direcionadas ou validação mais rígida

4. **Sem identificação explícita “já cadastrado”:**
   - Diferença é só na saudação (novo vs. retorno)
   - **Sugestão:** mensagem explícita tipo “Você já é cliente cadastrado” ou “Vamos fazer seu cadastro rápido”

### 6.2 Arquivos para Alterar Textos e Lógica

| Arquivo | O que alterar |
|---------|---------------|
| `backend/app/core/flow_engine.py` | Comandos globais, textos do menu, cancelar, ajuda, atendente |
| `backend/app/core/handlers.py` | Todos os textos de resposta, estrutura de perguntas, validações |
| `backend/app/core/state_machine.py` | Novos estados, se necessário |
| `backend/app/config.py` | `supported_bairros`, `default_delivery_time_minutes` |
| `backend/app/api/webhooks.py` | Tratamento de tipos de mensagem, fallback "menu" |

### 6.3 Onde Incluir Novos Dados do Cliente

- **Modelo:** `backend/app/models/customer.py` – já tem name, email, cpf_cnpj, address
- **Handlers:** em `get_or_create_customer` ou em novos passos após criação
- **Contexto:** `ConversationContext` em `state_machine.py` – pode ganhar campos temporários (ex: `pending_name`, `pending_cpf`)

---

## 7. Integração WAHA (Envio)

### 7.1 Métodos de Envio

| Método | Uso |
|--------|-----|
| `send_text(phone, text)` | Texto simples |
| `send_buttons(phone, text, buttons, footer)` | Até 3 botões |
| `send_image(phone, image_url, image_base64, caption)` | Imagem com legenda |
| `send_list(...)` | Lista de opções (não usado nos handlers atuais) |
| `mark_as_read(phone, message_id)` | Marca como lida |

### 7.2 Formato de Botões

```python
buttons = [
    {"id": "fazer_pedido", "text": "🛒 Fazer Pedido"},  # max 20 chars
    {"id": "ver_pedido", "text": "📦 Meus Pedidos"},
    {"id": "falar_atendente", "text": "👤 Atendente"},
]
```

### 7.3 Configuração WAHA

- `WAHA_URL` – base URL (ex: http://localhost:3000)
- `WAHA_SESSION_NAME` – nome da sessão (ex: default)
- `WAHA_API_KEY` – autenticação

---

## 8. Diagrama de Fluxo Simplificado

```
[Cliente envia mensagem]
         ↓
[Webhook recebe] → [EventLog] → [WebSocket operador]
         ↓
[FlowEngine: get_context(phone) do Redis]
         ↓
[Comandos globais?] → Sim → Resposta direta
         ↓ Não
[Handler do estado atual]
         ↓
[get_or_create_customer] (se START ou primeiro uso)
         ↓
[Lógica do estado: validar, atualizar contexto, montar resposta]
         ↓
[save_context no Redis]
         ↓
[send_responses → WAHA → WhatsApp]
         ↓
[EventLog message_sent]
```

---

## 9. Resumo para Claude

Para alterar textos e lógica do robô com foco em **coleta de dados** e **filtro de clientes**:

1. **Identificação de cadastrado:** usar `get_or_create_customer` e o retorno `(customer, is_new)` para mensagens distintas.
2. **Captura de dados:** novos estados ou passos para nome, CPF/CNPJ, e-mail antes ou durante o pedido.
3. **Textos:** concentrados em `flow_engine.py` (comandos globais) e `handlers.py` (respostas por estado).
4. **Comandos do menu:** incluir `ver_pedido` e `falar_atendente` no tratamento global ou no handler adequado.
5. **Banco:** `Customer` já suporta name, email, cpf_cnpj, address; é só preencher no fluxo.
6. **Contexto:** Redis guarda o estado da conversa; PostgreSQL guarda clientes, pedidos e logs de mensagens.

---

*Relatório gerado para suporte à reformulação do robô WhatsApp em 04/02/2026.*
