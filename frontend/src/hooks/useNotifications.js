/**
 * Hook useNotifications - Integração React com NotificationService
 * 
 * Gerencia notificações de pedidos com estado reativo
 * Integra com WebSocket via eventos do window
 * 
 * @example
 * const { pendingCount, history, test } = useNotifications({ enabled: true })
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import notificationService from '../services/NotificationService'

export const useNotifications = ({ 
  enabled = true,
  autoRequestPermission = false,
  onNotification = null,
} = {}) => {
  // Estados
  const [pendingCount, setPendingCount] = useState(0)
  const [history, setHistory] = useState([])
  const [permissionGranted, setPermissionGranted] = useState(false)
  const [settings, setSettings] = useState({})
  const [isInitialized, setIsInitialized] = useState(false)
  
  // Refs
  const initRef = useRef(false)
  const listenerRef = useRef(null)
  
  /**
   * Inicializar hook
   */
  useEffect(() => {
    if (!enabled || initRef.current) return
    
    initRef.current = true
    
    const initialize = async () => {
      console.log('🔔 useNotifications inicializando...')
      
      setPendingCount(notificationService.getPendingCount())
      setHistory(notificationService.getHistory())
      setSettings(notificationService.getSettings())
      setPermissionGranted(notificationService.permissionGranted)
      
      if (autoRequestPermission && !notificationService.permissionGranted) {
        await notificationService.requestNotificationPermission()
        setPermissionGranted(notificationService.permissionGranted)
      }
      
      setIsInitialized(true)
      console.log('✅ useNotifications inicializado')
    }
    
    initialize()
  }, [enabled, autoRequestPermission])
  
  /**
   * Listener para mudanças no serviço
   */
  useEffect(() => {
    if (!enabled || !isInitialized) return
    
    listenerRef.current = notificationService.addListener((data) => {
      console.log('📬 Evento:', data.type)
      
      switch (data.type) {
        case 'badge_update':
          setPendingCount(data.count)
          break
        case 'mark_read':
        case 'clear_history':
          setHistory([...notificationService.getHistory()])
          setPendingCount(notificationService.getPendingCount())
          break
        case 'setting_changed':
          setSettings(notificationService.getSettings())
          break
        case 'new_order':
          setHistory([...notificationService.getHistory()])
          setPendingCount(notificationService.getPendingCount())
          if (onNotification) onNotification(data)
          break
        default:
          setHistory([...notificationService.getHistory()])
          setPendingCount(notificationService.getPendingCount())
      }
    })
    
    return () => {
      if (listenerRef.current) {
        listenerRef.current()
      }
    }
  }, [enabled, isInitialized, onNotification])
  
  /**
   * Escutar eventos WebSocket via window
   */
  useEffect(() => {
    if (!enabled || !isInitialized) return
    
    const handleOrderCreated = (event) => {
      const { orderData } = event.detail
      console.log('📦 Novo pedido via evento:', orderData)
      notificationService.notifyNewOrder(orderData)
    }
    
    window.addEventListener('websocket:order_created', handleOrderCreated)
    
    return () => {
      window.removeEventListener('websocket:order_created', handleOrderCreated)
    }
  }, [enabled, isInitialized])
  
  /**
   * Marcar notificação como lida
   */
  const markAsRead = useCallback((notificationId) => {
    if (!enabled) return
    notificationService.markAsRead(notificationId)
  }, [enabled])
  
  /**
   * Marcar todas como lidas
   */
  const markAllAsRead = useCallback(() => {
    if (!enabled) return
    history.forEach(notif => {
      if (!notif.read) notificationService.markAsRead(notif.id)
    })
  }, [enabled, history])
  
  /**
   * Limpar histórico
   */
  const clearHistory = useCallback(() => {
    if (!enabled) return
    notificationService.clearHistory()
  }, [enabled])
  
  /**
   * Solicitar permissão
   */
  const requestPermission = useCallback(async () => {
    const granted = await notificationService.requestNotificationPermission()
    setPermissionGranted(granted)
    return granted
  }, [])
  
  /**
   * Atualizar configuração
   */
  const updateSetting = useCallback((key, value) => {
    if (!enabled) return
    notificationService.updateSetting(key, value)
  }, [enabled])
  
  /**
   * Testar notificação
   */
  const test = useCallback(() => {
    notificationService.test()
  }, [])
  
  // Retornar API do hook
  return {
    // Estado
    pendingCount,
    history,
    permissionGranted,
    settings,
    isInitialized,
    
    // Funções
    markAsRead,
    markAllAsRead,
    clearHistory,
    requestPermission,
    updateSetting,
    test,
    
    // Estado computado
    hasUnread: pendingCount > 0,
    unreadNotifications: history.filter(n => !n.read),
    totalNotifications: history.length,
  }
}

export default useNotifications
