# ⚡ REFERÊNCIA RÁPIDA - Sistema de Notificações

**Cheat Sheet para copiar e colar**

---

## 🚀 Uso Mais Simples (3 linhas)

```javascript
import { useNotifications } from '../hooks/useNotifications'
import NotificationBell from '../components/notifications/NotificationBell'

const { pendingCount } = useNotifications({ enabled: true })
return <NotificationBell count={pendingCount} />
```

---

## 📦 Imports Necessários

```javascript
// Hook
import { useNotifications } from '../hooks/useNotifications'

// Componentes
import NotificationBell from '../components/notifications/NotificationBell'
import { NotificationBadge } from '../components/notifications/NotificationBell'
import { NotificationButton } from '../components/notifications/NotificationBell'

// Helper WebSocket
import { setupNotificationWebSocket } from '../utils/notificationWebSocketHelper'

// Componente de Teste
import NotificationTester from '../components/notifications/NotificationTester'
```

---

## 🎯 Exemplos Rápidos

### 1. Sino no Header
```javascript
const { pendingCount } = useNotifications({ enabled: true })

<header>
  <h1>Meu App</h1>
  <NotificationBell count={pendingCount} />
</header>
```

### 2. Com Callback de Novo Pedido
```javascript
const { pendingCount } = useNotifications({
  enabled: true,
  onOrderCreated: (order) => {
    console.log('Novo pedido:', order.order_number)
    // Atualizar interface aqui
  }
})
```

### 3. Solicitar Permissão
```javascript
const { permissionGranted, requestPermission } = useNotifications()

{!permissionGranted && (
  <button onClick={requestPermission}>🔔 Ativar</button>
)}
```

### 4. Histórico
```javascript
const { history, markAsRead } = useNotifications()

{history.map(n => (
  <div key={n.id} onClick={() => markAsRead(n.id)}>
    {n.title}
  </div>
))}
```

### 5. Configurações
```javascript
const { settings, updateSetting } = useNotifications()

<input
  type="checkbox"
  checked={settings.sound}
  onChange={(e) => updateSetting('sound', e.target.checked)}
/>
```

### 6. Integração WebSocket
```javascript
import { setupNotificationWebSocket } from '../utils/notificationWebSocketHelper'

ws.onmessage = (event) => {
  const data = JSON.parse(event.data)
  setupNotificationWebSocket.handleMessage(data) // Só esta linha!
}
```

---

## 🧪 Testes Rápidos

### Console do Browser
```javascript
// Teste simples
notificationService.test()

// Notificação customizada
notificationService.notifyNewOrder({
  order_id: '123',
  order_number: 456,
  customer_name: 'João',
  total_amount: 150,
  bairro: 'Centro'
})

// Simular WebSocket
window.dispatchEvent(new CustomEvent('websocket:order_created', {
  detail: { orderData: { order_id: '789', order_number: 101 } }
}))
```

### Componente de Teste
```javascript
import NotificationTester from '../components/notifications/NotificationTester'
<NotificationTester /> // Adicionar em qualquer página
```

---

## 🎨 Variantes de Componentes

### Sino (Padrão)
```javascript
<NotificationBell count={5} onClick={() => {}} />
```

### Badge Compacto
```javascript
<NotificationBadge count={5} onClick={() => {}} />
```

### Botão com Texto
```javascript
<NotificationButton count={5} onClick={() => {}} />
```

---

## ⚙️ API do Hook

### Estados
```javascript
const {
  pendingCount,           // número de não lidas
  history,                // histórico completo
  permissionGranted,      // permissão concedida
  settings,               // configurações
  isInitialized,          // hook pronto
  hasUnread,              // tem não lidas
  unreadNotifications,    // array de não lidas
  totalNotifications,     // total no histórico
} = useNotifications()
```

### Funções
```javascript
const {
  markAsRead,             // (id) => void
  markAllAsRead,          // () => void
  clearHistory,           // () => void
  requestPermission,      // () => Promise<boolean>
  updateSetting,          // (key, value) => void
  test,                   // () => void
  notify,                 // (orderData) => void
} = useNotifications()
```

---

## 🔧 Configurações

| Key | Tipo | Padrão | Descrição |
|-----|------|--------|-----------|
| `sound` | boolean | `true` | Som |
| `vibration` | boolean | `true` | Vibração |
| `nativeNotifications` | boolean | `true` | Nativas |
| `soundVolume` | 0-1 | `0.7` | Volume |
| `autoClose` | ms | `5000` | Auto-fechar |

```javascript
updateSetting('sound', false)         // Desligar som
updateSetting('soundVolume', 1.0)     // Volume máximo
```

---

## 🔌 Eventos WebSocket

### Disparar Manualmente
```javascript
// Novo pedido
window.dispatchEvent(new CustomEvent('websocket:order_created', {
  detail: { orderData: {...} }
}))

// Status atualizado
window.dispatchEvent(new CustomEvent('websocket:order_status_updated', {
  detail: { orderId: '123', newStatus: 'confirmed' }
}))

// Reset diário
window.dispatchEvent(new CustomEvent('websocket:map_reset', {
  detail: {}
}))
```

---

## 🚨 Troubleshooting

### Som não toca
1. Adicionar `notification.mp3` em `/frontend/public/sounds/`
2. Verificar `settings.sound === true`

### Notificações não aparecem
1. Verificar `isInitialized === true`
2. Verificar `permissionGranted === true`
3. Testar: `notificationService.test()`

### WebSocket não dispara
1. Usar: `setupNotificationWebSocket.handleMessage(data)`
2. Ou disparar: `window.dispatchEvent(new CustomEvent(...))`

---

## 📁 Arquivos Criados

```
frontend/src/
├── hooks/useNotifications.js
├── utils/notificationWebSocketHelper.js
└── components/notifications/
    ├── NotificationBell.jsx
    └── NotificationTester.jsx
```

---

## 🎯 Dependências

**ZERO dependências adicionais!**

Usa apenas:
- React (já instalado)
- Tailwind CSS (já instalado)
- lucide-react (já instalado)
- react-hot-toast (já instalado na Fase 1)

---

## 📚 Documentação Completa

- `IMPLEMENTACAO_FASE2_NOTIFICACOES.md` - Documentação técnica
- `docs/guias/GUIA-USO-NOTIFICACOES.md` - Guia de uso
- `docs/guias/EXEMPLO-INTEGRACAO-DASHBOARD.md` - Exemplo prático

---

**Pronto para copiar e colar! 🚀🔔**
