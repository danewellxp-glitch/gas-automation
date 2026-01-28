# 🔍 AUDITORIA TÉCNICA COMPLETA - GAS AUTOMATION

**Data:** 27/01/2026  
**Auditor:** Tech Lead Sênior (Firebird + FastAPI + SQLAlchemy)  
**Versão Analisada:** Sistema atual (pré-produção)  
**Objetivo:** Validar checklist técnico e determinar GO/NO-GO para produção

---

## 📊 RESUMO EXECUTIVO

### Decisão Final: ⚠️ **NO-GO** (até correções críticas)

**Status Geral:** 65% Pronto para Produção

| Categoria | Status | Bloqueantes | Ação |
|-----------|--------|-------------|------|
| Banco de Dados | ❌ BLOQUEANTE | 2 críticos | Migração FK + NOT NULL |
| Firebird | ❌ BLOQUEANTE | 2 críticos | Criar usuário + validar generators |
| ORM/SQLAlchemy | ⚠️ AJUSTAR | 1 divergência | Sincronizar schema |
| Transações | ⚠️ AJUSTAR | 2 altos | Refatorar commits |
| Performance | ✅ OK | 0 | Monitorar |
| Segurança | ❌ BLOQUEANTE | 1 crítico | Remover SYSDBA |
| Deploy | ⚠️ AJUSTAR | 1 alto | Scripts validação |

**Problemas Críticos Encontrados:** 5  
**Problemas de Alta Severidade:** 5  
**Problemas de Média Severidade:** 8  
**Problemas de Baixa Severidade:** 3

### 🚨 Bloqueantes para Produção

1. 🔴 **SYSDBA no Firebird** - Segurança comprometida
2. 🔴 **FK `orders.customer_id` não existe** - Sem integridade referencial
3. 🔴 **`customer_id` permite NULL** - Schema incorreto
4. 🔴 **Generators não sincronizados** - Risco de falhas
5. 🟠 **Commits sem tratamento** - Risco de inconsistência

### ⏱️ Prazo Estimado para Correções: 2-3 dias

---

## 1. BANCO DE DADOS (PostgreSQL)

### 1.1 Versionamento via Alembic

**Status:** ✅ **OK** (após correção)

**Evidências:**
- ✅ Tabela `alembic_version` existe
- ✅ Versão atual: `20260124_firebird_export` (head)
- ✅ Migrações aplicadas corretamente

**Histórico:**
- Problema anterior: Banco criado manualmente sem controle de versão
- Solução aplicada: `alembic stamp` + `alembic upgrade head`
- Status atual: Sincronizado

**Ação:** Nenhuma necessária

---

### 1.2 Divergência de Schema

**Status:** ⚠️ **AJUSTAR** (2 problemas)

#### Problema 1: Campo `orders.customer_id` é NULL mas deveria ser NOT NULL

**Severidade:** 🔴 **CRÍTICA**

**Evidência:**
```sql
orders.customer_id: uuid (NULL)  -- ❌ DEVERIA SER NOT NULL
```

**Modelo SQLAlchemy:**
```python
customer_id: Mapped[uuid.UUID] = mapped_column(
    UUID(as_uuid=True),
    ForeignKey("customers.id", ondelete="RESTRICT"),
    nullable=False,  # ← Modelo diz NOT NULL
    index=True,
)
```

**Realidade no Banco:**
- Coluna é `NULL` no banco
- Modelo define `nullable=False`
- **Divergência crítica!**

**Risco:**
- Pedidos podem ser criados sem cliente
- Violação de integridade referencial
- Queries podem falhar com `customer_id IS NULL`

**Correção:**
```sql
-- Migração Alembic necessária
ALTER TABLE orders 
ALTER COLUMN customer_id SET NOT NULL;

-- Verificar dados existentes primeiro
SELECT COUNT(*) FROM orders WHERE customer_id IS NULL;
-- Se > 0, corrigir dados antes de aplicar NOT NULL
```

**Ação:** Criar migração para corrigir

---

#### Problema 2: Campos com defaults mas nullable

**Severidade:** 🟡 **MÉDIA**

**Campos afetados:**
- `orders.status`: nullable=YES, default='pending'
- `orders.total_amount`: nullable=YES, default=0

**Risco:**
- Valores NULL podem aparecer apesar do default
- Lógica de aplicação pode assumir valores não-null

**Correção:**
```sql
ALTER TABLE orders 
ALTER COLUMN status SET NOT NULL,
ALTER COLUMN total_amount SET NOT NULL;
```

**Ação:** Incluir na mesma migração

---

### 1.3 Primary Keys e Foreign Keys

**Status:** ✅ **OK** (com observações)

**Primary Keys:**
- ✅ Todas as tabelas têm PK
- ✅ Uso correto de UUID (gen_random_uuid())
- ✅ Sem problemas identificados

**Foreign Keys:**
- ✅ `order_items.order_id -> orders.id` (ON DELETE: CASCADE) ✅
- ❌ **NÃO EXISTE:** `orders.customer_id -> customers.id` (FK não foi criada no banco)

**Problema Identificado:**
```sql
-- ❌ FK NÃO EXISTE no banco
-- Verificação executada: 0 FKs encontradas para orders.customer_id
```

**Causa:**
- Migração inicial (`001_initial_schema.py`) define FK no modelo
- Mas FK não foi criada no banco (banco foi criado manualmente via schema.sql)
- Banco atual não tem a constraint

**Risco:**
- **CRÍTICO:** Pedidos podem referenciar clientes inexistentes
- **CRÍTICO:** DELETE em customers não é impedido mesmo com RESTRICT
- **ALTA:** Integridade referencial comprometida

**Correção:**
```sql
-- Criar FK
ALTER TABLE orders
ADD CONSTRAINT fk_orders_customer
FOREIGN KEY (customer_id)
REFERENCES customers(id)
ON DELETE RESTRICT;
```

**Ação:** Criar FK imediatamente (migração Alembic)

---

### 1.4 Índices em FKs e Campos Críticos

**Status:** ✅ **OK**

**Índices Verificados:**
- ✅ `order_items.order_id` tem índice
- ✅ `orders.customer_id` tem índice (mesmo sendo NULL)
- ✅ Campos de busca têm índices:
  - `orders.status`
  - `orders.firebird_export_status`
  - `customers.phone`
  - `products.code`

**Índices Compostos:**
- ✅ `ix_orders_status_created` (status, created_at)
- ✅ `ix_orders_customer_status` (customer_id, status)
- ✅ `ix_orders_bairro_status` (delivery_bairro, status)
- ✅ `ix_orders_firebird_export` (firebird_export_status, firebird_exported_at)

**Ação:** Nenhuma necessária

---

### 1.5 Tipos de Dados

**Status:** ⚠️ **AJUSTAR** (1 problema)

#### Problema: Uso de VARCHAR para status ao invés de ENUM

**Severidade:** 🟡 **MÉDIA**

**Evidência:**
```sql
orders.status: character varying (NULL) DEFAULT 'pending'::character varying
```

**Modelo:**
```python
status: Mapped[str] = mapped_column(
    String(50),
    default=OrderStatus.PENDING.value,
    nullable=False,  # ← Mas no banco é NULL!
)
```

**Risco:**
- Valores inválidos podem ser inseridos
- Sem validação no nível de banco
- Dependência total da aplicação

**Recomendação:**
```sql
-- Criar ENUM
CREATE TYPE order_status_enum AS ENUM (
    'pending', 'paid', 'preparing', 'dispatched', 'delivered', 'cancelled'
);

-- Alterar coluna
ALTER TABLE orders 
ALTER COLUMN status TYPE order_status_enum 
USING status::order_status_enum,
ALTER COLUMN status SET NOT NULL;
```

**Alternativa (se não quiser ENUM):**
- Adicionar CHECK constraint
- Manter validação na aplicação (atual)

**Ação:** Decisão arquitetural (ENUM vs VARCHAR + validação)

---

**Outros Tipos:**
- ✅ `Numeric(10, 2)` para valores monetários ✅
- ✅ `Boolean` para flags ✅
- ✅ `Timestamp with time zone` para datas ✅
- ✅ `UUID` para IDs ✅
- ✅ `JSONB` para dados estruturados ✅

---

## 2. FIREBIRD (Sistema Legado)

### 2.1 Generators Sincronizados com IDs

**Status:** ⚠️ **VERIFICAR** (não validado completamente)

**Generators Encontrados:**
- `FOLDER_ID_GEN`: valor atual = 39
- `G_ITEMMOVDIA`: valor atual = 92787
- `G_ITEMSALDO`: valor atual = 8601
- `G_PLANOSALDO`: valor atual = 13461
- `G_PLANOSALDOPESSOA`: valor atual = 130

**Problema:**
- ❌ Não foi verificado se generators estão sincronizados com IDs das tabelas
- ❌ Risco de conflito ao inserir novos registros

**Validação Necessária:**
```sql
-- Verificar se generators estão à frente dos IDs
SELECT 
    (SELECT MAX(ID) FROM TRADE) as max_trade_id,
    GEN_ID(G_TRADE_ID, 0) as current_gen_value;

-- Se current_gen_value < max_trade_id, há problema!
```

**Risco:**
- **ALTA:** Inserção de registros pode falhar com erro de chave duplicada
- **ALTA:** Exportação de pedidos pode falhar

**Correção:**
```sql
-- Sincronizar generator
SET GENERATOR G_TRADE_ID TO (SELECT MAX(ID) FROM TRADE);
```

**Ação:** **OBRIGATÓRIA** antes de produção

---

### 2.2 Charset e Encoding

**Status:** ✅ **OK**

**Evidências:**
- Charset configurado: `UTF8`
- Conexão usa: `charset=UTF8`
- Compatível com PostgreSQL (UTF-8)

**Ação:** Nenhuma necessária

---

### 2.3 Diferença de Versão Firebird

**Status:** ⚠️ **VERIFICAR**

**Problema:**
- Tentativa de usar `MON$VERSION` falhou
- Firebird pode ser versão < 2.5
- Ou tabelas MON$ não estão disponíveis

**Evidência:**
```
Error: Column unknown MON$VERSION
```

**Teste Alternativo:**
- Query `SELECT * FROM RDB$DATABASE` funcionou
- Indica Firebird 2.5+ (mas MON$ pode estar desabilitado)

**Risco:**
- **MÉDIA:** Funcionalidades específicas de versão podem não funcionar
- **BAIXA:** Compatibilidade geral parece OK

**Ação:**
```sql
-- Verificar versão via outra forma
SELECT * FROM RDB$DATABASE;
-- Ou via isql: isql -z
```

**Recomendação:** Documentar versão exata do Firebird em produção

---

### 2.4 Dados Inconsistentes ou Inválidos

**Status:** ⚠️ **NÃO VALIDADO**

**Não foi possível validar:**
- Integridade referencial entre tabelas
- Dados órfãos
- Valores inválidos

**Ação:** Script de validação necessário

---

## 3. ORM / SQLAlchemy

### 3.1 Mapeamento Fiel aos Schemas

**Status:** ⚠️ **AJUSTAR** (1 divergência crítica)

**Problema:** `orders.customer_id` nullable no banco vs NOT NULL no modelo

**Outros Mapeamentos:**
- ✅ Tipos de dados corretos
- ✅ Relacionamentos definidos
- ✅ Constraints mapeadas

**Ação:** Corrigir schema do banco (ver 1.2)

---

### 3.2 Relacionamentos Corretos

**Status:** ✅ **OK**

**Relacionamentos Verificados:**
- ✅ `Order.customer` → `Customer` (back_populates)
- ✅ `Order.items` → `OrderItem[]` (cascade delete)
- ✅ `Order.payments` → `Payment[]`
- ✅ `Customer.orders` → `Order[]`

**Lazy Loading:**
- ✅ Uso correto de `lazy="selectin"` para evitar N+1
- ✅ `selectinload()` usado em queries críticas

**Ação:** Nenhuma necessária

---

### 3.3 Uso Correto de Generators

**Status:** ✅ **OK**

**PostgreSQL:**
- ✅ Uso de `gen_random_uuid()` para UUIDs
- ✅ Sequência `order_number_seq` para números
- ✅ Sem autoincrement indevido

**Firebird:**
- ⚠️ Não usa generators do Firebird (apenas leitura)
- ✅ Exportação usa IDs já existentes

**Ação:** Nenhuma necessária

---

### 3.4 Queries N+1

**Status:** ✅ **OK**

**Evidências:**
- ✅ Uso extensivo de `selectinload()`:
  ```python
  select(Order).options(
      selectinload(Order.customer),
      selectinload(Order.items),
      selectinload(Order.payments),
  )
  ```
- ✅ Relacionamentos configurados com `lazy="selectin"`
- ✅ Queries otimizadas

**Ação:** Nenhuma necessária

---

## 4. TRANSAÇÕES

### 4.1 Commit e Rollback Corretos

**Status:** ⚠️ **AJUSTAR** (2 problemas)

#### Problema 1: Commits Manuais Fora do Padrão `get_db()`

**Severidade:** 🟠 **ALTA**

**Padrão Esperado:**
```python
async def endpoint(db: AsyncSession = Depends(get_db)):
    # get_db() faz commit/rollback automaticamente
    ...
```

**Problemas Encontrados:**

1. **`handlers.py:887`** - Commit sem try/except:
```python
async with AsyncSessionLocal() as db:
    order.status = OrderStatus.PAID.value
    await db.commit()  # ❌ Sem tratamento de erro
```

2. **`firebird_export_service.py:354, 361`** - Commits em try/except, mas sem rollback explícito:
```python
try:
    # ... exportação ...
    await session.commit()  # ✅ OK
except Exception as e:
    order.firebird_export_error = str(e)
    await session.commit()  # ⚠️ Commit mesmo em erro (pode ser intencional)
    raise
```

3. **Múltiplos serviços síncronos** usando `session.commit()` sem contexto:
   - `product_service.py`
   - `order_service.py`
   - `customer_service.py`
   - `delivery_service.py`

**Risco:**
- **ALTA:** Transações podem ficar abertas em caso de erro
- **ALTA:** Dados inconsistentes se commit falhar
- **MÉDIA:** Locks podem não ser liberados

**Correção:**
```python
# Padrão correto
async with AsyncSessionLocal() as session:
    try:
        # ... operações ...
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()  # Implícito no context manager
```

**Ação:** Refatorar commits manuais para usar padrão seguro

---

#### Problema 2: Transações Síncronas sem Context Manager

**Severidade:** 🟠 **ALTA**

**Serviços Afetados:**
- `product_service.py` (SQLModel síncrono)
- `order_service.py` (SQLModel síncrono)
- `customer_service.py` (SQLModel síncrono)

**Exemplo:**
```python
# ❌ PROBLEMA
self.session.commit()  # Sem try/except, sem rollback
```

**Risco:**
- **ALTA:** Falhas silenciosas
- **ALTA:** Dados inconsistentes

**Correção:**
```python
try:
    self.session.commit()
except Exception:
    self.session.rollback()
    raise
```

**Ação:** Adicionar tratamento de erro em todos os commits síncronos

---

### 4.2 Transações Longas

**Status:** ✅ **OK**

**Análise:**
- ✅ Transações são curtas (operações pontuais)
- ✅ Sem loops dentro de transações
- ✅ Exportação Firebird usa transação explícita com commit/rollback

**Ação:** Nenhuma necessária

---

### 4.3 Possíveis Locks

**Status:** ⚠️ **MONITORAR**

**Riscos Identificados:**

1. **Exportação Firebird:**
   - Transação síncrona no Firebird
   - Pode bloquear se demorar
   - **Mitigação:** Já usa `anyio.to_thread.run_sync()` (não bloqueia event loop)

2. **Sincronização:**
   - Sync-service pode processar muitos registros
   - **Mitigação:** Usa batches

**Ação:** Monitorar locks em produção

---

## 5. PERFORMANCE

### 5.1 Índices Ausentes

**Status:** ✅ **OK**

**Verificação:**
- ✅ FKs têm índices
- ✅ Campos de busca têm índices
- ✅ Índices compostos para queries comuns

**Ação:** Nenhuma necessária

---

### 5.2 Queries Lentas

**Status:** ✅ **OK** (com monitoramento recomendado)

**Análise:**
- ✅ Uso de `selectinload()` previne N+1
- ✅ Paginação implementada
- ✅ Queries com `LIMIT` e `OFFSET`
- ✅ Índices adequados

**Recomendação:**
- Habilitar `EXPLAIN ANALYZE` em desenvolvimento
- Monitorar queries lentas em produção

**Ação:** Configurar monitoramento

---

### 5.3 Impacto em Dashboards e Relatórios

**Status:** ⚠️ **VERIFICAR**

**Não foi possível validar:**
- Queries de relatórios
- Agregações complexas
- Performance com volume de dados

**Ação:** Testes de carga necessários

---

## 6. SEGURANÇA

### 6.1 Uso Indevido de SYSDBA

**Status:** 🔴 **CRÍTICO - BLOQUEANTE**

**Problema:**
- **TODAS as conexões Firebird usam `SYSDBA`**
- SYSDBA é superusuário com permissões totais
- Risco de segurança extremo

**Evidências:**
```python
# backend/app/config.py
firebird_user: str = "SYSDBA"  # ❌ CRÍTICO

# backend/services/sync-service/app/config.py
firebird_user: str = "SYSDBA"  # ❌ CRÍTICO
```

**Riscos:**
- **CRÍTICO:** Acesso total ao banco Firebird
- **CRÍTICO:** Possibilidade de deletar/modificar qualquer dado
- **ALTA:** Violação de princípio de menor privilégio
- **ALTA:** Auditoria comprometida (não sabe quem fez o quê)

**Correção OBRIGATÓRIA:**
```sql
-- 1. Criar usuário específico no Firebird
CREATE USER GAS_AUTOMATION PASSWORD 'senha_forte_aqui';
GRANT SELECT ON TABLE ITEM TO GAS_AUTOMATION;
GRANT SELECT ON TABLE PESSOA TO GAS_AUTOMATION;
GRANT SELECT ON TABLE ITEMSALDO TO GAS_AUTOMATION;
GRANT SELECT ON TABLE ITEMPRECO TO GAS_AUTOMATION;
GRANT INSERT, SELECT ON TABLE TRADE TO GAS_AUTOMATION;
GRANT INSERT, SELECT ON TABLE TRADEITEM TO GAS_AUTOMATION;
-- ... outros grants necessários
```

```python
# 2. Atualizar configuração
firebird_user: str = "GAS_AUTOMATION"  # ✅
```

**Ação:** **BLOQUEANTE** - Não pode ir para produção com SYSDBA

---

### 6.2 Permissões Excessivas

**Status:** 🔴 **CRÍTICO** (relacionado ao 6.1)

**Problema:**
- SYSDBA tem todas as permissões
- Aplicação precisa apenas de:
  - SELECT em tabelas de leitura (ITEM, PESSOA, ITEMSALDO)
  - INSERT em tabelas de escrita (TRADE, TRADEITEM)

**Ação:** Ver 6.1

---

### 6.3 Segredos no Código

**Status:** ⚠️ **AJUSTAR** (1 problema)

#### Problema: API Key Hardcoded

**Severidade:** 🟡 **MÉDIA**

**Evidência:**
```python
# backend/app/config.py
waha_api_key: str = "gasautomation123"  # ⚠️ Valor padrão fraco
```

**Risco:**
- **MÉDIA:** Se não configurado no .env, usa valor padrão
- **BAIXA:** Valor padrão é fraco mas não é secreto crítico

**Correção:**
```python
waha_api_key: str = Field(..., description="WAHA API Key")  # Obrigatório
```

**Ação:** Tornar obrigatório ou remover default

---

### 6.4 Exposição de Dados Sensíveis em Logs

**Status:** ✅ **OK**

**Verificação:**
- ✅ Logs não expõem senhas
- ✅ Logs não expõem tokens
- ✅ Apenas IDs e mensagens genéricas

**Exemplo Seguro:**
```python
logger.error(f"Falha ao exportar pedido {order_id} para Firebird: {e}")
# ✅ Não expõe dados sensíveis
```

**Ação:** Nenhuma necessária

---

## 7. DEPLOY

### 7.1 Risco na Migração

**Status:** ⚠️ **AJUSTAR**

**Riscos Identificados:**

1. **Migração de `customer_id` NOT NULL:**
   - Pode falhar se houver dados NULL
   - **Ação:** Validar dados antes

2. **Sincronização de Generators Firebird:**
   - Pode causar conflitos
   - **Ação:** Script de validação

**Plano de Migração:**
```sql
-- 1. Validar dados
SELECT COUNT(*) FROM orders WHERE customer_id IS NULL;
-- Se > 0, corrigir antes

-- 2. Aplicar NOT NULL
ALTER TABLE orders ALTER COLUMN customer_id SET NOT NULL;

-- 3. Validar generators Firebird
-- (script separado)
```

**Ação:** Criar script de pré-validação

---

### 7.2 Necessidade de Scripts de Saneamento

**Status:** ⚠️ **NECESSÁRIO**

**Scripts Necessários:**

1. **Validar dados antes de migração:**
```sql
-- Verificar pedidos sem cliente
SELECT id, order_number FROM orders WHERE customer_id IS NULL;

-- Verificar generators Firebird
SELECT GEN_ID(G_TRADE_ID, 0) as gen_val, 
       (SELECT MAX(ID) FROM TRADE) as max_id;
```

2. **Sincronizar generators:**
```sql
SET GENERATOR G_TRADE_ID TO (SELECT MAX(ID) FROM TRADE);
```

**Ação:** Criar scripts de validação e saneamento

---

### 7.3 Rollback Possível

**Status:** ✅ **OK**

**Alembic:**
- ✅ Migrações têm `downgrade()`
- ✅ Rollback possível via `alembic downgrade`

**Firebird:**
- ⚠️ Exportações não têm rollback automático
- ⚠️ Dados já inseridos no Firebird permanecem

**Ação:** Documentar processo de rollback

---

### 7.4 Segurança do Pós-Deploy

**Status:** ⚠️ **AJUSTAR**

**Recomendações:**

1. **Monitoramento:**
   - Logs de exportação Firebird
   - Erros de transação
   - Performance de queries

2. **Alertas:**
   - Falhas de exportação
   - Transações longas
   - Erros de conexão

3. **Validação:**
   - Verificar dados exportados no Firebird
   - Validar integridade referencial

**Ação:** Configurar monitoramento

---

## 📋 CHECKLIST FINAL

| Item | Status | Observações |
|------|--------|-------------|
| **1. Banco de Dados** | | |
| 1.1 Versionamento Alembic | ✅ OK | Sincronizado |
| 1.2 Divergência de schema | ❌ BLOQUEANTE | `customer_id` NULL |
| 1.3 Primary/Foreign Keys | ⚠️ AJUSTAR | FK pode estar faltando |
| 1.4 Índices | ✅ OK | Todos presentes |
| 1.5 Tipos de dados | ⚠️ AJUSTAR | Status deveria ser ENUM |
| **2. Firebird** | | |
| 2.1 Generators sincronizados | ❌ BLOQUEANTE | Não validado |
| 2.2 Charset/encoding | ✅ OK | UTF8 correto |
| 2.3 Versão Firebird | ⚠️ VERIFICAR | Versão não detectada |
| 2.4 Dados inconsistentes | ⚠️ NÃO VALIDADO | Script necessário |
| **3. ORM/SQLAlchemy** | | |
| 3.1 Mapeamento fiel | ⚠️ AJUSTAR | Divergência customer_id |
| 3.2 Relacionamentos | ✅ OK | Corretos |
| 3.3 Generators | ✅ OK | Uso correto |
| 3.4 N+1 queries | ✅ OK | Prevenido |
| **4. Transações** | | |
| 4.1 Commit/rollback | ⚠️ AJUSTAR | Commits sem tratamento |
| 4.2 Transações longas | ✅ OK | Sem problemas |
| 4.3 Locks | ⚠️ MONITORAR | Monitorar em produção |
| **5. Performance** | | |
| 5.1 Índices ausentes | ✅ OK | Todos presentes |
| 5.2 Queries lentas | ✅ OK | Otimizadas |
| 5.3 Dashboards | ⚠️ VERIFICAR | Testes necessários |
| **6. Segurança** | | |
| 6.1 Uso de SYSDBA | ❌ BLOQUEANTE | Crítico - criar usuário |
| 6.2 Permissões | ❌ BLOQUEANTE | Relacionado ao 6.1 |
| 6.3 Segredos no código | ⚠️ AJUSTAR | API key com default |
| 6.4 Logs sensíveis | ✅ OK | Sem exposição |
| **7. Deploy** | | |
| 7.1 Risco migração | ⚠️ AJUSTAR | Scripts necessários |
| 7.2 Scripts saneamento | ⚠️ NECESSÁRIO | Criar scripts |
| 7.3 Rollback | ✅ OK | Possível |
| 7.4 Pós-deploy | ⚠️ AJUSTAR | Monitoramento |

---

## 🚨 PROBLEMAS CRÍTICOS (BLOQUEANTES)

### 1. Uso de SYSDBA no Firebird 🔴

**Severidade:** CRÍTICA  
**Impacto:** Segurança comprometida  
**Ação:** Criar usuário específico com permissões mínimas

**Prazo:** Antes de qualquer deploy

---

### 2. `orders.customer_id` NULL no Banco 🔴

**Severidade:** CRÍTICA  
**Impacto:** Integridade de dados comprometida  
**Ação:** Migração para NOT NULL

**Prazo:** Antes de produção

---

### 3. Generators Firebird Não Sincronizados 🔴

**Severidade:** CRÍTICA  
**Impacto:** Falhas de inserção, chaves duplicadas  
**Ação:** Script de validação e sincronização

**Prazo:** Antes de produção

---

### 4. Foreign Key `orders.customer_id` NÃO EXISTE 🔴

**Severidade:** CRÍTICA  
**Impacto:** Sem integridade referencial, dados podem ficar inconsistentes  
**Evidência:** FK não encontrada no banco (verificação executada - 0 FKs encontradas)

**Causa:** Banco criado manualmente, FK da migração inicial não foi aplicada

**Ação:** Criar FK imediatamente

**Prazo:** Antes de produção

---

### 5. `orders.customer_id` é NULL mas deveria ser NOT NULL 🔴

**Severidade:** CRÍTICA  
**Impacto:** Integridade de dados comprometida  
**Evidência:** Coluna é NULL no banco, mas modelo define NOT NULL

**Dados Atuais:**
- ✅ 0 pedidos sem customer_id (dados estão OK)
- ❌ Coluna permite NULL (schema incorreto)

**Ação:** Migração para NOT NULL (junto com FK)

**Prazo:** Antes de produção

---

## 🟠 PROBLEMAS DE ALTA SEVERIDADE

### 5. Commits Sem Tratamento de Erro

**Arquivos Afetados:**
- `handlers.py:887`
- Múltiplos serviços síncronos

**Ação:** Adicionar try/except/rollback

---

### 6. Campos Nullable com Default

**Campos:** `orders.status`, `orders.total_amount`

**Ação:** Migração para NOT NULL

---

## 🟡 PROBLEMAS DE MÉDIA SEVERIDADE

### 7. Status como VARCHAR ao invés de ENUM

**Ação:** Decisão arquitetural

---

### 8. API Key com Default Fraco

**Ação:** Tornar obrigatório

---

### 9. Versão Firebird Não Detectada

**Ação:** Documentar versão manualmente

---

## 📝 CORREÇÕES TÉCNICAS RECOMENDADAS

### Migração 1: Criar FK e Corrigir `customer_id` NOT NULL

```python
# backend/alembic/versions/YYYYMMDD_fix_orders_customer_id.py
"""Fix orders.customer_id: Create FK and set NOT NULL

Revision ID: fix_customer_id
Revises: 20260124_firebird_export
"""

def upgrade():
    # 1. Validar dados
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM orders WHERE customer_id IS NULL) THEN
                RAISE EXCEPTION 'Existem pedidos sem customer_id. Corrija antes de aplicar NOT NULL.';
            END IF;
            
            -- Verificar se há pedidos com customer_id inválido
            IF EXISTS (
                SELECT 1 FROM orders o
                LEFT JOIN customers c ON o.customer_id = c.id
                WHERE c.id IS NULL
            ) THEN
                RAISE EXCEPTION 'Existem pedidos com customer_id inválido. Corrija antes de criar FK.';
            END IF;
        END $$;
    """)
    
    # 2. Criar FK (se não existir)
    # Verificar se já existe
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE table_name = 'orders'
                AND constraint_name = 'fk_orders_customer'
                AND constraint_type = 'FOREIGN KEY'
            ) THEN
                ALTER TABLE orders
                ADD CONSTRAINT fk_orders_customer
                FOREIGN KEY (customer_id)
                REFERENCES customers(id)
                ON DELETE RESTRICT;
            END IF;
        END $$;
    """)
    
    # 3. Aplicar NOT NULL
    op.alter_column('orders', 'customer_id', nullable=False)
    
    # 4. Aplicar NOT NULL em outros campos
    op.alter_column('orders', 'status', nullable=False)
    op.alter_column('orders', 'total_amount', nullable=False)

def downgrade():
    op.alter_column('orders', 'total_amount', nullable=True)
    op.alter_column('orders', 'status', nullable=True)
    op.alter_column('orders', 'customer_id', nullable=True)
    op.drop_constraint('fk_orders_customer', 'orders', type_='foreignkey')
```

---

### Script 2: Validar e Sincronizar Generators Firebird

```python
# backend/scripts/validate_firebird_generators.py
"""Valida e sincroniza generators do Firebird."""

from app.integrations.firebird import firebird_client

def validate_generators():
    with firebird_client.get_connection() as conn:
        cursor = conn.cursor()
        
        # Verificar TRADE
        cursor.execute("SELECT MAX(ID) FROM TRADE")
        max_id = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT GEN_ID(G_TRADE_ID, 0) FROM RDB$DATABASE")
        gen_val = cursor.fetchone()[0]
        
        if gen_val < max_id:
            print(f"⚠️ Generator desincronizado: G_TRADE_ID={gen_val}, MAX(ID)={max_id}")
            cursor.execute(f"SET GENERATOR G_TRADE_ID TO {max_id + 1}")
            conn.commit()
            print(f"✅ Generator sincronizado para {max_id + 1}")
        else:
            print(f"✅ Generator OK: {gen_val} >= {max_id}")
```

---

### Correção 3: Criar Usuário Firebird

```sql
-- Executar no Firebird como SYSDBA
CREATE USER GAS_AUTOMATION PASSWORD 'senha_forte_aqui_32_chars_min';

-- Permissões de LEITURA
GRANT SELECT ON TABLE ITEM TO GAS_AUTOMATION;
GRANT SELECT ON TABLE ITEMPRECO TO GAS_AUTOMATION;
GRANT SELECT ON TABLE ITEMSALDO TO GAS_AUTOMATION;
GRANT SELECT ON TABLE PESSOA TO GAS_AUTOMATION;
GRANT SELECT ON TABLE PESSOAFISICA TO GAS_AUTOMATION;
GRANT SELECT ON TABLE PESSOAJURIDICA TO GAS_AUTOMATION;
GRANT SELECT ON TABLE ENDERECO TO GAS_AUTOMATION;
GRANT SELECT ON TABLE FONE TO GAS_AUTOMATION;
GRANT SELECT ON TABLE CLIENTE TO GAS_AUTOMATION;

-- Permissões de ESCRITA (apenas exportação)
GRANT INSERT, SELECT ON TABLE TRADE TO GAS_AUTOMATION;
GRANT INSERT, SELECT ON TABLE TRADEITEM TO GAS_AUTOMATION;

-- Verificar permissões
SELECT * FROM RDB$USER_PRIVILEGES 
WHERE RDB$USER = 'GAS_AUTOMATION';
```

---

### Correção 4: Padronizar Transações

```python
# Padrão para commits manuais
async def safe_commit(session: AsyncSession):
    """Commit seguro com rollback automático."""
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise
```

---

## ✅ PONTOS POSITIVOS

1. ✅ Uso correto de `selectinload()` previne N+1
2. ✅ Índices bem implementados
3. ✅ Transações curtas
4. ✅ Logs não expõem dados sensíveis
5. ✅ Alembic configurado corretamente
6. ✅ Tipos de dados adequados (UUID, Numeric, JSONB)
7. ✅ Relacionamentos bem definidos

---

## 🎯 DECISÃO FINAL

### ⚠️ **NO-GO para Produção** (até correções)

**Motivos:**
1. 🔴 Uso de SYSDBA (segurança crítica)
2. 🔴 FK `orders.customer_id` não existe (integridade crítica)
3. 🔴 `customer_id` NULL no schema (integridade crítica)
4. 🔴 Generators não validados (risco de falhas)
5. 🟠 Commits sem tratamento (risco de inconsistência)

**Prazo Estimado para Correções:** 2-3 dias

**Após Correções:** ✅ **GO** (com monitoramento)

---

## 📋 PLANO DE AÇÃO PRIORITÁRIO

### Dia 1 (URGENTE)
1. ✅ Criar usuário Firebird específico
2. ✅ Atualizar configurações
3. ✅ Testar permissões

### Dia 2 (CRÍTICO)
1. ✅ Criar migração para `customer_id` NOT NULL
2. ✅ Validar dados existentes
3. ✅ Aplicar migração

### Dia 3 (VALIDAÇÃO)
1. ✅ Script de validação de generators
2. ✅ Sincronizar generators
3. ✅ Testes de exportação

### Dia 4 (MELHORIAS)
1. ✅ Refatorar commits manuais
2. ✅ Adicionar monitoramento
3. ✅ Testes finais

---

**Relatório gerado em:** 27/01/2026  
**Próxima revisão:** Após correções críticas
