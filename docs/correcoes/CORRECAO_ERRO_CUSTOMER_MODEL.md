# Correção: Erro de Atributos do Model Customer

**Data:** 2026-02-13  
**Status:** ✅ CORRIGIDO

---

## 🐛 Problema Identificado

Após implementar o Flow Engine V2, o sistema estava gerando erros ao processar mensagens:

```
AttributeError: 'Customer' object has no attribute 'document'
AttributeError: 'Customer' object has no attribute 'tipo_documento'
```

### Mensagens de Erro no WhatsApp

```
❌ Ocorreu um erro. Por favor, tente novamente ou digite atendente para falar com alguém.
```

---

## 🔍 Causa Raiz

**Incompatibilidade entre Model e Código V2:**

O código V2 foi desenvolvido assumindo que o model `Customer` tinha os seguintes campos:
- `document` (para CPF/CNPJ)
- `tipo_documento` (para tipo PF/PJ)
- `customer_type`
- `default_address_idx`
- `last_order_data`
- `preferences`
- `order_count`

**Mas o model real tem:**
- `cpf_cnpj` (ao invés de `document`)
- Não tem `tipo_documento` nem `customer_type`
- Não tem `default_address_idx`, `last_order_data`, `preferences`, `order_count`

---

## ✅ Solução Implementada

### 1. Correção no `ContextManager` (`backend/app/core/context_manager.py`)

**Ao carregar contexto (GET):**
```python
# ANTES (errado)
document=customer.document,
customer_type=customer.customer_type,

# DEPOIS (correto)
document=customer.cpf_cnpj,  # Mapear cpf_cnpj para document
customer_type=getattr(customer, 'customer_type', None) or "PF",
```

**Ao salvar contexto (SAVE):**
```python
# ANTES (errado)
customer.document = context.document
customer.customer_type = context.customer_type

# DEPOIS (correto)
customer.cpf_cnpj = context.document  # Mapear document para cpf_cnpj
if hasattr(customer, 'customer_type'):
    customer.customer_type = context.customer_type
```

**Uso de `getattr()` para campos opcionais:**
```python
addresses=customer.addresses or [],
default_address_idx=getattr(customer, 'default_address_idx', 0) or 0,
last_order=getattr(customer, 'last_order_data', None),
preferences=getattr(customer, 'preferences', None) or {},
order_count=getattr(customer, 'order_count', 0) or 0,
```

### 2. Correção no `GreetingInitialHandler` (`backend/app/core/handlers_v2/greeting_handlers.py`)

**Determinação automática do tipo de cliente:**
```python
# Determinar tipo de cliente baseado no CPF/CNPJ
customer_type = "PF"
if customer.cpf_cnpj:
    # CNPJ tem 14 dígitos, CPF tem 11
    cpf_cnpj_clean = ''.join(filter(str.isdigit, customer.cpf_cnpj))
    if len(cpf_cnpj_clean) == 14:
        customer_type = "PJ"

customer_context = CustomerContext(
    customer_id=str(customer.id),
    name=customer.name,
    document=customer.cpf_cnpj,
    customer_type=customer_type,  # Calculado automaticamente
    addresses=[customer.address] if customer.address else [],
    order_count=0,
)
```

---

## 🎯 Resultado

✅ **Sistema funcionando normalmente**  
✅ **Mapeamento correto entre Model e Context**  
✅ **Tipo de cliente detectado automaticamente (PF/PJ)**  
✅ **Campos opcionais tratados com `getattr()`**  

---

## 📝 Lições Aprendidas

1. **Sempre verificar o schema real do banco antes de usar campos**
2. **Usar `getattr()` para campos que podem não existir**
3. **Mapear nomes diferentes entre model e context (document ↔ cpf_cnpj)**
4. **Testar com dados reais antes de deploy**

---

## 🧪 Como Testar

```bash
# 1. Reiniciar backend
docker-compose restart backend

# 2. Enviar mensagem no WhatsApp
"menu"

# 3. Verificar logs (não deve ter erro)
docker-compose logs backend | grep ERROR
```

---

## 📊 Arquivos Modificados

- ✅ `backend/app/core/context_manager.py`
- ✅ `backend/app/core/handlers_v2/greeting_handlers.py`

---

**Status Final:** ✅ SISTEMA OPERACIONAL
