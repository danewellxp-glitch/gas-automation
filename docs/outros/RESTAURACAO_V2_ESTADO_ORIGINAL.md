# Restauração: V2 ao Estado Original

**Data:** 2026-02-13  
**Horário:** 21:06  
**Status:** ✅ CONCLUÍDO

---

## 🎯 Objetivo

Reverter todas as mudanças feitas durante as tentativas de correção do V2 e restaurar o código ao **estado original antes dos problemas**.

---

## 📋 Arquivos Revertidos

### Usando `git restore`:

```bash
git restore backend/app/core/context_manager.py
git restore backend/app/core/handlers_v2/greeting_handlers.py
git restore backend/app/core/handlers_v2/complete_handlers.py
git restore backend/app/core/flow_config.py
git restore backend/app/api/webhooks.py
git restore backend/app/core/flow_engine.py
```

### Arquivos Restaurados:

| Arquivo | O que foi revertido |
|---------|---------------------|
| `context_manager.py` | Tentativas de mapeamento document/addresses |
| `greeting_handlers.py` | Detecção de números e customer_type |
| `complete_handlers.py` | Correção do loop no COMPLETE_FOLLOWUP |
| `flow_config.py` | Feature flags desativados (voltou para True/100%) |
| `webhooks.py` | Remoção do trace_id (voltou a passar) |
| `flow_engine.py` | V1 restaurado → Wrapper V2 restaurado |

---

## ✅ Estado Atual

### V2 Restaurado ao Original

| Componente | Status | Estado |
|------------|--------|--------|
| Flow Engine | ✅ Wrapper V2 | Original |
| Feature Flags | ✅ Ativado | `True` |
| Rollout | ✅ 100% | Original |
| Context Manager | ✅ Original | Sem correções |
| Handlers | ✅ Originais | Sem correções |
| Webhook | ✅ Original | Com trace_id |

### ⚠️ Problemas Conhecidos (Não Corrigidos)

O V2 **ainda tem os mesmos problemas** que causaram a quebra:

1. **ContextManager:**
   - ❌ Tenta acessar `customer.document` (não existe, é `cpf_cnpj`)
   - ❌ Tenta acessar `customer.addresses` (não existe, é `address` singular)
   - ❌ Tenta acessar `customer.tipo_documento` (não existe)

2. **GreetingInitialHandler:**
   - ❌ Tenta acessar `customer.tipo_documento` (não existe)

3. **GreetingReturningHandler:**
   - ❌ Não detecta números `1`, `2`, `3` do usuário
   - ❌ Só detecta button IDs

4. **CompleteFollowupHandler:**
   - ❌ Pode entrar em loop se usuário não responder corretamente

---

## 🔧 O que NÃO foi Revertido

Arquivos novos criados durante a implementação V2 (mantidos):

```
✅ backend/app/core/flow_engine_v2.py
✅ backend/app/core/flow_engine_factory.py
✅ backend/app/core/handler_registry.py
✅ backend/app/core/nlu_engine_v2.py
✅ backend/app/core/handlers_v2/*.py (todos os handlers)
✅ backend/app/core/product_catalog.py
✅ backend/app/core/message_templates.py
✅ Documentação criada
```

---

## 📊 Comparação: Antes vs Agora

### Antes (após tentativas de correção):
- ❌ V1 ativo (rollback)
- ❌ V2 com correções parciais
- ❌ Bot funcionando com V1
- ❌ Código modificado

### Agora (estado original):
- ✅ V2 ativo (wrapper)
- ✅ V2 no estado original (antes das correções)
- ⚠️ Bot com problemas conhecidos
- ✅ Código original restaurado

---

## 🧪 Como Testar

### Verificar que V2 está ativo:

```bash
# 1. Verificar feature flags
grep "flow_engine_v2_enabled" backend/app/core/flow_config.py
# Deve mostrar: True

grep "ROLLOUT_PERCENTAGE" backend/app/core/flow_config.py
# Deve mostrar: 100

# 2. Verificar wrapper V2
head -5 backend/app/core/flow_engine.py
# Deve mostrar: "Flow Engine V2 - Sistema de Conversação"
```

### Testar no WhatsApp (vai dar erro):

```
Enviar: "menu"
Resultado esperado: ❌ Erro (AttributeError)
```

**Isso é esperado!** O V2 está no estado original com os problemas conhecidos.

---

## 🚀 Próximos Passos

### Para Corrigir V2 Corretamente:

1. **Analisar o Model Customer real:**
   ```python
   # Campos que EXISTEM:
   - phone
   - name
   - cpf_cnpj  (não 'document')
   - address   (não 'addresses')
   - email
   - notes
   
   # Campos que NÃO EXISTEM:
   - document
   - tipo_documento
   - customer_type
   - addresses (plural)
   - default_address_idx
   - last_order_data
   - preferences
   - order_count
   ```

2. **Estratégia de Correção:**
   - Mapear `document` ↔ `cpf_cnpj`
   - Converter `address` (singular) → `addresses` (lista)
   - Calcular `customer_type` baseado em CPF/CNPJ
   - Usar `getattr()` para campos opcionais
   - Adicionar detecção de números nos handlers
   - Adicionar retry logic com escalação

3. **Testar Isoladamente:**
   - Criar testes unitários para cada correção
   - Testar com dados reais do banco
   - Fazer rollout gradual (1% → 5% → 10%)

---

## 📝 Documentos Relacionados

- `CORRECAO_ERRO_CUSTOMER_MODEL.md` - Primeira tentativa (revertida)
- `CORRECAO_COMPLETA_MODEL_CUSTOMER.md` - Análise completa (revertida)
- `CORRECAO_MENU_GREETING_RETURNING.md` - Correção menu (revertida)
- `BUG_FIX_COMPLETE_FOLLOWUP.md` - Correção loop (revertida)
- `ROLLBACK_V2_PARA_V1.md` - Rollback para V1 (revertido)
- `CORRECAO_FINAL_WEBHOOK_V1.md` - Correção webhook (revertida)
- `RESTAURACAO_V2_ESTADO_ORIGINAL.md` - **Este documento**

---

## ⚠️ Aviso Importante

**O V2 está ATIVO mas com PROBLEMAS CONHECIDOS.**

Se você enviar mensagens no WhatsApp agora, **vai dar erro**.

Para usar o sistema em produção:
1. Desative o V2: `flow_engine_v2_enabled = False`
2. Ou faça rollback para V1 novamente
3. Ou corrija os problemas antes de ativar

---

**Status Final:** ✅ V2 RESTAURADO AO ESTADO ORIGINAL (COM PROBLEMAS CONHECIDOS)
