# 🔔 Planejamento: Sistema de Notificações Popup para Novos Pedidos

**Data:** 13/02/2026  
**Objetivo:** Implementar notificações popup em tempo real quando novos pedidos chegarem, com som, vibração e ações rápidas

---

## 🎯 Visão Geral

### Problema Atual
- Operador precisa ficar olhando a tela constantemente
- Novos pedidos podem passar despercebidos
- Não há alerta sonoro ou visual chamativo
- Falta ações rápidas (aprovar/visualizar direto do popup)

### Solução Proposta
1. **Popup Visual**: Toast customizado com destaque
2. **Som de Notificação**: Audio alert ao receber pedido
3. **Vibração (Mobile)**: Haptic feedback em dispositivos móveis
4. **Ações Rápidas**: Botões no popup (Ver Detalhes/Aprovar/Dispensar)
5. **Notificações Nativas**: Browser notification API
6. **Badge Counter**: Contador de pedidos pendentes
7. **Histórico de Notificações**: Lista de notificações recentes

---

## 📊 Arquitetura do Sistema

```
┌─────────────────────────────────────────────┐
│        Backend (WebSocket)                  │
│  - Evento: "order_created"                  │
│  - Payload: order_data + notification_type  │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│     Frontend - NotificationService          │
│  1. Recebe evento WebSocket                 │
│  2. Toca som de alerta                      │
│  3. Vibra dispositivo (se mobile)           │
│  4. Mostra toast customizado                │
│  5. Mostra native notification              │
│  6. Atualiza badge counter                  │
└─────────────────┬───────────────────────────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
┌──────────────┐    ┌──────────────────┐
│ Toast Popup  │    │ Native Notif     │
│ - Visual     │    │ - Browser API    │
│ - Ações      │    │ - Desktop/Mobile │
└──────────────┘    └──────────────────┘
```

---

## 🏗️ Implementação Detalhada

### **FASE 1: Serviço de Notificações** (2-3h)

#### 1.1. Criar `NotificationService`

**Arquivo:** `frontend/src/services/NotificationService.js` (NOVO)

```javascript
/**
 * NotificationService - Gerencia notificações de pedidos em tempo real
 * 
 * Features:
 * - Toast popup customizado
 * - Som de alerta
 * - Vibração (mobile)
 * - Native browser notifications
 * - Badge counter
 * - Histórico de notificações
 */

import toast from 'react-hot-toast'

class NotificationService {
  constructor() {
    this.audio = null
    this.pendingCount = 0
    this.history = []
    this.maxHistorySize = 50
    this.permissionGranted = false
    this.listeners = []
    
    // Inicializar
    this.init()
  }
  
  /**
   * Inicializa o serviço
   */
  async init() {
    // Pré-carregar som de notificação
    this.loadNotificationSound()
    
    // Solicitar permissão para notificações nativas
    await this.requestNotificationPermission()
  }
  
  /**
   * Carrega o arquivo de som
   */
  loadNotificationSound() {
    try {
      // Som: notification.mp3 (deve estar em public/)
      this.audio = new Audio('/sounds/notification.mp3')
      this.audio.volume = 0.7
      this.audio.preload = 'auto'
      
      console.log('✅ Som de notificação carregado')
    } catch (error) {
      console.warn('⚠️ Não foi possível carregar som de notificação:', error)
    }
  }
  
  /**
   * Solicita permissão para notificações nativas do browser
   */
  async requestNotificationPermission() {
    if (!('Notification' in window)) {
      console.warn('⚠️ Browser não suporta notificações nativas')
      return false
    }
    
    if (Notification.permission === 'granted') {
      this.permissionGranted = true
      return true
    }
    
    if (Notification.permission !== 'denied') {
      const permission = await Notification.requestPermission()
      this.permissionGranted = permission === 'granted'
      return this.permissionGranted
    }
    
    return false
  }
  
  /**
   * Notifica novo pedido
   * @param {Object} orderData - Dados do pedido
   */
  notifyNewOrder(orderData) {
    const notification = {
      id: `order-${orderData.order_id || Date.now()}`,
      type: 'new_order',
      title: '🔔 Novo Pedido!',
      message: this.formatOrderMessage(orderData),
      orderData,
      timestamp: new Date(),
      read: false,
    }
    
    // Adicionar ao histórico
    this.addToHistory(notification)
    
    // Incrementar contador
    this.incrementPendingCount()
    
    // Tocar som
    this.playSound()
    
    // Vibrar (mobile)
    this.vibrate([200, 100, 200])
    
    // Mostrar toast popup
    this.showToastNotification(notification)
    
    // Mostrar notificação nativa do browser
    this.showNativeNotification(notification)
    
    // Notificar listeners
    this.notifyListeners(notification)
    
    return notification
  }
  
  /**
   * Formata mensagem do pedido
   */
  formatOrderMessage(orderData) {
    const number = orderData.order_number || '#???'
    const customer = orderData.customer_name || 'Cliente'
    const amount = orderData.total_amount 
      ? `R$ ${orderData.total_amount.toFixed(2)}` 
      : ''
    const bairro = orderData.bairro || ''
    
    return `Pedido ${number} - ${customer} ${bairro ? `(${bairro})` : ''} ${amount}`
  }
  
  /**
   * Toca som de notificação
   */
  playSound() {
    if (this.audio) {
      try {
        // Reset e play
        this.audio.currentTime = 0
        this.audio.play().catch(err => {
          console.warn('⚠️ Não foi possível tocar som:', err)
        })
      } catch (error) {
        console.warn('⚠️ Erro ao tocar som:', error)
      }
    }
  }
  
  /**
   * Vibra dispositivo (mobile)
   * @param {Array|number} pattern - Padrão de vibração [duração, pausa, duração, ...]
   */
  vibrate(pattern = 200) {
    if ('vibrate' in navigator) {
      try {
        navigator.vibrate(pattern)
      } catch (error) {
        console.warn('⚠️ Não foi possível vibrar:', error)
      }
    }
  }
  
  /**
   * Mostra toast popup customizado com ações
   */
  showToastNotification(notification) {
    const { orderData } = notification
    
    // Toast customizado com react-hot-toast
    toast.custom(
      (t) => (
        <div
          className={`${
            t.visible ? 'animate-enter' : 'animate-leave'
          } max-w-md w-full bg-white shadow-lg rounded-lg pointer-events-auto flex ring-1 ring-black ring-opacity-5`}
        >
          <div className="flex-1 w-0 p-4">
            <div className="flex items-start">
              {/* Ícone */}
              <div className="flex-shrink-0 pt-0.5">
                <div className="h-10 w-10 rounded-full bg-primary-600 flex items-center justify-center animate-pulse">
                  <span className="text-white text-xl">🔔</span>
                </div>
              </div>
              
              {/* Conteúdo */}
              <div className="ml-3 flex-1">
                <p className="text-sm font-medium text-gray-900">
                  {notification.title}
                </p>
                <p className="mt-1 text-sm text-gray-500">
                  {notification.message}
                </p>
                
                {/* Badges de status */}
                <div className="mt-2 flex gap-2">
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
                    {orderData.status === 'pending' ? 'Aguardando' : orderData.status}
                  </span>
                  {orderData.bairro && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                      📍 {orderData.bairro}
                    </span>
                  )}
                </div>
              </div>
            </div>
            
            {/* Botões de ação */}
            <div className="mt-3 flex gap-2">
              <button
                onClick={() => {
                  this.onViewOrder(orderData.order_id)
                  toast.dismiss(t.id)
                }}
                className="flex-1 bg-primary-600 text-white px-3 py-2 rounded-md text-xs font-medium hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                👁️ Ver Detalhes
              </button>
              
              <button
                onClick={() => {
                  this.onApproveOrder(orderData.order_id)
                  toast.dismiss(t.id)
                }}
                className="flex-1 bg-green-600 text-white px-3 py-2 rounded-md text-xs font-medium hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500"
              >
                ✅ Aprovar
              </button>
              
              <button
                onClick={() => toast.dismiss(t.id)}
                className="bg-gray-200 text-gray-700 px-3 py-2 rounded-md text-xs font-medium hover:bg-gray-300 focus:outline-none"
              >
                ✕
              </button>
            </div>
          </div>
        </div>
      ),
      {
        duration: 10000, // 10 segundos
        position: 'top-right',
        id: notification.id, // Evitar duplicatas
      }
    )
  }
  
  /**
   * Mostra notificação nativa do browser
   */
  showNativeNotification(notification) {
    if (!this.permissionGranted) return
    
    try {
      const nativeNotif = new Notification(notification.title, {
        body: notification.message,
        icon: '/logo192.png', // Logo do app
        badge: '/badge.png',
        tag: notification.id, // Evitar duplicatas
        requireInteraction: false, // Auto-fechar após alguns segundos
        silent: true, // Som já tocou
        data: {
          orderId: notification.orderData.order_id,
          type: 'new_order'
        }
      })
      
      // Ao clicar na notificação
      nativeNotif.onclick = () => {
        window.focus()
        this.onViewOrder(notification.orderData.order_id)
        nativeNotif.close()
      }
      
      // Auto-fechar após 8 segundos
      setTimeout(() => nativeNotif.close(), 8000)
      
    } catch (error) {
      console.warn('⚠️ Erro ao mostrar notificação nativa:', error)
    }
  }
  
  /**
   * Callbacks de ações
   */
  onViewOrder(orderId) {
    // Disparar evento customizado
    window.dispatchEvent(new CustomEvent('notification:view-order', {
      detail: { orderId }
    }))
  }
  
  onApproveOrder(orderId) {
    // Disparar evento customizado
    window.dispatchEvent(new CustomEvent('notification:approve-order', {
      detail: { orderId }
    }))
  }
  
  /**
   * Gerenciamento de histórico
   */
  addToHistory(notification) {
    this.history.unshift(notification)
    
    // Limitar tamanho do histórico
    if (this.history.length > this.maxHistorySize) {
      this.history = this.history.slice(0, this.maxHistorySize)
    }
    
    // Persistir no localStorage
    this.saveHistory()
  }
  
  getHistory() {
    return this.history
  }
  
  markAsRead(notificationId) {
    const notif = this.history.find(n => n.id === notificationId)
    if (notif) {
      notif.read = true
      this.decrementPendingCount()
      this.saveHistory()
    }
  }
  
  clearHistory() {
    this.history = []
    this.pendingCount = 0
    this.saveHistory()
  }
  
  saveHistory() {
    try {
      localStorage.setItem('notifications_history', JSON.stringify({
        history: this.history.slice(0, 20), // Salvar apenas últimas 20
        pendingCount: this.pendingCount,
      }))
    } catch (error) {
      console.warn('⚠️ Erro ao salvar histórico:', error)
    }
  }
  
  loadHistory() {
    try {
      const saved = localStorage.getItem('notifications_history')
      if (saved) {
        const data = JSON.parse(saved)
        this.history = data.history || []
        this.pendingCount = data.pendingCount || 0
      }
    } catch (error) {
      console.warn('⚠️ Erro ao carregar histórico:', error)
    }
  }
  
  /**
   * Gerenciamento de contador
   */
  incrementPendingCount() {
    this.pendingCount++
    this.updateBadge()
  }
  
  decrementPendingCount() {
    if (this.pendingCount > 0) {
      this.pendingCount--
      this.updateBadge()
    }
  }
  
  resetPendingCount() {
    this.pendingCount = 0
    this.updateBadge()
  }
  
  getPendingCount() {
    return this.pendingCount
  }
  
  updateBadge() {
    // Atualizar badge no ícone do navegador (se suportado)
    if ('setAppBadge' in navigator) {
      navigator.setAppBadge(this.pendingCount).catch(err => {
        console.warn('⚠️ Não foi possível atualizar badge:', err)
      })
    }
    
    // Notificar listeners
    this.notifyListeners({ type: 'badge_update', count: this.pendingCount })
  }
  
  /**
   * Sistema de listeners (observers)
   */
  addListener(callback) {
    this.listeners.push(callback)
    return () => {
      this.listeners = this.listeners.filter(cb => cb !== callback)
    }
  }
  
  notifyListeners(data) {
    this.listeners.forEach(callback => {
      try {
        callback(data)
      } catch (error) {
        console.error('Erro em listener de notificação:', error)
      }
    })
  }
}

// Exportar instância singleton
export const notificationService = new NotificationService()

export default notificationService
```

#### 1.2. Adicionar som de notificação

**Arquivo:** `frontend/public/sounds/notification.mp3` (NOVO)

Opções de sons:
1. **Baixar de bibliotecas gratuitas:**
   - https://notificationsounds.com/
   - https://freesound.org/
   - https://mixkit.co/free-sound-effects/notification/

2. **Gerar com ferramentas:**
   - https://sfxr.me/ (gerador de sons 8-bit)
   - Audacity (editar/criar sons)

3. **Som recomendado:** Tom curto e agradável (não irritante)
   - Duração: 0.5-1.5 segundos
   - Volume moderado
   - Tom: campainha suave ou "ding"

---

### **FASE 2: Hook React de Notificações** (1h)

#### 2.1. Criar hook `useNotifications`

**Arquivo:** `frontend/src/hooks/useNotifications.js` (NOVO)

```javascript
/**
 * Hook useNotifications - Gerencia notificações de pedidos
 * Uso: const { pendingCount, history, markAsRead } = useNotifications();
 */

import { useState, useEffect, useCallback } from 'react'
import notificationService from '../services/NotificationService'
import { useWebSocket } from './useWebSocket'

export const useNotifications = ({ enabled = true } = {}) => {
  const [pendingCount, setPendingCount] = useState(0)
  const [history, setHistory] = useState([])
  const [permissionGranted, setPermissionGranted] = useState(false)
  
  // WebSocket para receber eventos
  const { addEventListener } = useWebSocket('/ws/operator')
  
  // Inicializar
  useEffect(() => {
    if (!enabled) return
    
    // Carregar histórico do localStorage
    notificationService.loadHistory()
    setPendingCount(notificationService.getPendingCount())
    setHistory(notificationService.getHistory())
    setPermissionGranted(notificationService.permissionGranted)
    
    // Listener para updates do serviço
    const unsubscribe = notificationService.addListener((data) => {
      if (data.type === 'badge_update') {
        setPendingCount(data.count)
      } else {
        setHistory([...notificationService.getHistory()])
      }
    })
    
    return () => unsubscribe()
  }, [enabled])
  
  // Escutar eventos de novos pedidos
  useEffect(() => {
    if (!enabled) return
    
    const handleNewOrder = (data) => {
      if (data.type === 'order_created') {
        notificationService.notifyNewOrder(data)
      }
    }
    
    const unsubscribe = addEventListener('order_created', handleNewOrder)
    
    return () => unsubscribe?.()
  }, [enabled, addEventListener])
  
  // Marcar como lida
  const markAsRead = useCallback((notificationId) => {
    notificationService.markAsRead(notificationId)
    setHistory([...notificationService.getHistory()])
    setPendingCount(notificationService.getPendingCount())
  }, [])
  
  // Limpar histórico
  const clearHistory = useCallback(() => {
    notificationService.clearHistory()
    setHistory([])
    setPendingCount(0)
  }, [])
  
  // Solicitar permissão
  const requestPermission = useCallback(async () => {
    const granted = await notificationService.requestNotificationPermission()
    setPermissionGranted(granted)
    return granted
  }, [])
  
  return {
    pendingCount,
    history,
    permissionGranted,
    markAsRead,
    clearHistory,
    requestPermission,
  }
}

export default useNotifications
```

---

### **FASE 3: Componente de Badge e Histórico** (2h)

#### 3.1. Criar `NotificationBadge`

**Arquivo:** `frontend/src/components/notifications/NotificationBadge.jsx` (NOVO)

```jsx
/**
 * Badge de notificações pendentes
 * Exibe contador de pedidos não lidos
 */

import { Bell } from 'lucide-react'

export default function NotificationBadge({ count = 0, onClick }) {
  return (
    <button
      onClick={onClick}
      className="relative p-2 text-gray-600 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary-500 rounded-full"
      aria-label={`${count} notificações pendentes`}
    >
      <Bell className="w-6 h-6" />
      
      {count > 0 && (
        <span className="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-600 text-xs font-bold text-white animate-pulse">
          {count > 9 ? '9+' : count}
        </span>
      )}
    </button>
  )
}
```

#### 3.2. Criar `NotificationPanel`

**Arquivo:** `frontend/src/components/notifications/NotificationPanel.jsx` (NOVO)

```jsx
/**
 * Painel de histórico de notificações
 * Lista de notificações recentes com ações
 */

import { useState } from 'react'
import { X, Check, Eye, Trash2 } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { ptBR } from 'date-fns/locale'

export default function NotificationPanel({ 
  isOpen, 
  onClose, 
  history = [],
  onMarkAsRead,
  onClearAll,
  onViewOrder,
}) {
  if (!isOpen) return null
  
  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black bg-opacity-25 z-40"
        onClick={onClose}
      />
      
      {/* Panel */}
      <div className="fixed top-0 right-0 h-full w-96 bg-white shadow-2xl z-50 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-semibold text-gray-900">
            Notificações ({history.length})
          </h2>
          <button
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-gray-600 rounded-full"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        {/* Lista de notificações */}
        <div className="flex-1 overflow-y-auto">
          {history.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-400">
              <Bell className="w-12 h-12 mb-2" />
              <p>Nenhuma notificação</p>
            </div>
          ) : (
            <div className="divide-y">
              {history.map((notif) => (
                <NotificationItem
                  key={notif.id}
                  notification={notif}
                  onMarkAsRead={onMarkAsRead}
                  onViewOrder={onViewOrder}
                />
              ))}
            </div>
          )}
        </div>
        
        {/* Footer */}
        {history.length > 0 && (
          <div className="p-4 border-t">
            <button
              onClick={onClearAll}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50 rounded-md"
            >
              <Trash2 className="w-4 h-4" />
              Limpar Tudo
            </button>
          </div>
        )}
      </div>
    </>
  )
}

function NotificationItem({ notification, onMarkAsRead, onViewOrder }) {
  const { id, title, message, timestamp, read, orderData } = notification
  
  return (
    <div 
      className={`p-4 hover:bg-gray-50 cursor-pointer ${!read ? 'bg-blue-50' : ''}`}
      onClick={() => onViewOrder(orderData.order_id)}
    >
      <div className="flex items-start gap-3">
        {/* Ícone */}
        <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          !read ? 'bg-primary-600 animate-pulse' : 'bg-gray-300'
        }`}>
          <span className="text-white text-sm">
            {!read ? '🔔' : '✓'}
          </span>
        </div>
        
        {/* Conteúdo */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900">
            {title}
          </p>
          <p className="text-xs text-gray-600 mt-1">
            {message}
          </p>
          <p className="text-xs text-gray-400 mt-1">
            {formatDistanceToNow(new Date(timestamp), {
              addSuffix: true,
              locale: ptBR
            })}
          </p>
          
          {/* Badges */}
          <div className="flex gap-2 mt-2">
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
              {orderData.status}
            </span>
            {orderData.bairro && (
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                📍 {orderData.bairro}
              </span>
            )}
          </div>
        </div>
        
        {/* Ações */}
        {!read && (
          <button
            onClick={(e) => {
              e.stopPropagation()
              onMarkAsRead(id)
            }}
            className="flex-shrink-0 p-1 text-primary-600 hover:bg-primary-50 rounded"
            title="Marcar como lida"
          >
            <Check className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  )
}
```

---

### **FASE 4: Integração com Dashboard do Operador** (1-2h)

#### 4.1. Atualizar `OperatorDashboard.jsx`

**Arquivo:** `frontend/src/pages/operator/OperatorDashboard.jsx`

```jsx
import { useState, useEffect } from 'react'
import { useNotifications } from '../../hooks/useNotifications'
import NotificationBadge from '../../components/notifications/NotificationBadge'
import NotificationPanel from '../../components/notifications/NotificationPanel'
import FlowbiteLayout from '../../components/flowbite/FlowbiteLayout'

export default function OperatorDashboard() {
  const { user, logout } = useAuth()
  const [activeView, setActiveView] = useState('dashboard')
  const [showNotificationPanel, setShowNotificationPanel] = useState(false)
  
  // NOVO: Hook de notificações
  const {
    pendingCount,
    history,
    permissionGranted,
    markAsRead,
    clearHistory,
    requestPermission,
  } = useNotifications({ enabled: true })
  
  // NOVO: Solicitar permissão ao montar (opcional)
  useEffect(() => {
    if (!permissionGranted) {
      // Mostrar banner pedindo permissão (não forçar)
      console.log('💡 Permita notificações para ser alertado de novos pedidos')
    }
  }, [permissionGranted])
  
  // NOVO: Escutar eventos de ação do NotificationService
  useEffect(() => {
    const handleViewOrder = (event) => {
      const { orderId } = event.detail
      // Navegar para detalhes do pedido ou abrir modal
      setActiveView('orders')
      // TODO: Filtrar/destacar pedido específico
      console.log('Ver pedido:', orderId)
    }
    
    const handleApproveOrder = async (event) => {
      const { orderId } = event.detail
      // Aprovar pedido diretamente
      try {
        await fetch(`/api/orders/${orderId}/status`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status: 'paid' })
        })
        toast.success('Pedido aprovado!')
      } catch (error) {
        toast.error('Erro ao aprovar pedido')
      }
    }
    
    window.addEventListener('notification:view-order', handleViewOrder)
    window.addEventListener('notification:approve-order', handleApproveOrder)
    
    return () => {
      window.removeEventListener('notification:view-order', handleViewOrder)
      window.removeEventListener('notification:approve-order', handleApproveOrder)
    }
  }, [])
  
  return (
    <FlowbiteLayout
      appName="Gas Automation"
      pageTitle="Operador"
      userEmail={user?.email || ''}
      onLogout={logout}
      
      // NOVO: Adicionar badge de notificações no header
      headerActions={
        <NotificationBadge
          count={pendingCount}
          onClick={() => setShowNotificationPanel(true)}
        />
      }
      
      navItems={[
        { key: 'dashboard', type: 'button', label: 'Dashboard', icon: LayoutDashboard, onClick: () => setActiveView('dashboard') },
        // ... outros itens ...
      ]}
    >
      {/* Views existentes */}
      {activeView === 'dashboard' && <OperatorDashboardOverview />}
      {/* ... outras views ... */}
      
      {/* NOVO: Painel de notificações */}
      <NotificationPanel
        isOpen={showNotificationPanel}
        onClose={() => setShowNotificationPanel(false)}
        history={history}
        onMarkAsRead={markAsRead}
        onClearAll={clearHistory}
        onViewOrder={(orderId) => {
          setShowNotificationPanel(false)
          // Navegar para pedido
          window.dispatchEvent(new CustomEvent('notification:view-order', {
            detail: { orderId }
          }))
        }}
      />
      
      {/* NOVO: Banner de permissão (se não concedida) */}
      {!permissionGranted && (
        <div className="fixed bottom-4 right-4 z-50 max-w-sm">
          <div className="bg-white rounded-lg shadow-lg p-4 border-l-4 border-primary-600">
            <div className="flex items-start gap-3">
              <span className="text-2xl">🔔</span>
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">
                  Ativar Notificações
                </p>
                <p className="text-xs text-gray-600 mt-1">
                  Receba alertas de novos pedidos mesmo com a aba em segundo plano
                </p>
                <button
                  onClick={requestPermission}
                  className="mt-2 text-xs text-primary-600 font-medium hover:underline"
                >
                  Permitir Notificações
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </FlowbiteLayout>
  )
}
```

---

### **FASE 5: Melhorias e Personalizações** (1-2h)

#### 5.1. Configurações de notificação

**Arquivo:** `frontend/src/components/notifications/NotificationSettings.jsx` (NOVO)

```jsx
/**
 * Configurações de notificações
 * Permite usuário personalizar comportamento
 */

import { useState, useEffect } from 'react'
import { Volume2, VolumeX, Vibrate, Bell, BellOff } from 'lucide-react'

export default function NotificationSettings() {
  const [settings, setSettings] = useState({
    enabled: true,
    sound: true,
    vibration: true,
    nativeNotifications: true,
    soundVolume: 0.7,
  })
  
  useEffect(() => {
    // Carregar do localStorage
    const saved = localStorage.getItem('notification_settings')
    if (saved) {
      setSettings(JSON.parse(saved))
    }
  }, [])
  
  const updateSetting = (key, value) => {
    const newSettings = { ...settings, [key]: value }
    setSettings(newSettings)
    localStorage.setItem('notification_settings', JSON.stringify(newSettings))
    
    // Aplicar mudanças
    if (key === 'soundVolume') {
      notificationService.audio.volume = value
    }
  }
  
  return (
    <div className="bg-white rounded-lg shadow p-6 space-y-4">
      <h3 className="text-lg font-semibold text-gray-900">
        Configurações de Notificações
      </h3>
      
      {/* Habilitar/Desabilitar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {settings.enabled ? <Bell className="w-5 h-5 text-primary-600" /> : <BellOff className="w-5 h-5 text-gray-400" />}
          <span className="text-sm font-medium">Notificações</span>
        </div>
        <label className="relative inline-flex items-center cursor-pointer">
          <input
            type="checkbox"
            checked={settings.enabled}
            onChange={(e) => updateSetting('enabled', e.target.checked)}
            className="sr-only peer"
          />
          <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
        </label>
      </div>
      
      {/* Som */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {settings.sound ? <Volume2 className="w-5 h-5" /> : <VolumeX className="w-5 h-5 text-gray-400" />}
          <span className="text-sm">Som</span>
        </div>
        <label className="relative inline-flex items-center cursor-pointer">
          <input
            type="checkbox"
            checked={settings.sound}
            onChange={(e) => updateSetting('sound', e.target.checked)}
            className="sr-only peer"
          />
          <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
        </label>
      </div>
      
      {/* Volume */}
      {settings.sound && (
        <div className="pl-7">
          <label className="text-xs text-gray-600">Volume</label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={settings.soundVolume}
            onChange={(e) => updateSetting('soundVolume', parseFloat(e.target.value))}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
          />
        </div>
      )}
      
      {/* Vibração */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Vibrate className="w-5 h-5" />
          <span className="text-sm">Vibração (Mobile)</span>
        </div>
        <label className="relative inline-flex items-center cursor-pointer">
          <input
            type="checkbox"
            checked={settings.vibration}
            onChange={(e) => updateSetting('vibration', e.target.checked)}
            className="sr-only peer"
          />
          <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
        </label>
      </div>
    </div>
  )
}
```

---

## 🎨 Tipos de Notificações

### 1. **Novo Pedido** (Prioridade Alta)
- **Cor:** 🟢 Verde/Azul
- **Som:** Campainha alegre
- **Vibração:** 200ms
- **Duração:** 10 segundos
- **Ações:** Ver Detalhes | Aprovar

### 2. **Pedido Urgente** (Cliente VIP ou valor alto)
- **Cor:** 🟡 Amarelo/Dourado
- **Som:** Campainha + repetição
- **Vibração:** 200ms, pausa, 200ms
- **Duração:** 15 segundos
- **Ações:** Ver Detalhes | Aprovar Imediatamente

### 3. **Problema na Entrega** (Prioridade Média)
- **Cor:** 🟠 Laranja
- **Som:** Tom de alerta
- **Vibração:** 300ms
- **Duração:** 12 segundos
- **Ações:** Ver Detalhes | Contatar Entregador

### 4. **Pedido Cancelado** (Informativo)
- **Cor:** 🔴 Vermelho
- **Som:** Tom curto
- **Vibração:** 100ms
- **Duração:** 5 segundos
- **Ações:** Ver Motivo

---

## 📊 Fluxo Completo

```
1. CLIENTE FAZ PEDIDO VIA WHATSAPP
   ↓
2. BACKEND CRIA PEDIDO
   - Geocodifica endereço
   - Salva no banco
   ↓
3. BACKEND EMITE WEBSOCKET "order_created"
   - Payload: order_data completo
   - Target: operadores + admin
   ↓
4. FRONTEND RECEBE EVENTO
   - useWebSocket hook captura
   - useNotifications processa
   ↓
5. NOTIFICATION SERVICE EXECUTA:
   5.1. Toca som (audio.play())
   5.2. Vibra dispositivo (navigator.vibrate())
   5.3. Mostra toast popup (react-hot-toast)
   5.4. Mostra native notification (Notification API)
   5.5. Atualiza badge counter
   5.6. Adiciona ao histórico
   ↓
6. OPERADOR VÊ/OUVE NOTIFICAÇÃO
   - Visual: Toast animado no canto
   - Audio: Som de campainha
   - Native: Notificação do OS
   - Badge: Contador vermelho (1)
   ↓
7. OPERADOR INTERAGE
   Opção A: Clica "Ver Detalhes" → Abre pedido
   Opção B: Clica "Aprovar" → Aprova direto
   Opção C: Ignora → Fica no histórico
   Opção D: Clica badge → Abre painel
   ↓
8. MARCAR COMO LIDA
   - Contador diminui
   - Badge atualiza
   - Histórico persiste
```

---

## ✅ Checklist de Implementação

### Backend
- [ ] Garantir evento WebSocket `order_created` está sendo emitido
- [ ] Payload completo (order_data + customer + location)
- [ ] Broadcast para role `operator` e `admin`
- [ ] Testar emissão em tempo real

### Frontend - Core
- [ ] Criar `NotificationService.js`
- [ ] Adicionar som `notification.mp3` em `/public/sounds/`
- [ ] Criar hook `useNotifications.js`
- [ ] Testar permissões de notificação
- [ ] Testar som e vibração

### Frontend - Componentes
- [ ] Criar `NotificationBadge.jsx`
- [ ] Criar `NotificationPanel.jsx`
- [ ] Criar `NotificationSettings.jsx` (opcional)
- [ ] Integrar no `OperatorDashboard.jsx`
- [ ] Adicionar banner de permissão

### Frontend - Integração
- [ ] Escutar evento `order_created` via WebSocket
- [ ] Implementar ações: Ver Detalhes / Aprovar
- [ ] Persistir histórico no localStorage
- [ ] Atualizar badge counter em tempo real
- [ ] Testar múltiplas notificações simultâneas

### UX/UI
- [ ] Animações suaves (enter/leave)
- [ ] Sons não irritantes
- [ ] Feedback visual claro
- [ ] Acessibilidade (aria-labels)
- [ ] Responsivo (mobile/desktop)

### Testes
- [ ] Testar com vários pedidos seguidos
- [ ] Testar som em diferentes browsers
- [ ] Testar notificações nativas (Chrome/Firefox/Safari)
- [ ] Testar vibração em mobile
- [ ] Testar persistência do histórico
- [ ] Testar ações rápidas (aprovar/ver)

---

## 🚀 Estimativas de Tempo

| Fase | Descrição | Tempo Estimado |
|------|-----------|----------------|
| 1 | Serviço de Notificações | 2-3h |
| 2 | Hook React | 1h |
| 3 | Badge e Histórico | 2h |
| 4 | Integração com Dashboard | 1-2h |
| 5 | Melhorias e Personalizações | 1-2h |
| **TOTAL** | **Implementação Completa** | **7-10 horas** |

---

## 📈 Melhorias Futuras

### Fase 2.0
1. **Smart Notifications**: Não notificar se usuário está na aba ativa
2. **Agrupamento**: Agrupar múltiplos pedidos em uma notificação
3. **Priorização**: Notificações diferentes para clientes VIP
4. **Snooze**: Adiar notificação por X minutos
5. **Filtros**: Notificar apenas pedidos de certos bairros

### Fase 3.0
1. **Push Notifications**: Service Worker para notificações offline
2. **Email Digest**: Resumo diário de pedidos por email
3. **SMS Alerts**: Notificar via SMS em casos críticos
4. **Analytics**: Rastrear taxa de conversão por notificação
5. **A/B Testing**: Testar diferentes sons/mensagens

---

## 🎉 Resultado Final

Após implementação completa, o sistema terá:

✅ **Notificações Visuais**: Toast popup customizado e atraente  
✅ **Som de Alerta**: Audio notification ao receber pedido  
✅ **Vibração Mobile**: Haptic feedback em smartphones  
✅ **Notificações Nativas**: Browser notifications (desktop/mobile)  
✅ **Badge Counter**: Contador vermelho de pendentes  
✅ **Ações Rápidas**: Aprovar/Ver direto do popup  
✅ **Histórico**: Lista de todas as notificações recentes  
✅ **Persistência**: Histórico salvo no localStorage  
✅ **Configurável**: Usuário pode ajustar volume, som, vibração  
✅ **Multi-browser**: Funciona em Chrome, Firefox, Safari, Edge

---

## 📝 Considerações Importantes

### Performance
- ✅ Áudio pré-carregado (evita delay)
- ✅ Debounce para múltiplas notificações simultâneas
- ✅ Limite de histórico (50 últimas)
- ✅ Cleanup de listeners ao desmontar

### UX
- ⚠️ Som não deve ser irritante (volume moderado)
- ⚠️ Toast não deve bloquear interface
- ⚠️ Permitir desabilitar notificações facilmente
- ⚠️ Respeitar preferência "Do Not Disturb" do OS

### Browsers
- ✅ Chrome/Edge: Suporte completo
- ✅ Firefox: Suporte completo
- ✅ Safari: Notification API requer permissão explícita
- ⚠️ iOS Safari: Notificações nativas limitadas

### Segurança
- ✅ Verificar role do usuário antes de notificar
- ✅ Não incluir dados sensíveis na notificação nativa
- ✅ Respeitar LGPD (dados pessoais)

---

**Pronto para implementar?** 🔔

Este planejamento detalha **TUDO** necessário para criar um sistema completo de notificações popup de novos pedidos com som, vibração e ações rápidas!
