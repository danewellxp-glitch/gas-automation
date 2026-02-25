# V2: Estado com Loop após Confirmar Pedido

**Data:** 2026-02-13  
**Horário:** 21:48  
**Status:** ✅ APLICADO

---

## 🎯 Estado Atual

Sistema V2 com as seguintes características:

### ✅ Correções Mantidas:

1. **ContextManager** - Mapeamento de campos funcionando
   - `document` ↔ `cpf_cnpj`
   - `addresses` ↔ `address` (singular)
   - Uso de `getattr()` para campos opcionais

2. **GreetingInitialHandler** - Cálculo de customer_type
   - Detecta automaticamente PF/PJ baseado em CPF/CNPJ

3. **GreetingReturningHandler** - Menu principal corrigido
   - ✅ Detecta números `1`, `2`, `3`
   - ✅ Interpretação contextual baseada em histórico
   - ✅ Consulta banco para verificar histórico real

4. **TrackingOptionsHandler** - Menu após ver pedidos corrigido
   - ✅ Detecta números `1`, `2`

5. **TrackingStatusHandler** - OrderStatus correto
   - ✅ Usa PAID, PREPARING, DISPATCHED, DELIVERED

---

### ⚠️ Problema Mantido (Loop):

**CompleteFollowupHandler** - Loop após confirmar pedido

**Comportamento:**
```
[User] (confirma pedido)
[Bot] PEDIDO #23 CONFIRMADO!
      ...
      Posso ajudar com mais alguma coisa?
      1. 📦 Ver Status
      2. 🛒 Novo Pedido
      3. 👤 Atendente

[User] 2
[Bot] Posso ajudar com mais alguma coisa? ← LOOP
      1. 📦 Ver Status
      2. 🛒 Novo Pedido
      3. 👤 Atendente
```

**Causa:**
O `CompleteFollowupHandler` não detecta números `1`, `2`, `3`. Apenas detecta palavras-chave usando `any(word in msg_lower ...)`.

---

## 📊 Status dos Handlers

| Handler | Detecta Números? | Status |
|---------|------------------|--------|
| GreetingReturningHandler | ✅ Sim (1, 2, 3) | ✅ Funcional |
| TrackingOptionsHandler | ✅ Sim (1, 2) | ✅ Funcional |
| CompleteFollowupHandler | ❌ Não | ⚠️ Loop |

---

## 🧪 Como Reproduzir o Loop

```bash
# 1. Fazer um pedido completo até confirmação
[WhatsApp] menu
[WhatsApp] 2 (novo pedido)
[WhatsApp] 1 (P13)
[WhatsApp] 2 (quantidade)
[WhatsApp] troca
[WhatsApp] (confirmar endereço)
[WhatsApp] 1 (dinheiro)
[WhatsApp] sim (confirmar)

# 2. Bot confirma o pedido e pergunta:
[Bot] Posso ajudar com mais alguma coisa?
      1. 📦 Ver Status
      2. 🛒 Novo Pedido
      3. 👤 Atendente

# 3. Testar opções:
[WhatsApp] 2
[Bot] Posso ajudar com mais alguma coisa? ← LOOP (não reconhece o "2")

[WhatsApp] 1
[Bot] Posso ajudar com mais alguma coisa? ← LOOP (não reconhece o "1")

[WhatsApp] 3
[Bot] Posso ajudar com mais alguma coisa? ← LOOP (não reconhece o "3")

# Apenas palavras-chave funcionam:
[WhatsApp] novo
[Bot] 🛒 Vamos fazer um novo pedido! ✅ (funciona)
```

---

## 🔧 Como Corrigir (Quando Necessário)

Para corrigir o loop, adicionar no `CompleteFollowupHandler`:

```python
# Detectar números
if msg_lower == "1":
    # Ver Status
    return tracking_status()

if msg_lower == "2":
    # Novo Pedido
    return novo_pedido()

if msg_lower == "3":
    # Atendente
    return atendente()
```

---

## 📝 Arquivos no Estado Atual

### Corrigidos (mantidos):
- ✅ `backend/app/core/context_manager.py`
- ✅ `backend/app/core/handlers_v2/greeting_handlers.py`
  - `GreetingInitialHandler`
  - `GreetingReturningHandler`
- ✅ `backend/app/core/handlers_v2/support_handlers.py`
  - `TrackingStatusHandler` (OrderStatus)
  - `TrackingOptionsHandler` (números)

### Com Loop (revertido):
- ⚠️ `backend/app/core/handlers_v2/complete_handlers.py`
  - `CompleteFollowupHandler` (não detecta números)

---

## 🎯 Fluxos

### ✅ Funciona:
- Menu principal (números 1, 2, 3) ✅
- Ver pedidos → opções (números 1, 2) ✅
- Todos os AttributeError corrigidos ✅

### ⚠️ Com Loop:
- Após confirmar pedido → opções (números 1, 2, 3) ❌

---

**Status Final:** ✅ V2 COM LOOP APENAS NO COMPLETE_FOLLOWUP

Este é o estado que você pediu! O bot funciona normalmente, mas tem loop após confirmar pedido.
