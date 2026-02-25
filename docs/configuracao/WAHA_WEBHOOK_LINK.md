# WAHA – Link do Webhook e Teste E2E

## Link do webhook (API WAHA → Backend)

O WAHA envia as mensagens recebidas do WhatsApp para este endpoint do backend:

| Ambiente | URL do webhook |
|----------|----------------|
| **Local (backend na máquina)** | `http://localhost:8000/webhooks/waha` |
| **Docker (interno)** | `http://backend:8000/webhooks/waha` |
| **Com host customizado** | `http://SEU_HOST:8000/webhooks/waha` |

- **Método:** `POST`
- **Content-Type:** `application/json`
- **Corpo:** JSON no formato do WAHA (evento `message`, `session`, `payload` com `from`, `body`, `fromMe`, etc.).

No `docker-compose` o WAHA usa (por padrão):

```yaml
WHATSAPP_HOOK_URL: ${WHATSAPP_HOOK_URL:-http://backend:8000/webhooks/waha}
```

- Se **backend e WAHA** rodam no mesmo Docker: não defina `WHATSAPP_HOOK_URL` (vale `http://backend:8000/webhooks/waha`).
- Se o **backend roda na máquina** (fora do Docker) e o WAHA no Docker: no `.env` defina a URL acessível pelo container, por exemplo:  
  `WHATSAPP_HOOK_URL=http://192.168.10.156:8000/webhooks/waha`  
  (troque pelo IP da máquina onde o backend está).

## Teste ponta a ponta (mensagem → chat do operador)

Script que simula uma mensagem no webhook e confere se ela aparece no chat do operador:

```bash
# Com backend em http://localhost:8000
python backend/scripts/test_waha_webhook_e2e.py

# Backend em outra URL
BACKEND_URL=http://192.168.10.156:8000 python backend/scripts/test_waha_webhook_e2e.py
```

O script:

1. Envia `POST` para `/webhooks/waha` com uma mensagem simulada.
2. Aguarda o processamento em background.
3. Verifica em `GET /api/conversations` e `GET /api/conversations/{id}/messages` se a mensagem aparece.

Se tudo estiver ok, a mensagem deve aparecer no painel do operador (Conversas / Chat).

## Links úteis

- **Health dos webhooks:** `GET http://localhost:8000/webhooks/health`
- **Status da sessão WAHA:** `GET http://localhost:8000/api/waha-status`
- **Dashboard WAHA (se exposto):** `http://localhost:3000` ou `http://waha.localhost` (Traefik)

---

## Bot não responde / nada aparece no Operador > Conversas

**Sintomas:** você manda mensagem no WhatsApp, o bot não responde e nada aparece em Operador > Conversas.

**Causa mais comum:** o WAHA não consegue chamar o backend (webhook nunca chega).

### 1. Backend fora do Docker

Se o backend roda na sua máquina (ex.: `uvicorn` na porta 8000) e o WAHA está no Docker, o container do WAHA **não** resolve o nome `backend`. Ele precisa da URL do host.

No **`.env`** (na raiz do projeto), adicione ou ajuste:

```env
WHATSAPP_HOOK_URL=http://192.168.10.156:8000/webhooks/waha
```

Use o IP da máquina onde o backend está (no mesmo PC use `host.docker.internal:8000` no Mac/Windows, ou o IP da interface; no Linux pode ser `172.17.0.1` ou o IP da sua rede, ex. `192.168.10.156`).

Depois **reinicie o container do WAHA** para carregar a variável:

```bash
docker-compose restart waha
```

### 2. Conferir se o webhook está sendo chamado

Nos **logs do backend**, ao receber algo do WAHA, deve aparecer algo como:

```text
WAHA Webhook recebido: event=message session=default payload_keys=[...]
```

- Se **nunca** aparecer `WAHA Webhook recebido` quando você manda mensagem no WhatsApp, o WAHA não está conseguindo chamar o backend (veja passo 1, firewall, ou se a sessão foi iniciada com webhook).
- Se aparecer `event=message` mas `fromMe=true` e "ignorando mensagem própria", você está mandando do mesmo número que está conectado no WAHA; use outro número para testar.

### 3. Teste manual do webhook

Confirme que o backend responde ao webhook:

```bash
BACKEND_URL=http://192.168.10.156:8000 python3 backend/scripts/test_waha_webhook_e2e.py
```

Se esse teste passar, o fluxo backend → EventLog → Operador está ok; o problema é só o WAHA não chamar a URL (passo 1).

### 4. Robô não responde no WhatsApp (webhook chega, mas envio falha com 422)

**Sintoma:** mensagem aparece no Operador > Conversas, mas o robô não responde no WhatsApp.

**Causa:** a sessão WAHA está **STOPPED**. O backend recebe o webhook e processa, mas ao enviar a resposta o WAHA retorna 422 (Session status is not as expected, status: STOPPED).

**Solução:** iniciar a sessão e garantir que o webhook está na config da sessão:

```bash
# 1) Atualizar sessão com webhook (se ainda não tiver)
curl -s -X PUT "http://192.168.10.156:3000/api/sessions/default" \
  -H "X-Api-Key: gasautomation123" \
  -H "Content-Type: application/json" \
  -d '{"name":"default","config":{"webhooks":[{"url":"http://backend:8000/webhooks/waha","events":["message","message.ack","session.status"]}]}}'

# 2) Iniciar a sessão
curl -s -X POST "http://192.168.10.156:3000/api/sessions/default/start" \
  -H "X-Api-Key: gasautomation123" \
  -H "Content-Type: application/json"

# 3) Verificar status (deve mostrar "status": "WORKING" após alguns segundos)
curl -s "http://192.168.10.156:3000/api/sessions/default" -H "X-Api-Key: gasautomation123"
```

Depois de **WORKING**, envie uma nova mensagem no WhatsApp; o robô deve responder. Se a sessão voltar a STOPPED após reiniciar o container WAHA, repita o passo 2 (start).
