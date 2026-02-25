# ✅ CHECKLIST - Implementação Fase 2

Use este checklist para implementar as notificações no seu projeto.

---

## 📦 1. Arquivos Criados (Automático)

- [x] `frontend/src/hooks/useNotifications.js`
- [x] `frontend/src/utils/notificationWebSocketHelper.js`
- [x] `frontend/src/components/notifications/NotificationBell.jsx`
- [x] `frontend/src/components/notifications/NotificationTester.jsx`
- [x] `frontend/src/services/NotificationService.js` (Fase 1)
- [x] Documentação completa

**✅ PRONTO!** Todos os arquivos já foram criados.

---

## 🔧 2. Integração no Seu Dashboard

### Passo 1: Importar Hook e Componente
```javascript
// Adicionar no topo do arquivo do seu dashboard
import { useNotifications } from '../../hooks/useNotifications'
import NotificationBell from '../notifications/NotificationBell'
```

- [ ] Imports adicionados

### Passo 2: Adicionar Hook no Componente
```javascript
// Dentro do componente, após outros useState
const { pendingCount } = useNotifications({ enabled: true })
```

- [ ] Hook adicionado

### Passo 3: Adicionar Sino no JSX
```javascript
// No header ou onde preferir
<NotificationBell count={pendingCount} />
```

- [ ] Componente adicionado no JSX

---

## 🧪 3. Teste Básico

### Passo 1: Adicionar Componente de Teste (Temporário)
```javascript
import NotificationTester from '../notifications/NotificationTester'

// No final do JSX
{process.env.NODE_ENV === 'development' && <NotificationTester />}
```

- [ ] NotificationTester adicionado

### Passo 2: Abrir o Dashboard no Browser
- [ ] Dashboard aberto
- [ ] Sino aparece no header
- [ ] NotificationTester aparece no canto inferior direito

### Passo 3: Testar Notificação
- [ ] Clicar em "🔔 Notificação de Teste"
- [ ] Toast popup aparece
- [ ] Contador do sino aumenta (de 0 para 1)
- [ ] Som toca (se configurado)

### Passo 4: Testar Permissão
- [ ] Clicar em "🔐 Solicitar Permissão"
- [ ] Browser pede permissão
- [ ] Permitir notificações
- [ ] Status muda para "✅ Sim"

### Passo 5: Testar Notificação Nativa
- [ ] Clicar em "🔔 Notificação de Teste" novamente
- [ ] Notificação nativa do browser aparece
- [ ] Toast popup aparece
- [ ] Contador aumenta

### Passo 6: Testar Configurações
- [ ] Desmarcar "🔊 Som"
- [ ] Clicar em teste novamente
- [ ] Som não toca, mas popup aparece

### Passo 7: Limpar Testes
- [ ] Clicar em "🗑️ Limpar Histórico"
- [ ] Contador volta para 0
- [ ] Histórico limpo

### Passo 8: Remover NotificationTester
```javascript
// Remover esta linha quando tudo estiver funcionando
{process.env.NODE_ENV === 'development' && <NotificationTester />}
```

- [ ] NotificationTester removido

---

## 🔌 4. Integração com WebSocket (Opcional)

Se você já tem WebSocket no projeto:

### Opção A: Usar o Helper
```javascript
import { setupNotificationWebSocket } from '../../utils/notificationWebSocketHelper'

// Onde você processa mensagens WebSocket:
ws.onmessage = (event) => {
  const data = JSON.parse(event.data)
  // ... seu código existente ...
  setupNotificationWebSocket.handleMessage(data) // Adicionar esta linha
}
```

- [ ] Helper importado
- [ ] `handleMessage()` adicionado

### Opção B: Disparar Eventos Manualmente
```javascript
// Quando receber order_created via WebSocket:
window.dispatchEvent(new CustomEvent('websocket:order_created', {
  detail: { orderData: data }
}))
```

- [ ] Eventos customizados disparados

---

## 🎯 5. Callback de Novo Pedido (Opcional)

Se quiser executar ações quando novo pedido chegar:

```javascript
const { pendingCount } = useNotifications({
  enabled: true,
  onOrderCreated: (orderData) => {
    console.log('🆕 Novo pedido:', orderData.order_number)
    
    // Atualizar lista de pedidos
    fetchOrders()
    
    // Atualizar mapa
    updateMap()
    
    // Qualquer outra ação
  }
})
```

- [ ] Callback adicionado (se necessário)

---

## 🎨 6. Banner de Permissão (Opcional)

Adicionar banner pedindo permissão:

```javascript
const { permissionGranted, requestPermission } = useNotifications()

// No JSX, antes do conteúdo principal:
{!permissionGranted && (
  <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4">
    <div className="flex items-center justify-between">
      <div>
        <p className="text-sm font-medium text-yellow-800">
          Ativar Notificações
        </p>
        <p className="text-xs text-yellow-700 mt-1">
          Receba alertas de novos pedidos
        </p>
      </div>
      <button
        onClick={requestPermission}
        className="px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700"
      >
        Permitir
      </button>
    </div>
  </div>
)}
```

- [ ] Banner adicionado (se desejado)

---

## 🔊 7. Adicionar Som (Opcional)

### Opção 1: Gerar Som Simples
1. [ ] Abrir `frontend/public/sounds/generator.html` no browser
2. [ ] Clicar em "Generate & Test"
3. [ ] Clicar em "Download"
4. [ ] Salvar como `notification.mp3` em `frontend/public/sounds/`

### Opção 2: Usar Som Customizado
1. [ ] Baixar um som .mp3 da internet
2. [ ] Renomear para `notification.mp3`
3. [ ] Colocar em `frontend/public/sounds/`

### Verificar
- [ ] Arquivo existe: `frontend/public/sounds/notification.mp3`
- [ ] Testar: NotificationTester → clicar em teste → som toca

---

## 📱 8. Testes em Dispositivos

### Desktop
- [ ] Chrome - Funciona
- [ ] Firefox - Funciona
- [ ] Edge - Funciona

### Mobile
- [ ] Chrome Android - Funciona
- [ ] Safari iOS - Funciona (vibração não disponível em iOS)

---

## 🚀 9. Deploy

### Antes de Fazer Deploy
- [ ] NotificationTester removido (ou com `process.env.NODE_ENV === 'development'`)
- [ ] Arquivo de som (`notification.mp3`) incluído
- [ ] Imports corrigidos
- [ ] Sem erros no console

### Após Deploy
- [ ] Testar em produção
- [ ] Verificar permissões
- [ ] Verificar som
- [ ] Verificar notificações nativas

---

## 🎉 10. Sucesso!

Se todos os itens acima estão marcados:

✅ **Sistema de Notificações 100% Funcional!**

---

## 📚 Próximos Passos (Opcional)

- [ ] Implementar Fase 3 (Painel UI completo)
- [ ] Implementar Fase 4 (Backend WebSocket)
- [ ] Customizar estilo dos componentes
- [ ] Adicionar mais tipos de notificações

---

## 🆘 Ajuda

Se algo não funcionar:

1. **Verificar imports**
   - Caminhos relativos corretos?
   - Todos os arquivos existem?

2. **Verificar console**
   - Abrir F12 → Console
   - Tem erros?

3. **Testar manualmente**
   - Console: `notificationService.test()`
   - Funciona?

4. **Documentação completa**
   - `IMPLEMENTACAO_FASE2_NOTIFICACOES.md`
   - `docs/guias/GUIA-USO-NOTIFICACOES.md`
   - `REFERENCIA-RAPIDA-NOTIFICACOES.md`

---

**Boa sorte! 🚀🔔**
