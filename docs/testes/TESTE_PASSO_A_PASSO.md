# 🎯 TESTE PASSO A PASSO

## FASE 1: Verificar Backend

Antes de testar frontend, certifique-se que o backend está funcionando:

```bash
# 1. Verificar se containers estão rodando
docker-compose ps

# Resultado esperado:
# - gas_backend: Up
# - gas_frontend: Up
# - postgres: Up
# - redis: Up
```

## FASE 2: Testar API Diretamente

```bash
# 2. Testar endpoint /api/chats sem login
curl -s http://localhost:8000/api/chats | python3 -m json.tool

# Resultado esperado:
# [
#   {
#     "phone": "5541999999999@c.us",
#     "customer_name": null,
#     "customer_id": "...",
#     "last_message": "Sua última mensagem",
#     "last_message_time": "2026-01-20T04:07:44.251835Z",
#     "unread_count": 0,
#     "state": "start"
#   },
#   ...
# ]
```

Se vir erro JSON, significa que não há dados no banco.

## FASE 3: Testar Frontend

### PASSO 1: Acesse o login
- URL: http://localhost:3001
- Veja se aparece tela de login (fundo gradiente laranja/azul)
- Credenciais pré-preenchidas:
  - Email: `admin@gasautomation.local`
  - Senha: `Admin@123456`

### PASSO 2: Clique "Entrar"
- Aguarde redirecionamento para `/dashboard`
- Você deve ser levado para o AdminDashboard

### PASSO 3: Abra o Console (F12)
1. Pressione **F12** no navegador
2. Clique na aba **Console**
3. Você verá logs como:
   - `[Chats] Iniciando loadChats...`
   - `[Chats] Chamando getChats()...`
   - `[API] getChats: Token presente? true`
   - `[API] getChats: Resposta recebida [...]`
   - `[Chats] getChats() retornou: [...]`
   - `[Chats] Estado atualizado com X conversas`

**Se você NÃO vê esses logs**: clique em "Chats" no menu e recarregue (F5) a página.

### PASSO 4: Clique em "Chats" no menu
- Você deve ser levado para `/chats`
- A página mostra:
  - Sidebar esquerdo com título "Conversas"
  - Lista de conversas (ou "Nenhuma conversa ativa" se banco vazio)
  - Área de chat vazia à direita

## ESPERADO VS REAL

### SE TUDO ESTÁ OK ✅

```
Tela mostra:
┌─────────────────────────────────────────────┐
│  Conversas  🔄                              │
├─────────────────────────────────────────────┤
│  🔵 +5541999999999  08:34                  │
│     Seu último pedido                       │
│                                             │
│  🔵 +5541988888888  06:45                  │
│     TESTE REAL AGORA                        │
│                                             │
│  🔵 +5541977777777  04:43                  │
│     MENSAGEM DE TESTE                       │
│                                             │
│  ... (mais 3 conversas)                     │
└─────────────────────────────────────────────┘
```

Console mostra:
```
[Chats] Iniciando loadChats...
[Chats] Chamando getChats()...
[API] getChats: Token presente? true
[API] getChats: Resposta recebida Array(6)
[Chats] getChats() retornou: Array(6)
[Chats] Estado atualizado com 6 conversas
```

### SE ESTÁ COM PROBLEMA ❌

```
Tela mostra:
┌─────────────────────────────────────────────┐
│  Conversas  🔄                              │
├─────────────────────────────────────────────┤
│                                             │
│      Nenhuma conversa ativa                 │
│                                             │
│                                             │
│                                             │
│                                             │
└─────────────────────────────────────────────┘
```

Console pode mostrar:
- Nenhum log (problema: loadChats não foi chamado)
- Erro 401 (problema: token inválido)
- Erro CORS (problema: backend não aceitando requisição)
- Erro na requisição (problema: endpoint quebrado)

## SOLUÇÃO DE PROBLEMAS

### Cenário 1: Console vazio (nenhum log aparece)

**Possível causa**: Você precisa ir para `/chats` DEPOIS de fazer login.

**Solução**:
1. Faça login
2. Clique em "Chats" no menu (ou acesse http://localhost:3001/chats)
3. Abra F12 > Console
4. Você deve ver logs imediatamente

### Cenário 2: Console mostra erro 401

**Possível causa**: Token JWT expirou ou não foi salvado.

**Solução**:
1. Faça login novamente
2. Veja se localStorage tem `access_token`:
   ```javascript
   // No console, digite:
   localStorage.getItem('access_token')
   // Deve retornar um JWT bem longo
   ```
3. Recarregue a página (F5)

### Cenário 3: Console mostra sucesso mas tela vazia

**Possível causa**: Não há dados no banco de dados.

**Solução**:
1. Envie uma mensagem de teste:
   ```bash
   python3 test_message.py
   ```
2. Recarregue a página (F5)
3. Você deve ver a nova conversa aparecer

### Cenário 4: Tela mostra "Nenhuma conversa ativa" mas console mostra "Estado atualizado com 6 conversas"

**Possível causa**: Componente React não atualizou corretamente.

**Solução**: Recarregue a página (F5) ou reinicie os containers:
```bash
docker-compose restart frontend
```

## TESTE FINAL

Se tudo está OK, teste enviar uma mensagem:

```bash
# Terminal 1: Ver logs do backend em tempo real
docker-compose logs backend -f | grep -E "Processando|WebSocket"

# Terminal 2: Enviar mensagem de teste
python3 test_message.py

# Esperado no Terminal 1:
# Processando mensagem de 5585987654321: Oi, essa é uma mensagem de teste!
# WebSocket emitido para 5585987654321: Oi, essa é uma mensagem de teste!
```

Se você vê isso, significa que:
- ✅ Webhook funcionando
- ✅ Backend salvando evento
- ✅ WebSocket emitindo evento
- ✅ Sistema pronto para receber mensagens do WhatsApp

---

**Data**: 2025-01-20
**Status**: Sistema pronto para teste
**Próximo**: Execute estes testes e relate o que vê no console
