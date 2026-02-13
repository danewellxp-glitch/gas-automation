# 🚨 PROBLEMA IDENTIFICADO - Pipeline Quebrado

**Data:** 13 de Fevereiro de 2026  
**Status:** 🔴 CRÍTICO

---

## 📊 DIAGNÓSTICO COMPLETO

### ❌ PROBLEMA #1: WAHA Não Está Enviando Webhooks

**Evidência:**
- Nenhum POST para `/webhooks/waha` nos logs
- Comando `grep -E "POST.*waha|/webhooks/waha"` retorna vazio

**Impacto:**
- Mensagens não chegam via webhook
- Sistema depende 100% do WAHA Poller (fallback)

**Causa Provável:**
- WAHA não está configurado para enviar webhooks para o backend
- URL do webhook pode estar incorreta no WAHA
- WAHA pode estar com problemas de configuração

---

### ❌ PROBLEMA #2: WAHA Poller Não Usa Redis Stream

**Evidência:**
- Poller chama `process_whatsapp_message` DIRETAMENTE (linha 263 de `waha_poller.py`)
- Não adiciona mensagens ao `stream:messages`
- Consumer não recebe mensagens do stream

**Código Problemático:**
```python
# waha_poller.py:263
await process_whatsapp_message(
    message,
    original_chat_id=original_chat_id,
)
```

**Impacto:**
- Mensagens são processadas diretamente, sem passar pelo stream
- Consumer não tem mensagens para processar
- Logs estruturados não aparecem porque não passam pelo webhook

---

### ❌ PROBLEMA #3: Trace ID Incorreto

**Evidência:**
- Trace ID nos logs: `trace-false_71`
- Deveria ser: `trace-{uuid}` (ex: `trace-a1b2c3d4e5f6`)

**Causa:**
- `structured_logging.py:141` gera trace_id a partir dos primeiros 8 caracteres do message_id
- `MessageContextManager` não recebe trace_id correto do Poller

**Código Problemático:**
```python
# structured_logging.py:141
self.trace_id = trace_id or (f"trace-{message_id[:8]}" if message_id else None)
```

**Impacto:**
- Todos os trace_ids são iguais (`trace-false_71`)
- Impossível rastrear mensagens individualmente
- Logs não podem ser correlacionados

---

### ❌ PROBLEMA #4: Todas as Mensagens Marcadas como Duplicadas

**Evidência:**
- Todas as mensagens têm `is_duplicate=True`
- Mensagens são descartadas antes de serem processadas

**Causa Provável:**
- Dedup está marcando mensagens como processadas incorretamente
- Pode ser problema com message_id ou com Redis

---

### ❌ PROBLEMA #5: Consumer Parando Imediatamente

**Evidência:**
- Logs mostram: `[StreamConsumer] Consumer iniciado` → logo depois `[StreamConsumer] Consumer parado`
- Consumer para imediatamente após iniciar

**Causa Provável:**
- Loop está saindo por algum motivo
- Pode ser `asyncio.CancelledError` ou `self.running = False`

---

## 🔧 SOLUÇÕES NECESSÁRIAS

### Solução #1: Corrigir WAHA Poller para Usar Stream

**Arquivo:** `backend/app/services/waha_poller.py`

**Mudança Necessária:**
Em vez de chamar `process_whatsapp_message` diretamente, adicionar ao stream:

```python
# ANTES (linha 263):
await process_whatsapp_message(
    message,
    original_chat_id=original_chat_id,
)

# DEPOIS:
# Adicionar ao stream em vez de processar diretamente
message_data = {
    "key": key_data,
    "message": {"conversation": body} if body else None,
    "messageTimestamp": timestamp,
    "pushName": push_name,
}

stream_message_id = await redis_manager.add_message_to_stream(
    message_data=message_data,
    original_chat_id=original_chat_id,
)

if stream_message_id:
    logger.info(f"[Poller] Mensagem adicionada ao stream: {stream_message_id}")
else:
    # Fallback: processar diretamente se stream falhar
    await process_whatsapp_message(
        message,
        original_chat_id=original_chat_id,
    )
```

---

### Solução #2: Corrigir Trace ID no Poller

**Arquivo:** `backend/app/services/waha_poller.py`

**Mudança Necessária:**
Gerar trace_id único antes de processar:

```python
# Adicionar no início de _process_message:
import uuid
trace_id = f"trace-{uuid.uuid4().hex[:12]}"

# Usar MessageContextManager com trace_id:
with MessageContextManager(message_id=msg_id_str, phone=resolved_chat_id, trace_id=trace_id):
    # ... resto do código ...
```

---

### Solução #3: Verificar Configuração do WAHA

**Verificar:**
1. URL do webhook no WAHA está correta?
2. WAHA está configurado para enviar webhooks?
3. Headers de autenticação estão corretos?

**Comando para verificar:**
```bash
# Verificar configuração do WAHA
docker-compose logs waha | grep -i webhook
```

---

### Solução #4: Investigar Por Que Consumer Para

**Verificar:**
1. Por que o loop está saindo?
2. Há algum erro silencioso?
3. `self.running` está sendo setado para False?

**Adicionar logs:**
```python
# No consume loop:
logger.info(f"[CONSUMER_LOOP] running={self.running} iteration={i}")
```

---

## 🎯 PRÓXIMOS PASSOS

1. ✅ **Corrigir WAHA Poller** para usar Redis Stream
2. ✅ **Corrigir Trace ID** no Poller
3. ✅ **Verificar configuração do WAHA** para webhooks
4. ✅ **Investigar Consumer** que está parando
5. ✅ **Testar pipeline completo** após correções

---

## 📝 RESUMO EXECUTIVO

**Problema Principal:**
- WAHA não envia webhooks → Sistema depende do Poller
- Poller não usa Stream → Mensagens processadas diretamente
- Consumer não recebe mensagens → Pipeline quebrado

**Solução Imediata:**
- Modificar Poller para adicionar mensagens ao Stream
- Corrigir Trace ID para ser único
- Verificar configuração do WAHA

**Resultado Esperado:**
- Mensagens chegam ao Stream via Poller
- Consumer processa mensagens do Stream
- Logs estruturados aparecem corretamente
- Pipeline funciona end-to-end
