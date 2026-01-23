# 📊 MATRIZ TÉCNICA - CONVERSÃO MODELOS ERIC_FILES → APP

**Status:** ✅ PREPARADO PARA FASE 2  
**Complexidade:** 🟡 MÉDIA  
**Tempo estimado:** 2-3 dias

---

## 📋 CONVERTER POR CAMPO

### 1. USER MODEL

| Campo | eric_files | app | Ação |
|-------|-----------|-----|------|
| `id` | int autoincrement | int autoincrement | ✅ MANTÉM |
| `email` | unique, FK deleted | unique | ✅ MANTÉM |
| `name` | str | — | ⚠️ RENOMEAR → full_name |
| **NEW** | — | username unique | 🆕 ADICIONAR |
| **NEW** | — | role = "user" | 🆕 ADICIONAR |
| **NEW** | — | is_active = True | 🆕 ADICIONAR |
| `created_by` | FK user.id | — | ❌ REMOVER (usar AuditLog) |
| timestamps | datetime.now() | datetime.now() | ⚠️ STANDARDIZAR TIMEZONE |

**Migration SQL:**
```sql
-- eric_files user
ALTER TABLE "user" 
  ADD COLUMN username VARCHAR(255) UNIQUE DEFAULT NULL,
  ADD COLUMN role VARCHAR(50) DEFAULT 'user',
  ADD COLUMN is_active BOOLEAN DEFAULT TRUE,
  RENAME COLUMN name TO full_name;

-- Populate username from email (fazer em Python)
UPDATE "user" SET username = SUBSTR(email, 1, POSITION('@' IN email) - 1);
ALTER TABLE "user" ALTER COLUMN username SET NOT NULL;
```

---

### 2. CUSTOMER MODEL

| Campo | eric_files | app | Ação |
|-------|-----------|-----|------|
| `id` | int autoincrement | int autoincrement | ✅ MANTÉM |
| `telefone` | unique, str | phone unique, str | ✅ RENAME |
| `nome` | str | name str | ✅ RENAME |
| `endereco` | str (bruto) | address JSON | ⚠️ CONVERTER |
| `numero` | str | address.number | ⚠️ CONVERTER |
| `complemento` | str | address.complement | ⚠️ CONVERTER |
| `bairro` | str | address.bairro | ⚠️ CONVERTER |
| `cidade` | str | address.city | ⚠️ CONVERTER |
| `estado` | str | address.state | ⚠️ CONVERTER |
| `cep` | str | address.cep | ⚠️ CONVERTER |
| `ponto_referencia` | str | address.ponto_referencia | ⚠️ CONVERTER |
| `latitude` | float | address.latitude | ⚠️ CONVERTER |
| `longitude` | float | address.longitude | ⚠️ CONVERTER |
| **NEW** | — | firebird_id | 🆕 ADICIONAR (null inicialmente) |
| **NEW** | — | asaas_customer_id | 🆕 ADICIONAR (null inicialmente) |
| **NEW** | — | email | 🆕 ADICIONAR (null inicialmente) |
| **NEW** | — | cpf_cnpj | 🆕 ADICIONAR (null inicialmente) |
| **NEW** | — | notes | 🆕 ADICIONAR (null inicialmente) |

**Migration Python:**
```python
import json
from sqlalchemy import text

def migrate_customers(session):
    """Convert eric_files customers to app format"""
    customers = session.execute(
        text("SELECT id, telefone, nome, endereco, numero, complemento, bairro, cidade, estado, cep, ponto_referencia, latitude, longitude FROM customer")
    ).fetchall()
    
    for old_cust in customers:
        address = {
            "street": old_cust.endereco,
            "number": old_cust.numero,
            "complement": old_cust.complemento,
            "bairro": old_cust.bairro,
            "city": old_cust.cidade,
            "state": old_cust.estado,
            "cep": old_cust.cep,
            "ponto_referencia": old_cust.ponto_referencia,
            "latitude": old_cust.latitude,
            "longitude": old_cust.longitude,
        }
        
        session.execute(
            text("""
                INSERT INTO customer (id, phone, name, address) 
                VALUES (:id, :phone, :name, :address)
                ON CONFLICT (id) DO UPDATE SET address = :address
            """),
            {"id": old_cust.id, "phone": old_cust.telefone, "name": old_cust.nome, "address": json.dumps(address)}
        )
    
    session.commit()
```

---

### 3. ORDER MODEL

| Campo | eric_files | app | Ação |
|-------|-----------|-----|------|
| `id` | int autoincrement | int autoincrement | ✅ MANTÉM |
| `customer_id` | int FK | int FK | ✅ MANTÉM |
| `numero_pedido` | str | order_number int | ⚠️ CONVERTER |
| `status` | enum (PT) | enum (EN) | ⚠️ MAPEAR |
| **ADDRESS FIELDS** | 8 campos separados | address JSON | ⚠️ CONVERTER |
| `subtotal` | float | — | ❓ VERIFICAR |
| `taxa_entrega` | float | — | ❓ VERIFICAR |
| `desconto` | float | — | ❓ VERIFICAR |
| `total` | float | total_amount Decimal | ⚠️ CONVERTER |
| `forma_pagamento` | enum | payment_method str | ⚠️ MAPEAR |
| `status_pagamento` | enum | — | ❓ VERIFICAR |
| `troco_para` | float | — | ❓ VERIFICAR |
| `observacoes` | str | notes str | ✅ RENAME |
| `created_at` | timestamp | — | ⚠️ VERIFICAR |
| `confirmed_at` | timestamp | — | ⚠️ MAPEAR |
| `completed_at` | timestamp | delivered_at | ⚠️ RENAME |
| `cancelled_at` | timestamp | — | ⚠️ VERIFICAR |

**Enum Mapping:**
```python
ORDER_STATUS_MAP = {
    "NOVO": "pending",
    "CONFIRMADO": "paid",
    "EM_PREPARO": "preparing",
    "SAIU_ENTREGA": "dispatched",
    "ENTREGUE": "delivered",
    "CANCELADO": "cancelled",
}

PAYMENT_METHOD_MAP = {
    "PIX": "pix",
    "CARTAO_CREDITO": "credit_card",
    "CARTAO_DEBITO": "debit_card",
    "DINHEIRO": "cash",
    "BOLETO": "boleto",
}

PAYMENT_STATUS_MAP = {
    "PENDENTE": "pending",
    "PAGO": "paid",
    "RECUSADO": "failed",
}
```

---

### 4. ORDERITEM MODEL

| Campo | eric_files | app | Ação |
|-------|-----------|-----|------|
| `id` | int autoincrement | int autoincrement | ✅ MANTÉM |
| `order_id` | int FK | int FK | ✅ MANTÉM |
| `product_id` | int FK | int FK | ✅ MANTÉM |
| `quantidade` | int | quantity int | ✅ RENAME |
| `preco_unitario` | float | price Decimal | ⚠️ CONVERTER |
| `tem_troca` | bool | has_exchange bool | ✅ RENAME |
| `subtotal` | float | — | ❓ VERIFICAR |

---

### 5. DELIVERY MODEL

| Campo | eric_files | app | Ação |
|-------|-----------|-----|------|
| `id` | int autoincrement | int autoincrement | ✅ MANTÉM |
| `order_id` | int FK unique | int FK unique | ✅ MANTÉM |
| `driver_id` | int FK | UUID nullable | ⚠️ CONVERTER |
| `atribuido_em` | timestamp | — | ⚠️ MAPEAR |
| `saiu_em` | timestamp | — | ⚠️ MAPEAR |
| `entregue_em` | timestamp | — | ⚠️ MAPEAR |
| `tempo_estimado` | int (minutes) | estimated_minutes | ✅ RENAME |
| `distancia_km` | float | — | ❓ VERIFICAR |
| `confirmado_cliente` | bool | — | ❓ VERIFICAR |
| `foto_entrega` | str (URL) | — | ❓ VERIFICAR |
| `observacoes` | str | notes | ✅ RENAME |

**Nota:** app/DeliveryHistory não existe em eric_files. Recomendação: manter como rastreamento separado.

---

### 6. DRIVER MODEL

| Campo | eric_files | app | Ação |
|-------|-----------|-----|------|
| `id` | int autoincrement | UUID | 🔴 CONVERTER |
| `nome` | str | name str | ✅ RENAME |
| `telefone` | str unique | phone str unique | ✅ RENAME |
| `status` | enum (PT) | enum (EN) | ⚠️ MAPEAR |
| `latitude` | float | — | ⚠️ CENTRALIZAR GPS |
| `longitude` | float | — | ⚠️ CENTRALIZAR GPS |
| `ultima_localizacao` | timestamp | — | ⚠️ REMOVER (usar separada) |
| `velocidade_kmh` | float | — | ❓ VERIFICAR |
| **NEW** | — | email str | 🆕 ADICIONAR |
| **NEW** | — | vehicle_type | 🆕 ADICIONAR |
| **NEW** | — | license_plate | 🆕 ADICIONAR |
| **NEW** | — | current_location JSON | 🆕 CRIAR |
| **NEW** | — | rating | 🆕 ADICIONAR |
| **NEW** | — | total_deliveries | 🆕 ADICIONAR |

**Driver Status Enum:**
```python
DRIVER_STATUS_MAP = {
    "OFFLINE": "offline",
    "ATIVO": "available",
    "EM_ENTREGA": "busy",
    "PAUSA": "break",
}
```

---

### 7. PRODUCT MODEL

| Campo | eric_files | app | Ação |
|-------|-----------|-----|------|
| `id` | int autoincrement | int autoincrement | ✅ MANTÉM |
| `nome` | str unique | nome str unique | ✅ MANTÉM |
| `descricao` | str | — | ❓ VERIFICAR |
| `peso_kg` | float | — | ❓ VERIFICAR |
| `preco` | float | price Decimal | ⚠️ CONVERTER |
| `preco_troca` | float | exchange_price Decimal | ✅ RENAME |
| `estoque_atual` | int | current_stock int | ✅ RENAME |
| `ativo` | bool | is_active bool | ✅ RENAME |
| `created_at` | timestamp | created_at timestamp | ✅ MANTÉM |
| `updated_at` | timestamp | updated_at timestamp | ✅ MANTÉM |

---

## 🔄 ORDEM DE EXECUÇÃO

### Passo 1: Criar tabelas app/ (já existem?)
```
[ ] User
[ ] Customer  
[ ] Order
[ ] OrderItem
[ ] Delivery
[ ] Driver
[ ] Product
```

### Passo 2: Executar Migrations
```
[ ] Migration 1: Adicionar campos em eric_files
[ ] Migration 2: Criar índices
[ ] Migration 3: Remover constraints antigas
```

### Passo 3: Executar Scripts de Conversão
```python
# Em sequência:
migrate_users()
migrate_customers()
migrate_products()
migrate_drivers()
migrate_orders()
migrate_order_items()
migrate_deliveries()
```

### Passo 4: Validação
```
[ ] Contar registros antes/depois
[ ] Verificar referential integrity
[ ] Verificar enums mapeados corretamente
[ ] Verificar timestamps
```

---

## ⚠️ CUIDADOS ESPECIAIS

1. **INT → UUID em Driver:**
   - Driver IDs vão mudar
   - Delivery.driver_id precisa ser mapeado
   - Histórico precisa ser preservado

2. **Address JSON Conversion:**
   - Backup dos dados originais
   - Validação de que todos os campos foram convertidos
   - Criar JSON schema para validação

3. **Enums:**
   - Todos os valores PT precisam mapear 100%
   - Nenhum valor desconhecido pode ficar
   - Adicionar validates em models

4. **Decimals vs Floats:**
   - Valores monetários devem ser Decimal
   - Não usar float para dinheiro!
   - Cuidado com arredondamento

---

## 📊 CHECKLIST FINAL

- [ ] Todos os fields mapeados
- [ ] Todos os enums mapeados
- [ ] Scripts de migração testados localmente
- [ ] Backup de dados originais criado
- [ ] Validação de integridade referencial escrita
- [ ] Documentação atualizada
- [ ] Team review feito
- [ ] Pronto para FASE 2 executar

---

**Status:** ✅ PRONTO PARA EXECUÇÃO  
**Próximo:** Aguardar aprovação para iniciar migrações
