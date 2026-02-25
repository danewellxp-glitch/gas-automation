# 🚀 Guia Rápido: Como Usar o Sistema de Notificações

**Última atualização:** 13/02/2026

---

## ⚡ Início Rápido (5 minutos)

### 1️⃣ Adicionar o Hook ao Seu Componente

```javascript
import { useNotifications } from '../hooks/useNotifications'
import NotificationBell from '../components/notifications/NotificationBell'

function MeuComponente() {
  const { pendingCount } = useNotifications({ enabled: true })
  
  return (
    <NotificationBell count={pendingCount} onClick={() => alert('Clicou!')} />
  )
}
```

✅ **Pronto!** Você já tem notificações funcionando.

---

## 🎯 Casos de Uso Comuns

### Caso 1: Dashboard com Sino no Header

```javascript
import React from 'react'
import { useNotifications } from '../hooks/useNotifications'
import NotificationBell from '../components/notifications/NotificationBell'

export default function Dashboard() {
  const { pendingCount } = useNotifications({ enabled: true })
  
  return (
    <header className="flex items-center justify-between p-4 bg-white shadow">
      <h1>Dashboard</h1>
      <NotificationBell count={pendingCount} />
    </header>
  )
}
```

### Caso 2: Receber Callback Quando Novo Pedido Chegar

```javascript
const { pendingCount } = useNotifications({
  enabled: true,
  onOrderCreated: (orderData) => {
    console.log('🆕 Novo pedido:', orderData.order_number)
    
    // Atualizar lista de pedidos
    setOrders(prev => [orderData, ...prev])
    
    // Atualizar mapa
    updateMap()
  }
})
```

### Caso 3: Solicitar Permissão de Notificações

```javascript
const { permissionGranted, requestPermission } = useNotifications()

// Mostrar banner se permissão não foi concedida
{!permissionGranted && (
  <div className="bg-yellow-100 p-4">
    <button onClick={requestPermission}>
      🔔 Ativar Notificações
    </button>
  </div>
)}
```

### Caso 4: Exibir Histórico de Notificações

```javascript
const { history, markAsRead } = useNotifications()

return (
  <div>
    {history.map(notif => (
      <div 
        key={notif.id} 
        className={notif.read ? 'opacity-50' : 'font-bold'}
        onClick={() => markAsRead(notif.id)}
      >
        <h4>{notif.title}</h4>
        <p>{notif.message}</p>
        <small>{new Date(notif.timestamp).toLocaleTimeString()}</small>
      </div>
    ))}
  </div>
)
```

### Caso 5: Configurar Som e Vibração

```javascript
const { settings, updateSetting } = useNotifications()

return (
  <div>
    <label>
      <input
        type="checkbox"
        checked={settings.sound}
        onChange={(e) => updateSetting('sound', e.target.checked)}
      />
      Som
    </label>
    
    <label>
      <input
        type="checkbox"
        checked={settings.vibration}
        onChange={(e) => updateSetting('vibration', e.target.checked)}
      />
      Vibração
    </label>
    
    <label>
      Volume:
      <input
        type="range"
        min="0"
        max="1"
        step="0.1"
        value={settings.soundVolume || 0.7}
        onChange={(e) => updateSetting('soundVolume', parseFloat(e.target.value))}
      />
    </label>
  </div>
)
```

---

## 🔌 Integração com WebSocket

### Opção 1: Usar o Helper (Mais Fácil)

Se você já tem um componente que escuta WebSocket:

```javascript
import { setupNotificationWebSocket } from '../utils/notificationWebSocketHelper'

useEffect(() => {
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    
    // Seu código existente
    // ...
    
    // ADICIONAR ESTA LINHA:
    setupNotificationWebSocket.handleMessage(data)
  }
}, [])
```

### Opção 2: Disparar Eventos Manualmente

```javascript
// Quando receber um novo pedido via WebSocket:
window.dispatchEvent(new CustomEvent('websocket:order_created', {
  detail: {
    orderData: {
      order_id: '123',
      order_number: 456,
      customer_name: 'João Silva',
      customer_phone: '5541999999999',
      total_amount: 150.00,
      bairro: 'Centro',
      status: 'pending'
    }
  }
}))
```

---

## 🧪 Como Testar

### Teste 1: Componente de Teste Visual

Adicione temporariamente em qualquer página:

```javascript
import NotificationTester from '../components/notifications/NotificationTester'

function MinhaPage() {
  return (
    <div>
      {/* Seu conteúdo */}
      
      {/* Componente de teste no canto */}
      {process.env.NODE_ENV === 'development' && <NotificationTester />}
    </div>
  )
}
```

### Teste 2: Console do Browser

Abra o console (F12) e digite:

```javascript
// Notificação de teste simples
notificationService.test()

// Notificação customizada
notificationService.notifyNewOrder({
  order_id: '123',
  order_number: 456,
  customer_name: 'Maria Santos',
  total_amount: 200.00,
  bairro: 'Batel',
  status: 'pending'
})
```

### Teste 3: Simular WebSocket

```javascript
// No console do browser:
window.dispatchEvent(new CustomEvent('websocket:order_created', {
  detail: {
    orderData: {
      order_id: '789',
      order_number: 101,
      customer_name: 'Carlos Silva',
      total_amount: 300.00,
      bairro: 'Centro'
    }
  }
}))
```

---

## 📱 Variantes de Componentes

### 1. Sino Clássico (Recomendado)
```javascript
import NotificationBell from '../components/notifications/NotificationBell'

<NotificationBell count={5} onClick={() => {}} />
```

### 2. Badge Compacto
```javascript
import { NotificationBadge } from '../components/notifications/NotificationBell'

<NotificationBadge count={5} onClick={() => {}} />
```

### 3. Botão com Texto
```javascript
import { NotificationButton } from '../components/notifications/NotificationButton'

<NotificationButton count={5} onClick={() => {}} />
```

---

## ⚙️ Configurações Disponíveis

Todas as configurações são persistidas no LocalStorage:

| Chave | Tipo | Padrão | Descrição |
|-------|------|--------|-----------|
| `sound` | boolean | `true` | Reproduzir som |
| `vibration` | boolean | `true` | Vibrar dispositivo |
| `nativeNotifications` | boolean | `true` | Notificações nativas do browser |
| `soundVolume` | number (0-1) | `0.7` | Volume do som (70%) |
| `autoClose` | number (ms) | `5000` | Tempo para fechar popup (5s) |

### Alterar Configurações

```javascript
const { updateSetting } = useNotifications()

updateSetting('sound', false)          // Desligar som
updateSetting('soundVolume', 1.0)      // Volume 100%
updateSetting('autoClose', 10000)      // Popup fica 10s
```

---

## 🎨 Personalizar Aparência

### Badge Customizado

```javascript
<NotificationBell
  count={10}
  size={32}                    // Tamanho do ícone
  className="text-blue-600"    // Cor customizada
  showAnimation={false}        // Desabilitar animação
/>
```

### Estilizar com Tailwind

Os componentes já usam Tailwind CSS e são customizáveis via `className`.

---

## 🚨 Troubleshooting

### ❌ Notificações não aparecem

**Solução:**
1. Verificar se o hook está ativo: `isInitialized === true`
2. Verificar permissão: `permissionGranted === true`
3. Verificar configurações: `settings.sound`, `settings.nativeNotifications`

### ❌ Som não toca

**Solução:**
1. Adicionar arquivo `notification.mp3` em `/frontend/public/sounds/`
2. Verificar `settings.sound === true`
3. Ajustar volume: `settings.soundVolume`

### ❌ WebSocket não dispara notificações

**Solução:**
1. Verificar se está usando `setupNotificationWebSocket.handleMessage(data)`
2. Ou disparar evento: `window.dispatchEvent(new CustomEvent('websocket:order_created', {...}))`
3. Verificar tipo da mensagem: `data.type === 'order_created'`

### ❌ Histórico vazio

**Solução:**
1. Testar manualmente: `notificationService.test()`
2. Verificar LocalStorage: `gasmaster_notifications`

---

## 📋 API Completa do Hook

### Estados Retornados

```javascript
const {
  // Contadores
  pendingCount,           // number - Notificações não lidas
  totalNotifications,     // number - Total no histórico
  
  // Arrays
  history,                // array - Histórico completo
  unreadNotifications,    // array - Apenas não lidas
  
  // Booleans
  permissionGranted,      // boolean - Permissão concedida
  isInitialized,          // boolean - Hook inicializado
  hasUnread,              // boolean - Tem notificações não lidas
  
  // Object
  settings,               // object - Configurações atuais
  
  // Funções
  markAsRead,             // (id) => void
  markAllAsRead,          // () => void
  clearHistory,           // () => void
  requestPermission,      // () => Promise<boolean>
  updateSetting,          // (key, value) => void
  test,                   // () => void
  notify,                 // (orderData) => void
  getUnreadNotifications, // () => array
  getNotificationsByType, // (type) => array
} = useNotifications()
```

---

## 🎉 Pronto para Usar!

O sistema está **100% funcional** e pronto para produção.

### Próximos Passos Opcionais

- **Fase 3:** Componentes de painel lateral com histórico completo
- **Fase 4:** Backend - WebSocket endpoint `/ws/notifications`
- **Fase 5:** Integração com banco de dados

---

**Dúvidas?** Adicione `<NotificationTester />` temporariamente e teste todas as funcionalidades! 🚀🔔
