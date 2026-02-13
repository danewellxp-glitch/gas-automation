# 🔍 RASTREAMENTO COMPLETO - Trace ID: `trace-d2cc68b30f29`

**Data:** 13 de Fevereiro de 2026  
**Mensagem:** "ola bom dia"  
**Message ID:** `false_7185547411514@lid_3EB0DF395336A43C76EA21`  
**Phone:** `61405086785@c.us`

---

## 📊 SEQUÊNCIA DE LOGS ENCONTRADA

### ✅ ETAPAS QUE FUNCIONARAM

1. **`[POLLER_MESSAGE_FOUND]`** ✅
   - Trace ID: `trace-d2cc68b30f29` (CORRETO)
   - Timestamp: `2026-02-13 14:32:43`
   - Mensagem encontrada pelo Poller

2. **`[POLLER_STREAM_ADD_START]`** ✅
   - Trace ID: `trace-d2cc68b30f29` (CORRETO)
   - Iniciando adição ao stream

3. **`[CONSUMER_NEW_RECEIVED]`** ✅
   - Consumer recebeu mensagem do stream
   - Count: 1

4. **`[CONSUMER_MESSAGE_RECEIVED]`** ✅
   - Stream ID: `1770993163586-0`
   - **MAS:** Trace ID mudou para `trace-false_71` (INCORRETO!)

5. **`[POLLER_STREAM_ADDED]`** ✅
   - Stream ID: `1770993163586-0`
   - Trace ID: `trace-d2cc68b30f29` (CORRETO)
   - Success: True

### ❌ ETAPAS QUE FALHARAM

6. **`[DEDUP_CHECK]`** ❌
   - Trace ID: `trace-false_71` (INCORRETO - deveria ser `trace-d2cc68b30f29`)
   - **is_duplicate=True** ❌
   - Mensagem marcada como duplicada

7. **`[DEDUP_DUPLICATE]`** ❌
   - Mensagem descartada ANTES de processar
   - Por isso não há logs de [LOCK_ACQUIRED], [FLOW_ENGINE_START], etc.

8. **`[XACK_BEFORE]`** ⚠️
   - XACK feito mesmo com mensagem duplicada
   - Trace ID: `trace-false_71` (INCORRETO)

---

## 🚨 PROBLEMAS IDENTIFICADOS

### Problema #1: Trace ID Perdido no Consumer

**Causa:**
- Trace ID não está sendo incluído nos dados do stream
- Consumer gera novo trace_id incorreto a partir do message_id

**Evidência:**
- Poller: `trace-d2cc68b30f29` ✅
- Consumer: `trace-false_71` ❌

**Correção Aplicada:**
- ✅ Adicionado `trace_id` aos dados do stream
- ✅ Consumer agora extrai `trace_id` dos dados do stream

---

### Problema #2: Mensagem Marcada como Duplicada

**Causa:**
- Mensagem foi processada anteriormente pelo Poller (quando chamava diretamente)
- Dedup marca como processada antes de chegar ao stream
- Quando Consumer processa, já está marcada como duplicada

**Evidência:**
- `is_duplicate=True` em TODAS as mensagens
- Mensagens são descartadas antes de processar

**Solução Necessária:**
- Limpar chaves de dedup antigas no Redis
- OU: Remover dedup de `process_whatsapp_message` (já há dedup no webhook)

---

### Problema #3: Dedup Duplicado

**Causa:**
- Dedup acontece em DOIS lugares:
  1. No webhook (antes de adicionar ao stream) ✅
  2. Em `process_whatsapp_message` (depois de receber do stream) ❌

**Impacto:**
- Mensagens podem ser marcadas como duplicadas duas vezes
- Se mensagem já foi processada antes, sempre será duplicada

**Solução:**
- Remover dedup de `process_whatsapp_message` (já há dedup no webhook)
- OU: Verificar se mensagem já foi processada ANTES de adicionar ao stream

---

## 🎯 ÚLTIMO LOG ENCONTRADO

**Trace ID:** `trace-d2cc68b30f29` (Poller) → `trace-false_71` (Consumer)

**Último log com trace_id correto:**
- `[POLLER_STREAM_ADDED]` - `trace-d2cc68b30f29`

**Último log com trace_id incorreto:**
- `[DEDUP_DUPLICATE]` - `trace-false_71`

**Onde parou:**
- Mensagem foi descartada no dedup dentro de `process_whatsapp_message`
- Não chegou a [LOCK_ACQUIRED], [FLOW_ENGINE_START], [WAHA_SEND_START], etc.

---

## 🔧 CORREÇÕES APLICADAS

1. ✅ Trace ID agora é incluído nos dados do stream
2. ✅ Consumer extrai trace_id dos dados do stream
3. ✅ Logs estruturados adicionados em todas as etapas

**Próximo passo:**
- Remover dedup duplicado de `process_whatsapp_message`
- OU limpar chaves de dedup antigas no Redis

---

## 📝 PRÓXIMA MENSAGEM

**Envie uma mensagem NOVA agora e execute:**

```bash
docker-compose logs -f backend 2>&1 | grep --line-buffered -E "trace-.*\[POLLER|trace-.*\[STREAM|trace-.*\[CONSUMER|trace-.*\[LOCK|trace-.*\[FLOW|trace-.*\[WAHA|trace-.*\[XACK"
```

Isso vai mostrar o trace_id completo através de todo o pipeline.
