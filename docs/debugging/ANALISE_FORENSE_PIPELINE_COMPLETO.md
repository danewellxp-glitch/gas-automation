# 🧠 DEBUGGING ULTRA PROFUNDO – PIPELINE COMPLETO WHATSAPP → STREAM → FLOW → WAHA → WEBSOCKET

**Data:** 13 de Fevereiro de 2026  
**Engenheiro:** SRE + Backend Staff Engineer  
**Objetivo:** Identificar exatamente onde o pipeline está quebrando

---

## 🔴 PROBLEMA REPORTADO

**Sintoma:**
- Robô não responde mensagens no WhatsApp
- Não envia eventos para o painel do atendente

**Arquitetura Atual:**
```
WAHA → /webhooks/waha → deduplicação Redis → XADD stream:messages → 
MessageStreamConsumer (Consumer Group: gas-workers) → Lock por telefone → 
Flow Engine → Order Service → WAHA send → Redis Pub/Sub → WebSocket → Frontend
```

---

## 📊 FASE 1 – INSTRUMENTAÇÃO OBRIGATÓRIA

### 1.1 Logs Estruturados Temporários

**Campos obrigatórios em TODOS os logs:**
- `message_id` - ID único da mensagem WhatsApp
- `trace_id` - ID de rastreamento gerado no webhook
- `phone` - Número de telefone normalizado
- `stream_id` - ID da mensagem no Redis Stream
- `workflow_state` - Estado atual da conversa
- `retry_count` - Número de tentativas
- `step` - Etapa atual do pipeline
- `duration_ms` - Tempo decorrido desde entrada no webhook

### 1.2 Pontos Críticos de Instrumentação

**P1: Entrada no Webhook**
```python
# LOG: [WEBHOOK_ENTRY] trace_id={trace_id} message_id={message_id} phone={phone}
```

**P2: Após Deduplicação**
```python
# LOG: [DEDUP_RESULT] trace_id={trace_id} message_id={message_id} is_duplicate={bool}
```

**P3: Após XADD no Redis**
```python
# LOG: [STREAM_ADDED] trace_id={trace_id} stream_id={stream_id} success={bool}
```

**P4: Antes do XREADGROUP**
```python
# LOG: [CONSUMER_READ_START] trace_id={trace_id} consumer={name} block_ms={block_time}
```

**P5: Ao Receber Mensagem no Consumer**
```python
# LOG: [CONSUMER_MESSAGE_RECEIVED] trace_id={trace_id} stream_id={stream_id} consumer={name}
```

**P6: Ao Adquirir Lock**
```python
# LOG: [LOCK_ACQUIRED] trace_id={trace_id} phone={phone} lock_id={lock_id} success={bool}
```

**P7: Antes do Flow Engine**
```python
# LOG: [FLOW_ENGINE_START] trace_id={trace_id} phone={phone} state={state} message={msg}
```

**P8: Depois do Flow Engine**
```python
# LOG: [FLOW_ENGINE_COMPLETE] trace_id={trace_id} new_state={state} responses_count={len}
```

**P9: Antes do Envio WAHA**
```python
# LOG: [WAHA_SEND_START] trace_id={trace_id} phone={phone} response_type={text/buttons}
```

**P10: Depois do Envio WAHA**
```python
# LOG: [WAHA_SEND_COMPLETE] trace_id={trace_id} success={bool} status_code={code}
```

**P11: Antes do XACK**
```python
# LOG: [XACK_BEFORE] trace_id={trace_id} stream_id={stream_id} success={bool}
```

**P12: Antes de Publicar WebSocket**
```python
# LOG: [WEBSOCKET_PUBLISH_START] trace_id={trace_id} event_type={type} phone={phone}
```

---

## 🔍 FASE 2 – VALIDAÇÃO DE CADA ETAPA

### 2.1 WEBHOOK (`/webhooks/waha`)

**Código Atual:** `backend/app/api/webhooks.py:36-237`

**Problemas Identificados:**

#### ❌ PROBLEMA CRÍTICO #1: Erro de Indentação (Linha 201-219)

```python
# CÓDIGO ATUAL (ERRADO):
with MessageContextManager(message_id=message_id, phone=chat_id):
    logger.info(...)
    if message_id:
        # dedup check
        ...
    
# Adicionar mensagem ao Redis Stream
stream_message_id = await redis_manager.add_message_to_stream(...)

    if stream_message_id:  # ❌ INDENTAÇÃO ERRADA - está dentro do with mas deveria estar fora
        logger.info(...)
        return {...}
    else:
        logger.warning(...)
    background_tasks.add_task(...)  # ❌ INDENTAÇÃO ERRADA
    return {...}
```

**Impacto:** 
- Se `stream_message_id` for None, o código dentro do `with` não executa o fallback corretamente
- O `background_tasks.add_task` pode não ser chamado
- Mensagem pode ser perdida silenciosamente

**Probabilidade:** 🔴 ALTA - Erro de sintaxe lógica

#### ❌ PROBLEMA CRÍTICO #2: Exceção Silenciosa na Validação HMAC

```python
# Linha 66
await verify_waha_signature(temp_req)
```

**Problema:**
- Se `verify_waha_signature` lançar `HTTPException`, o webhook retorna 401
- WAHA pode parar de enviar webhooks após múltiplos 401s
- Não há log estruturado antes da validação

**Probabilidade:** 🟡 MÉDIA - Depende de configuração

#### ❌ PROBLEMA CRÍTICO #3: Resolução de LID Pode Travar

```python
# Linha 118-125
resolved = await waha_client.resolve_lid(chat_id)
```

**Problema:**
- Se WAHA estiver lento ou offline, `resolve_lid` pode demorar muito
- Não há timeout explícito
- Webhook pode demorar > 30s e WAHA pode fazer retry

**Probabilidade:** 🟡 MÉDIA - Depende de latência WAHA

#### ✅ VALIDAÇÃO NECESSÁRIA:

```python
# 1. Webhook está retornando 200?
# ✅ SIM - código retorna dict que FastAPI converte para 200

# 2. Existe exceção silenciosa?
# ❌ SIM - verify_waha_signature pode lançar HTTPException sem log estruturado

# 3. Validação HMAC pode estar bloqueando?
# ✅ SIM - se secret configurado e signature inválida, retorna 401
```

---

### 2.2 REDIS STREAM (`XADD stream:messages`)

**Código Atual:** `backend/app/database.py:234-294`

**Problemas Identificados:**

#### ❌ PROBLEMA CRÍTICO #4: Conexão Redis Não Reutilizada

```python
# Linha 261-275
stream_client = redis_streams.from_url(...)
message_id = await stream_client.xadd(...)
await stream_client.close()  # ❌ Fecha conexão toda vez
```

**Problema:**
- Cria nova conexão Redis a cada mensagem
- Overhead de conexão pode causar timeout
- Se Redis estiver lento, pode falhar silenciosamente

**Probabilidade:** 🟡 MÉDIA - Depende de carga

#### ❌ PROBLEMA CRÍTICO #5: Erro de Serialização Não Tratado

```python
# Linha 254-258
stream_data = {
    "message": json.dumps(message_data),  # ❌ Pode falhar se message_data não serializável
    "original_chat_id": original_chat_id or "",
    "timestamp": str(time.time()),
}
```

**Problema:**
- Se `message_data` contém objetos não serializáveis, `json.dumps` lança exceção
- Exceção é capturada mas retorna `None` sem log detalhado
- Mensagem é perdida

**Probabilidade:** 🟢 BAIXA - Mas possível com dados complexos

#### ✅ VALIDAÇÃO NECESSÁRIA:

```python
# 1. XADD está realmente adicionando?
# ✅ Verificar logs: "[RedisStream] Mensagem adicionada ao stream"
# ❌ Se não aparecer, XADD falhou

# 2. Existe erro de serialização?
# ❌ SIM - json.dumps pode falhar silenciosamente

# 3. Existe problema de conexão Redis?
# ❌ SIM - conexão criada toda vez pode falhar
```

---

### 2.3 CONSUMER (`MessageStreamConsumer`)

**Código Atual:** `backend/app/services/message_stream_consumer.py`

**Problemas Identificados:**

#### ❌ PROBLEMA CRÍTICO #6: Loop Principal Pode Travar em Exception Genérica

```python
# Linha 367-369
except Exception as e:
    logger.error(f"[StreamConsumer] Erro no consumer loop: {e}", exc_info=True)
    await asyncio.sleep(1)  # ❌ Se exception for recorrente, loop trava
```

**Problema:**
- Se exception ocorrer repetidamente, loop fica em sleep(1) infinito
- Mensagens não são processadas
- Consumer aparece como "rodando" mas não faz nada

**Probabilidade:** 🟡 MÉDIA - Depende do tipo de erro

#### ❌ PROBLEMA CRÍTICO #7: XACK em Caso de Erro de Verificação de Retries

```python
# Linha 471-478
except Exception as e:
    logger.error(f"[StreamConsumer] Erro ao verificar retries: {e}")
    # Em caso de erro, fazer XACK para não travar
    await self.redis_client.xack(...)  # ❌ XACK mesmo em erro - mensagem perdida
```

**Problema:**
- Se XPENDING falhar, faz XACK mesmo assim
- Mensagem é marcada como processada mas não foi
- Mensagem é perdida permanentemente

**Probabilidade:** 🔴 ALTA - Se Redis XPENDING falhar

#### ❌ PROBLEMA CRÍTICO #8: Consumer Group Pode Não Ser Criado

```python
# Linha 90-106
try:
    await self.redis_client.xgroup_create(...)
except redis.ResponseError as e:
    if "BUSYGROUP" in str(e):
        logger.debug(...)  # ✅ OK
    else:
        logger.warning(...)  # ❌ Outros erros são apenas warning
```

**Problema:**
- Se erro diferente de BUSYGROUP ocorrer, apenas loga warning
- Consumer continua mas não consegue ler mensagens
- Mensagens ficam no stream mas nunca são processadas

**Probabilidade:** 🟢 BAIXA - Mas possível

#### ❌ PROBLEMA CRÍTICO #9: Block=5000 Pode Travar Indefinidamente

```python
# Linha 342-348
events = await self.redis_client.xreadgroup(
    ...
    block=BLOCK_TIME,  # 5000ms
)
```

**Problema:**
- Se Redis estiver lento ou com problemas, `block=5000` pode não retornar
- Loop fica esperando indefinidamente
- Não há timeout explícito

**Probabilidade:** 🟢 BAIXA - Mas possível

#### ✅ VALIDAÇÃO NECESSÁRIA:

```python
# 1. Loop principal está rodando?
# ✅ Verificar métrica: stream_consumer_running == 1
# ✅ Verificar logs: "[StreamConsumer] Iniciando consumer"

# 2. Existe cancelamento de task?
# ❌ SIM - se main.py não iniciar consumer corretamente

# 3. Block=5000 está travando?
# ❌ SIM - possível se Redis estiver lento

# 4. Consumer group foi criado corretamente?
# ❌ Verificar logs: "[StreamConsumer] Consumer group criado"
# ❌ Se não aparecer, consumer não funciona

# 5. XPENDING mostra mensagens presas?
# ✅ Verificar: redis-cli XPENDING stream:messages gas-workers
```

---

### 2.4 LOCK DISTRIBUÍDO (`acquire_phone_lock`)

**Código Atual:** `backend/app/database.py:199-228`

**Problemas Identificados:**

#### ❌ PROBLEMA CRÍTICO #10: Lock Não Expira Corretamente em Falha

```python
# backend/app/api/webhooks.py:286-302
lock_acquired = await redis_manager.acquire_phone_lock(...)
if not lock_acquired:
    await asyncio.sleep(1.5)
    lock_acquired = await redis_manager.acquire_phone_lock(...)
    if not lock_acquired:
        logger.error(...)
        return  # ❌ Mensagem é descartada sem processar
```

**Problema:**
- Se lock não for adquirido após 2 tentativas, mensagem é descartada
- Não vai para DLQ
- Cliente não recebe resposta

**Probabilidade:** 🟡 MÉDIA - Em alta concorrência

#### ❌ PROBLEMA CRÍTICO #11: Lock Pode Não Ser Liberado em Exception

```python
# backend/app/api/webhooks.py:407-413
finally:
    if lock_acquired:
        try:
            await redis_manager.release_phone_lock(...)
        except Exception:
            pass  # ❌ Se release falhar, lock pode ficar preso
```

**Problema:**
- Se `release_phone_lock` falhar, lock fica preso até TTL expirar
- Durante esse tempo, outras mensagens do mesmo telefone são bloqueadas
- Cliente não recebe respostas

**Probabilidade:** 🟡 MÉDIA - Se Redis falhar durante release

#### ✅ VALIDAÇÃO NECESSÁRIA:

```python
# 1. acquire_phone_lock pode não estar expirando?
# ✅ TTL está configurado (30s) - OK
# ❌ Mas se release falhar, lock fica preso até TTL

# 2. Existe deadlock?
# ❌ SIM - possível se múltiplos workers tentarem mesmo telefone simultaneamente

# 3. TTL está incorreto?
# ✅ TTL=30s parece razoável

# 4. Lock está sendo liberado mesmo em exception?
# ❌ NÃO - se release falhar, lock não é liberado
```

---

### 2.5 FLOW ENGINE (`flow_engine.process_message`)

**Código Atual:** `backend/app/core/flow_engine.py:222-321`

**Problemas Identificados:**

#### ❌ PROBLEMA CRÍTICO #12: Handler Pode Lançar Exceção Não Capturada

```python
# Linha 293-307
try:
    result = await self._route_message(context, message, intention)
    # ... salvar contexto
except Exception as e:
    logger.error(...)
    return ProcessedMessage(success=False, ...)  # ✅ Captura exceção
```

**Problema:**
- Se handler específico lançar exceção antes de retornar, é capturada
- Mas se exceção ocorrer em `send_responses`, não é capturada aqui
- Mensagem pode não ser enviada

**Probabilidade:** 🟡 MÉDIA - Depende do handler

#### ❌ PROBLEMA CRÍTICO #13: Ollama Pode Travar Sem Timeout

```python
# backend/app/core/nlp_utils.py (não visto, mas usado)
intention = detect_intention(message, context)  # Pode chamar Ollama
```

**Problema:**
- Se Ollama estiver offline ou lento, `detect_intention` pode travar
- Não há timeout explícito no código visto
- Mensagem fica travada no Flow Engine

**Probabilidade:** 🟡 MÉDIA - Depende de Ollama

#### ❌ PROBLEMA CRÍTICO #14: Salvar Contexto Pode Falhar Silenciosamente

```python
# Linha 301-305
try:
    await self.save_context(result.context, previous_state=previous_state)
except Exception as save_err:
    logger.error(f"Falha ao salvar contexto: {save_err}")
    result.context.state = previous_state  # ❌ Reverte estado mas continua
```

**Problema:**
- Se salvar contexto falhar, estado é revertido
- Mas resposta já foi gerada com novo estado
- Próxima mensagem pode estar em estado inconsistente

**Probabilidade:** 🟢 BAIXA - Mas possível

#### ✅ VALIDAÇÃO NECESSÁRIA:

```python
# 1. Algum handler pode lançar exceção não capturada?
# ✅ Exceções são capturadas no try/except principal
# ❌ Mas exceções em send_responses não são capturadas aqui

# 2. Algum await externo pode estar travando?
# ❌ SIM - Ollama pode travar sem timeout

# 3. Existe dependência externa lenta?
# ❌ SIM - Ollama, PostgreSQL, Redis

# 4. Timeout está configurado?
# ❌ NÃO - não há timeout explícito em detect_intention
```

---

### 2.6 ENVIO WAHA (`waha_client.send_text`)

**Código Atual:** `backend/app/integrations/waha.py:290-359`

**Problemas Identificados:**

#### ❌ PROBLEMA CRÍTICO #15: Erro 422 Não Tratado Corretamente

```python
# Linha 314-352
if response.status_code == 422:
    # Tenta reiniciar sessão e retry
    ...
    retry = await client.post("/api/sendText", json=payload)
    if retry.is_success:
        return result
    # ❌ Se retry também falhar, lança exceção
    raise httpx.HTTPStatusError(...)
```

**Problema:**
- Se retry falhar, exceção é lançada
- Exceção pode não ser capturada em `send_responses`
- Mensagem não é enviada e cliente não recebe resposta

**Probabilidade:** 🔴 ALTA - Se sessão WAHA estiver desconectada

#### ❌ PROBLEMA CRÍTICO #16: Timeout HTTP Não Configurado Explicitamente

```python
# Linha 46-50
self._client = httpx.AsyncClient(
    base_url=self.base_url,
    timeout=self.timeout,  # ✅ Timeout configurado (30s)
    headers=headers,
)
```

**Problema:**
- Timeout está configurado (30s)
- Mas se WAHA estiver muito lento, pode demorar 30s antes de falhar
- Cliente espera muito tempo sem resposta

**Probabilidade:** 🟢 BAIXA - Timeout existe

#### ❌ PROBLEMA CRÍTICO #17: Sessão WAHA Pode Estar Desconectada

```python
# Linha 323-334
if status and status != "WORKING":
    # Tenta reiniciar sessão
    await client.post(f"/api/sessions/{self.session_name}/start", ...)
    await asyncio.sleep(3)
    retry = await client.post("/api/sendText", json=payload)
```

**Problema:**
- Se sessão não iniciar em 3s, retry pode ainda falhar
- Não há verificação se sessão realmente ficou WORKING
- Mensagem pode não ser enviada

**Probabilidade:** 🔴 ALTA - Se WAHA estiver com problemas

#### ✅ VALIDAÇÃO NECESSÁRIA:

```python
# 1. sendText está tratando erro 500?
# ✅ Sim - httpx.HTTPError é capturado
# ❌ Mas exceção pode não ser tratada em send_responses

# 2. Timeout HTTP está configurado?
# ✅ Sim - 30s

# 3. Sessão WAHA pode estar desconectada?
# ❌ SIM - código tenta reiniciar mas pode falhar
```

---

### 2.7 XACK (Confirmação de Processamento)

**Código Atual:** `backend/app/services/message_stream_consumer.py:407-414`

**Problemas Identificados:**

#### ❌ PROBLEMA CRÍTICO #18: XACK Não É Chamado Se process_message Retornar False

```python
# Linha 404-414
success = await self.process_message(event_id_str, data)

if success:
    await self.redis_client.xack(...)  # ✅ XACK em sucesso
else:
    # Verifica retries...
    # ❌ Se retry_count < MAX_RETRIES, NÃO faz XACK
    # Mensagem fica pendente para retry
```

**Problema:**
- Se `process_message` retornar False e retry_count < 3, não faz XACK
- Mensagem fica pendente no PEL (Pending Entry List)
- Redis redeliver após timeout (default 1min)
- Mas se consumer morrer antes, mensagem pode ficar presa

**Probabilidade:** 🟡 MÉDIA - Se consumer morrer durante retry

#### ❌ PROBLEMA CRÍTICO #19: XACK em Caso de Erro de Deserialização

```python
# Linha 480-492
except Exception as e:
    logger.error(...)
    # Tentar fazer XACK mesmo assim para não travar
    try:
        await self.redis_client.xack(...)  # ❌ XACK mesmo em erro
    except Exception:
        pass
```

**Problema:**
- Se deserialização falhar, faz XACK mesmo assim
- Mensagem é marcada como processada mas não foi
- Mensagem é perdida permanentemente

**Probabilidade:** 🟢 BAIXA - Mas possível

#### ✅ VALIDAÇÃO NECESSÁRIA:

```python
# 1. Existe caminho onde XACK nunca é chamado?
# ❌ SIM - se process_message retornar False e retry_count < 3
# ✅ Mas isso é intencional para retry

# 2. Existe return antecipado?
# ❌ SIM - em vários lugares há return sem XACK
# ✅ Mas são casos de erro que devem ir para retry/DLQ
```

---

### 2.8 DLQ (Dead Letter Queue)

**Código Atual:** `backend/app/services/message_stream_consumer.py:222-274`

**Problemas Identificados:**

#### ✅ DLQ Parece Funcionar Corretamente

- Mensagens são movidas para DLQ após 3 tentativas
- Alerta é enviado
- Métricas são atualizadas

**Probabilidade de Problema:** 🟢 BAIXA

---

### 2.9 WEBSOCKET (`emit_new_message`, `emit_new_order`)

**Código Atual:** `backend/app/api/websocket.py:519-604`

**Problemas Identificados:**

#### ❌ PROBLEMA CRÍTICO #20: publish() Pode Falhar Silenciosamente

```python
# backend/app/api/websocket.py:578-603
async def emit_new_message(...):
    ...
    await manager.broadcast(msg)  # ❌ Se broadcast falhar, não há tratamento
```

**Problema:**
- Se `broadcast` falhar (ex: Redis Pub/Sub offline), exceção pode não ser capturada
- Evento não aparece no painel
- Não há log estruturado de falha

**Probabilidade:** 🟡 MÉDIA - Se Redis Pub/Sub falhar

#### ❌ PROBLEMA CRÍTICO #21: Redis Pub/Sub Pode Estar Offline

```python
# backend/app/core/redis_websocket_bridge.py (não visto completamente)
# Se Redis Pub/Sub não estiver funcionando, bridge não envia eventos
```

**Problema:**
- Se Redis Pub/Sub falhar, eventos não são propagados
- Painel não recebe atualizações
- Não há fallback

**Probabilidade:** 🟡 MÉDIA - Depende de Redis

#### ❌ PROBLEMA CRÍTICO #22: Filtros Por Role Podem Descartar Evento

```python
# Linha 600-603
if bairro:
    await manager.broadcast_to_neighborhood(msg, bairro=bairro)
else:
    await manager.broadcast(msg)  # ❌ Se não tem bairro, broadcast geral
```

**Problema:**
- Se mensagem não tem bairro associado, faz broadcast geral
- Mas se filtros estiverem muito restritivos, pode não chegar a ninguém
- Operador não vê mensagem

**Probabilidade:** 🟢 BAIXA - Mas possível

#### ✅ VALIDAÇÃO NECESSÁRIA:

```python
# 1. publish() está sendo chamado?
# ✅ Verificar logs: "[WEBSOCKET_PUBLISH_START]"
# ❌ Se não aparecer, publish não foi chamado

# 2. Redis Pub/Sub está ativo?
# ✅ Verificar: redis-cli PUBSUB CHANNELS
# ❌ Se não houver canais, Pub/Sub não está funcionando

# 3. Bridge pode estar morto?
# ✅ Verificar logs: "[RedisWSBridge]"
# ❌ Se não aparecer, bridge não está rodando

# 4. Filtros por role podem estar descartando?
# ❌ SIM - possível se filtros muito restritivos
```

---

## 🎯 FASE 3 – IDENTIFICAÇÃO DE PONTOS CRÍTICOS POR PROBABILIDADE

### 🔴 ALTA PROBABILIDADE (Causam exatamente o sintoma)

#### 1. Erro de Indentação no Webhook (Linha 201-219)
**Por que causa o sintoma:**
- Se `stream_message_id` for None, fallback não executa corretamente
- Mensagem não vai para stream nem para BackgroundTask
- Mensagem é perdida silenciosamente
- Cliente não recebe resposta

**Evidência:**
```python
# Código atual tem indentação errada
stream_message_id = await redis_manager.add_message_to_stream(...)

    if stream_message_id:  # ❌ Está dentro do with mas deveria estar fora
```

#### 2. XACK em Caso de Erro de Verificação de Retries (Linha 471-478)
**Por que causa o sintoma:**
- Se XPENDING falhar, faz XACK mesmo assim
- Mensagem é marcada como processada mas não foi
- Mensagem é perdida permanentemente
- Cliente não recebe resposta

**Evidência:**
```python
except Exception as e:
    logger.error(f"[StreamConsumer] Erro ao verificar retries: {e}")
    await self.redis_client.xack(...)  # ❌ XACK mesmo em erro
```

#### 3. Sessão WAHA Desconectada (Linha 323-334)
**Por que causa o sintoma:**
- Se sessão não iniciar corretamente, sendText falha
- Mensagem não é enviada
- Cliente não recebe resposta
- Evento não é emitido (porque resposta não foi enviada)

**Evidência:**
```python
if status and status != "WORKING":
    await client.post(f"/api/sessions/{self.session_name}/start", ...)
    await asyncio.sleep(3)  # ❌ Pode não ser suficiente
    retry = await client.post("/api/sendText", json=payload)
    # Se retry falhar, exceção é lançada
```

#### 4. Exceção em send_responses Não Capturada
**Por que causa o sintoma:**
- Se `send_responses` lançar exceção, não é capturada em `process_whatsapp_message`
- Mensagem não é enviada
- Cliente não recebe resposta
- Evento WebSocket pode não ser emitido

**Evidência:**
```python
# backend/app/api/webhooks.py:382-384
await flow_engine.send_responses(send_to, result.responses)
# ❌ Se send_responses lançar exceção, não é capturada aqui
```

### 🟡 MÉDIA PROBABILIDADE

#### 5. Consumer Loop Travado em Exception Recorrente
**Por que causa o sintoma:**
- Se exception ocorrer repetidamente, loop fica em sleep(1) infinito
- Mensagens não são processadas
- Cliente não recebe resposta

#### 6. Lock Não Adquirido Após 2 Tentativas
**Por que causa o sintoma:**
- Mensagem é descartada sem processar
- Não vai para DLQ
- Cliente não recebe resposta

#### 7. Redis Pub/Sub Offline
**Por que causa o sintoma:**
- Eventos não são propagados para outras instâncias
- Painel não recebe atualizações
- Operador não vê mensagens

### 🟢 BAIXA PROBABILIDADE

#### 8. Ollama Travado Sem Timeout
#### 9. Erro de Serialização JSON
#### 10. Consumer Group Não Criado

---

## 🔧 FASE 4 – PROPOSTA DE CORREÇÃO CONCRETA

### CORREÇÃO #1: Erro de Indentação no Webhook

**Arquivo:** `backend/app/api/webhooks.py`

**Trecho Problemático (Linha 196-219):**
```python
stream_message_id = await redis_manager.add_message_to_stream(
    message_data=message_data,
    original_chat_id=original_chat_id if original_chat_id != chat_id else None,
)

    if stream_message_id:  # ❌ INDENTAÇÃO ERRADA
        logger.info(...)
        return {"status": "queued", "stream_id": stream_message_id}
    else:
        logger.warning(...)
    background_tasks.add_task(...)  # ❌ INDENTAÇÃO ERRADA
    return {"status": "processing", "fallback": "background_task"}
```

**Código Corrigido:**
```python
# Gerar trace_id único para rastreamento
import uuid
trace_id = f"trace-{uuid.uuid4().hex[:12]}"

# Definir contexto ANTES de adicionar ao stream
with MessageContextManager(message_id=message_id, phone=chat_id, trace_id=trace_id):
    logger.info(
        f"[WEBHOOK_ENTRY] trace_id={trace_id} message_id={message_id} phone={chat_id}",
        extra={
            "trace_id": trace_id,
            "message_id": message_id,
            "phone": chat_id,
            "step": "webhook_entry"
        }
    )
    
    if message_id:
        try:
            is_duplicate = await redis_manager.check_message_processed(message_id)
            if is_duplicate:
                logger.info(
                    f"[DEDUP_RESULT] trace_id={trace_id} message_id={message_id} is_duplicate=True",
                    extra={"trace_id": trace_id, "step": "dedup_result", "is_duplicate": True}
                )
                return {"status": "duplicate", "message_id": message_id}
            logger.info(
                f"[DEDUP_RESULT] trace_id={trace_id} message_id={message_id} is_duplicate=False",
                extra={"trace_id": trace_id, "step": "dedup_result", "is_duplicate": False}
            )
        except Exception as e:
            logger.warning(
                f"[DEDUP_ERROR] trace_id={trace_id} error={e}",
                exc_info=True,
                extra={"trace_id": trace_id, "step": "dedup_error"}
            )

# Adicionar mensagem ao Redis Stream (FORA do with para garantir execução)
stream_message_id = await redis_manager.add_message_to_stream(
    message_data=message_data,
    original_chat_id=original_chat_id if original_chat_id != chat_id else None,
)

if stream_message_id:
    logger.info(
        f"[STREAM_ADDED] trace_id={trace_id} stream_id={stream_message_id} success=True",
        extra={
            "trace_id": trace_id,
            "stream_id": stream_message_id,
            "step": "stream_added",
            "success": True
        }
    )
    return {"status": "queued", "stream_id": stream_message_id, "trace_id": trace_id}
else:
    # Fallback: se stream falhar, usar BackgroundTask (compatibilidade)
    logger.warning(
        f"[STREAM_FAILED] trace_id={trace_id} using_fallback=True",
        extra={"trace_id": trace_id, "step": "stream_failed", "fallback": True}
    )
    background_tasks.add_task(
        process_whatsapp_message,
        message=message,
        original_chat_id=original_chat_id if original_chat_id != chat_id else None,
    )
    return {"status": "processing", "fallback": "background_task", "trace_id": trace_id}
```

**Melhoria Estrutural:**
- Adicionar métrica: `webhook_stream_add_failures_total`
- Adicionar alerta se fallback for usado frequentemente

---

### CORREÇÃO #2: XACK em Caso de Erro

**Arquivo:** `backend/app/services/message_stream_consumer.py`

**Trecho Problemático (Linha 471-478):**
```python
except Exception as e:
    logger.error(f"[StreamConsumer] Erro ao verificar retries: {e}")
    # Em caso de erro, fazer XACK para não travar
    await self.redis_client.xack(...)  # ❌ XACK mesmo em erro
```

**Código Corrigido:**
```python
except Exception as e:
    logger.error(
        f"[RETRY_CHECK_ERROR] trace_id={trace_id} stream_id={event_id_str} error={e}",
        exc_info=True,
        extra={
            "trace_id": trace_id,
            "stream_id": event_id_str,
            "step": "retry_check_error"
        }
    )
    # ❌ NÃO fazer XACK - deixar mensagem pendente para retry manual ou DLQ
    # Se XPENDING falhou, não sabemos quantas tentativas já foram feitas
    # É mais seguro deixar pendente do que perder a mensagem
    logger.warning(
        f"[RETRY_CHECK_FAILED] trace_id={trace_id} stream_id={event_id_str} "
        f"message left in PENDING for manual inspection",
        extra={
            "trace_id": trace_id,
            "stream_id": event_id_str,
            "step": "retry_check_failed"
        }
    )
    # Não fazer XACK - mensagem ficará pendente até timeout ou retry manual
```

**Melhoria Estrutural:**
- Adicionar métrica: `stream_retry_check_failures_total`
- Adicionar alerta se retry_check falhar frequentemente
- Criar script para inspecionar mensagens pendentes manualmente

---

### CORREÇÃO #3: Tratamento de Exceção em send_responses

**Arquivo:** `backend/app/core/flow_engine.py`

**Trecho Problemático (Linha 731-772):**
```python
async def send_responses(self, phone: str, responses: List[MessageResponse]):
    ...
    for response in responses:
        try:
            if response.has_buttons():
                await waha_client.send_buttons(...)
            else:
                await waha_client.send_text(...)
        except Exception as e:
            logger.error(f"Erro ao enviar resposta: {e}")  # ❌ Apenas loga, não propaga
            # Continua para próxima resposta
```

**Código Corrigido:**
```python
async def send_responses(
    self, 
    phone: str, 
    responses: List[MessageResponse],
    trace_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Envia respostas com tratamento robusto de erros.
    
    Returns:
        Dict com status de cada resposta enviada
    """
    results = {
        "sent": 0,
        "failed": 0,
        "errors": []
    }
    
    for idx, response in enumerate(responses):
        try:
            logger.info(
                f"[WAHA_SEND_START] trace_id={trace_id} phone={phone} "
                f"response_idx={idx} type={'buttons' if response.has_buttons() else 'text'}",
                extra={
                    "trace_id": trace_id,
                    "phone": phone,
                    "step": "waha_send_start",
                    "response_idx": idx
                }
            )
            
            if response.has_buttons():
                result = await waha_client.send_buttons(
                    phone, response.text, response.buttons, footer=response.footer
                )
            else:
                result = await waha_client.send_text(phone, response.text)
            
            logger.info(
                f"[WAHA_SEND_COMPLETE] trace_id={trace_id} phone={phone} "
                f"response_idx={idx} success=True",
                extra={
                    "trace_id": trace_id,
                    "phone": phone,
                    "step": "waha_send_complete",
                    "success": True,
                    "response_idx": idx
                }
            )
            results["sent"] += 1
            
        except httpx.HTTPStatusError as e:
            # Erro HTTP específico (422, 500, etc)
            status_code = e.response.status_code if e.response else 0
            logger.error(
                f"[WAHA_SEND_ERROR] trace_id={trace_id} phone={phone} "
                f"response_idx={idx} status_code={status_code} error={e}",
                exc_info=True,
                extra={
                    "trace_id": trace_id,
                    "phone": phone,
                    "step": "waha_send_error",
                    "status_code": status_code,
                    "response_idx": idx
                }
            )
            results["failed"] += 1
            results["errors"].append({
                "idx": idx,
                "status_code": status_code,
                "error": str(e)
            })
            
            # Se for erro 422 (sessão não WORKING), tentar reiniciar uma vez
            if status_code == 422:
                try:
                    logger.warning(
                        f"[WAHA_SESSION_RESTART] trace_id={trace_id} phone={phone}",
                        extra={"trace_id": trace_id, "step": "waha_session_restart"}
                    )
                    await waha_client.ensure_session_ready()
                    # Tentar enviar novamente
                    if response.has_buttons():
                        result = await waha_client.send_buttons(
                            phone, response.text, response.buttons, footer=response.footer
                        )
                    else:
                        result = await waha_client.send_text(phone, response.text)
                    results["sent"] += 1
                    results["failed"] -= 1
                    logger.info(
                        f"[WAHA_SEND_RETRY_SUCCESS] trace_id={trace_id} phone={phone} response_idx={idx}",
                        extra={"trace_id": trace_id, "step": "waha_send_retry_success"}
                    )
                except Exception as retry_err:
                    logger.error(
                        f"[WAHA_SEND_RETRY_FAILED] trace_id={trace_id} phone={phone} "
                        f"response_idx={idx} error={retry_err}",
                        exc_info=True,
                        extra={"trace_id": trace_id, "step": "waha_send_retry_failed"}
                    )
            
        except Exception as e:
            # Outros erros (timeout, conexão, etc)
            logger.error(
                f"[WAHA_SEND_ERROR] trace_id={trace_id} phone={phone} "
                f"response_idx={idx} error={e}",
                exc_info=True,
                extra={
                    "trace_id": trace_id,
                    "phone": phone,
                    "step": "waha_send_error",
                    "response_idx": idx,
                    "error_type": type(e).__name__
                }
            )
            results["failed"] += 1
            results["errors"].append({
                "idx": idx,
                "error": str(e),
                "error_type": type(e).__name__
            })
    
    # Se todas as respostas falharam, lançar exceção
    if results["failed"] == len(responses) and results["sent"] == 0:
        raise Exception(
            f"Todas as respostas falharam para {phone}. "
            f"Erros: {results['errors']}"
        )
    
    return results
```

**Uso em `process_whatsapp_message`:**
```python
# Linha 382-384
try:
    send_results = await flow_engine.send_responses(
        send_to, 
        result.responses,
        trace_id=get_message_context().get("trace_id")
    )
    logger.info(
        f"[RESPONSES_SENT] trace_id={trace_id} phone={phone} "
        f"sent={send_results['sent']} failed={send_results['failed']}",
        extra={
            "trace_id": trace_id,
            "phone": phone,
            "step": "responses_sent",
            **send_results
        }
    )
except Exception as send_err:
    logger.error(
        f"[RESPONSES_SEND_FAILED] trace_id={trace_id} phone={phone} error={send_err}",
        exc_info=True,
        extra={
            "trace_id": trace_id,
            "phone": phone,
            "step": "responses_send_failed"
        }
    )
    # Tentar enviar mensagem de erro genérica
    try:
        await waha_client.send_text(
            phone,
            "Desculpe, ocorreu um erro ao processar sua mensagem. "
            "Digite *menu* para recomeçar."
        )
    except Exception:
        pass
```

**Melhoria Estrutural:**
- Adicionar métrica: `waha_send_failures_total{status_code}`
- Adicionar alerta se taxa de falha > 10%
- Implementar retry exponencial para erros temporários

---

### CORREÇÃO #4: Consumer Loop com Tratamento Robusto

**Arquivo:** `backend/app/services/message_stream_consumer.py`

**Trecho Problemático (Linha 367-369):**
```python
except Exception as e:
    logger.error(f"[StreamConsumer] Erro no consumer loop: {e}", exc_info=True)
    await asyncio.sleep(1)  # ❌ Se exception recorrente, loop trava
```

**Código Corrigido:**
```python
except Exception as e:
    error_type = type(e).__name__
    error_count_key = f"consumer_error_count:{error_type}"
    
    # Contar erros consecutivos do mesmo tipo
    try:
        error_count = await self.redis_client.incr(error_count_key)
        await self.redis_client.expire(error_count_key, 60)  # Reset após 60s
    except:
        error_count = 1
    
    logger.error(
        f"[CONSUMER_LOOP_ERROR] consumer={self.consumer_name} "
        f"error_type={error_type} error_count={error_count} error={e}",
        exc_info=True,
        extra={
            "consumer": self.consumer_name,
            "error_type": error_type,
            "error_count": error_count,
            "step": "consumer_loop_error"
        }
    )
    
    # Se muitos erros consecutivos, aumentar delay exponencialmente
    if error_count > 10:
        sleep_time = min(60, 2 ** min(error_count - 10, 6))  # Max 60s
        logger.critical(
            f"[CONSUMER_DEGRADED] consumer={self.consumer_name} "
            f"error_count={error_count} sleeping={sleep_time}s",
            extra={
                "consumer": self.consumer_name,
                "error_count": error_count,
                "sleep_time": sleep_time,
                "step": "consumer_degraded"
            }
        )
        await asyncio.sleep(sleep_time)
    else:
        await asyncio.sleep(1)
    
    # Se erro persistir muito, tentar reconectar
    if error_count > 20:
        logger.critical(
            f"[CONSUMER_RECONNECT] consumer={self.consumer_name} "
            f"attempting reconnect after {error_count} errors",
            extra={"consumer": self.consumer_name, "step": "consumer_reconnect"}
        )
        try:
            await self.disconnect()
            await asyncio.sleep(5)
            await self.connect()
        except Exception as reconnect_err:
            logger.error(
                f"[CONSUMER_RECONNECT_FAILED] consumer={self.consumer_name} error={reconnect_err}",
                exc_info=True
            )
```

**Melhoria Estrutural:**
- Adicionar métrica: `stream_consumer_errors_total{error_type}`
- Adicionar alerta se error_count > 10
- Implementar circuit breaker se erros persistirem

---

### CORREÇÃO #5: Instrumentação Completa no Consumer

**Arquivo:** `backend/app/services/message_stream_consumer.py`

**Adicionar logs estruturados em `_process_batch`:**

```python
async def _process_batch(self, stream, messages):
    """Processa um batch de mensagens."""
    stream_name = stream.decode() if isinstance(stream, bytes) else stream

    for event_id, event_data in messages:
        event_id_str = (
            event_id.decode() if isinstance(event_id, bytes) else event_id
        )
        
        # Gerar trace_id se não existir nos dados
        trace_id = None
        try:
            # Tentar extrair trace_id dos dados
            if isinstance(event_data, dict):
                message_data_raw = event_data.get("message", {})
                if isinstance(message_data_raw, str):
                    message_data = json.loads(message_data_raw)
                else:
                    message_data = message_data_raw
                key_data = message_data.get("key", {})
                msg_id = key_data.get("id", "")
                trace_id = f"trace-{msg_id[:8]}" if msg_id else f"trace-{event_id_str[:8]}"
        except:
            trace_id = f"trace-{event_id_str[:8]}"
        
        logger.info(
            f"[CONSUMER_MESSAGE_RECEIVED] trace_id={trace_id} stream_id={event_id_str} "
            f"consumer={self.consumer_name}",
            extra={
                "trace_id": trace_id,
                "stream_id": event_id_str,
                "consumer": self.consumer_name,
                "step": "consumer_message_received"
            }
        )

        # Deserializar dados
        try:
            # ... código de deserialização existente ...
            
            # Extrair phone para contexto
            phone = None
            msg_id = None
            try:
                message_data_raw = data.get("message", {})
                if isinstance(message_data_raw, str):
                    message_data = json.loads(message_data_raw)
                else:
                    message_data = message_data_raw
                key_data = message_data.get("key", {})
                phone = key_data.get("remoteJid", "").replace("@c.us", "").replace("@lid", "")
                msg_id = key_data.get("id", "")
            except:
                pass
            
            # Definir contexto de mensagem
            with MessageContextManager(message_id=msg_id, phone=phone, trace_id=trace_id):
                # Processar mensagem
                success = await self.process_message(event_id_str, data)
                
                if success:
                    # Confirmar processamento (XACK)
                    logger.info(
                        f"[XACK_BEFORE] trace_id={trace_id} stream_id={event_id_str} success=True",
                        extra={
                            "trace_id": trace_id,
                            "stream_id": event_id_str,
                            "step": "xack_before",
                            "success": True
                        }
                    )
                    await self.redis_client.xack(
                        STREAM_NAME, CONSUMER_GROUP, event_id_str
                    )
                    logger.debug(
                        f"[XACK_COMPLETE] trace_id={trace_id} stream_id={event_id_str}",
                        extra={
                            "trace_id": trace_id,
                            "stream_id": event_id_str,
                            "step": "xack_complete"
                        }
                    )
                else:
                    # ... código de retry existente ...
                    
        except Exception as e:
            logger.error(
                f"[CONSUMER_DESERIALIZE_ERROR] trace_id={trace_id} stream_id={event_id_str} error={e}",
                exc_info=True,
                extra={
                    "trace_id": trace_id,
                    "stream_id": event_id_str,
                    "step": "consumer_deserialize_error"
                }
            )
            # ❌ NÃO fazer XACK - deixar mensagem pendente para inspeção manual
            # Se deserialização falhou, mensagem está corrompida
            # Melhor deixar pendente do que perder
```

---

### CORREÇÃO #6: Instrumentação no Flow Engine

**Arquivo:** `backend/app/core/flow_engine.py`

**Adicionar logs estruturados em `process_message`:**

```python
async def process_message(
    self,
    phone: str,
    message: str,
    message_id: Optional[str] = None,
    waha_chat_id: Optional[str] = None,
) -> ProcessedMessage:
    # Obter trace_id do contexto
    from app.utils.structured_logging import get_message_context
    context_data = get_message_context()
    trace_id = context_data.get("trace_id") or f"trace-{message_id[:8]}" if message_id else None
    
    # Normalizar phone
    original_phone = phone
    if "@" in phone:
        phone = phone.split("@")[0]
    
    logger.info(
        f"[FLOW_ENGINE_START] trace_id={trace_id} phone={phone} "
        f"original_phone={original_phone} message_id={message_id} message={message[:50]}",
        extra={
            "trace_id": trace_id,
            "phone": phone,
            "original_phone": original_phone,
            "message_id": message_id,
            "step": "flow_engine_start"
        }
    )
    
    # Carregar contexto
    context = await self.get_context(phone)
    previous_state = context.state
    
    logger.info(
        f"[FLOW_CONTEXT_LOADED] trace_id={trace_id} phone={phone} "
        f"state={context.state.value} previous_state={previous_state.value}",
        extra={
            "trace_id": trace_id,
            "phone": phone,
            "state": context.state.value,
            "previous_state": previous_state.value,
            "step": "flow_context_loaded"
        }
    )
    
    # ... resto do código ...
    
    try:
        result = await self._route_message(context, message, intention)
        
        logger.info(
            f"[FLOW_ENGINE_COMPLETE] trace_id={trace_id} phone={phone} "
            f"new_state={result.new_state.value} responses_count={len(result.responses)} "
            f"success={result.success}",
            extra={
                "trace_id": trace_id,
                "phone": phone,
                "new_state": result.new_state.value,
                "responses_count": len(result.responses),
                "success": result.success,
                "step": "flow_engine_complete"
            }
        )
        
        # Salvar contexto
        new_state = result.new_state
        if new_state != previous_state:
            result.context.retry_count = 0
        result.context.state = new_state
        try:
            await self.save_context(result.context, previous_state=previous_state)
        except Exception as save_err:
            logger.error(
                f"[FLOW_CONTEXT_SAVE_FAILED] trace_id={trace_id} phone={phone} error={save_err}",
                exc_info=True,
                extra={
                    "trace_id": trace_id,
                    "phone": phone,
                    "step": "flow_context_save_failed"
                }
            )
            result.context.state = previous_state
        
        return result
        
    except Exception as e:
        logger.error(
            f"[FLOW_ENGINE_ERROR] trace_id={trace_id} phone={phone} error={e}",
            exc_info=True,
            extra={
                "trace_id": trace_id,
                "phone": phone,
                "step": "flow_engine_error"
            }
        )
        return ProcessedMessage(
            context=context,
            responses=[
                MessageResponse(
                    text="Desculpe, ocorreu um erro. Por favor, tente novamente ou digite *menu* para recomecar."
                )
            ],
            new_state=context.state,
            success=False,
            error=str(e),
        )
```

---

### CORREÇÃO #7: Instrumentação no WebSocket

**Arquivo:** `backend/app/api/websocket.py`

**Adicionar logs estruturados em `emit_new_message`:**

```python
async def emit_new_message(
    phone: str, 
    message: str, 
    direction: str = "incoming", 
    customer_data: dict = None
):
    # Obter trace_id do contexto
    from app.utils.structured_logging import get_message_context
    context_data = get_message_context()
    trace_id = context_data.get("trace_id")
    
    bairro = None
    if customer_data:
        bairro = customer_data.get("bairro")
    
    msg = {
        "type": "new_message",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "phone": phone,
            "message": message,
            "direction": direction,
        },
    }
    
    logger.info(
        f"[WEBSOCKET_PUBLISH_START] trace_id={trace_id} phone={phone} "
        f"event_type=new_message bairro={bairro}",
        extra={
            "trace_id": trace_id,
            "phone": phone,
            "event_type": "new_message",
            "bairro": bairro,
            "step": "websocket_publish_start"
        }
    )
    
    try:
        if bairro:
            await manager.broadcast_to_neighborhood(msg, bairro=bairro)
        else:
            await manager.broadcast(msg)
        
        logger.info(
            f"[WEBSOCKET_PUBLISH_COMPLETE] trace_id={trace_id} phone={phone} success=True",
            extra={
                "trace_id": trace_id,
                "phone": phone,
                "step": "websocket_publish_complete",
                "success": True
            }
        )
    except Exception as e:
        logger.error(
            f"[WEBSOCKET_PUBLISH_ERROR] trace_id={trace_id} phone={phone} error={e}",
            exc_info=True,
            extra={
                "trace_id": trace_id,
                "phone": phone,
                "step": "websocket_publish_error"
            }
        )
        # Não propagar exceção - evento não é crítico para resposta ao cliente
```

---

## 🔄 FASE 5 – VERIFICAÇÃO DE RACE CONDITION

### Cenário de Race Condition Identificado

**Situação:**
1. Cliente envia mensagem M1 no WhatsApp
2. WAHA envia webhook W1 para backend (message_id=MSG1)
3. Webhook W1 adiciona M1 ao stream (stream_id=S1)
4. Cliente envia mensagem M2 rapidamente (message_id=MSG2)
5. WAHA envia webhook W2 para backend
6. Webhook W2 adiciona M2 ao stream (stream_id=S2)
7. Worker 1 lê S1 do stream
8. Worker 1 adquire lock para telefone (lock_id=L1)
9. Worker 2 lê S2 do stream (ANTES de Worker 1 processar S1)
10. Worker 2 tenta adquirir lock - FALHA (contention)
11. Worker 2 espera 1.5s e tenta novamente - FALHA (Worker 1 ainda processando)
12. Worker 2 descarta M2 (return sem processar)
13. Worker 1 processa M1 e libera lock
14. **RESULTADO: M2 foi perdida**

**Código Problemático:**
```python
# backend/app/api/webhooks.py:286-302
lock_acquired = await redis_manager.acquire_phone_lock(...)
if not lock_acquired:
    await asyncio.sleep(1.5)
    lock_acquired = await redis_manager.acquire_phone_lock(...)
    if not lock_acquired:
        logger.error(...)
        return  # ❌ Mensagem descartada
```

**Solução:**

**Opção 1: Adicionar ao Stream em vez de Descartar**
```python
# Se lock não for adquirido após 2 tentativas, adicionar ao stream novamente
# para retry posterior
if not lock_acquired:
    logger.warning(
        f"[LOCK_CONTENTION] trace_id={trace_id} phone={phone} "
        f"message_id={message_id} - re-queuing to stream",
        extra={
            "trace_id": trace_id,
            "phone": phone,
            "message_id": message_id,
            "step": "lock_contention"
        }
    )
    # Re-adicionar ao stream com delay para retry
    await asyncio.sleep(2)
    stream_id = await redis_manager.add_message_to_stream(
        message_data=message_data,
        original_chat_id=original_chat_id,
    )
    if stream_id:
        return {"status": "queued_retry", "stream_id": stream_id}
    # Se stream também falhar, usar BackgroundTask como último recurso
    background_tasks.add_task(
        process_whatsapp_message,
        message=message,
        original_chat_id=original_chat_id,
    )
    return {"status": "processing", "fallback": "background_task"}
```

**Opção 2: Usar Fila com Prioridade**
- Implementar fila Redis com prioridade
- Mensagens do mesmo telefone são processadas em ordem
- Evita race conditions completamente

---

## 📈 MÉTRICAS PROMETHEUS ADICIONAIS

### Métricas Propostas

```python
# Webhook
webhook_requests_total{status, event_type}
webhook_processing_duration_seconds
webhook_stream_add_failures_total
webhook_fallback_used_total

# Stream
stream_messages_added_total{success}
stream_consumer_read_duration_seconds
stream_consumer_pending_messages
stream_xack_failures_total

# Lock
lock_acquisition_total{success}
lock_contention_total
lock_held_duration_seconds
lock_release_failures_total

# Flow Engine
flow_engine_processing_duration_seconds{state}
flow_engine_state_transitions_total{from_state, to_state}
flow_engine_context_save_failures_total

# WAHA Send
waha_send_total{success, status_code}
waha_send_duration_seconds
waha_session_restarts_total
waha_send_retries_total

# WebSocket
websocket_publish_total{success, event_type}
websocket_publish_failures_total
```

---

## 🎯 RESUMO EXECUTIVO

### Problemas Críticos Encontrados (Ordem de Prioridade)

1. **🔴 CRÍTICO: Erro de Indentação no Webhook** (Linha 201-219)
   - Mensagens podem ser perdidas silenciosamente
   - **Ação:** Corrigir indentação imediatamente

2. **🔴 CRÍTICO: XACK em Caso de Erro de Verificação** (Linha 471-478)
   - Mensagens podem ser marcadas como processadas sem serem
   - **Ação:** Não fazer XACK em caso de erro

3. **🔴 CRÍTICO: Exceção em send_responses Não Capturada**
   - Mensagens podem não ser enviadas
   - **Ação:** Adicionar try/except em send_responses

4. **🔴 CRÍTICO: Sessão WAHA Desconectada**
   - Mensagens não são enviadas
   - **Ação:** Melhorar tratamento de sessão WAHA

5. **🟡 MÉDIO: Lock Contention**
   - Mensagens podem ser descartadas
   - **Ação:** Re-queue em vez de descartar

6. **🟡 MÉDIO: Consumer Loop Travado**
   - Mensagens não são processadas
   - **Ação:** Melhorar tratamento de erros recorrentes

### Próximos Passos

1. ✅ Aplicar todas as correções propostas
2. ✅ Adicionar instrumentação completa
3. ✅ Implementar métricas Prometheus
4. ✅ Configurar alertas
5. ✅ Testar pipeline completo end-to-end
6. ✅ Monitorar logs estruturados por 24h
7. ✅ Ajustar conforme necessário

---

**Objetivo Final:** Garantir que nenhuma mensagem morra silenciosamente no sistema e que todos os pontos de falha sejam instrumentados e monitorados.
