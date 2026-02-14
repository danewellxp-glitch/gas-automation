/**
 * NotificationService - Sistema de Notificações V2
 * 
 * Versão: 2.0 - Robusta e sem erros
 * Arquivo: .jsx (CORRETO - contém JSX)
 * 
 * Features:
 * - Toast popup com react-hot-toast
 * - Som de alerta
 * - Vibração (mobile)
 * - Notificações nativas do browser
 * - Badge counter
 * - Histórico persistente (LocalStorage)
 * - Sistema de listeners (Observer Pattern)
 * - Configurações personalizáveis
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
    this.settings = {
      sound: true,
      volume: 0.7,
      vibration: true,
      nativeNotifications: true,
      autoCloseTime: 10000, // 10 segundos
    }
    
    console.log('🔔 NotificationService V2 inicializando...')
    this.init()
  }
  
  /**
   * Inicialização do serviço
   */
  async init() {
    try {
      await this.loadSettings()
      await this.loadHistory()
      this.loadNotificationSound()
      await this.requestNotificationPermission()
      console.log('✅ NotificationService V2 inicializado')
    } catch (error) {
      console.error('❌ Erro ao inicializar NotificationService:', error)
    }
  }
  
  /**
   * Carregar configurações do LocalStorage
   */
  loadSettings() {
    try {
      const saved = localStorage.getItem('notification_settings')
      if (saved) {
        this.settings = { ...this.settings, ...JSON.parse(saved) }
        console.log('⚙️ Configurações carregadas:', this.settings)
      }
    } catch (error) {
      console.warn('⚠️ Erro ao carregar configurações:', error)
    }
  }
  
  /**
   * Carregar histórico do LocalStorage
   */
  loadHistory() {
    try {
      const saved = localStorage.getItem('notifications_history')
      if (saved) {
        const data = JSON.parse(saved)
        this.history = data.history || []
        this.pendingCount = data.pendingCount || 0
        console.log(`📋 Histórico carregado: ${this.history.length} notificações`)
      }
    } catch (error) {
      console.warn('⚠️ Erro ao carregar histórico:', error)
    }
  }
  
  /**
   * Carregar som de notificação
   */
  loadNotificationSound() {
    try {
      this.audio = new Audio('/sounds/notification.mp3')
      this.audio.volume = this.settings.volume
      this.audio.preload = 'auto'
      console.log('🔊 Som de notificação carregado')
    } catch (error) {
      console.warn('⚠️ Erro ao carregar som:', error)
    }
  }
  
  /**
   * Solicitar permissão para notificações nativas
   */
  async requestNotificationPermission() {
    if (!('Notification' in window)) {
      console.warn('⚠️ Browser não suporta notificações nativas')
      return false
    }
    
    if (Notification.permission === 'granted') {
      this.permissionGranted = true
      console.log('✅ Permissão de notificações concedida')
      return true
    }
    
    if (Notification.permission !== 'denied') {
      try {
        const permission = await Notification.requestPermission()
        this.permissionGranted = permission === 'granted'
        console.log(`🔐 Permissão de notificações: ${permission}`)
        return this.permissionGranted
      } catch (error) {
        console.warn('⚠️ Erro ao solicitar permissão:', error)
        return false
      }
    }
    
    return false
  }
  
  /**
   * Notificar novo pedido (método principal)
   */
  notifyNewOrder(orderData) {
    console.log('📦 Notificando novo pedido:', orderData)
    
    const notification = {
      id: `order-${orderData.order_id || Date.now()}`,
      type: 'new_order',
      title: '🔔 Novo Pedido!',
      message: this.formatOrderMessage(orderData),
      orderData,
      timestamp: new Date().toISOString(),
      read: false,
    }
    
    // Adicionar ao histórico
    this.addToHistory(notification)
    
    // Incrementar contador
    this.incrementPendingCount()
    
    // Executar ações
    if (this.settings.sound) {
      this.playSound()
    }
    
    if (this.settings.vibration) {
      this.vibrate([200, 100, 200])
    }
    
    this.showToastNotification(notification)
    
    if (this.settings.nativeNotifications && this.permissionGranted) {
      this.showNativeNotification(notification)
    }
    
    // Notificar listeners
    this.notifyListeners({ type: 'new_order', notification })
    
    return notification
  }
  
  /**
   * Formatar mensagem do pedido
   */
  formatOrderMessage(orderData) {
    const number = orderData.order_number || '#???'
    const customer = orderData.customer_name || 'Cliente'
    const amount = orderData.total_amount 
      ? `R$ ${orderData.total_amount.toFixed(2)}` 
      : ''
    const bairro = orderData.bairro || ''
    
    return `Pedido ${number} - ${customer} ${bairro ? `(${bairro})` : ''} ${amount}`.trim()
  }
  
  /**
   * Tocar som
   */
  playSound() {
    if (this.audio) {
      try {
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
   * Vibrar dispositivo
   */
  vibrate(pattern = 200) {
    if ('vibrate' in navigator) {
      try {
        navigator.vibrate(pattern)
      } catch (error) {
        console.warn('⚠️ Erro ao vibrar:', error)
      }
    }
  }
  
  /**
   * Mostrar toast notification (SIMPLES para evitar erros)
   */
  showToastNotification(notification) {
    // Versão SIMPLES primeiro (evita erros de JSX complexo)
    toast.success(notification.message, {
      duration: this.settings.autoCloseTime,
      icon: '🔔',
      style: {
        background: '#10B981',
        color: '#fff',
        fontSize: '14px',
        fontWeight: '500',
      },
    })
  }
  
  /**
   * Mostrar notificação nativa
   */
  showNativeNotification(notification) {
    if (!this.permissionGranted) return
    
    try {
      const nativeNotif = new Notification(notification.title, {
        body: notification.message,
        icon: '/logo192.png',
        tag: notification.id,
        requireInteraction: false,
        silent: true,
      })
      
      nativeNotif.onclick = () => {
        window.focus()
        window.dispatchEvent(new CustomEvent('notification:view-order', {
          detail: { orderId: notification.orderData.order_id }
        }))
        nativeNotif.close()
      }
      
      setTimeout(() => nativeNotif.close(), 8000)
    } catch (error) {
      console.warn('⚠️ Erro ao mostrar notificação nativa:', error)
    }
  }
  
  /**
   * Adicionar ao histórico
   */
  addToHistory(notification) {
    this.history.unshift(notification)
    
    // Limitar a 50
    if (this.history.length > this.maxHistorySize) {
      this.history = this.history.slice(0, this.maxHistorySize)
    }
    
    this.saveHistory()
  }
  
  /**
   * Salvar histórico
   */
  saveHistory() {
    try {
      localStorage.setItem('notifications_history', JSON.stringify({
        history: this.history.slice(0, 20),
        pendingCount: this.pendingCount,
      }))
    } catch (error) {
      console.warn('⚠️ Erro ao salvar histórico:', error)
    }
  }
  
  /**
   * Obter histórico
   */
  getHistory() {
    return this.history
  }
  
  /**
   * Obter contador
   */
  getPendingCount() {
    return this.pendingCount
  }
  
  /**
   * Incrementar contador
   */
  incrementPendingCount() {
    this.pendingCount++
    this.updateBadge()
  }
  
  /**
   * Decrementar contador
   */
  decrementPendingCount() {
    if (this.pendingCount > 0) {
      this.pendingCount--
      this.updateBadge()
    }
  }
  
  /**
   * Atualizar badge
   */
  updateBadge() {
    this.notifyListeners({ type: 'badge_update', count: this.pendingCount })
  }
  
  /**
   * Marcar como lida
   */
  markAsRead(notificationId) {
    const notif = this.history.find(n => n.id === notificationId)
    if (notif && !notif.read) {
      notif.read = true
      this.decrementPendingCount()
      this.saveHistory()
      this.notifyListeners({ type: 'mark_read', notificationId })
    }
  }
  
  /**
   * Limpar histórico
   */
  clearHistory() {
    this.history = []
    this.pendingCount = 0
    this.saveHistory()
    this.notifyListeners({ type: 'clear_history' })
  }
  
  /**
   * Atualizar configuração
   */
  updateSetting(key, value) {
    this.settings[key] = value
    
    // Aplicar mudança imediatamente
    if (key === 'volume' && this.audio) {
      this.audio.volume = value
    }
    
    // Salvar
    try {
      localStorage.setItem('notification_settings', JSON.stringify(this.settings))
      this.notifyListeners({ type: 'setting_changed', key, value })
    } catch (error) {
      console.warn('⚠️ Erro ao salvar configuração:', error)
    }
  }
  
  /**
   * Obter configurações
   */
  getSettings() {
    return this.settings
  }
  
  /**
   * Adicionar listener
   */
  addListener(callback) {
    this.listeners.push(callback)
    return () => {
      this.listeners = this.listeners.filter(cb => cb !== callback)
    }
  }
  
  /**
   * Notificar listeners
   */
  notifyListeners(data) {
    this.listeners.forEach(callback => {
      try {
        callback(data)
      } catch (error) {
        console.error('❌ Erro em listener:', error)
      }
    })
  }
  
  /**
   * Testar notificação
   */
  test() {
    console.log('🧪 Testando notificação...')
    this.notifyNewOrder({
      order_id: Date.now(),
      order_number: '#TESTE',
      customer_name: 'Cliente Teste',
      total_amount: 123.45,
      bairro: 'Centro',
      status: 'pending'
    })
  }
}

// Exportar instância singleton
const notificationService = new NotificationService()

export default notificationService
export { notificationService }