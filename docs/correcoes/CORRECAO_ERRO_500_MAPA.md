# Correção: Erro 500 no Mapa do Painel

**Data:** 2026-02-13  
**Horário:** 21:52  
**Status:** ✅ CORRIGIDO

---

## 🐛 Problema

O mapa do painel do operador estava retornando **erro 500**:

```
GET /api/locations/map-data?include_offline_drivers=false&hours_back=24
HTTP/1.1 500 Internal Server Error
```

### Erro nos Logs:

```
ERROR [app.api.locations] Erro ao buscar dados do mapa: 
(sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) 
<class 'asyncpg.exceptions.UndefinedColumnError'>: 
column drivers.bairro does not exist

[SQL: SELECT drivers.name, drivers.phone, drivers.email, drivers.bairro, ...
FROM drivers 
WHERE drivers.is_active = true]
```

---

## 🔍 Causa Raiz

**Dessincronia entre Model e Banco:**

### Model Driver (Código)
```python
class Driver(BaseModel):
    bairro: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Bairro de atuação do entregador"
    )
```
✅ Campo `bairro` existe no model

### Tabela drivers (PostgreSQL)
```sql
\d drivers

 id               | uuid
 name             | varchar(100)
 phone            | varchar(20)
 email            | varchar(100)
 vehicle_type     | varchar(50)
 ...
```
❌ Coluna `bairro` **não existe** na tabela

---

## ✅ Solução

Adicionar a coluna `bairro` na tabela `drivers`:

```sql
-- 1. Adicionar coluna
ALTER TABLE drivers 
ADD COLUMN IF NOT EXISTS bairro VARCHAR(100);

-- 2. Criar índice (para performance)
CREATE INDEX IF NOT EXISTS ix_drivers_bairro 
ON drivers(bairro);
```

### Execução:

```bash
docker-compose exec -T postgres psql -U gasadmin -d gas_automation \
  -c "ALTER TABLE drivers ADD COLUMN IF NOT EXISTS bairro VARCHAR(100);"

docker-compose exec -T postgres psql -U gasadmin -d gas_automation \
  -c "CREATE INDEX IF NOT EXISTS ix_drivers_bairro ON drivers(bairro);"
```

---

## ✅ Resultado

### Antes:
```
GET /api/locations/map-data
→ 500 Internal Server Error
→ column drivers.bairro does not exist
```

### Depois:
```
GET /api/locations/map-data
→ 200 OK
→ Mapa funciona normalmente
```

---

## 🧪 Como Testar

### Teste 1: Verificar coluna no banco
```bash
docker-compose exec -T postgres psql -U gasadmin -d gas_automation \
  -c "\d drivers" | grep bairro
```
**Resultado esperado:**
```
 bairro           | character varying(100)   |           |          | 
    "ix_drivers_bairro" btree (bairro)
```

### Teste 2: Acessar mapa no painel
```
1. Abrir navegador
2. Ir para: http://localhost:3000/mapa
3. Verificar que o mapa carrega sem erro 500
```

### Teste 3: Verificar API
```bash
curl http://localhost:8000/api/locations/map-data
```
**Resultado esperado:** JSON com dados dos drivers (200 OK)

---

## 📝 Por que isso aconteceu?

O campo `bairro` foi adicionado no **model Python** mas:
- ❌ Não foi criada uma migration
- ❌ Não foi executado `alembic upgrade head`
- ❌ A tabela não foi atualizada no banco

**Resultado:** Model e banco ficaram dessincronizados.

---

## 🔧 Solução Permanente (Recomendação)

Para evitar esse problema no futuro, usar **Alembic migrations**:

```bash
# 1. Criar migration
alembic revision --autogenerate -m "Adicionar coluna bairro em drivers"

# 2. Aplicar migration
alembic upgrade head
```

Mas como não estamos usando migrations ativas, a solução SQL direta funciona.

---

## 📊 Impacto

| Antes | Depois |
|-------|--------|
| ❌ Mapa não carrega | ✅ Mapa funciona |
| ❌ Erro 500 | ✅ 200 OK |
| ❌ Painel com erro | ✅ Painel operacional |

---

## 🔗 Endpoint Afetado

**API:** `GET /api/locations/map-data`

**Usado por:** Painel do operador (dashboard) para mostrar:
- 📍 Localização de entregadores
- 🚚 Entregas em andamento
- 🏠 Localização de clientes
- 🗺️ Mapa em tempo real

---

## 📝 Documentos Relacionados

- `backend/app/models/driver.py` - Model com campo bairro
- `backend/app/api/locations.py` - Endpoint do mapa

---

**Status Final:** ✅ MAPA DO PAINEL FUNCIONANDO

O erro 500 foi corrigido! O mapa agora carrega normalmente. 🎉
