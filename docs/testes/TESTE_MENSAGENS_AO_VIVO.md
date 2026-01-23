## ✅ TESTE COMPLETO DE MENSAGENS AO VIVO

### 1. VERIFICAR BACKEND

```bash
# Terminal 1: Ver logs do backend
docker-compose logs backend -f | grep -E "Processando|WebSocket|Erro"
```

### 2. ACESSAR O DASHBOARD

1. Abra: http://localhost:3001/
2. Veja a tela de Login com credenciais pré-preenchidas:
   - Email: `admin@gasautomation.local`
   - Senha: `Admin@123456`
3. Clique em "Entrar"
4. Você deve ser redirecionado para `/dashboard` e depois pode clicar em "Chats"

### 3. VER LOGS DO NAVEGADOR

1. Pressione **F12** para abrir o Developer Tools
2. Vá para a aba **Console**
3. Você deve ver logs como:
   ```
   [Chats] Iniciando loadChats...
   [Chats] Chamando getChats()...
   [API] getChats: Token presente? true
   [API] getChats: Resposta recebida [...]
   [Chats] getChats() retornou: [...]
   [Chats] Estado atualizado com 6 conversas
   ```

### 4. ENVIAR MENSAGEM DE TESTE

```bash
python3 test_message.py
```

Você deve ver na console do navegador:
```
[Chats] handleNewMessage recebido: 5541987654321@c.us
[Chats] Conversa atualizada
```

### 5. VERIFICAR API DIRETAMENTE

```bash
# Testar o endpoint /api/chats
curl -H "Authorization: Bearer SEU_TOKEN_JWT" \
  http://localhost:8000/api/chats | python3 -m json.tool
```

Deve retornar uma lista de conversas com telefones, mensagens, etc.

### 6. ENTENDER O FLUXO

```
WhatsApp → WAHA Webhook (/webhooks/waha)
   ↓
Backend recebe mensagem
   ↓
Salva em EventLog (message_received)
   ↓
Emite evento WebSocket "new_message"
   ↓
Frontend recebe evento (WebSocket listener)
   ↓
Frontend chama loadChats() via handleNewMessage()
   ↓
getChats() busca conversas do /api/chats
   ↓
Backend retorna conversas do EventLog
   ↓
Frontend atualiza lista e exibe conversa
```

### 7. POSSÍVEIS PROBLEMAS E SOLUÇÕES

**Problema: "Nenhuma conversa ativa"**
- ✅ CONSERTADO: Agora busca do EventLog em vez de Redis
- Verifique os logs do navegador (F12 > Console)

**Problema: Token não sendo enviado**
- Verificado: Há um interceptor axios que adiciona o token automaticamente
- Logs devem mostrar: `[API] getChats: Token presente? true`

**Problema: API retorna erro 401**
- Significa que o token é inválido
- Faça login novamente para obter novo token
- Token é salvo em localStorage (chave: `access_token`)

**Problema: Conversas não aparecem mesmo com logs OK**
- Verifique se há dados no banco: `curl http://localhost:8000/api/chats`
- Se retorna `[]`, envie uma mensagem de teste com `python3 test_message.py`

### 8. VERIFICAR BANCO DE DADOS

```bash
# Acessar container postgres
docker-compose exec postgres psql -U gas_admin -d gas_db

# Ver eventos de mensagem
SELECT phone, payload->>'message' as mensagem, created_at 
FROM event_logs 
WHERE event_type = 'message_received' 
ORDER BY created_at DESC 
LIMIT 10;
```

### 9. TESTE FINAL

- [ ] Login realizado com sucesso
- [ ] Redirecionado para /dashboard
- [ ] Clicou em "Chats"
- [ ] Console mostra "[Chats] Estado atualizado com X conversas"
- [ ] Conversa aparece na lista (não mostra "Nenhuma conversa ativa")
- [ ] WebSocket conecta (verifica na Console)
- [ ] Envia mensagem de teste com `python3 test_message.py`
- [ ] Nova conversa aparece em tempo real (ou conversa existente tem mensagem nova)
- [ ] Clica em conversa para ver mensagens
- [ ] Responde com uma mensagem
- [ ] Mensagem aparece no chat

---

**Data da última atualização**: 2025-01-20
**Status**: ✅ Conversas agora carregam do banco de dados (EventLog)
**Próximos passos**: Verificar se mensagens aparecem em tempo real após WebSocket
