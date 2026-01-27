# 📋 PLANO DE ADAPTAÇÃO: eric_files → Servidor Ubuntu 192.168.10.156

## 📊 ANÁLISE ATUAL

### Estrutura eric_files (Localhost/Antigo)
```
eric_files/
├── auth.py                      → Autenticação (síncrono)
├── base_models_eric.py          → Modelos básicos (User, Conversation, Message)
├── customer_service_eric.py     → Serviço de clientes
├── delivery_models_eric.py      → Modelos de entrega
├── delivery_service_eric.py     → Serviço de entregas
├── driver_service_eric.py       → Serviço de entregadores
├── init_eric.py                 → Inicialização
├── main_e.py                    → Versão experimental
├── main_eric.py                 → Versão principal (2600+ linhas)
├── order_service_eric.py        → Serviço de pedidos
└── product_service_eric.py      → Serviço de produtos
```

### Estrutura app (Novo/Moderno)
```
app/
├── auth.py                      → Autenticação (async)
├── config.py                    → Settings
├── database.py                  → Conexões
├── main.py                      → FastAPI app
├── metrics.py                   → Prometheus
├── models/                      → Modelos
│   ├── auth_models.py
│   ├── base.py
│   ├── customer.py
│   ├── delivery.py
│   ├── driver.py
│   ├── order.py
│   ├── payment.py
│   └── product.py
├── api/                         → Routers
├── services/                    → Serviços
└── utils/                       → Utilitários
```

---

## 🔍 COMPARAÇÃO DETALHADA

### 1️⃣ AUTH (eric_files/auth.py vs app/auth.py)

| Aspecto | eric_files | app | Ação |
|---------|-----------|-----|------|
| **Async** | ❌ Síncrono | ✅ Async | Modernizar |
| **Session** | Manual | Dependency | Manter app/ |
| **Password Hash** | bcrypt | argon2 | Manter app/ (melhor) |
| **Token Format** | `{"sub": email}` | `{"sub": username}` | Harmonizar |
| **Expired Check** | Sim | Sim | Compatível |

**Ação:** ✅ Usar app/auth.py (melhor implementado)

---

### 2️⃣ BASE MODELS (eric_files/base_models_eric.py)

#### User (eric_files)
```python
class User(SQLModel, table=True):
    id, email, name, password_hash, role, is_active
    created_at, last_login, created_by
```

#### User (app/auth_models.py)
```python
class User(SQLModel, table=True):
    id, username, email, full_name, hashed_password, role, is_active
    created_at, updated_at
```

**Diferenças:**
- eric_files: `email` único
- app: `username` único + email
- eric_files: `name` simples
- app: `full_name`
- eric_files: `password_hash`
- app: `hashed_password`
- eric_files: `created_by` (foreign key)
- app: sem created_by

**Ação:** ✅ Manter app/ (mais completo) + CRIAR MIGRATION

---

### 3️⃣ CONVERSATION & MESSAGE (eric_files/base_models_eric.py)

#### eric_files
```python
class Conversation(SQLModel, table=True):
    id, customer_number, name, assigned_to (FK)
    created_by (FK), created_at, status

class Message(SQLModel, table=True):
    id, conversation_id (FK), sender, message_type
    content, bot_service, n8n_workflow_id, n8n_execution_id
    n8n_processed, timestamp
```

⚠️ **IMPORTANTE - N8N SERÁ REMOVIDO:**
- `n8n_workflow_id` → ❌ REMOVER
- `n8n_execution_id` → ❌ REMOVER
- `n8n_processed` → ❌ REMOVER

Estas campos serão **descartados** na migração, pois n8n não será usado no servidor.

#### app
- Está em `app/models/` mas precisa verificar estrutura
- Provavelmente similar

**Ação:** ✅ Verificar compatibilidade + CRIAR MIGRATION se necessário

---

### 4️⃣ DELIVERY MODELS (eric_files/delivery_models_eric.py)

#### eric_files tem:
- Customer (telefone, endereço, localização)
- Order (pedido, itens, status)
- OrderItem (item do pedido)
- Delivery (entrega)
- DeliveryHistory (histórico)
- Driver (motorista)
- DriverStatus, OrderStatus (enums)
- PaymentMethod, PaymentStatus (enums)

#### app deve ter similar em:
- `app/models/customer.py`
- `app/models/order.py`
- `app/models/delivery.py`
- `app/models/driver.py`
- `app/models/payment.py`

**Ação:** ✅ Verificar alinhamento + Consolidar enums

---

### 5️⃣ SERVICES (5 arquivos de serviço)

#### eric_files Services (Síncrono)
```python
class CustomerService:
    def __init__(self, session: Session):  # Síncrono
        self.session = session
    
    def get_by_phone(self, telefone: str):
        return self.session.exec(select(...)).first()

class OrderService:
    def get_by_id(self, order_id: int):
        return self.session.get(Order, order_id)
```

#### app Services (Async)
```python
class CustomerService:
    def __init__(self, session: AsyncSession):  # Async
        self.session = session
    
    async def get_by_phone(self, telefone: str):
        result = await self.session.execute(select(...))
        return result.scalar_one_or_none()
```

**Diferenças:**
- eric_files: `Session` (sync)
- app: `AsyncSession` (async)
- eric_files: `.first()` / `.get()`
- app: `.scalar_one_or_none()` / `.scalar_one_or_none()`
- eric_files: Métodos síncronos
- app: Métodos async

**Ação:** ✅ Manter app/ (melhor) + Portar lógica de negócio do eric_files se necessário

---

## 🎯 PLANO DE ADAPTAÇÃO (SEM IMPLEMENTAR)

### FASE 1: ANÁLISE & CONSOLIDAÇÃO (1-2 dias)

#### 1.1 Auditoria Completa
```
[ ] Comparar TODOS os modelos (eric_files vs app)
    - [ ] User
    - [ ] Conversation
    - [ ] Message
    - [ ] Customer
    - [ ] Order
    - [ ] OrderItem
    - [ ] Delivery
    - [ ] Driver
    - [ ] Product
    - [ ] Payment
    - [ ] Enums (OrderStatus, PaymentStatus, etc)

[ ] Comparar TODOS os serviços (eric_files vs app)
    - [ ] CustomerService
    - [ ] OrderService
    - [ ] DeliveryService
    - [ ] DriverService
    - [ ] ProductService

[ ] Documentar diferenças e incompatibilidades
[ ] Identificar lógica de negócio única no eric_files
[ ] Identificar duplicações no app
```

#### 1.2 Criar Matriz de Compatibilidade
```
Feature                 | eric_files | app | Status
Authentication          | ✅         | ✅  | Compatível
User Management         | ✅         | ✅  | Próximo passo
Conversation Mgmt       | ✅         | ✅  | Verificar
Order Management        | ✅         | ✅  | Próximo passo
Delivery Management     | ✅         | ✅  | Próximo passo
Driver Management       | ✅         | ✅  | Próximo passo
Product Catalog         | ✅         | ✅  | Próximo passo
```

---

### FASE 2: SINCRONIZAÇÃO DE MODELOS (2-3 dias)

#### 2.1 User Model
```
❌ Problema atual: eric_files usa `email` único, app usa `username` único
   
Solução:
  Option A: Manter ambos únicos
    ✅ Pro: Melhor para autenticação
    ❌ Con: Mais validação necessária
    
  Option B: Usar apenas email
    ✅ Pro: Mais simples
    ❌ Con: Quebra autenticação atual

RECOMENDAÇÃO: Option A (manter ambos)
  - Atualizar app/models/auth_models.py para aceitar AMBOS
  - Criar Migration para adicionar username se precisar
  - Atualizar app/api/auth.py para aceitar email E username no login
```

#### 2.2 Conversation & Message
```
❌ Problema: eric_files tem N8N fields que app pode não ter
❌ DECISÃO: N8N SERÁ REMOVIDO

Solução:
  ✅ NÃO copiar campos n8n_workflow_id, n8n_execution_id, n8n_processed
  ✅ Se app/models já tem esses campos: Remover em migration
  ✅ Revisar services que usam esses campos
     - OrderBotService (revisar)
     - EnhancedChatbotService (revisar)
  ✅ Remover lógica de processamento n8n
  ✅ Usar apenas: bot_service (claude, ollama, rasa, fallback)
  
Ver seção: "🗑️ REMOÇÃO DE N8N" acima
```

#### 2.3 Delivery Models
```
✅ Provavelmente compatível
Ações:
  - Verificar enums (OrderStatus, PaymentStatus)
  - Garantir campos de localização (latitude/longitude)
  - Verificar histórico de entregas
```

---

### FASE 3: SINCRONIZAÇÃO DE SERVIÇOS (2-3 dias)

#### 3.1 Converter Services para Async

```
Cada service (CustomerService, OrderService, etc):
  
eric_files (antes):
  def __init__(self, session: Session):
      self.session = session
  
  def get_by_id(self, id: int):
      return self.session.get(Model, id)

app (depois):
  def __init__(self, session: AsyncSession):
      self.session = session
  
  async def get_by_id(self, id: int):
      return await self.session.get(Model, id)  # Ou scalar_one_or_none

Passos:
  1. Copiar lógica de negócio do eric_files
  2. Converter Session → AsyncSession
  3. Converter métodos síncronos → async
  4. Converter .first() → .scalar_one_or_none()
  5. Adicionar await em session.execute()
  6. Testar em localhost primeiro
```

#### 3.2 Portar Lógica de Negócio
```
CustomerService:
  - Lógica de limpeza de telefone
  - Buscar por telefone
  - Criar cliente com validações
  
OrderService:
  - Criar pedido com itens
  - Validar produtos
  - Calcular totais
  - Atualizar status
  
DeliveryService:
  - Atribuir driver
  - Gerenciar histórico
  - Calcular tempo estimado
  
DriverService:
  - Gerenciar disponibilidade
  - Atribuições ativas
  
ProductService:
  - Estoque
  - Preços (venda vs troca)
  - Produtos padrão (P13, P20, P45)
```

---

### FASE 4: MIGRAÇÃO DE DADOS (1-2 dias)

#### 4.1 Script de Migração
```sql
-- Se houver dados no localhost que precisam ir para o servidor:

1. Criar script de export (postgresql)
   - Tabelas: users, conversations, messages, customers, orders, drivers, products
   
2. Criar script de import
   - Considerar relacionamentos (FKs)
   - Considerar enums
   - Considerar timestamps

3. Validar integridade
   - Contar registros
   - Verificar FKs
   - Testar endpoints

Comando de backup:
  pg_dump -h localhost -U user -d database > backup.sql

Comando de restore:
  psql -h 192.168.10.156 -U user -d database < backup.sql
```

---

### FASE 5: TESTES & VALIDAÇÃO (1-2 dias)

#### 5.1 Testes Unitários
```
[ ] CustomerService
    [ ] get_by_phone (com/sem telefone)
    [ ] get_by_id
    [ ] create
    [ ] update

[ ] OrderService
    [ ] create_order
    [ ] list_pending
    [ ] update_status
    [ ] calculate_total

[ ] DeliveryService
    [ ] assign_driver
    [ ] start_delivery
    [ ] complete_delivery

[ ] DriverService
    [ ] list_available
    [ ] update_status

[ ] ProductService
    [ ] list_available
    [ ] update_stock
    [ ] create_default_products
```

#### 5.2 Testes de Integração
```
[ ] API endpoints protegidos
[ ] WebSocket funcionando
[ ] Banco de dados conectando
[ ] Redis cache funcionando
[ ] Mensagens sendo processadas
```

#### 5.3 Testes de Performance
```
[ ] Query performance (com índices)
[ ] Memory usage
[ ] Connection pooling
[ ] Rate limiting
```

---

### FASE 6: DEPLOYMENT (1 dia)

#### 6.1 Build & Deploy
```
[ ] Build Docker image
[ ] Push para registry (se houver)
[ ] Deploy no servidor
[ ] Verificar health checks
[ ] Monitorar logs
[ ] Testar acesso externo
```

#### 6.2 Configuração Servidor
```
[ ] .env com valores corretos (JWT_SECRET, DB_URL, etc)
[ ] Variáveis de ambiente
[ ] Certificados SSL (se usar HTTPS)
[ ] Firewall rules
[ ] Backups automáticos
```

---

## 📋 CHECKLIST DE ARQUIVOS

### Arquivos Eric_files
```
[ ] auth.py                     → DESCARTAR (usar app/auth.py)
[ ] base_models_eric.py         → EXTRAIR SCHEMA → Consolidar em app/models
[ ] customer_service_eric.py    → PORTAR LÓGICA → app/services/customer_service.py
[ ] delivery_models_eric.py     → EXTRAIR SCHEMA → Consolidar em app/models/delivery.py
[ ] delivery_service_eric.py    → PORTAR LÓGICA → app/services/delivery_service.py
[ ] driver_service_eric.py      → PORTAR LÓGICA → app/services/driver_service.py
[ ] init_eric.py                → DESCARTAR (usar app/main.py)
[ ] main_e.py                   → DESCARTAR (usar app/main.py)
[ ] main_eric.py                → DESCARTAR (usar app/main.py)
[ ] order_service_eric.py       → PORTAR LÓGICA → app/services/order_service.py
[ ] product_service_eric.py     → PORTAR LÓGICA → app/services/product_service.py
```

---

## 🎯 ESTRUTURA FINAL (ALVO)

```
backend/
├── app/
│   ├── main.py                  ← Consolidado
│   ├── auth.py                  ← Consolidado
│   ├── config.py                ← Consolidado
│   ├── database.py              ← Consolidado
│   │
│   ├── models/
│   │   ├── auth_models.py       ← User atualizado
│   │   ├── base.py              ← Base classes
│   │   ├── customer.py          ← Consolidado
│   │   ├── delivery.py          ← Consolidado (com enums)
│   │   ├── driver.py            ← Consolidado
│   │   ├── order.py             ← Consolidado
│   │   ├── payment.py           ← Consolidado
│   │   ├── product.py           ← Consolidado
│   │   ├── conversation.py      ← Novo (se necessário)
│   │   └── message.py           ← Novo (se necessário)
│   │
│   ├── services/
│   │   ├── customer_service.py  ← Async + lógica do eric_files
│   │   ├── delivery_service.py  ← Async + lógica do eric_files
│   │   ├── driver_service.py    ← Async + lógica do eric_files
│   │   ├── order_service.py     ← Async + lógica do eric_files
│   │   └── product_service.py   ← Async + lógica do eric_files
│   │
│   ├── api/
│   │   ├── auth.py              ← Consolidado
│   │   ├── orders.py            ← Consolidado
│   │   ├── customers.py         ← Consolidado
│   │   ├── drivers.py           ← Consolidado
│   │   ├── deliveries.py        ← Consolidado
│   │   ├── products.py          ← Consolidado
│   │   ├── chats.py             ← Consolidado
│   │   ├── websocket.py         ← Consolidado
│   │   └── webhooks.py          ← Consolidado
│   │
│   └── utils/
│       ├── validators.py        ← Novas (ex: validar telefone)
│       └── helpers.py           ← Novas
│
├── alembic/                     ← Migrations
│   ├── versions/
│   │   ├── 001_initial.py       ← Initial schema
│   │   ├── 002_user_updates.py  ← Adicionar username
│   │   ├── 003_models_fixes.py  ← Corrigir incompatibilidades
│   │   └── ...
│   └── env.py
│
├── eric_files/                  ← MANTER (referência histórica)
│   └── *.py                     ← Para consulta/auditoria
│
└── tests/
    ├── test_customer_service.py
    ├── test_order_service.py
    └── ...
```

---

## 🗑️ REMOÇÃO DE N8N

### O que é N8N nos eric_files?

N8N é uma plataforma de automação de workflows. No eric_files estava integrada para:
- Processamento automático de mensagens
- Orquestração de fluxos de conversas
- Automação de tarefas

### Por que remover?

```
❌ Razões para remover N8N:
1. Complexidade desnecessária
2. Não será utilizado no servidor Ubuntu
3. Adiciona dependências externas
4. Dificulta manutenção
5. Não há requisitos de orquestração tão complexa
```

### Campos N8N a remover

| Modelo | Campo | Ação |
|--------|-------|------|
| **Message** | `n8n_workflow_id` | ❌ DELETE |
| **Message** | `n8n_execution_id` | ❌ DELETE |
| **Message** | `n8n_processed` | ❌ DELETE |

### Processo de Remoção

#### FASE 2.2: Na sincronização de modelos

```
Etapas:
  1. NÃO copiar campos n8n para app/models/message.py
  2. Se já existem: Remover em Migration
  3. Revisar services que usam esses campos
     - OrderBotService
     - EnhancedChatbotService
  4. Remover lógica de processamento n8n
  5. Atualizar routers (chats, chatbot)
```

#### Migration SQL a criar

```sql
-- Arquivo: alembic/versions/002_remove_n8n_fields.py

def upgrade():
    op.drop_column('message', 'n8n_workflow_id')
    op.drop_column('message', 'n8n_execution_id')
    op.drop_column('message', 'n8n_processed')

def downgrade():
    op.add_column('message', sa.Column('n8n_workflow_id', sa.String()))
    op.add_column('message', sa.Column('n8n_execution_id', sa.String()))
    op.add_column('message', sa.Column('n8n_processed', sa.Boolean(), default=False))
```

### Arquivos que usam N8N (para revisar)

```
[ ] backend/eric_files/base_models_eric.py
    - Message class com campos n8n
    
[ ] backend/app/services/order_bot_service.py (se existir)
    - Pode estar invocando n8n workflows
    
[ ] backend/app/services/enhanced_chatbot_service.py (se existir)
    - Pode estar processando com n8n
    
[ ] backend/app/api/chatbot.py
    - Endpoints que usam n8n
    
[ ] backend/app/api/chats.py
    - Endpoints de chat que usam n8n
```

### Alternativas ao N8N (para futuro)

Se precisar de automação no futuro, considerar:
- ✅ Celery + Redis (tarefas assíncronas simples)
- ✅ APScheduler (agendamento)
- ✅ Workers em separado (processamento paralelo)
- ⚠️ Apache Airflow (se workflows forem complexos)

### Checklist de Remoção

```
[ ] FASE 2: Na sincronização de modelos
    [ ] NÃO incluir campos n8n em app/models/message.py
    [ ] Documentar que foram removidos
    
[ ] FASE 3: Na sincronização de services
    [ ] Revisar OrderBotService
    [ ] Revisar EnhancedChatbotService
    [ ] Remover invocações a n8n
    [ ] Remover lógica de processamento n8n
    
[ ] FASE 4: Na migração de dados
    [ ] Ignorar campos n8n no script de migração
    [ ] NÃO restaurar esses dados
    [ ] Validar que não foi copiado
    
[ ] FASE 5: Nos testes
    [ ] Testar que Message funciona SEM n8n fields
    [ ] Testar que chatbot funciona sem n8n
    [ ] Testar que bot_service apenas com: claude, ollama, rasa
```

---

## ⚠️ RISCOS & MITIGAÇÕES

### Risco 1: Incompatibilidade de Modelos
```
❌ Problema: Campo X em eric_files não existe em app
✅ Solução:
   - Adicionar campo como Optional
   - Criar migration
   - Testar com dados antigos

⚠️ ESPECIAL - N8N:
   - Se encontrar campos n8n: REMOVER (não adicionar)
   - Se houver dados n8n antigos: IGNORAR na migração
```

### Risco 2: Lógica de Negócio Perdida
```
❌ Problema: Lógica específica no eric_files não foi portada
✅ Solução:
   - Auditar TODOS os serviços
   - Criar testes para validar comportamento
   - Comparação linha-por-linha se necessário

⚠️ ESPECIAL - N8N:
   - Se houver processamento via n8n: SUBSTITUIR por alternativa
   - Exemplo: Tarefas simples → Celery + Redis
   - Exemplo: Agendamentos → APScheduler
```

### Risco 3: Performance em Produção
```
❌ Problema: Queries lentas no servidor
✅ Solução:
   - Adicionar índices no banco
   - Implementar cache (Redis)
   - Load test antes de deploy
   - Monitorar com Prometheus
```

### Risco 4: Dados Perdidos
```
❌ Problema: Migração de dados incompleta
✅ Solução:
   - Fazer backup primeiro
   - Validar integridade
   - Testar restore procedure
   - Manter dados antigos por 30 dias
```

---

## 📊 ESTIMATIVA DE ESFORÇO

| Fase | Atividade | Dias | Dependências |
|------|-----------|------|-------------|
| 1 | Análise & Consolidação | 2 | - |
| 2 | Sincronização de Modelos | 3 | Fase 1 |
| 3 | Sincronização de Serviços | 3 | Fase 2 |
| 4 | Migração de Dados | 2 | Fase 3 |
| 5 | Testes & Validação | 2 | Fase 4 |
| 6 | Deployment | 1 | Fase 5 |
| **TOTAL** | | **13 dias** | |

---

## 🎯 RECOMENDAÇÕES FINAIS

### FAZER ✅
1. Manter `app/` como base (está bem estruturado)
2. Extrair lógica de negócio única do `eric_files`
3. Converter services para async
4. Criar migrations para mudanças de schema
5. Implementar testes antes de deploy
6. Usar Docker para isolamento

### NÃO FAZER ❌
1. Não copiar/colar código todo do eric_files
2. Não descartar eric_files (manter para referência)
3. Não fazer deploy sem testar primeiro
4. Não ignorar incompatibilidades de modelos
5. Não deixar localhost hardcoded no código

### PRIORIDADES 🔴
1. **CRÍTICO:** Sincronizar modelos (User, Order, Delivery)
2. **CRÍTICO:** Portar services com lógica de negócio
3. **ALTO:** Testar localmente antes de deploy
4. **ALTO:** Backup de dados
5. **MÉDIO:** Otimizações de performance

---

## 📞 PRÓXIMAS AÇÕES

Quando decidir implementar:

1. Chamar: `FASE 1: Auditoria Completa`
   - Comparar modelos
   - Documentar diferenças
   - Criar matriz

2. Chamar: `FASE 2: Sincronização de Modelos`
   - Atualizar User model
   - Adicionar campos faltantes
   - Criar migrations

3. E assim por diante...

**Cada fase pode ser dividida em tarefas menores conforme necessário.**
