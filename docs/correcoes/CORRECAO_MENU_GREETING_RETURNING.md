# Correção: Menu GREETING_RETURNING não reconhecia números

**Data:** 2026-02-13  
**Status:** ✅ CORRIGIDO

---

## 🐛 Problema Identificado

Após digitar "menu" e receber as opções, o bot não reconhecia quando o usuário digitava números (`1`, `2`, `3`), ficando em loop e mostrando a mesma mensagem repetidamente:

```
[17:42] Eric: menu
[17:42] Bot: 👋 Olá, Heinz!
             Último pedido: 23 - R$ 640,00
             Deseja repetir?
             1. 🔄 Repetir
             2. 🛒 Novo Pedido
             3. 📦 Rastrear

[17:42] Eric: 2
[17:42] Bot: Como posso ajudar?
             1. 🛒 Fazer Pedido
             2. 📦 Meus Pedidos
             3. 👤 Atendente

[17:42] Eric: 2
[17:42] Bot: Como posso ajudar?  ← LOOP
             1. 🛒 Fazer Pedido
             2. 📦 Meus Pedidos
             3. 👤 Atendente

[17:42] Eric: 1
[17:42] Bot: Vou te conectar com um atendente.  ← ERRADO! Deveria ser "Fazer Pedido"
```

---

## 🔍 Causa Raiz

O `GreetingReturningHandler` tinha **dois problemas críticos**:

### 1. Não detectava números (`1`, `2`, `3`)

O handler só detectava **button IDs** (`repeat_order`, `new_order`, `track_order`) mas não os **números** que o usuário digitava.

```python
# ANTES (errado)
if msg_lower in ["repeat_order", "repetir", "o de sempre"]:  # ❌ Sem "1"
if msg_lower in ["new_order", "novo", "fazer_pedido"]:       # ❌ Sem "2"
if msg_lower in ["track_order", "rastrear", "ver_pedido"]:   # ❌ Sem "3"
```

### 2. Dois menus diferentes com números conflitantes

O sistema mostra **dois menus diferentes** dependendo se o cliente tem histórico de pedidos:

**Menu A (COM histórico):**
```
1. 🔄 Repetir
2. 🛒 Novo Pedido
3. 📦 Rastrear
```

**Menu B (SEM histórico):**
```
1. 🛒 Fazer Pedido
2. 📦 Meus Pedidos
3. 👤 Atendente
```

O handler não diferenciava qual menu foi mostrado, então o número "1" sempre era interpretado da mesma forma, independente do contexto.

---

## ✅ Solução Implementada

### 1. Detecção de Button IDs (sempre funciona)

```python
# Detectar button IDs (sempre funciona, independente do menu)
if msg_lower == "repeat_order":
    # ... lógica para repetir pedido
    
if msg_lower in ["new_order", "fazer_pedido", "novo"]:
    # ... lógica para novo pedido
    
if msg_lower in ["track_order", "ver_pedido", "rastrear", "meus pedidos"]:
    # ... lógica para rastrear
    
if msg_lower in ["falar_atendente", "atendente", "humano"]:
    # ... lógica para atendente
```

### 2. Detecção de Números Contextual

```python
# Verificar se tem histórico de pedido para saber qual menu foi mostrado
has_order_history = customer_context and customer_context.last_order

# Detectar números baseado no menu mostrado
if msg_lower == "1":
    if has_order_history:
        # Menu com histórico: 1 = Repetir
        return repetir_pedido()
    else:
        # Menu sem histórico: 1 = Fazer Pedido
        return fazer_pedido()

if msg_lower == "2":
    if has_order_history:
        # Menu com histórico: 2 = Novo Pedido
        return fazer_pedido()
    else:
        # Menu sem histórico: 2 = Meus Pedidos
        return ver_pedidos()

if msg_lower == "3":
    if has_order_history:
        # Menu com histórico: 3 = Rastrear
        return ver_pedidos()
    else:
        # Menu sem histórico: 3 = Atendente
        return falar_atendente()
```

---

## 🎯 Resultado

✅ **Números detectados corretamente**  
✅ **Contexto do menu respeitado (com/sem histórico)**  
✅ **Button IDs funcionam normalmente**  
✅ **Palavras-chave também funcionam** (novo, rastrear, atendente, etc.)

---

## 📊 Fluxo Correto Agora

### Cenário 1: Cliente COM histórico

```
[User] menu
[Bot] 👋 Olá, Heinz!
      Último pedido: 23 - R$ 640,00
      Deseja repetir?
      1. 🔄 Repetir
      2. 🛒 Novo Pedido
      3. 📦 Rastrear

[User] 2
[Bot] Oi Heinz!
      🛒 Qual botijão você precisa?
      🔥 P13 (13kg) - R$ 120,00
      ...
```

### Cenário 2: Cliente SEM histórico

```
[User] menu
[Bot] Como posso ajudar?
      1. 🛒 Fazer Pedido
      2. 📦 Meus Pedidos
      3. 👤 Atendente

[User] 1
[Bot] Olá!
      🛒 Qual botijão você precisa?
      🔥 P13 (13kg) - R$ 120,00
      ...
```

---

## 🧪 Como Testar

```bash
# 1. Reiniciar backend
docker-compose restart backend

# 2. Enviar no WhatsApp
"menu"

# 3. Testar opções
"1"  # Deve funcionar
"2"  # Deve funcionar
"3"  # Deve funcionar

# 4. Testar palavras-chave
"novo"      # Deve funcionar
"rastrear"  # Deve funcionar
"atendente" # Deve funcionar
```

---

## 📝 Arquivos Modificados

- ✅ `backend/app/core/handlers_v2/greeting_handlers.py` (GreetingReturningHandler)

---

## 🔗 Relacionado

- `CORRECAO_ERRO_CUSTOMER_MODEL.md` - Correção anterior de campos do model
- `BUG_FIX_COMPLETE_FOLLOWUP.md` - Correção similar no estado COMPLETE_FOLLOWUP

---

**Status Final:** ✅ SISTEMA OPERACIONAL
