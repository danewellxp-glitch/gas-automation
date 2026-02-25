# Guia: Resolver @lid para Numero Real do Cliente com WAHA

## O Problema

O WhatsApp usa internamente um formato chamado **LID (Linked ID)** para identificar contatos. Em vez de retornar o numero real do telefone (ex: `5511999998888`), o WAHA retorna IDs no formato:

```
5521912345678-1234567890@lid
```

Isso faz com que na interface do sistema apareca esse ID criptico em vez do numero real do cliente.

## A Solucao

A resolucao e feita usando o **endpoint `/api/contacts` do WAHA**, que recebe um `contactId` (no formato @lid) e retorna as informacoes reais do contato, incluindo o numero de telefone.

---

## Implementacao Passo a Passo

### 1. Servico de Resolucao de Contato

Crie um metodo que chama a API do WAHA para resolver o LID:

```typescript
/**
 * Resolve um chatId do WAHA (formato @lid ou @c.us) para o numero real do telefone.
 *
 * ENDPOINT WAHA: GET /api/contacts?session={session}&contactId={contactId}
 *
 * O WAHA retorna um objeto com o campo "number" contendo o telefone real.
 */
async getContactInfo(contactId: string): Promise<{
  number: string;           // Numero real do telefone (ex: "5511999998888")
  pushname: string | null;  // Nome que o cliente definiu no WhatsApp
  name: string | null;      // Nome salvo na agenda (se houver)
  isBusiness: boolean;      // Se e conta business
  profilePictureURL: string | null;
} | null> {
  try {
    // CHAMADA PRINCIPAL - Resolve LID para numero real
    const res = await axios.get(`${WAHA_API_URL}/api/contacts`, {
      params: {
        session: WAHA_SESSION,  // ex: "default"
        contactId: contactId    // ex: "5521912345678-1234567890@lid"
      },
      headers: { 'X-Api-Key': WAHA_API_KEY },
    });

    const d = res.data;

    // OPCIONAL: Buscar foto de perfil (endpoint separado)
    let profilePictureURL: string | null = null;
    try {
      const picRes = await axios.get(
        `${WAHA_API_URL}/api/contacts/profile-picture`,
        {
          params: { session: WAHA_SESSION, contactId },
          headers: { 'X-Api-Key': WAHA_API_KEY },
        },
      );
      profilePictureURL = picRes.data?.profilePictureURL || null;
    } catch {
      // Alguns contatos nao tem foto de perfil - ignorar erro
    }

    return {
      number: d.number || null,      // <-- ESTE E O NUMERO REAL
      pushname: d.pushname || null,
      name: d.name || d.shortName || null,
      isBusiness: d.isBusiness || false,
      profilePictureURL,
    };
  } catch (error) {
    console.warn(`Falha ao resolver contato ${contactId}: ${error.message}`);
    return null;
  }
}
```

### 2. Onde Chamar a Resolucao

Chame `getContactInfo()` em **TODOS** os pontos de entrada de mensagens:

#### A) No Polling (se voce usa polling para buscar mensagens)

```typescript
// Ao processar cada chat com mensagens novas:
const chatId = "5521912345678-1234567890@lid"; // vem do WAHA

// RESOLVER LID -> NUMERO REAL
const contactInfo = await getContactInfo(chatId);

let customerPhone = chatId; // fallback: usa o proprio chatId
if (contactInfo?.number) {
  customerPhone = contactInfo.number; // ex: "5521999998888"
  console.log(`Resolvido: ${chatId} -> ${customerPhone}`);
}

// Usar customerPhone (numero real) para criar/buscar a conversa
```

#### B) No Webhook (se o WAHA envia webhooks)

```typescript
// No handler do webhook de mensagem recebida:
async handleIncomingMessage(payload: any) {
  const chatId = payload.from; // ex: "5521912345678-1234567890@lid"

  // RESOLVER LID -> NUMERO REAL
  const contactInfo = await getContactInfo(chatId);

  let customerPhone = chatId;
  if (contactInfo?.number) {
    customerPhone = contactInfo.number;
  }

  const customerName = contactInfo?.pushname || payload.notifyName || null;

  // Salvar conversa/mensagem usando customerPhone (numero real)
}
```

### 3. Armazenamento no Banco de Dados

A estrategia e:
- **`customerPhone`**: Sempre armazena o **numero real** (resolvido)
- **`metadata.chatId`**: Armazena o **chatId original** (pode ser @lid) para usar ao enviar mensagens de volta

```typescript
// Modelo da conversa (exemplo Prisma)
model Conversation {
  id            String  @id @default(uuid())
  customerPhone String  // NUMERO REAL: "5521999998888"
  customerName  String? // Nome do contato
  metadata      Json?   // { chatId: "...@lid", pushname: "...", isBusiness: false }
  // ...

  @@unique([companyId, customerPhone]) // Unique por numero real
}
```

Ao criar/atualizar a conversa:

```typescript
// Criar nova conversa
const conversation = await prisma.conversation.create({
  data: {
    companyId,
    customerPhone,      // NUMERO REAL resolvido
    customerName,
    metadata: {
      chatId,           // ID original do WAHA (pode ser @lid)
      pushname: contactInfo?.pushname,
      name: contactInfo?.name,
      isBusiness: contactInfo?.isBusiness,
      profilePictureURL: contactInfo?.profilePictureURL,
    },
  },
});
```

### 4. Envio de Mensagens (Resposta ao Cliente)

**IMPORTANTE**: Ao enviar mensagem de volta, use o `chatId` original (do metadata), nao o numero real. O WAHA precisa do chatId original para rotear corretamente:

```typescript
async sendMessage(conversationId: string, text: string) {
  const conversation = await prisma.conversation.findUnique({
    where: { id: conversationId },
  });

  // Usar chatId original (LID) para enviar, com fallback para customerPhone
  const metadata = conversation.metadata as any;
  const sendTo = metadata?.chatId || conversation.customerPhone;

  // Se nao tem @, adicionar @c.us (formato que o WAHA espera)
  const chatId = sendTo.includes('@') ? sendTo : `${sendTo}@c.us`;

  await axios.post(`${WAHA_API_URL}/api/sendText`, {
    session: WAHA_SESSION,
    chatId,
    text,
  }, {
    headers: { 'X-Api-Key': WAHA_API_KEY },
  });
}
```

### 5. Migracao de Conversas Antigas (Backward Compatibility)

Se voce ja tem conversas salvas com o @lid como `customerPhone`, adicione logica de migracao:

```typescript
async handleIncomingMessage(companyId, customerPhone, chatId, ...) {
  // 1. Tentar encontrar por numero real
  let conversation = await prisma.conversation.findUnique({
    where: { companyId_customerPhone: { companyId, customerPhone } },
  });

  // 2. Se nao achou, tentar pelo chatId antigo (LID salvo como customerPhone)
  if (!conversation && chatId && chatId !== customerPhone) {
    conversation = await prisma.conversation.findUnique({
      where: { companyId_customerPhone: { companyId, customerPhone: chatId } },
    });

    // 3. MIGRAR: atualizar o customerPhone antigo (LID) para o numero real
    if (conversation) {
      console.log(`Migrando conversa: ${chatId} -> ${customerPhone}`);
      conversation = await prisma.conversation.update({
        where: { id: conversation.id },
        data: {
          customerPhone,  // Agora salva o numero real
          metadata: {
            ...(conversation.metadata as any),
            chatId,       // Preserva o chatId original no metadata
          },
        },
      });
    }
  }

  // 4. Se nao existe, criar nova
  if (!conversation) {
    conversation = await prisma.conversation.create({
      data: {
        companyId,
        customerPhone,
        metadata: { chatId },
      },
    });
  }
}
```

---

## Resumo do Fluxo Completo

```
MENSAGEM RECEBIDA DO WAHA
         |
         v
  chatId = "5521912345678-1234567890@lid"
         |
         v
  GET /api/contacts?contactId={chatId}
         |
         v
  response.number = "5521999998888"  <-- NUMERO REAL
         |
         v
  Salvar no banco:
    conversation.customerPhone = "5521999998888"  (numero real - mostrado na UI)
    conversation.metadata.chatId = "...@lid"       (ID original - usado para enviar)
         |
         v
  ENVIAR RESPOSTA
         |
         v
  POST /api/sendText { chatId: metadata.chatId }  (usa o ID original)
```

---

## Endpoints WAHA Utilizados

| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/api/contacts?session={s}&contactId={id}` | GET | **Resolve LID para numero real** |
| `/api/contacts/profile-picture?session={s}&contactId={id}` | GET | Busca foto de perfil (opcional) |
| `/api/{session}/chats/overview` | GET | Lista chats com contagem de nao lidos |
| `/api/{session}/chats/{chatId}/messages` | GET | Busca mensagens de um chat |
| `/api/{session}/chats/{chatId}/messages/read` | POST | Marca mensagens como lidas |
| `/api/sendText` | POST | Envia mensagem de texto |

---

## Checklist de Implementacao

- [ ] Criar metodo `getContactInfo(contactId)` que chama `GET /api/contacts`
- [ ] Chamar `getContactInfo()` ao receber mensagem (webhook ou polling)
- [ ] Salvar `customerPhone` com o numero real (campo `number` da resposta)
- [ ] Salvar `chatId` original no campo `metadata` da conversa
- [ ] Ao enviar mensagem, usar `metadata.chatId` (nao o `customerPhone`)
- [ ] Implementar migracao para conversas antigas que tem @lid como customerPhone
- [ ] Tratar fallback: se `getContactInfo()` falhar, usar o chatId como customerPhone

---

## Variaveis de Ambiente Necessarias

```env
WAHA_API_URL=http://localhost:3101    # URL do WAHA
WAHA_API_KEY=sua_api_key              # Chave de API do WAHA
WAHA_SESSION=default                  # Nome da sessao do WAHA
```

---

## Observacoes Importantes

1. **O endpoint `/api/contacts` e a chave**: Sem ele, voce so tem o @lid. Esse endpoint e o que faz a traducao.

2. **Cache**: Se o volume de mensagens for alto, considere cachear o resultado de `getContactInfo()` por alguns minutos para evitar chamadas excessivas ao WAHA.

3. **Fallback**: Nem sempre a resolucao funciona (contato nao encontrado, WAHA fora do ar). Sempre tenha um fallback usando o proprio chatId.

4. **Envio usa chatId, nao numero**: Para enviar mensagens de volta, use SEMPRE o `chatId` original (que pode ser @lid), nao o numero resolvido. O WAHA precisa do ID original para rotear.

5. **Unique constraint**: O campo `customerPhone` deve ter unique constraint junto com `companyId` para evitar conversas duplicadas por cliente.
