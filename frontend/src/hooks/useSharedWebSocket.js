import { useState, useEffect, useCallback } from 'react'
import sharedWebSocketService from '../services/sharedWebSocket'
import logger from '../utils/logger'

/**
 * Hook para usar WebSocket compartilhado entre abas.
 * 
 * Apenas UMA aba (líder) mantém a conexão real ao servidor.
 * Todas as outras abas recebem mensagens via BroadcastChannel.
 * 
 * Redução de tráfego: 5 abas = 1 conexão (80% menos tráfego!)
 */
export function useSharedWebSocket() {
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState(null)

  useEffect(() => {
    // Conectar automaticamente
    // (Na verdade já conecta no singleton, mas mantém consistência)
    
    // Listeners
    const unsubConnected = sharedWebSocketService.on('connected', (data) => {
      setIsConnected(true)
      logger.log('[useSharedWebSocket] Conectado', data)
    })

    const unsubDisconnected = sharedWebSocketService.on('disconnected', () => {
      setIsConnected(false)
      logger.log('[useSharedWebSocket] Desconectado')
    })

    // Cleanup
    return () => {
      unsubConnected()
      unsubDisconnected()
    }
  }, [])

  const send = useCallback((data) => {
    sharedWebSocketService.send(data)
  }, [])

  return {
    isConnected,
    lastMessage,
    send,
  }
}

/**
 * Hook para escutar eventos específicos do WebSocket compartilhado.
 * 
 * @param {string} event - Nome do evento (ex: 'new_order', 'order_update')
 * @param {Function} callback - Função chamada quando evento ocorre
 */
export function useSharedWebSocketEvent(event, callback) {
  useEffect(() => {
    const unsubscribe = sharedWebSocketService.on(event, callback)
    return unsubscribe
  }, [event, callback])
}

export default useSharedWebSocket
