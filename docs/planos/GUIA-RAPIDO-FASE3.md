# ⚡ GUIA RÁPIDO - Fase 3: Componentes UI

**Como usar o sistema completo de notificações**

---

## 🚀 Uso Mais Simples (5 linhas)

```javascript
import { useState } from 'react'
import { useNotifications } from '../hooks/useNotifications'
import NotificationBell from '../components/notifications/NotificationBell'
import NotificationPanel from '../components/notifications/NotificationPanel'

const [showPanel, setShowPanel] = useState(false)
const { pendingCount } = useNotifications({ enabled: true })

<NotificationBell count={pendingCount} onClick={() => setShowPanel(true)} />
<NotificationPanel isOpen={showPanel} onClose={() => setShowPanel(false)} />
```

---

## 📦 Imports Necessários

```javascript
// Componentes
import NotificationBell from '../components/notifications/NotificationBell'
import NotificationPanel from '../components/notifications/NotificationPanel'
import NotificationSettings from '../components/notifications/NotificationSettings'
import NotificationDemo from '../components/notifications/NotificationDemo'

// Hook
import { useNotifications } from '../hooks/useNotifications'
```

---

## 🎯 Exemplos Rápidos

### 1. Dashboard Completo
```javascript
import { useState } from 'react'
import NotificationBell from '../components/notifications/NotificationBell'
import NotificationPanel from '../components/notifications/NotificationPanel'
import NotificationSettings from '../components/notifications/NotificationSettings'

export default function Dashboard() {
  const [showPanel, setShowPanel] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const { pendingCount } = useNotifications({ enabled: true })
  
  return (
    <>
      <header>
        <NotificationBell count={pendingCount} onClick={() => setShowPanel(true)} />
        <button onClick={() => setShowSettings(true)}>⚙️</button>
      </header>
      
      <NotificationPanel isOpen={showPanel} onClose={() => setShowPanel(false)} />
      <NotificationSettings isOpen={showSettings} onClose={() => setShowSettings(false)} />
    </>
  )
}
```

### 2. Apenas Demonstração
```javascript
import NotificationDemo from '../components/notifications/NotificationDemo'

<NotificationDemo />
```

### 3. Com Callback de Novo Pedido
```javascript
const { pendingCount } = useNotifications({
  enabled: true,
  onOrderCreated: (order) => {
    console.log('Novo pedido:', order.order_number)
    // Atualizar interface, mapa, etc.
  }
})
```

---

## 🔌 Escutar Eventos

```javascript
// Clique em notificação
window.addEventListener('notification:click', (e) => {
  const { notification } = e.detail
  navigate(`/orders/${notification.orderData?.order_id}`)
})

// Visualizar pedido
window.addEventListener('notification:view-order', (e) => {
  const { orderId } = e.detail
  // Abrir modal, navegar, etc.
})

// Aprovar pedido
window.addEventListener('notification:approve-order', (e) => {
  const { orderId } = e.detail
  // Aprovar via API
})
```

---

## 🧪 Testar Notificação

### Console do Browser
```javascript
window.dispatchEvent(new CustomEvent('websocket:order_created', {
  detail: {
    orderData: {
      order_id: '123',
      order_number: 456,
      customer_name: 'João Silva',
      total_amount: 150.00,
      bairro: 'Centro'
    }
  }
}))
```

### Botão de Teste
```javascript
<button onClick={() => {
  window.dispatchEvent(new CustomEvent('websocket:order_created', {
    detail: { orderData: { /* ... */ } }
  }))
}}>
  Testar Notificação
</button>
```

---

## 🎨 Componentes Disponíveis

| Componente | Descrição | Props |
|------------|-----------|-------|
| `NotificationBell` | Sino com badge | `count`, `onClick` |
| `NotificationPanel` | Painel lateral | `isOpen`, `onClose` |
| `NotificationSettings` | Modal de config | `isOpen`, `onClose` |
| `NotificationDemo` | Exemplo completo | - |
| `NotificationItem` | Item individual | `notification`, `onClick`, `onMarkRead` |

---

## ⚙️ Configurações Disponíveis

| Config | Tipo | Padrão | Descrição |
|--------|------|--------|-----------|
| `sound` | boolean | `true` | Som on/off |
| `soundVolume` | 0-1 | `0.7` | Volume |
| `vibration` | boolean | `true` | Vibração |
| `nativeNotifications` | boolean | `true` | Nativas |
| `autoClose` | ms | `5000` | Auto-fechar |

---

## 🎯 Estrutura de Notificação

```javascript
{
  id: 'unique-id',
  type: 'order',
  title: 'Novo Pedido',
  message: 'Pedido #123 recebido',
  timestamp: '2026-02-14T01:30:00Z',
  read: false,
  orderData: {
    order_id: '123',
    order_number: 456,
    customer_name: 'João Silva',
    total_amount: 150.00,
    bairro: 'Centro'
  }
}
```

---

## 🚨 Troubleshooting

### ❌ Painel não aparece
```javascript
// Verificar estado
const [showPanel, setShowPanel] = useState(false)

// Verificar chamada
<NotificationBell onClick={() => setShowPanel(true)} />
```

### ❌ Configurações não salvam
```javascript
// Usar updateSetting
const { updateSetting } = useNotifications()
updateSetting('sound', false)

// LocalStorage persiste automaticamente
```

### ❌ Eventos não disparam
```javascript
// Registrar listener DEPOIS do mount
useEffect(() => {
  window.addEventListener('notification:click', handler)
  return () => window.removeEventListener('notification:click', handler)
}, [])
```

---

## 📁 Arquivos Criados (Fase 3)

```
frontend/src/components/notifications/
├── NotificationPanel.jsx       ← Painel lateral
├── NotificationItem.jsx        ← Item individual
├── NotificationSettings.jsx    ← Configurações
└── NotificationDemo.jsx        ← Demonstração
```

---

## 🎉 Pronto para Usar!

**Sistema completo de notificações com UI profissional!**

### Para testar agora:
```javascript
<NotificationDemo />
```

### Para usar em produção:
```javascript
// Seu código com NotificationBell + NotificationPanel + NotificationSettings
```

---

**Versão:** 3.0.0  
**Fase:** 3 de 5  
**Status:** ✅ Completo
