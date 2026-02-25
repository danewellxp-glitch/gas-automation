# Como ativar botões reais no WhatsApp (WAHA)

Este guia explica a limitação atual dos botões no WAHA Plus e **o que você pode fazer** para ter botões de verdade (em vez do texto numerado).

---

## O que já está implementado no nosso backend

- Os handlers já definem **botões** em todos os pontos certos (menu, PF/PJ, produtos, pagamento, etc.).
- O cliente WAHA chama `POST /api/sendButtons` com `chatId`, `text`, `buttons` (até 3).
- Se a API retornar **501** (ou 404), o backend faz **fallback em texto numerado** automaticamente.

Ou seja: **não falta implementar botões no fluxo**. O que falta é a **API do WAHA aceitar** o envio de nova mensagem com botões.

---

## Por que hoje sai texto numerado?

| Item | Situação |
|------|----------|
| **WAHA Core** | `POST /api/sendButtons` existe mas está **deprecated** e pode retornar **501** (Not Implemented). |
| **WAHA Plus** | Não expõe endpoint para **enviar nova mensagem com botões**. O endpoint `POST /api/send/buttons/reply` é só para **responder ao clique** do usuário (replyTo, selectedButtonID, selectedDisplayText), não para enviar uma mensagem nova com 3 botões. |

Por isso, ao chamar `sendButtons`, o Plus devolve 501 e o backend cai no fallback (texto com "1. Opção A", "2. Opção B", etc.).

---

## O que você pode fazer

### 1. Verificar no Swagger do seu WAHA Plus

Se você tem acesso ao container Plus:

1. Abra o Swagger do WAHA (ex.: `http://<seu-waha>:3000/docs` ou a URL que você usa).
2. Procure por algo como:
   - **Send buttons** / **Send interactive message** / **sendButtons**
   - Ou um endpoint que aceite `buttons` no body para **enviar** (não só "reply").
3. Se existir um endpoint para **enviar** nova mensagem com botões:
   - Anote o path (ex.: `POST /api/...`) e o body esperado.
   - Podemos adicionar no `waha.py` uma tentativa com esse endpoint antes do fallback.

Se não houver nenhum endpoint para “enviar botões”, a limitação é do próprio WAHA Plus.

---

### 2. Pedir suporte de “enviar botões” ao projeto WAHA

- Abrir um **feature request** ou discussão no repositório: [devlikeapro/waha](https://github.com/devlikeapro/waha).
- Pedir: endpoint no **Plus** para **enviar nova mensagem com botões** (não só “reply on button message”).
- Quando eles disponibilizarem (novo endpoint ou `sendButtons` passando a funcionar no Plus), nosso código já chama `send_buttons()`; em muitos casos basta o WAHA passar a retornar 200 em vez de 501, ou precisamos só adicionar uma segunda tentativa com o novo path no `waha.py`.

---

### 3. Testar com WAHA Core (se for viável)

- No **Core**, `POST /api/sendButtons` às vezes ainda funciona (depende da engine/versão).
- Se você puder usar uma sessão com **Core** só para testar:
  - Apontar `WAHA_URL` (e sessão) para esse Core.
  - Se o Core aceitar `sendButtons`, os botões devem aparecer sem mudar nosso fluxo.

Isso não “implementa” botões no Plus; só confirma que a lógica do nosso backend está correta.

---

### 4. Usar WhatsApp Business API (Meta Cloud API)

- A **API oficial** do Meta suporta mensagens interativas (botões, listas) em templates e em fluxos de conversa.
- Exige outra integração (Cloud API em vez de WAHA); não é “ativar um switch” no WAHA Plus.

Só vale se a decisão for migrar o canal de WhatsApp para a API oficial.

---

## Resumo prático

| Sua pergunta | Resposta |
|--------------|----------|
| Preciso implementar algo novo no fluxo? | **Não.** Botões já estão definidos nos handlers; o envio já usa `send_buttons()` e fallback em texto. |
| O que falta para aparecer botão de verdade? | O **WAHA Plus** (ou o engine que você usa) precisar **aceitar** o envio de nova mensagem com botões (endpoint que hoje retorna 501 ou não existe). |
| O que fazer agora? | (1) Checar o Swagger do Plus por endpoint de “send buttons”; (2) Se não houver, pedir ao WAHA um endpoint para isso; (3) Opcional: testar com Core para validar nosso código. |

Quando o WAHA tiver um endpoint que **envie** nova mensagem com botões (seja o mesmo `sendButtons` retornando 200 ou um endpoint novo), podemos, se necessário, adicionar no `waha.py` uma tentativa com o path/body correto; o restante do fluxo já está pronto.
