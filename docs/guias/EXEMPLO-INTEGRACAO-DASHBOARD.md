# 📝 Exemplo de Integração - Dashboard do Operador

Este exemplo mostra como integrar o sistema de notificações no dashboard existente.

---

## 1. Adicionar ao Header do Dashboard

### Arquivo: `DashboardOverview.jsx` (ou similar)

```javascript
// 1. Importar no topo do arquivo
import { useNotifications } from '../../hooks/useNotifications'
import NotificationBell from '../notifications/NotificationBell'
import { setupNotificationWebSocket } from '../../utils/notificationWebSocketHelper'

export default function DashboardOverview() {
  // 2. Adicionar o hook (logo após os outros useState)
  const { 
    pendingCount, 
    permissionGranted,
    requestPermission 
  } = useNotifications({
    enabled: true,
    onOrderCreated: (orderData) => {
      console.log('🆕 Novo pedido recebido:', orderData.order_number)
      
      // Opcional: Atualizar dados do dashboard
      fetchMetrics() // Se você tiver esta função
    }
  })
  
  // ... resto do código ...
  
  // 3. Adicionar no JSX do header (onde está o ícone de usuário/logout)
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <h1 className="text-2xl font-bold text-gray-900">
              Dashboard do Operador
            </h1>
            
            {/* ADICIONAR AQUI */}
            <div className="flex items-center gap-4">
              {/* Banner de permissão (opcional) */}
              {!permissionGranted && (
                <button
                  onClick={requestPermission}
                  className="text-xs px-3 py-1 bg-yellow-100 text-yellow-800 rounded-full hover:bg-yellow-200"
                >
                  🔔 Ativar Notificações
                </button>
              )}
              
              {/* Sino de notificações */}
              <NotificationBell count={pendingCount} />
              
              {/* Outros elementos do header */}
            </div>
          </div>
        </div>
      </header>
      
      {/* Resto do conteúdo */}
    </div>
  )
}
```

---

## 2. Integrar com WebSocket (se já existe)

Se o seu dashboard já tem WebSocket, adicione a integração:

### Opção A: Usando o Helper (Recomendado)

```javascript
import { setupNotificationWebSocket } from '../../utils/notificationWebSocketHelper'

useEffect(() => {
  // Seu código WebSocket existente
  const ws = new WebSocket('ws://...')
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    
    // Seu código existente
    if (data.type === 'order_created') {
      // Atualizar estado, mapa, etc
      setOrders(prev => [data, ...prev])
    }
    
    // ADICIONAR ESTA LINHA:
    setupNotificationWebSocket.handleMessage(data)
  }
  
  return () => ws.close()
}, [])
```

### Opção B: Disparar Eventos Manualmente

```javascript
useEffect(() => {
  const ws = new WebSocket('ws://...')
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    
    // Quando receber order_created:
    if (data.type === 'order_created') {
      // Seu código existente
      setOrders(prev => [data, ...prev])
      
      // Disparar evento de notificação
      window.dispatchEvent(new CustomEvent('websocket:order_created', {
        detail: { orderData: data }
      }))
    }
  }
  
  return () => ws.close()
}, [])
```

---

## 3. Exemplo Completo Mínimo

Se você quer apenas adicionar o sino no header, use este código mínimo:

```javascript
import { useNotifications } from '../../hooks/useNotifications'
import NotificationBell from '../notifications/NotificationBell'

export default function MeuDashboard() {
  const { pendingCount } = useNotifications({ enabled: true })
  
  return (
    <div>
      <header className="flex justify-between items-center p-4 bg-white shadow">
        <h1>Dashboard</h1>
        <NotificationBell count={pendingCount} />
      </header>
      
      {/* Resto do dashboard */}
    </div>
  )
}
```

---

## 4. Testar a Integração

### Passo 1: Adicionar Componente de Teste (Temporário)

```javascript
import NotificationTester from '../notifications/NotificationTester'

export default function MeuDashboard() {
  // ... código existente ...
  
  return (
    <div>
      {/* Seu conteúdo */}
      
      {/* APENAS PARA DESENVOLVIMENTO */}
      {process.env.NODE_ENV === 'development' && <NotificationTester />}
    </div>
  )
}
```

### Passo 2: Abrir o Dashboard

Você verá:
- ✅ Sino no header (contador em 0)
- ✅ Componente de teste no canto inferior direito

### Passo 3: Testar Notificação

Clique em "🔔 Notificação de Teste" no componente de teste.

Você deve ver:
- ✅ Toast popup aparece
- ✅ Som toca (se configurado)
- ✅ Contador do sino aumenta
- ✅ Notificação nativa do browser (se permitido)

### Passo 4: Remover Componente de Teste

Quando tudo estiver funcionando, remova a linha do `NotificationTester`.

---

## 5. Exemplo com Sidebar (Alternativa)

Se o seu dashboard tem sidebar, você pode adicionar lá:

```javascript
<aside className="w-64 bg-white shadow-lg">
  <nav className="p-4">
    <ul className="space-y-2">
      <li>
        <a href="/dashboard" className="flex items-center gap-3 p-2">
          <HomeIcon />
          <span>Início</span>
        </a>
      </li>
      
      {/* ADICIONAR AQUI */}
      <li>
        <button className="flex items-center gap-3 p-2 w-full text-left">
          <NotificationBell count={pendingCount} size={20} />
          <span>Notificações</span>
          {pendingCount > 0 && (
            <span className="ml-auto bg-red-600 text-white text-xs px-2 py-0.5 rounded-full">
              {pendingCount}
            </span>
          )}
        </button>
      </li>
      
      <li>
        <a href="/orders" className="flex items-center gap-3 p-2">
          <PackageIcon />
          <span>Pedidos</span>
        </a>
      </li>
    </ul>
  </nav>
</aside>
```

---

## 6. Troubleshooting

### ❌ Erro: "Cannot find module 'useNotifications'"

**Solução:** Verificar o caminho relativo do import:
```javascript
// Se o componente está em: src/components/admin/
import { useNotifications } from '../../hooks/useNotifications'

// Se o componente está em: src/pages/
import { useNotifications } from '../hooks/useNotifications'
```

### ❌ Sino aparece mas contador sempre 0

**Solução:** Testar manualmente:
1. Abrir console do browser (F12)
2. Digitar: `notificationService.test()`
3. Se funcionar no console mas não no componente, verificar se `enabled: true`

### ❌ Notificações não aparecem quando WebSocket recebe dados

**Solução:** Verificar se está usando o helper:
```javascript
import { setupNotificationWebSocket } from '../../utils/notificationWebSocketHelper'

// No handler do WebSocket:
setupNotificationWebSocket.handleMessage(data)
```

---

## 7. Checklist de Integração

- [ ] Importar `useNotifications` e `NotificationBell`
- [ ] Adicionar hook no componente: `const { pendingCount } = useNotifications({ enabled: true })`
- [ ] Adicionar `<NotificationBell count={pendingCount} />` no JSX
- [ ] (Opcional) Integrar com WebSocket existente
- [ ] (Opcional) Adicionar banner de permissão
- [ ] Testar com `NotificationTester` (temporariamente)
- [ ] Remover `NotificationTester` após testar

---

## 🎉 Pronto!

Seu dashboard agora tem notificações funcionando! 🚀🔔

Para customizar mais, veja: `docs/guias/GUIA-USO-NOTIFICACOES.md`
