# Análise Profunda do Pipeline — Flow Engine V2 e Mensagem de Erro Global

**Objetivo:** Diagnosticar por que o bot responde sempre *"Desculpe, ocorreu um erro. Digite menu para recomeçar."* após implementar o Flow Engine V2.

**Abordagem:** Modelagem do pipeline real no código, mapeamento do ponto exato onde a mensagem de erro é enviada, e plano de debug por camadas com instrumentação e isolamento.

---

## 1. Onde a mensagem de erro é gerada

### 1.1 Origem única da mensagem ao usuário

A string **"Desculpe, ocorreu um erro. Digite menu para recomeçar."** é enviada ao usuário em **um único lugar** no código:

| Arquivo | Linha | Condição |
|---------|--------|----------|
| `backend/app/api/webhooks.py` | **824-826** | Qualquer exceção não tratada no bloco `try` que envolve o processamento da mensagem em `process_whatsapp_message()` |

Trecho relevante:

```python
# webhooks.py, dentro de process_whatsapp_message()
try:
    # ... lock, typing, EventLog, flow_engine.process_message(), result.context, send_responses ...
except Exception as e:
    logger.error(
        f"[PROCESSING_ERROR] trace_id={trace_id} phone={phone} message_id={message_id} error={e}",
        exc_info=True,
        ...
    )
    ...
    await waha_client.send_text(
        phone,
        "Desculpe, ocorreu um erro. Digite *menu* para recomeçar."
    )
```

Conclusão: **qualquer exceção** entre o início do `try` (após lock) e o fim do bloco (incluindo `flow_engine.process_message`, acesso a `result.context`/`result.new_state`, e `send_responses`) resulta nessa mensagem. Não existe “erro de estado inexistente” ou “transição” como mensagem alternativa; tudo cai nesse fallback.

### 1.2 Segundo ponto (erro no envio das respostas)

Há um **segundo** texto de erro, usado quando o processamento retorna respostas mas **o envio via WAHA falha**:

| Arquivo | Linha | Condição |
|---------|--------|----------|
| `backend/app/api/webhooks.py` | **786-790** | `flow_engine.send_responses()` levanta exceção |

Mensagem: *"Desculpe, ocorreu um erro ao processar sua mensagem. Digite *menu* para recomeçar."*

Para o sintoma que você descreveu (“sempre essa mensagem”), o mais provável é o **primeiro** caso: exceção antes de chegar ao envio normal das respostas.

---

## 2. Pipeline real (mapeamento no código)

O fluxo efetivo não tem “Message Normalizer” nem “Condition Evaluator” como componentes nomeados; o que existe é o seguinte.

### 2.1 Diagrama do pipeline

```
WAHA (WhatsApp)
    │
    ▼ POST /webhooks/waha
┌─────────────────────────────────────────────────────────────────┐
│ 1. WEBHOOK (webhooks.py)                                         │
│    - Gera trace_id, lê body, verifica assinatura                  │
│    - Parse JSON → event, payload                                  │
│    - event=="message" → extrai from, body, LID resolve            │
│    - Monta WAHAMessage, dedup (Redis SET NX), mark read, typing    │
│    - redis_manager.add_message_to_stream(message_data, trace_id)  │
│    - Retorna {"status":"queued", "stream_id":...}                 │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼ stream:messages (Redis)
┌─────────────────────────────────────────────────────────────────┐
│ 2. REDIS STREAM (database.py)                                    │
│    - XADD stream:messages { message: JSON, original_chat_id,      │
│      timestamp, trace_id? }                                       │
│    - decode_responses=False (bytes)                               │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼ XREADGROUP gas-workers
┌─────────────────────────────────────────────────────────────────┐
│ 3. MESSAGE STREAM CONSUMER (message_stream_consumer.py)           │
│    - Poll em stream:messages, consumer group "gas-workers"         │
│    - Deserializa event_data → data (message, original_chat_id…)    │
│    - MessageContextManager(trace_id, phone, message_id)           │
│    - process_message(stream_msg_id, data)                        │
│      → Reconstrói WAHAMessage, chama process_whatsapp_message()  │
│    - XACK em sucesso                                              │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. process_whatsapp_message() (webhooks.py)                       │
│    - phone, text, message_id, original_chat_id da WAHAMessage     │
│    - Lock por telefone (Redis), typing, mark read                 │
│    - EventLog, emit_new_message (WebSocket)                       │
│    - flow_engine.process_message(phone, content, message_id,      │
│      waha_chat_id, trace_id)  ← AQUI OCORRE A EXCEÇÃO TÍPICA     │
│    - result.context.waha_chat_id, result.new_state.value         │
│    - flow_engine.send_responses(send_to, result.responses)        │
│    - Release lock                                                 │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼ flow_engine = FlowEngineWrapper (flow_engine.py)
┌─────────────────────────────────────────────────────────────────┐
│ 5. FLOW ENGINE WRAPPER (flow_engine.py)                           │
│    - _get_v2_engine() → get_flow_engine_v2() (singleton)          │
│    - engine.process_message(phone, message, trace_id=…)           │
│    - _adapt_response(responses, waha_chat_id, current_state)      │
│      → Objeto com .responses, .context, .new_state                │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼ FlowEngineV2 (flow_engine_v2.py)
┌─────────────────────────────────────────────────────────────────┐
│ 6. FLOW ENGINE V2                                                 │
│    - _load_contexts(phone) → Redis/novo ConversationContext       │
│    - _detect_intent(message) → NLU (keyword/pattern/LLM)          │
│    - _check_fast_track()                                          │
│    - handler = handler_registry.get(current_state)                │
│    - handler.handle() → HandlerResult                             │
│    - _finalize_response() → save context, format responses        │
│    - Retorna List[Dict] com type, text, buttons, media_url        │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼ ContextManager (context_manager.py) + Handler (handlers_v2/)
┌─────────────────────────────────────────────────────────────────┐
│ 7. STATE LOADER + HANDLERS                                        │
│    - Redis: conversation:{phone}, order:{phone}                   │
│    - PostgreSQL: Customer (por phone), Order                      │
│    - Handler (ex.: GreetingInitialHandler) usa ConversationContext│
│      e CustomerContext, retorna HandlerResult (MessageResponse[]) │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼ _finalize_response
┌─────────────────────────────────────────────────────────────────┐
│ 8. RESPONSE BUILDER (flow_engine_v2._finalize_response)            │
│    - result.responses são MessageResponse (text, buttons,        │
│      image_url, footer) — NÃO possuem .type nem .media_url        │
│    - Formatação para [{ "type", "text", "buttons", "media_url" }]│
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ 9. WAHA SEND (integrations/waha.py)                               │
│    - flow_engine.send_responses() → waha_client.send_text/buttons  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Camadas e arquivos

| Camada | Arquivo(s) | Função/Classe principal |
|--------|------------|---------------------------|
| Webhook | `api/webhooks.py` | `waha_webhook()`, construção de `WAHAMessage` e `add_message_to_stream` |
| Redis Stream (produção) | `database.py` | `RedisManager.add_message_to_stream()` (XADD) |
| Consumer | `services/message_stream_consumer.py` | `MessageStreamConsumer`, `process_message()`, `_process_batch()` |
| Processamento da mensagem | `api/webhooks.py` | `process_whatsapp_message()` |
| Flow Engine (interface) | `core/flow_engine.py` | `FlowEngineWrapper.process_message()`, `_adapt_response()` |
| Flow Engine V2 | `core/flow_engine_v2.py` | `FlowEngineV2.process_message()`, `_finalize_response()` |
| State loader / persist | `core/context_manager.py` | `get_conversation_context`, `save_conversation_context` (Redis) |
| Handlers | `core/handlers_v2/*.py` | `GreetingInitialHandler` etc., retornam `HandlerResult` |
| Response builder | `core/flow_engine_v2.py` | `_finalize_response()` formata `MessageResponse` → dict |
| Envio WAHA | `integrations/waha.py` | `waha_client.send_text()`, `send_buttons()` |

Não há, no código atual, entidades como “flow_version”, “flow_assignment” ou “Condition Evaluator” separados; o “state” é `ConversationContext.current_state` (enum) e a “transição” é o `next_state` definido pelo handler.

---

## 3. Etapa 1 — Classificar o tipo de falha

Como a mensagem de erro é única, a classificação é pela **exceção** que está sendo lançada. Formas de identificar:

### 3.1 Exceção não tratada (caso atual)

- **Onde:** Em qualquer ponto do `try` em `process_whatsapp_message` (webhooks ~588–806).
- **Como provar:** Log `[PROCESSING_ERROR]` com `error={e}` e stacktrace (`exc_info=True`). O tipo de `e` e a linha do traceback indicam a camada.
- **Exemplos já vistos neste projeto:**
  - `TypeError: process_message() got an unexpected keyword argument 'trace_id'` → wrapper não aceitava `trace_id`.
  - `AttributeError: 'V1CompatibleResponse' object has no attribute 'context'` → wrapper não retornava `result.context`.
  - `AttributeError: 'MessageResponse' object has no attribute 'type'` → `_finalize_response` usava `response.type`/`response.media_url` em objeto que não tem esses atributos.

### 3.2 Falha de estado / handler não encontrado

- **Onde:** `flow_engine_v2.py`: `handler_registry.get(current_state)` retorna `None` e o fallback para `ERROR_RECOVERY` também falha.
- **Sintoma:** `ValueError: Handler não encontrado: <state>`.
- **Como provar:** Log `[trace_id] Handler não encontrado para estado: ...` antes da exceção.

### 3.3 Falha ao carregar contexto (Redis/JSON)

- **Onde:** `context_manager.get_conversation_context()` ou `save_conversation_context()` (Redis indisponível, JSON inválido).
- **Sintoma:** `ConnectionError`, `TimeoutError`, ou exceção no `json.loads`/`json.dumps` em `context_manager`.
- **Como provar:** Stacktrace apontando para `context_manager.py` ou Redis.

### 3.4 Falha no handler (DB, regra de negócio)

- **Onde:** Dentro de `handler.handle()` (ex.: `GreetingInitialHandler._get_customer_by_phone`).
- **Sintoma:** Exceção de SQLAlchemy, `AttributeError` em modelo, ou erro de validação.
- **Como provar:** Stacktrace com `handlers_v2/` ou `base.py` (ex.: `_get_customer_by_phone`).

### 3.5 Timeout

- **Onde:** Qualquer `await` longo (Redis, PostgreSQL, WAHA, NLU).
- **Sintoma:** `asyncio.TimeoutError` ou timeout do cliente HTTP.
- **Como provar:** Log de timeout ou stacktrace correspondente.

### 3.6 Consumer não processando

- **Sintoma:** Webhook retorna 200 e “queued”, mas o usuário nunca recebe resposta (nem a de erro). A mensagem fica no stream ou na pending list.
- **Não é** o caso em que o usuário **recebe** “Desculpe, ocorreu um erro”; nesse caso o consumer está processando e a falha está dentro de `process_whatsapp_message`.

---

## 4. Etapa 2 — Debug por camadas

### 4.1 Webhook

**Validar payload e endpoint:**

- Garantir que o WAHA está chamando a URL correta (ex.: `https://<backend>/webhooks/waha` ou `/api/webhooks/waha` conforme roteamento).
- Logs obrigatórios já existentes:
  - `[WEBHOOK_RECEIVED]` com `trace_id`, `method`, `step=webhook_received`
  - `WAHA Webhook recebido: event=... session=... payload_keys=...`
- Se não aparecer `event=message` e `payload` com `from`, `body` ou `_data`, o problema é antes do backend (WAHA ou rede).
- **Instrumentação sugerida:** Logar (em DEBUG ou INFO) `payload.get("from")`, `payload.get("body")` e o `chat_id` após resolução de LID, com `trace_id`.

**Como validar roteamento:**

- Ver em `main.py` como o router de webhooks está montado (ex.: `app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])`).
- Um POST no endpoint deve gerar pelo menos `[WEBHOOK_RECEIVED]`.

### 4.2 API Backend (após webhook)

- O “controller” é o mesmo: `waha_webhook` → depois `add_message_to_stream` → return. Não há outro controller no meio.
- **Validar:** Após o log do webhook, deve aparecer log de stream (ex.: em `database.py` ou onde for logado o `stream_message_id`). Se houver fallback para `BackgroundTasks`, o log indicará.

### 4.3 Redis Stream

**Publicação (XADD):**

- `redis_manager.add_message_to_stream(message_data, original_chat_id, trace_id)` em `webhooks.py`.
- Em caso de falha, retorna `None` e o código usa `background_tasks.add_task(process_whatsapp_message, ...)` (fallback).
- **Validar:** Log de sucesso do XADD (ex.: “[RedisStream] Mensagem adicionada ao stream”) ou tratamento de `stream_message_id is None`.
- **Instrumentação:** Logar `trace_id`, `stream_id` retornado e tamanho de `message_data` ao adicionar ao stream.

**Consumo (XREADGROUP):**

- Consumer em loop em `message_stream_consumer.py` lendo `stream:messages` com o consumer group.
- **Validar:** Comando Redis: `XINFO GROUPS stream:messages` e `XPENDING stream:messages gas-workers` para ver se há mensagens não confirmadas e quantos consumers existem.
- Logs: `[CONSUMER_NEW_RECEIVED]`, `[CONSUMER_MESSAGE_RECEIVED]` com `trace_id`, `stream_id`, `phone`, `message_id`.

### 4.4 Consumer

- **Ativo:** Log periódico de leitura (ex.: “consumer_new_received”) ou métrica de processamento.
- **Pending:** `XPENDING stream:messages gas-workers [- + count]` e depois `XRANGE stream:messages - +` para ver último ID.
- **Múltiplos consumers:** `XINFO CONSUMERS stream:messages gas-workers` — vários consumers é esperado; o importante é que pelo menos um esteja processando e fazendo XACK.
- **Bug conhecido no consumer:** Em `_process_batch`, após extrair `trace_id`, `phone`, `msg_id` do payload, três linhas **sempre** sobrescrevem: `trace_id = f"trace-{event_id_str[:8]}"`, `phone = None`, `msg_id = None`. Isso estraga o contexto de log e pode afetar qualquer lógica que dependa de `phone`/`msg_id` no contexto. O `process_message(stream_id, data)` recebe `data` completo, então o conteúdo processado está correto; o problema é só contexto de log/trace. Recomendação: remover essas três atribuições fora do `except` ou movê-las apenas para o ramo “em caso de erro na extração”.

### 4.5 Flow Engine V2

- **Fluxo carregado:** O “fluxo” é o `handler_registry` (mapeamento estado → handler) em `handler_registry.py`; não há JSON de fluxo externo. Validar que o app sobe sem erro ao importar `get_handler_registry()` e que todos os estados usados têm handler.
- **Estado inicial:** Se não há contexto no Redis, `_load_contexts` cria `ConversationContext(phone, current_state=ConversationState.GREETING_INITIAL)`. Estado inicial está hardcoded.
- **Transições:** Definidas pelo handler via `HandlerResult(next_state=...)`. Não há “condition evaluator” separado; a lógica está nos handlers.
- **Instrumentação:** Já existem logs como `[trace_id] Processando mensagem`, `[trace_id] NLU detectou: ...`, `[trace_id] Executando handler: ...`. Adicionar log explícito do `current_state` antes de `handler_registry.get(current_state)` e do `handler.__class__.__name__`.

### 4.6 Banco de dados

- **Flow Engine V2 não usa** “flow_version” nem “flow_assignment”. Usa:
  - **Redis:** chaves `conversation:{phone}`, `order:{phone}` (e possivelmente customer cache).
  - **PostgreSQL:** tabelas `Customer` (por phone), `Order`, etc., acessadas pelos handlers (ex.: `_get_customer_by_phone`, `_get_last_order`).
- **Validar:** Conexão Redis (ex.: health check ou `redis.ping()`); conexão PostgreSQL (session); se o handler faz query (ex.: Customer por phone), verificar se a tabela existe e se o formato de `phone` (ex.: com/sem sufixo @c.us) é o esperado.
- **Snapshot:** No V2, “snapshot” seria o estado serializado no Redis; se estiver corrompido, `get_conversation_context` pode lançar ao fazer `json.loads` ou ao construir `ConversationContext`. Tratar exceção e logar o conteúdo da chave.

### 4.7 Response builder

- **Onde:** `flow_engine_v2._finalize_response()` itera `result.responses` (cada um é `MessageResponse` com `text`, `buttons`, `image_url`, `image_base64`, `footer`). Não usar `response.type` nem `response.media_url` (não existem em `MessageResponse`); usar `getattr(response, "image_url", None)` e derivar `type` (ex.: "image" se houver imagem, senão "text").
- **Resposta vazia:** Se `result.responses` for lista vazia, o webhook não envia nada ao usuário (não envia a mensagem de erro); a mensagem de erro só é enviada quando há **exceção**. Portanto, “resposta vazia” não explica o “Desculpe, ocorreu um erro” — a menos que em algum caminho se force uma exceção (ex.: acesso a atributo inexistente em `result`).
- **Erro silencioso:** Se o handler retornar respostas válidas mas `_finalize_response` lançar (ex.: AttributeError em `response`), isso é exceção e cai no fallback. Log com `exc_info=True` no `except` do `process_message` do V2 mostra o ponto exato.

---

## 5. Etapa 3 — Instrumentação obrigatória

### 5.1 Logs estruturados por camada

Recomendação: usar um único formato de `extra` para todos os passos, incluindo sempre que possível:

- `trace_id`
- `phone` (ou `chat_id`)
- `message_id`
- `step` (nome do passo, ex.: `webhook_received`, `stream_added`, `lock_acquired`, `flow_engine_start`, `flow_engine_complete`, `processing_error`)

Assim dá para filtrar por `trace_id` e reconstruir o caminho da mensagem.

### 5.2 Onde colocar cada log

| O que logar | Onde | Arquivo |
|-------------|------|--------|
| Entrada webhook (event, session, payload keys) | Início do handler do POST | `webhooks.py` |
| trace_id gerado no webhook | Após gerar trace_id | `webhooks.py` |
| chat_id após LID | Após resolução de LID | `webhooks.py` |
| stream_id retornado pelo XADD | Após add_message_to_stream | `webhooks.py` ou `database.py` |
| Entrada em process_whatsapp_message (phone, content, trace_id) | Início de process_whatsapp_message | `webhooks.py` |
| Lock adquirido (lock_id, normalized_phone) | Após acquire_phone_lock | `webhooks.py` |
| Antes de flow_engine.process_message (phone, content, trace_id) | Imediatamente antes do await | `webhooks.py` |
| Saída de flow_engine (responses count, new_state) | Imediatamente após o await (no try) | `webhooks.py` |
| result.context / result.new_state (para debug) | Após process_message (se não houver exceção) | `webhooks.py` |
| Exceção completa (tipo, mensagem, stacktrace) | No except que envia “Desculpe, ocorreu um erro” | `webhooks.py` (já existe com exc_info=True) |
| Estado atual antes de buscar handler | Em process_message do V2 | `flow_engine_v2.py` |
| Handler escolhido (nome da classe) | Após handler_registry.get | `flow_engine_v2.py` |
| Entrada em _finalize_response (len(responses)) | Início de _finalize_response | `flow_engine_v2.py` |
| Erro no V2 (dentro do except) | No except de process_message do V2 | `flow_engine_v2.py` |

### 5.3 Exceção completa

No bloco `except Exception as e` em `process_whatsapp_message` (webhooks.py) já existe:

```python
logger.error(..., exc_info=True, extra={...})
```

Isso registra o stacktrace completo. Para diagnóstico, garantir que esse log não seja filtrado (nível INFO/ERROR ativo para o logger do app) e que os logs estejam acessíveis (ex.: stdout no Docker ou arquivo coletado por Promtail/Loki). Opcional: em ambiente de debug, logar também `repr(e)` e `type(e).__name__` na mensagem para facilitar grep.

---

## 6. Etapa 4 — Causas mais prováveis (ordem)

Com base no comportamento “sempre erro ao dizer ola boa tarde” e no código atual:

1. **AttributeError em Response Builder (`_finalize_response`)**  
   - **Por quê:** `MessageResponse` não tem `type` nem `media_url`. Usar `response.type` ou `response.media_url` gera AttributeError. Já houve correção nesse sentido; garantir que não reste nenhum uso desses atributos em `_finalize_response`.

2. **Interface do wrapper incompatível com o webhook**  
   - **Por quê:** O webhook chama `flow_engine.process_message(..., trace_id=trace_id)` e usa `result.context.waha_chat_id`, `result.context.state`, `result.new_state`. Se o wrapper não aceitar `trace_id` ou não retornar um objeto com `context` e `new_state`, ocorre TypeError ou AttributeError. Já houve correção; validar que o wrapper exportado é o que tem essas adaptações.

3. **Exceção no handler (ex.: GreetingInitialHandler)**  
   - **Por quê:** “Ola boa tarde” cai em GREETING_INITIAL; o handler chama `_get_customer_by_phone(conversation_context.phone)`. Se o formato de `phone` (ex.: `5541999999999@c.us`) não bater com o que está no banco, ou se a sessão do DB falhar, a exceção sobe e cai no fallback.
   - **Como verificar:** Stacktrace com `_get_customer_by_phone` ou `AsyncSessionLocal`/`select(Customer)`.

4. **Redis indisponível ou contexto corrompido**  
   - **Por quê:** `context_manager.get_conversation_context` ou `save_conversation_context` pode falhar (conexão, timeout, JSON inválido). O V2 trata Redis opcional (retorna None); mas se Redis estiver configurado e falhar no meio, pode lançar.
   - **Como verificar:** Stacktrace em `context_manager.py` ou erros de conexão Redis nos logs.

5. **Consumer não repassando trace_id / contexto**  
   - **Por quê:** Se o consumer sobrescreve `trace_id` ou não repassa `trace_id` no payload do stream, o `process_whatsapp_message` pode usar um trace_id diferente ou o contexto de log fica inconsistente; isso não costuma causar exceção sozinho, mas o bug de sobrescrever `phone`/`msg_id` no consumer pode indicar outros descuidos. Menos provável como causa direta da mensagem de erro.

6. **Handler não encontrado**  
   - **Por quê:** Estado inesperado ou enum diferente do registrado. Há fallback para ERROR_RECOVERY; só daria exceção se ERROR_RECOVERY também não estiver registrado. Menos provável se o registry estiver fechado.

7. **Timeout (Redis/PostgreSQL/WAHA)**  
   - **Por quê:** Rede ou serviço lento. Menos provável se o erro for imediato e consistente.

---

## 7. Etapa 5 — Plano de isolamento

### 7.1 Isolar backend do Redis (stream)

- **Objetivo:** Ver se o erro está na publicação/consumo do stream ou no processamento em si.
- **Passos:**
  1. Desabilitar temporariamente o consumer (ex.: não iniciar a task do `MessageStreamConsumer` no `main.py` ou usar feature flag).
  2. No webhook, quando `add_message_to_stream` retornar None (ou por flag), chamar diretamente `await process_whatsapp_message(message=..., original_chat_id=...)` no mesmo processo (sem stream).
  3. Enviar “ola boa tarde” e ver se a exceção e o log `[PROCESSING_ERROR]` aparecem da mesma forma.
- **Interpretação:** Se o erro continuar, a falha está em `process_whatsapp_message` / Flow Engine / WAHA send, não no Redis Stream nem no consumer.

### 7.2 Isolar Flow Engine (sem WAHA)

- **Objetivo:** Ver se o erro está no Flow Engine ou no envio.
- **Passos:**
  1. Criar um endpoint de teste (ex.: POST `/internal/test-flow`) que recebe `phone` e `message`, chama `flow_engine.process_message(phone, message, trace_id="test-...")` e retorna JSON com `responses`, `result.context` (se existir), `result.new_state` e qualquer exceção capturada (tipo, mensagem, traceback em string).
  2. Chamar esse endpoint com `phone=5541999999999` e `message=ola boa tarde` (sem passar pelo webhook nem pelo consumer).
  3. Se o endpoint retornar 200 com respostas, o Flow Engine está ok e o problema está no webhook/consumer/WAHA. Se o endpoint retornar 500 ou exceção no JSON, o stacktrace aponta para a camada exata (wrapper, V2, handler, context_manager).

### 7.3 Simular execução local sem WAHA

- **Objetivo:** Eliminar rede e WAHA como variáveis.
- **Passos:**
  1. No mesmo endpoint de teste acima, após `flow_engine.process_message`, não chamar `send_responses`; apenas retornar as respostas no JSON.
  2. Ou rodar um script local que usa `AsyncSessionLocal` e Redis (ou mocks) e chama apenas `get_flow_engine_v2()` e `engine.process_message(phone, "ola boa tarde", trace_id="local")` e imprime o resultado ou exceção.
- **Interpretação:** Se falhar sem WAHA, a causa é Flow Engine ou dependências (Redis/DB).

### 7.4 Executar fluxo manual com input mockado

- **Objetivo:** Testar só o V2 com contextos controlados.
- **Passos:**
  1. Script ou teste que:
     - Cria `ConversationContext(phone="5541999999999", current_state=ConversationState.GREETING_INITIAL)`.
     - Chama `GreetingInitialHandler().handle(message="ola boa tarde", conversation_context=..., customer_context=None, order_context=None, entities=None)`.
     - Verifica o `HandlerResult` (responses, next_state).
  2. Se quiser testar com Redis/DB reais, usar o mesmo `ContextManager` e `get_conversation_context`/`save_conversation_context` com um phone fixo.
- **Interpretação:** Se o handler falhar aqui, a causa é handler ou DB (ex.: modelo Customer, formato de phone). Se passar, o problema está na orquestração (wrapper, _finalize_response, ou formato de retorno).

### 7.5 Verificar sem infraestrutura (mocks)

- **Objetivo:** Isolar falha de código puro (ex.: AttributeError em objeto).
- **Passos:**
  1. Teste unitário que instancia `MessageResponse(text="Oi", buttons=None)` e chama a lógica de formatação de `_finalize_response` (extrair para função pura se necessário) e verifica que não acessa `.type` nem `.media_url`.
  2. Teste que o objeto retornado por `FlowEngineWrapper._adapt_response(...)` possui `context` e `new_state` e que `context` tem `waha_chat_id` e `state`.
- **Interpretação:** Elimina causas puramente de contrato de tipos/atributos.

---

## 8. Resultado esperado: diagnóstico e checklist

### 8.1 Diagnóstico provável (resumo)

- A mensagem “Desculpe, ocorreu um erro. Digite menu para recomeçar.” é enviada **apenas** quando uma exceção é capturada no `try` de `process_whatsapp_message` (webhooks.py).
- As causas mais prováveis já identificadas neste projeto foram:
  - **AttributeError** em `_finalize_response` (uso de `response.type` / `response.media_url` em `MessageResponse`).
  - **TypeError/AttributeError** no wrapper (falta de `trace_id` na assinatura e falta de `result.context` / `result.new_state` no retorno).
- Se essas correções já foram aplicadas e o erro persiste, o próximo passo é **obrigatoriamente** inspecionar o log com `[PROCESSING_ERROR]` e o stacktrace para ver o tipo e a linha exata da exceção.

### 8.2 Checklist técnico

- [ ] Confirmar que o log `[PROCESSING_ERROR]` aparece ao reproduzir o problema e que o stacktrace está visível.
- [ ] Identificar `type(e).__name__` e o arquivo/linha do traceback (ex.: `flow_engine_v2.py`, `_finalize_response`; ou `handlers_v2/greeting_handlers.py`; ou `context_manager.py`).
- [ ] Confirmar que `FlowEngineWrapper` aceita `trace_id` e `waha_chat_id` e retorna objeto com `context` e `new_state`.
- [ ] Confirmar que `_finalize_response` não acessa `response.type` nem `response.media_url`; usar apenas atributos de `MessageResponse` (text, buttons, image_url, etc.).
- [ ] Testar endpoint interno que chama apenas `flow_engine.process_message(phone, "ola boa tarde", trace_id="...")` e retorna JSON (sem consumer, sem WAHA).
- [ ] Verificar Redis e PostgreSQL (health/logs) durante uma mensagem que falha.
- [ ] Corrigir o bug no consumer que sobrescreve `trace_id`, `phone` e `msg_id` após extração bem-sucedida (para não atrapalhar logs e possíveis usos futuros do contexto).

### 8.3 Estratégia para provar a causa

1. Reproduzir “ola boa tarde” em ambiente com logs completos (stdout ou arquivo).
2. Buscar pela última ocorrência de `[PROCESSING_ERROR]` com o `trace_id` daquela requisição (ou pelo horário próximo).
3. No stacktrace, anotar o primeiro frame que pertence ao código da aplicação (não asyncio/lib); esse frame é a camada onde a exceção foi levantada.
4. Se for AttributeError/TypeError, corrigir o contrato (atributos/assinatura) naquela camada e repetir o teste.
5. Se for exceção de Redis/DB/WAHA, tratar conexão, timeout ou dados (ex.: formato de phone, schema).

### 8.4 Estratégia para corrigir sem quebrar produção

1. **Não alterar** o texto da mensagem de erro nem remover o `except` que a envia; manter fallback para o usuário.
2. Adicionar instrumentação (logs com `trace_id`, `step`, estado, handler) em nível DEBUG ou INFO e deploy em staging/canary; depois ativar em produção com amostragem se necessário.
3. Corrigir apenas o ponto indicado pelo stacktrace (ex.: um único arquivo/função); evitar refatorações grandes em paralelo.
4. Manter o endpoint de teste (`/internal/test-flow` ou similar) atrás de auth ou apenas em ambientes não produtivos, para não expor dados.
5. Após a correção, rodar teste automatizado que simula “ola boa tarde” (endpoint de teste ou teste e2e com stream mockado) e verificar que a resposta é a esperada e que não há exceção.

---

## Referência rápida — Arquivos e linhas

| O quê | Arquivo | Linha (aprox.) |
|-------|---------|-----------------|
| Envio da mensagem de erro ao usuário | `api/webhooks.py` | 824-826 |
| Bloco except que captura a exceção | `api/webhooks.py` | 807-835 |
| Chamada ao flow_engine.process_message | `api/webhooks.py` | 720-726 |
| Uso de result.context e result.new_state | `api/webhooks.py` | 750-751, 797, 802 |
| FlowEngineWrapper.process_message | `core/flow_engine.py` | 33-63 |
| FlowEngineV2.process_message | `core/flow_engine_v2.py` | 65-192 |
| _finalize_response (formatação das respostas) | `core/flow_engine_v2.py` | 340-429 |
| MessageResponse (atributos: text, buttons, image_url, footer) | `core/handlers_v2/base.py` | 21-32 |
| add_message_to_stream (XADD) | `database.py` | 234-296 |
| Consumer process_message → process_whatsapp_message | `services/message_stream_consumer.py` | 127-191, 524 |
| Extração trace_id/phone/msg_id no consumer (bug overwrite) | `services/message_stream_consumer.py` | 466-505 |

Com isso, você tem um mapa exato do pipeline, onde o erro é gerado, como classificar a falha, como debugar por camada, onde instrumentar e como isolar e corrigir sem quebrar produção.
