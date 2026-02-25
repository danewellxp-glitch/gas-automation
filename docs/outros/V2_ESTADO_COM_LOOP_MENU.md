# V2: Estado com Loop no Menu

**Data:** 2026-02-13  
**Horário:** 21:10  
**Status:** ✅ APLICADO

---

## 🎯 Objetivo

Restaurar o V2 para o estado onde:
- ✅ **Não tem erros de AttributeError** (corrigidos)
- ⚠️ **Tem problema de loop no menu** (não corrigido ainda)

Este é o estado intermediário onde o bot funciona mas fica em loop quando o usuário digita números no menu.

---

## ✅ Correções Aplicadas

### 1. ContextManager - Mapeamento de Campos

**Arquivo:** `backend/app/core/context_manager.py`

#### GET (carregar contexto):
```python
# Mapear campos do Model para Context
document=customer.cpf_cnpj,  # Model tem cpf_cnpj, não document
addresses=[customer.address] if customer.address else [],  # Converter singular para lista
customer_type=getattr(customer, 'customer_type', None) or "PF",  # Safe access
```

#### SAVE (salvar contexto):
```python
# Mapear campos do Context para Model
customer.cpf_cnpj = context.document  # Reverter mapeamento
customer.address = context.addresses[0] if context.addresses else None  # Pegar primeiro da lista
```

### 2. GreetingInitialHandler - Calcular customer_type

**Arquivo:** `backend/app/core/handlers_v2/greeting_handlers.py`

```python
# Determinar tipo de cliente baseado no CPF/CNPJ
customer_type = "PF"
if customer.cpf_cnpj:
    cpf_cnpj_clean = ''.join(filter(str.isdigit, customer.cpf_cnpj))
    if len(cpf_cnpj_clean) == 14:
        customer_type = "PJ"  # CNPJ tem 14 dígitos
```

---

## ⚠️ Problema Conhecido (NÃO Corrigido)

### Loop no Menu após digitar "menu"

**Comportamento:**
```
[User] menu
[Bot] 👋 Olá, Heinz!
      Último pedido: 23 - R$ 640,00
      Deseja repetir?
      1. 🔄 Repetir
      2. 🛒 Novo Pedido
      3. 📦 Rastrear

[User] 2
[Bot] Como posso ajudar?
      1. 🛒 Fazer Pedido
      2. 📦 Meus Pedidos
      3. 👤 Atendente

[User] 2  ← LOOP AQUI
[Bot] Como posso ajudar?
      1. 🛒 Fazer Pedido
      2. 📦 Meus Pedidos
      3. 👤 Atendente
```

**Causa:**
O `GreetingReturningHandler` não detecta números (`1`, `2`, `3`), apenas button IDs (`repeat_order`, `new_order`, `track_order`).

**Arquivo com problema:**
`backend/app/core/handlers_v2/greeting_handlers.py` - Classe `GreetingReturningHandler`

---

## 📊 Estado Atual

| Componente | Status | Observação |
|------------|--------|------------|
| AttributeError (document) | ✅ Corrigido | Mapeado para cpf_cnpj |
| AttributeError (addresses) | ✅ Corrigido | Convertido singular→plural |
| AttributeError (tipo_documento) | ✅ Corrigido | Calculado baseado em CPF/CNPJ |
| Loop no menu | ❌ Não corrigido | Handler não detecta números |
| V2 Ativo | ✅ Sim | 100% rollout |
| Backend | ✅ Rodando | Sem erros de AttributeError |

---

## 🧪 Como Testar

### Teste 1: Verificar que não tem AttributeError

```bash
# Enviar mensagem no WhatsApp
"menu"

# Verificar logs (não deve ter AttributeError)
docker-compose logs backend | grep AttributeError

# Resultado esperado: Nenhum erro
```

### Teste 2: Reproduzir o loop

```
[WhatsApp]
1. Enviar: "menu"
2. Bot responde com menu
3. Enviar: "2"
4. Bot responde com outro menu
5. Enviar: "2" novamente
6. Bot responde com MESMO menu (LOOP) ← Problema aqui
```

---

## 🔧 Como Corrigir o Loop (Próximo Passo)

Para corrigir o loop no menu, é necessário modificar `GreetingReturningHandler`:

```python
# backend/app/core/handlers_v2/greeting_handlers.py

class GreetingReturningHandler(BaseHandler):
    async def handle(...):
        msg_lower = message.lower().strip()
        
        # Verificar se tem histórico
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
        
        # ... etc
```

---

## 📝 Arquivos Modificados

- ✅ `backend/app/core/context_manager.py`
  - Método `get_customer_context()` - Linhas ~203-213
  - Método `save_customer_context()` - Linhas ~255-280

- ✅ `backend/app/core/handlers_v2/greeting_handlers.py`
  - Classe `GreetingInitialHandler` - Linhas ~70-85

---

## 🔗 Documentos Relacionados

- `CORRECAO_ERRO_CUSTOMER_MODEL.md` - Primeira tentativa de correção
- `CORRECAO_COMPLETA_MODEL_CUSTOMER.md` - Análise completa dos problemas
- `CORRECAO_MENU_GREETING_RETURNING.md` - Solução para o loop (não aplicada ainda)
- `RESTAURACAO_V2_ESTADO_ORIGINAL.md` - Estado original (antes destas correções)
- `V2_ESTADO_COM_LOOP_MENU.md` - **Este documento** (estado atual)

---

## ⚠️ Aviso

**O bot está funcionando mas tem o problema do loop no menu.**

Para uso em produção:
1. ✅ Pode usar para testes básicos
2. ⚠️ Usuários vão encontrar o loop se digitarem números
3. 🔧 Recomendado: Aplicar correção do loop antes de produção

---

**Status Final:** ✅ V2 ATIVO COM CORREÇÕES PARCIAIS (SEM AttributeError, COM LOOP NO MENU)
