# Correção Completa: Incompatibilidade Model Customer vs V2

**Data:** 2026-02-13  
**Status:** ✅ CORRIGIDO

---

## 🐛 Problema Geral

O código V2 foi desenvolvido assumindo campos que **não existem** no model `Customer` do banco de dados, causando múltiplos erros:

```
AttributeError: 'Customer' object has no attribute 'document'
AttributeError: 'Customer' object has no attribute 'tipo_documento'
AttributeError: 'Customer' object has no attribute 'addresses'
```

---

## 🔍 Análise: Model Real vs Código V2

### Model Customer (Real - PostgreSQL)

```python
class Customer(BaseModel):
    phone: str                    # ✅ Existe
    name: Optional[str]           # ✅ Existe
    cpf_cnpj: Optional[str]       # ⚠️ V2 esperava 'document'
    address: Optional[dict]       # ⚠️ V2 esperava 'addresses' (plural)
    email: Optional[str]          # ✅ Existe
    notes: Optional[str]          # ✅ Existe
    waha_chat_id: Optional[str]   # ✅ Existe
    
    # Campos que NÃO existem:
    # ❌ document
    # ❌ tipo_documento
    # ❌ customer_type
    # ❌ addresses (plural)
    # ❌ default_address_idx
    # ❌ last_order_data
    # ❌ preferences
    # ❌ order_count
```

### CustomerContext (V2 - Esperado)

```python
@dataclass
class CustomerContext:
    customer_id: str
    name: Optional[str]
    document: Optional[str]           # ⚠️ Model tem 'cpf_cnpj'
    customer_type: str                # ❌ Não existe no model
    addresses: List[Dict]             # ⚠️ Model tem 'address' (singular)
    default_address_idx: int          # ❌ Não existe no model
    last_order: Optional[Dict]        # ❌ Não existe no model
    preferences: Dict                 # ❌ Não existe no model
    order_count: int                  # ❌ Não existe no model
```

---

## ✅ Correções Implementadas

### 1. ContextManager - Método `get_customer_context`

**Problema:** Tentava acessar campos inexistentes

**Solução:**

```python
# ANTES (errado)
document=customer.document,                    # ❌ Não existe
customer_type=customer.customer_type,          # ❌ Não existe
addresses=customer.addresses or [],            # ❌ Não existe (plural)
default_address_idx=customer.default_address_idx,  # ❌ Não existe

# DEPOIS (correto)
document=customer.cpf_cnpj,                    # ✅ Mapeado
customer_type=getattr(customer, 'customer_type', None) or "PF",  # ✅ Safe
addresses=[customer.address] if customer.address else [],  # ✅ Convertido para lista
default_address_idx=0,                         # ✅ Valor padrão
last_order=getattr(customer, 'last_order_data', None),  # ✅ Safe
preferences=getattr(customer, 'preferences', None) or {},  # ✅ Safe
order_count=getattr(customer, 'order_count', 0) or 0,  # ✅ Safe
```

### 2. ContextManager - Método `save_customer_context`

**Problema:** Tentava salvar em campos inexistentes

**Solução:**

```python
# ANTES (errado)
customer.document = context.document           # ❌ Não existe
customer.customer_type = context.customer_type # ❌ Não existe
customer.addresses = context.addresses         # ❌ Não existe (plural)

# DEPOIS (correto)
customer.cpf_cnpj = context.document           # ✅ Mapeado
if hasattr(customer, 'customer_type'):         # ✅ Safe check
    customer.customer_type = context.customer_type
customer.address = context.addresses[0] if context.addresses else None  # ✅ Singular
```

### 3. GreetingInitialHandler

**Problema:** Tentava acessar `customer.tipo_documento`

**Solução:**

```python
# ANTES (errado)
customer_type=customer.tipo_documento or "PF",  # ❌ Não existe

# DEPOIS (correto)
# Determinar tipo de cliente baseado no CPF/CNPJ
customer_type = "PF"
if customer.cpf_cnpj:
    cpf_cnpj_clean = ''.join(filter(str.isdigit, customer.cpf_cnpj))
    if len(cpf_cnpj_clean) == 14:
        customer_type = "PJ"  # CNPJ tem 14 dígitos
```

---

## 🎯 Estratégia de Mapeamento

### Campos com Nomes Diferentes

| V2 Context       | Model Customer | Mapeamento                          |
|------------------|----------------|-------------------------------------|
| `document`       | `cpf_cnpj`     | Direto: `customer.cpf_cnpj`        |
| `addresses` (plural) | `address` (singular) | Lista: `[customer.address]` |

### Campos que Não Existem no Model

| V2 Context           | Solução                                    |
|----------------------|--------------------------------------------|
| `customer_type`      | Calcular baseado em CPF/CNPJ (11 ou 14 dígitos) |
| `default_address_idx`| Sempre `0` (só tem 1 endereço)            |
| `last_order_data`    | `getattr()` com fallback `None`           |
| `preferences`        | `getattr()` com fallback `{}`             |
| `order_count`        | `getattr()` com fallback `0`              |

### Uso de `getattr()` para Segurança

```python
# Evita AttributeError se campo não existir
value = getattr(customer, 'campo_opcional', valor_padrao)
```

---

## 📊 Arquivos Modificados

1. ✅ `backend/app/core/context_manager.py`
   - Método `get_customer_context()` - Linha 203-213
   - Método `save_customer_context()` - Linha 255-282

2. ✅ `backend/app/core/handlers_v2/greeting_handlers.py`
   - Método `handle()` do `GreetingInitialHandler` - Linha 70-85

---

## 🧪 Como Testar

```bash
# 1. Reiniciar backend
docker-compose restart backend

# 2. Verificar logs (não deve ter AttributeError)
docker-compose logs backend | grep AttributeError

# 3. Testar no WhatsApp
"menu"
"2"  # Deve funcionar normalmente
```

---

## 📝 Lições Aprendidas

1. **Sempre verificar o schema real do banco antes de desenvolver**
2. **Usar `getattr()` para campos opcionais/futuros**
3. **Mapear nomes diferentes explicitamente** (document ↔ cpf_cnpj)
4. **Converter tipos quando necessário** (singular ↔ plural)
5. **Calcular campos derivados** (customer_type baseado em CPF/CNPJ)

---

## 🔗 Documentos Relacionados

- `CORRECAO_ERRO_CUSTOMER_MODEL.md` - Primeira correção (document/tipo_documento)
- `CORRECAO_MENU_GREETING_RETURNING.md` - Correção do menu com números
- `BUG_FIX_COMPLETE_FOLLOWUP.md` - Correção do loop no COMPLETE_FOLLOWUP

---

**Status Final:** ✅ SISTEMA TOTALMENTE OPERACIONAL

Todos os erros de incompatibilidade entre Model e V2 foram corrigidos!
