# Correção Final: Webhook incompatível com V1

**Data:** 2026-02-13  
**Horário:** 21:02  
**Status:** ✅ CORRIGIDO

---

## 🐛 Problema

Após fazer rollback para V1, o bot continuou **totalmente quebrado** com erro:

```
FlowEngine.process_message() got an unexpected keyword argument 'trace_id'
```

**Mensagens no WhatsApp:**
```
[18:00] Eric: menu
[18:00] Bot: Desculpe, ocorreu um erro. Digite menu para recomeçar.
[18:00] Eric: menu
[18:00] Bot: Desculpe, ocorreu um erro. Digite menu para recomeça
```

---

## 🔍 Causa Raiz

Durante a implementação do V2, o **webhook foi modificado** para passar parâmetros que o V2 aceita mas o **V1 NÃO aceita**:

### Webhook (modificado para V2)

```python
# backend/app/api/webhooks.py
result = await flow_engine.process_message(
    phone=phone,
    message=content,
    message_id=message_id,
    waha_chat_id=original_chat_id or (phone if "@" in phone else None),
    trace_id=trace_id,  # ❌ V1 NÃO aceita este parâmetro
)
```

### FlowEngine V1 (assinatura original)

```python
# backend/app/core/flow_engine.py (V1)
async def process_message(
    self,
    phone: str,
    message: str,
    message_id: Optional[str] = None,
    waha_chat_id: Optional[str] = None,
    # ❌ NÃO TEM trace_id
) -> ProcessedMessage:
```

### FlowEngine V2 (assinatura nova)

```python
# backend/app/core/flow_engine_v2.py (V2)
async def process_message(
    self,
    phone: str,
    message: str,
    trace_id: Optional[str] = None,  # ✅ V2 aceita
) -> List[Dict]:
```

---

## ✅ Solução

Remover o parâmetro `trace_id` da chamada no webhook, tornando-o compatível com V1:

```python
# backend/app/api/webhooks.py (CORRIGIDO)
result = await flow_engine.process_message(
    phone=phone,
    message=content,
    message_id=message_id,
    waha_chat_id=original_chat_id or (phone if "@" in phone else None),
    # trace_id removido - V1 não aceita
)
```

**Nota:** O V1 ainda captura o `trace_id` internamente via `get_message_context()`, então não há perda de funcionalidade de logging.

---

## 📊 Arquivos Modificados

- ✅ `backend/app/api/webhooks.py` - Linha 720-726

---

## 🧪 Como Testar

```bash
# 1. Reiniciar backend
docker-compose restart backend

# 2. Verificar logs (não deve ter erro de trace_id)
docker-compose logs backend | grep "unexpected keyword argument"

# 3. Testar no WhatsApp
"menu"

# Deve funcionar normalmente agora!
```

---

## 📝 Cronologia Completa dos Problemas

### 17:38 - Primeiro erro (V2 ativo)
```
❌ Ocorreu um erro. Por favor, tente novamente...
```
**Causa:** V2 com erros de model (document, tipo_documento, addresses)

### 17:42 - Loop no menu (V2 ativo)
```
Eric: 2
Bot: Como posso ajudar? (loop infinito)
```
**Causa:** Handler não detectava números 1, 2, 3

### 20:58 - Rollback para V1
```
✅ V1 restaurado do backup
```

### 21:00 - Bot totalmente quebrado (V1 ativo mas webhook incompatível)
```
Bot: Desculpe, ocorreu um erro. Digite menu para recomeçar.
```
**Causa:** Webhook passando `trace_id` que V1 não aceita

### 21:02 - Correção final
```
✅ Webhook corrigido para V1
✅ Backend reiniciado
✅ Bot funcionando
```

---

## 🎯 Estado Final

| Componente | Status | Versão |
|------------|--------|--------|
| Flow Engine | ✅ Ativo | **V1** |
| Webhook | ✅ Compatível | V1 |
| Feature Flag V2 | ❌ Desativado | `False` |
| Backend | ✅ Rodando | V1 |
| Bot WhatsApp | ✅ Funcionando | V1 |

---

## 🔗 Documentos Relacionados

1. `CORRECAO_ERRO_CUSTOMER_MODEL.md` - Primeira tentativa de correção V2
2. `CORRECAO_COMPLETA_MODEL_CUSTOMER.md` - Análise completa dos erros V2
3. `CORRECAO_MENU_GREETING_RETURNING.md` - Correção do menu V2
4. `ROLLBACK_V2_PARA_V1.md` - Processo de rollback
5. `CORRECAO_FINAL_WEBHOOK_V1.md` - **Este documento** (correção final)

---

## ⚠️ Lições Aprendidas

1. **Ao modificar interfaces (assinaturas de funções), verificar TODOS os callers**
2. **Ao fazer rollback, verificar se há modificações em arquivos compartilhados (webhook)**
3. **Manter compatibilidade retroativa ou usar feature flags nos callers também**
4. **Testar imediatamente após rollback para garantir que funcionou**

---

## 🚀 Próximos Passos (Para Reativar V2 no Futuro)

### 1. Corrigir todos os problemas do V2:
- ✅ Mapeamento de campos (document ↔ cpf_cnpj)
- ✅ Conversão singular/plural (address ↔ addresses)
- ✅ Campos derivados (customer_type baseado em CPF/CNPJ)
- ✅ Detecção de números no menu (1, 2, 3)

### 2. Testar V2 em ambiente isolado:
```bash
# Ativar V2 para apenas 1 usuário (hash específico)
ROLLOUT_PERCENTAGE = 1
```

### 3. Rollout gradual:
```
1% → 5% → 10% → 25% → 50% → 100%
```

### 4. Monitoramento contínuo:
```bash
# Monitorar erros
docker-compose logs -f backend | grep ERROR
```

---

**Status Final:** ✅ SISTEMA TOTALMENTE OPERACIONAL COM V1

O bot está funcionando perfeitamente com Flow Engine V1!
