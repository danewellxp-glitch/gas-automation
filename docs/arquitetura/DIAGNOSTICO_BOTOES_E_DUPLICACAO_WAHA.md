# Diagnóstico e arquitetura: botões WAHA Plus e duplicação de mensagens

**Objetivo:** Solução arquitetural para (1) botões interativos não aparecerem no WhatsApp e (2) mensagens duplicadas, sem gambiarras.

---

## PARTE 1 — BOTÕES WAHA PLUS

### 1.1 Diferença WAHA Core vs Plus vs WebJS

| Aspecto | WAHA Core | WAHA Plus | WebJS (engine) |
|--------|-----------|-----------|----------------|
| Botões | `POST /api/sendButtons` (deprecated) | `POST /api/send/buttons/reply` (Plus only) | Limitações do WhatsApp Web |
| Listas | `POST /api/sendList` | Idem (➕) | Idem |
| sendButtons | Retorna 501 em Plus | Não usado em Plus | - |
| send/buttons/reply | Não existe | Existe; **semantic**: "Reply on a button message" no OpenAPI | - |

**Ponto crítico:** O endpoint Plus **não serve para enviar nova mensagem com botões.** Ele é "Reply on a button message": usado quando o **usuário já clicou** um botão e o backend envia uma resposta referenciando esse clique.

### 1.2 Formato esperado pelos endpoints

**Enviar nova mensagem com botões:** `POST /api/sendButtons` (Core, deprecated; em Plus retorna 501)

```json
{
  "session": "default",
  "chatId": "5541999999999@c.us",
  "text": "Escolha uma opção",
  "buttons": [
    { "id": "opt1", "text": "Opção 1" },
    { "id": "opt2", "text": "Opção 2" }
  ]
}
```

**Responder ao clique do usuário em um botão:** `POST /api/send/buttons/reply` (Plus) — schema **MessageButtonReply** (Swagger):

```json
{
  "chatId": "11111111111@c.us",
  "replyTo": null,
  "selectedDisplayText": "string",
  "selectedButtonID": "string",
  "session": "default"
}
```

- `replyTo`: messageId da mensagem de botão à qual se responde.
- `selectedButtonID`: id do botão que o usuário clicou.
- `selectedDisplayText`: texto exibido do botão clicado.

Ou seja: este endpoint é para **responder** quando o usuário clica num botão (ex.: enviar confirmação), **não** para enviar uma nova mensagem com 3 botões. Por isso o backend usa apenas `/api/sendButtons` para “enviar botões”; em Plus cai em fallback (texto numerado).

### 1.3 text vs body

- **Core** usa `text` em sendText e SendButtonsRequest.
- **Plus** em alguns endpoints usa `body`; o MessageButtonReply usa `selectedDisplayText`/`selectedButtonID`, não `body`/`buttons` para enviar nova mensagem com botões.

### 1.4 Limitações reais do WhatsApp (WebJS)

- **Botões:** Máximo 3 botões; texto do botão até 20 caracteres; só em chats 1:1 (não em grupos em algumas versões).
- **List messages:** Seções e linhas com limites de tamanho.
- **Contexto:** Algumas APIs exigem que a mensagem seja enviada “no contexto” da conversa (sessão ativa, chat aberto). Falhas silenciosas podem ocorrer se o chatId estiver errado (ex.: enviar com @lid quando o servidor espera @c.us após resolver).

### 1.5 Checklist de verificação — Botões

1. **Enviar nova mensagem com botões:** Usar apenas `POST /api/sendButtons` (payload: chatId, session, text, buttons). Em WAHA Plus retorna 501 → fallback em texto numerado.
2. **Responder ao clique do usuário:** Usar `POST /api/send/buttons/reply` com MessageButtonReply (chatId, session, replyTo, selectedButtonID, selectedDisplayText).
3. **LID:** Para envio usar sempre `chatId` resolvido para @c.us (`_get_chat_id`/`resolve_lid`).

### 1.6 Estratégia de envio de botões (implementada)

1. **Uma tentativa:** `POST /api/sendButtons` com payload Core (text, buttons). Se 501/404/erro → fallback em texto numerado.
2. **Não usar** `/api/send/buttons/reply` para “enviar botões”: esse endpoint é só para “reply on button message” (resposta ao clique).
3. **Fallback:** `_send_buttons_as_text` envia texto com opções numeradas (1. Opção A, 2. Opção B, …).

### 1.7 Onde os botões aparecem no fluxo (já definidos no código)

Não é necessário especificar de novo onde os botões devem aparecer: os handlers já definem `buttons` nos pontos abaixo. Quando o WAHA suportar envio de nova mensagem com botões, esses pontos passarão a exibir botões; hoje saem como texto numerado.

| Momento no fluxo | Handler / estado | Conteúdo dos botões |
|------------------|------------------|----------------------|
| Menu principal | greeting (returning), support, checkout, ordering | `get_quick_replies("main_menu")` → Fazer Pedido, Meus Pedidos, Atendente |
| Tipo de cliente (PF/PJ) | greeting (GREETING_NEW), identify | `get_quick_replies("customer_type")` → Pessoa Física, Empresa |
| Escolha de produto | ordering_handlers | Botões por produto (P13, P20, P45, etc.) |
| Método de pagamento | checkout, ordering | `payment_methods_pf` / `payment_methods_pj` |
| Confirmações / fim de passo | Vários | Sim/Não, Voltar ao menu, etc. |

Ou seja: **não é preciso mapear de novo**; os pontos do fluxo que têm opções limitadas já usam `buttons` em `_create_response`. A limitação atual é só do WAHA Plus (501 em sendButtons → fallback texto).

---

## PARTE 2 — DUPLICAÇÃO DE MENSAGENS

### 2.1 Cenários técnicos possíveis

| Cenário | Descrição | Como identificar |
|--------|-----------|-------------------|
| Webhook chamado 2x | WAHA reenvia o mesmo evento (retry, rede) | Mesmo `message_id` nos logs em dois requests; dedup no webhook deve rejeitar o segundo |
| Mesmo message_id processado 2x | Entrada duplicada no stream ou consumer reprocessa | Logs com mesmo `message_id` em dois `PROCESSING_STREAM_START` ou dois `FLOW_ENGINE_START` |
| Flow Engine retorna 2 respostas | Handler devolve lista + botões (ou 2 mensagens) no mesmo `result.responses` | Logs `responses_count=2` e dois `[SEND_RESPONSE]` consecutivos |
| Webhook + Redis consumer ambos ativos | Webhook coloca no stream e também processa em background | Não ocorre no fluxo atual: ou stream ou fallback BackgroundTask |
| Retry WAHA | WAHA faz retry do webhook; segundo request com mesmo payload | Dedup por `message_id` no webhook (SET NX) evita reprocessar |
| Race condition | Dois workers pegam a mesma mensagem do stream | Consumer group Redis garante entrega a um único consumer; XACK após sucesso |
| Processamento não idempotente | Nenhum lock por message_id no processamento; bug ou duplicata no stream gera 2 respostas | Mesmo message_id gera 2 envios; falta de lock por message_id no `process_whatsapp_message` |
| Async handler executando 2x | Dupla inscrição ou dupla chamada do consumer | Logs de consumer com mesmo stream_id processado 2x |

### 2.2 Deduplicação superficial vs idempotência real

- **Deduplicação superficial:** Evitar que o **mesmo evento de entrada** (mesmo request do webhook) entre duas vezes no sistema. Hoje: `check_message_processed(message_id)` no webhook com Redis SET NX + TTL (1h). Quem chama primeiro “marca” o message_id; segundo retorna “duplicata” e não adiciona ao stream.
- **Dedup por conteúdo (phone + texto):** `check_recent_same_content(phone, body, window_sec=5)` no webhook: se o mesmo número enviar o mesmo texto nos últimos 5 segundos, não adiciona ao stream. Evita múltiplas entregas do mesmo "1" com message_ids diferentes (WAHA/rede).
- **Idempotência real:** Garantir que **o efeito de processar a mensagem X (message_id)** seja aplicado **no máximo uma vez**, mesmo que:
  - o mesmo message_id apareça em mais de uma entrada do stream (bug ou reprocessamento), ou
  - dois processos (ex.: fallback e stream) tentem processar o mesmo id.  
  Isso exige um **lock de processamento** por `message_id`: só quem obtiver o lock processa; os outros desistem (e, se for stream, podem dar XACK para não reprocessar infinitamente).

### 2.3 Arquitetura correta de idempotência

1. **Ingress (webhook):**  
   - Manter dedup por `message_id` (SET NX, TTL 1h) **antes** de adicionar ao stream.  
   - Retornar 200 rápido; não processar no request do webhook (apenas enfileirar).

2. **Stream (consumer):**  
   - Uma única fonte de verdade: apenas o consumer processa mensagens (stream ou fallback em memória quando stream falha).  
   - Não ter dois caminhos que processem o mesmo message_id (ex.: webhook síncrono + stream).

3. **Processamento (process_whatsapp_message):**  
   - **Lock por message_id:** Antes de qualquer lógica de negócio, tentar adquirir `lock:process:{message_id}` com NX e TTL (ex.: 60s).  
   - Se não conseguir: considerar a mensagem já em processamento ou já processada → sair sem enviar resposta (idempotente).  
   - Se conseguir: processar; ao terminar (sucesso ou falha após envio), manter o lock até expirar (ou deletar opcionalmente). Não liberar antes de terminar de enviar, para evitar que outra instância processe o mesmo id.

4. **Envio:**  
   - Um handler deve preferir retornar **uma única resposta** por passo (lista **ou** botões, não os dois em sequência para o mesmo CTA).  
   - Se o fluxo de negócio exigir duas mensagens (ex.: “Instruções PIX” + “Resumo com botões”), são duas respostas distintas e válidas; a regra “não enviar botões logo após lista” no `send_responses` evita o caso “lista + botões redundantes” no mesmo passo.

### 2.4 Modelo de bloqueio por message_id com TTL

- **Chave:** `lock:process:{message_id}`  
- **Valor:** identificador do worker/request (ex.: `trace_id` ou `consumer_name`) para debug.  
- **Comando:** `SET key value NX EX 60`  
- **Comportamento:**  
  - Retorna True se o lock foi adquirido (primeira vez para esse message_id no TTL).  
  - Retorna False se a chave já existir (outro processo já está processando ou processou recentemente).  
- **TTL 60s:** Maior que o tempo típico de processamento (flow + envio). Evita lock eterno em crash.  
- Não é necessário “release” explícito; o TTL limpa. Opcionalmente, após enviar com sucesso, pode-se manter a chave com TTL curto (ex.: 10s) para absorver atrasos de rede, mas não é obrigatório.

### 2.5 Fluxo ideal de logs para debugging

- `[WEBHOOK_ENTRY]` + message_id + trace_id  
- `[DEDUP_RESULT]` + message_id + is_duplicate  
- `[STREAM_ADDED]` + stream_id + message_id  
- `[CONSUMER_MESSAGE_RECEIVED]` + stream_id + message_id + consumer  
- `[PROCESS_LOCK_ACQUIRED]` ou `[PROCESS_LOCK_SKIP]` + message_id  
- `[FLOW_ENGINE_START]` + message_id  
- `[FLOW_ENGINE_COMPLETE]` + responses_count  
- `[SEND_RESPONSE]` por resposta (idx, has_buttons, has_list_sections)  
- `[WAHA_SEND_COMPLETE]` sent/failed  
- `[XACK_BEFORE]` / `[XACK_COMPLETE]`

Isso permite ver: se o mesmo message_id entrou duas vezes, se o lock foi pulado, se o flow retornou várias respostas e quantas foram enviadas.

---

## IMPLEMENTAÇÃO PRÁTICA

### Idempotência no processamento

- Em `process_whatsapp_message`, no início (após obter message_id e trace_id):  
  - `acquired = await redis_manager.acquire_process_lock(message_id, ttl=60)`  
  - Se não `acquired`, logar `[PROCESS_LOCK_SKIP]` e return (sem enviar nada).  
  - Caso contrário, seguir com lock por message_id até o fim do processamento (lock expira por TTL).

- Em `database.py` (ou redis_manager):  
  - `acquire_process_lock(message_id: str, ttl: int = 60) -> bool`  
  - Implementação: `SET lock:process:{message_id} {trace_id ou instance_id} NX EX {ttl}`; retornar True se SET retornou True.

### Botões (WAHA)

- **Enviar nova mensagem com botões:** usar apenas `POST /api/sendButtons` (chatId, session, text, buttons). Em Plus retorna 501 → fallback em texto numerado.
- **Não usar** `/api/send/buttons/reply` para isso: esse endpoint é para "Reply on a button message" (replyTo, selectedButtonID, selectedDisplayText).

### Handlers e send_responses

- Manter regra: após enviar uma resposta com `list_sections`, não enviar a próxima se for só `buttons` (evita “lista + botões” duplicados no mesmo passo).  
- Dedup por conteúdo idêntico consecutivo já implementado.

---

## CONCLUSÃO EXECUTIVA

1. **Botões:** O endpoint Plus `POST /api/send/buttons/reply` está documentado como “Reply on a button message”. É essencial validar no Swagger o schema (MessageButtonReply) e se serve para **enviar nova mensagem com botões** ou só para “reply”. Ajustar payload e usar uma tentativa Plus + fallback em texto; em 400 logar resposta para diagnóstico.  
2. **Duplicação:** A duplicação é combatida em três níveis: (a) dedup no webhook por message_id (SET NX); (b) lock de processamento por message_id no `process_whatsapp_message` (idempotência real); (c) regras em `send_responses` para não enviar lista + botões redundantes e mesmo texto duas vezes.  
3. **Arquitetura:** Uma única fila (stream) como entrada do processamento; webhook só enfileira; consumer processa com lock por message_id; envio com uma tentativa correta de botões e fallback limpo.

Com isso evita-se gambiarras e “if para ignorar segunda mensagem”: a segunda tentativa de processar o mesmo message_id é bloqueada pelo lock e os handlers/regras de envio evitam respostas duplicadas no mesmo passo.

---

## Checklist de verificação (produção)

- [ ] **Webhook:** Dedup por `message_id` (SET NX) e por conteúdo recente `last_msg_content:{phone}` (janela 5s) antes de adicionar ao stream; retorno 200 rápido.
- [ ] **Consumer:** Apenas um consumer group processa o stream; XACK após sucesso.
- [ ] **process_whatsapp_message:** Lock `lock:process:{message_id}` no início; se não adquirir, return sem enviar.
- [ ] **Botões:** Uma tentativa Plus; em 4xx/5xx fallback em texto; log de 400 com body para diagnóstico.
- [ ] **send_responses:** Não enviar mesma mensagem duas vezes (conteúdo idêntico); não enviar botões logo após lista no mesmo lote.

## Como testar idempotência

1. Simular dois requests de webhook com o mesmo `message_id` (ex.: script que envia 2x o mesmo payload). O segundo deve retornar `{"status": "duplicate", ...}` e não adicionar ao stream.
2. Injetar no stream duas entradas com o mesmo `message_id` (para teste). Apenas a primeira execução deve passar pelo `PROCESS_LOCK_ACQUIRED` e enviar resposta; a segunda deve logar `PROCESS_LOCK_SKIP` e não enviar.
3. Logs: buscar por `PROCESS_LOCK_SKIP` e `DEDUP_RESULT` para confirmar comportamento.
