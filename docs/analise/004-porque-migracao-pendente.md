# Por Que a Migração Está Pendente?

**Data:** 27/01/2026  
**Problema:** Migração `20260124_firebird_export` não aplicada

---

## 🔍 DIAGNÓSTICO

### Problema Identificado

A migração está pendente porque **o banco de dados nunca foi inicializado com Alembic**.

### Evidências

1. **Tabela `alembic_version` não existe:**
   ```sql
   ERROR: relation "alembic_version" does not exist
   ```

2. **Comando `alembic current` retorna vazio:**
   ```bash
   $ alembic current
   # (nenhuma versão retornada)
   ```

3. **Comando `alembic check` confirma:**
   ```bash
   $ alembic check
   FAILED: Target database is not up to date.
   ```

4. **Colunas Firebird não existem:**
   ```sql
   SELECT column_name FROM information_schema.columns
   WHERE table_name = 'orders' AND column_name LIKE '%firebird%';
   -- Resultado: 0 linhas
   ```

---

## 📋 CAUSA RAIZ

### Como o Banco Foi Criado?

O banco de dados foi criado de uma das seguintes formas:

1. **Via `schema.sql`** (schema inicial)
2. **Manualmente** (CREATE TABLE direto)
3. **Outro sistema de migração**

**NÃO foi criado via Alembic**, por isso:
- ❌ Tabela `alembic_version` não existe
- ❌ Controle de versão não está funcionando
- ❌ Migrações não podem ser aplicadas normalmente

---

## ✅ SOLUÇÃO

### Opção 1: Marcar Banco como Atualizado (Recomendado)

Se o banco já tem todas as estruturas básicas, mas apenas falta a migração do Firebird:

```bash
# 1. Marcar banco como estando na versão anterior
docker exec gas_backend alembic stamp 20260124_vasilhames

# 2. Aplicar apenas a migração do Firebird
docker exec gas_backend alembic upgrade head
```

**Quando usar:** Se o banco já tem todas as tabelas e estruturas, mas apenas falta a migração do Firebird.

---

### Opção 2: Inicializar Alembic do Zero

Se o banco foi criado manualmente e precisa de controle de versão:

```bash
# 1. Marcar como estando na versão HEAD (assumindo que tudo já existe)
docker exec gas_backend alembic stamp head

# 2. Verificar se está sincronizado
docker exec gas_backend alembic check
```

**Quando usar:** Se você quer que o Alembic reconheça o estado atual do banco.

---

### Opção 3: Aplicar Todas as Migrações (Mais Seguro)

Se você quer garantir que todas as migrações sejam aplicadas:

```bash
# 1. Verificar histórico de migrações
docker exec gas_backend alembic history

# 2. Aplicar todas as migrações pendentes
docker exec gas_backend alembic upgrade head
```

**Quando usar:** Se você quer garantir que o banco está 100% sincronizado com o código.

---

## 🎯 RECOMENDAÇÃO ESPECÍFICA

### Para Este Caso:

Como o banco já tem:
- ✅ Tabela `orders` (12 pedidos)
- ✅ Tabela `products` (3 produtos)
- ✅ Tabela `customers` (3 clientes)
- ❌ Mas NÃO tem colunas Firebird

**Ação Recomendada:**

```bash
# 1. Marcar banco como estando na versão anterior à migração Firebird
docker exec gas_backend alembic stamp 20260124_vasilhames

# 2. Aplicar apenas a migração do Firebird
docker exec gas_backend alembic upgrade head

# 3. Verificar se funcionou
docker exec gas_backend alembic current
# Deve mostrar: 20260124_firebird_export

# 4. Verificar se colunas foram criadas
docker exec gas_backend python -c "
from sqlalchemy import text
from app.database import AsyncSessionLocal
import asyncio

async def check():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text('''
            SELECT column_name 
            FROM information_schema.columns
            WHERE table_name = \\'orders\\'
            AND column_name LIKE \\'%firebird%\\'
            ORDER BY column_name
        '''))
        cols = result.fetchall()
        print(f'Colunas firebird: {len(cols)}')
        for col in cols:
            print(f'  - {col[0]}')

asyncio.run(check())
"
```

---

## 📊 ESTADO ATUAL vs ESTADO ESPERADO

### Estado Atual
```
Banco de Dados:
├── Tabelas básicas: ✅ Existem
├── Tabela alembic_version: ❌ NÃO existe
├── Versão registrada: ❌ Nenhuma
└── Colunas Firebird: ❌ NÃO existem
```

### Estado Esperado (Após Correção)
```
Banco de Dados:
├── Tabelas básicas: ✅ Existem
├── Tabela alembic_version: ✅ Existe
├── Versão registrada: ✅ 20260124_firebird_export
└── Colunas Firebird: ✅ Existem
    ├── firebird_trade_id
    ├── firebird_export_status
    ├── firebird_exported_at
    ├── firebird_export_attempts
    └── firebird_export_error
```

---

## ⚠️ IMPORTANTE

### Antes de Aplicar

1. **Backup do banco:**
   ```bash
   docker exec postgres pg_dump -U gasadmin gas_automation > backup_antes_migracao.sql
   ```

2. **Verificar se não há conflitos:**
   - As colunas que serão criadas não devem existir
   - Não deve haver dados que dependam dessas colunas

3. **Testar em ambiente de desenvolvimento primeiro** (se possível)

---

## 🔗 Referências

- `backend/alembic/versions/20260124_add_firebird_export_fields.py` - Migração
- `docs/analise/003-varredura-profunda-firebird.md` - Análise completa
- Documentação Alembic: https://alembic.sqlalchemy.org/

---

## ✅ CONCLUSÃO E RESOLUÇÃO

### Por Que Estava Pendente

**Causa Raiz:**
- O banco foi criado **sem controle de versão do Alembic**
- A tabela `alembic_version` **não existia**
- O Alembic **não sabia qual versão** o banco estava
- As colunas Firebird **nunca foram criadas**

**Evidências:**
- `alembic current` retornava vazio
- `alembic check` mostrava "Target database is not up to date"
- Colunas Firebird não existiam (0 colunas encontradas)

### O Que Foi Feito

1. ✅ **`alembic stamp 20260124_vasilhames`** - Marcou banco como estando na versão anterior
2. ✅ **`alembic upgrade head`** - Aplicou a migração do Firebird

### Resultado Final

**✅ MIGRAÇÃO APLICADA COM SUCESSO!**

Colunas criadas na tabela `orders`:
- ✅ `firebird_trade_id` (integer)
- ✅ `firebird_export_status` (character varying)
- ✅ `firebird_exported_at` (timestamp with time zone)
- ✅ `firebird_export_attempts` (integer)
- ✅ `firebird_export_error` (text)

**Status Atual:**
- ✅ Versão no banco: `20260124_firebird_export` (head)
- ✅ Colunas Firebird: 5/5 criadas
- ✅ Banco sincronizado com código

**Tempo total:** ~2 minutos

---

## 📝 RESUMO

**Problema:** Migração pendente porque banco não tinha controle de versão Alembic

**Solução:** Marcar versão anterior + aplicar upgrade

**Status:** ✅ **RESOLVIDO** - Migração aplicada com sucesso
