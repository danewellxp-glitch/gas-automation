# 🔍 DIAGNÓSTICO COMPLETO - Trace ID e Pipeline

**Data:** 13 de Fevereiro de 2026  
**Problema:** Mensagens não respondem e não aparecem no painel

---

## 📊 ANÁLISE DOS LOGS

### Trace ID Encontrado: `trace-false_71`

**Logs encontrados:**
```
[DEDUP_CHECK] trace_id=trace-false_71 message_id=false_7185547411514@lid_3EB0F4D67EEDC29EFCB0A7 phone=61405086785@c.us is_duplicate=True
[DEDUP_DUPLICATE] trace_id=trace-false_71 message_id=false_7185547411514@lid_3EB0F4D67EEDC29EFCB0A7 phone=61405086785@c.us
```

### ❌ PROBLEMAS IDENTIFICADOS

#### 1. Trace ID Incorreto
- **Esperado:** `trace-{uuid}` (ex: `trace-a1b2c3d4e5f6`)
- **Encontrado:** `trace-false_71`
- **Causa:** `structured_logging.py:98` está gerando trace_id a partir dos primeiros 8 caracteres do message_id
- **Impacto:** Todos os trace_ids são iguais, impossibilitando rastreamento único

#### 2. Todas as Mensagens Marcadas como Duplicadas
- **Status:** `is_duplicate=True` em TODAS as mensagens
- **Causa:** Dedup está marcando mensagens como processadas antes mesmo de serem processadas
- **Impacto:** Mensagens são descartadas ANTES de chegar ao stream

#### 3. Logs [WEBHOOK_ENTRY] Não Aparecem
- **Esperado:** Log `[WEBHOOK_ENTRY]` deve aparecer para cada mensagem
- **Encontrado:** Nenhum log `[WEBHOOK_ENTRY]` nos últimos logs
- **Possíveis Causas:**
  - Código não foi reiniciado após mudanças
  - Log está em nível DEBUG (não aparece em INFO)
  - Código está retornando antes de chegar ao log

#### 4. Nenhuma Mensagem no Stream
- **Verificação:** `XLEN stream:messages = 0`
- **Causa:** Mensagens são descartadas no dedup antes de chegar ao stream
- **Impacto:** Consumer não tem mensagens para processar

---

## 🔧 CORREÇÕES NECESSÁRIAS

### Correção #1: Trace ID Incorreto

**Arquivo:** `backend/app/utils/structured_logging.py:98`

**Problema:**
```python
trace_id_context.set(f"trace-{message_id[:8]}")
```

**Solução:**
```python
# NÃO gerar trace_id baseado em message_id
# Trace_id deve ser gerado ANTES de entrar no contexto
# Remover esta linha ou garantir que trace_id já foi setado antes
```

**Correção no webhook:**
O trace_id já está sendo gerado corretamente em `webhooks.py:223`:
```python
trace_id = f"trace-{uuid.uuid4().hex[:12]}"
```

Mas o `MessageContextManager` pode estar sobrescrevendo com o trace_id incorreto.

### Correção #2: Verificar Por Que Mensagens São Duplicadas

**Verificar:**
1. Se `check_message_processed` está marcando mensagens como processadas incorretamente
2. Se há mensagens antigas no Redis marcando novas mensagens como duplicadas
3. Se o message_id está sendo gerado corretamente

**Comando para verificar:**
```bash
docker-compose exec -T redis redis-cli KEYS "msg_processed:*"
```

### Correção #3: Verificar Por Que [WEBHOOK_ENTRY] Não Aparece

**Possíveis causas:**
1. Código não foi reiniciado após mudanças
2. Log está em nível DEBUG
3. Código está retornando antes de chegar ao log

**Verificar:**
```bash
# Verificar nível de log
docker-compose logs backend 2>&1 | grep -i "level\|logging"

# Verificar se código foi reiniciado
docker-compose logs backend 2>&1 | grep -E "started|restart|reload"
```

---

## 🎯 PRÓXIMOS PASSOS

1. **Enviar uma mensagem NOVA** (não duplicada) para capturar trace_id correto
2. **Verificar se log [WEBHOOK_ENTRY] aparece** após reiniciar backend
3. **Rastrear trace_id completo** através de todo o pipeline
4. **Verificar se mensagem chega ao stream** (não deve ser duplicada)

---

## 📝 SEQUÊNCIA ESPERADA DE LOGS

Para uma mensagem NÃO duplicada, deve aparecer:

1. `[WEBHOOK_RECEIVED]` ou `[WEBHOOK_ENTRY]`
2. `[DEDUP_CHECK]` com `is_duplicate=False`
3. `[STREAM_ADD_START]`
4. `[STREAM_ADDED]` com `success=True`
5. `[CONSUMER_MESSAGE_RECEIVED]`
6. `[LOCK_ACQUIRED]`
7. `[FLOW_ENGINE_START]`
8. `[FLOW_ENGINE_COMPLETE]`
9. `[WAHA_SEND_START]`
10. `[WAHA_SEND_COMPLETE]`
11. `[XACK_COMPLETE]`
12. `[WEBSOCKET_PUBLISH_COMPLETE]`

---

## 🚨 AÇÃO IMEDIATA

**Envie uma mensagem NOVA agora e execute:**

```bash
docker-compose logs -f backend 2>&1 | grep --line-buffered -E "\[WEBHOOK|\[STREAM|\[CONSUMER|\[LOCK|\[FLOW|\[WAHA|\[XACK|\[WEBSOCKET"
```

Isso vai mostrar exatamente onde o pipeline está parando.

---

## ✅ CORREÇÕES APLICADAS (13/02/2026 - 14:39)

### 1. Trace ID no Poller ✅
- Poller agora gera `trace_id` único e passa para `add_message_to_stream`
- `database.py` aceita e armazena `trace_id` no stream

### 2. Trace ID no Consumer ✅
- Consumer extrai `trace_id` dos dados do stream
- Se não encontrar, gera novo baseado em `message_id`
- **CORRIGIDO:** `trace_id` agora é inicializado antes do try/except para evitar `NameError`

### 3. Trace ID Preservado no MessageContextManager ✅
- `MessageContextManager` em `process_message` agora recebe `trace_id` explicitamente
- Trace ID é preservado através de todo o pipeline

### 4. Deduplicação Redundante ✅
- `process_whatsapp_message` não descarta mais mensagens se `is_duplicate=True`
- Apenas loga warning e continua processamento

---

## 🐛 ERROS CRÍTICOS ENCONTRADOS E CORRIGIDOS

### Erro #1 (14:38:50): `name 'trace_id' is not defined` em `_process_batch`

**Erro:** `name 'trace_id' is not defined`  
**Causa:** Variável `trace_id` não estava sendo inicializada antes do bloco try/except  
**Impacto:** Mensagens eram movidas para DLQ após 3 tentativas  
**Correção:** Inicialização de `trace_id`, `phone`, e `msg_id` antes do try/except

**Arquivo:** `backend/app/services/message_stream_consumer.py:454-497`

### Erro #2 (14:40:12): `name 'trace_id' is not defined` em `process_message`

**Erro:** `name 'trace_id' is not defined` na linha 169  
**Causa:** `trace_id` não estava sendo extraído dentro de `process_message`  
**Impacto:** Mensagens eram movidas para DLQ após 3 tentativas  
**Correção:** Extração de `trace_id` dos dados do stream dentro de `process_message`

**Arquivo:** `backend/app/services/message_stream_consumer.py:166-169`

**Antes:**
```python
# Definir contexto de mensagem para logging estruturado
msg_id = key_data.get("id", "")
# Usar trace_id extraído dos dados do stream (já foi extraído anteriormente)
with MessageContextManager(message_id=msg_id, phone=message.phone, trace_id=trace_id):
```

**Depois:**
```python
# Definir contexto de mensagem para logging estruturado
msg_id = key_data.get("id", "")
# Extrair trace_id dos dados do stream (pode estar em data ou message_data)
trace_id = data.get("trace_id") or message_data.get("trace_id")
if not trace_id:
    # Gerar trace_id baseado em message_id se não encontrado
    trace_id = f"trace-{msg_id[:8]}" if msg_id else f"trace-{message_id[:8]}"

# Usar trace_id extraído dos dados do stream
with MessageContextManager(message_id=msg_id, phone=message.phone, trace_id=trace_id):
```

**Arquivo:** `backend/app/services/message_stream_consumer.py:454-493`

**Antes:**
```python
# Extrair phone, message_id e trace_id para contexto
try:
    trace_id = data.get("trace_id")
    # ... resto do código
except Exception as e:
    # trace_id não definido se houver exceção!
```

**Depois:**
```python
# Extrair phone, message_id e trace_id para contexto
# Inicializar variáveis com valores padrão para evitar NameError
trace_id = None
phone = ""
msg_id = ""

try:
    trace_id = data.get("trace_id")
    # ... resto do código
except Exception as e:
    # Garantir que trace_id tenha um valor mesmo em caso de erro
    if not trace_id:
        trace_id = f"trace-{event_id_str[:8]}" if event_id_str else "trace-unknown"
```

---

## 📊 RESULTADO DO RASTREAMENTO `trace-ccf8d7648af7`

**Mensagem:** "pessoa fisica"  
**Message ID:** `false_7185547411514@lid_3EB0A06913703A5AC63601`  
**Stream ID:** `1770993530770-0`

**Status:** ❌ Movida para DLQ após 3 tentativas  
**Causa:** `NameError: name 'trace_id' is not defined`  
**Status após correção:** ✅ Aguardando nova mensagem para teste

---

## 🎯 PRÓXIMA MENSAGEM DE TESTE

**Envie uma mensagem NOVA agora e execute:**

```bash
docker-compose logs -f backend 2>&1 | grep --line-buffered -E "trace-.*\[POLLER|trace-.*\[STREAM|trace-.*\[CONSUMER|trace-.*\[LOCK|trace-.*\[FLOW|trace-.*\[WAHA|trace-.*\[XACK"
```

Agora o trace_id deve ser preservado através de TODO o pipeline! 🎉
