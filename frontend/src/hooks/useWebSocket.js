/**
 * Hook useWebSocket - Conexão WebSocket com reconexão automática
 * Uso: const { isConnected, send } = useWebSocket('/ws/chat');
 */

import { useEffect, useRef, useCallback, useState } from 'react'

export const useWebSocket = (url) => {
  const ws = useRef(null)
  const [isConnected, setIsConnected] = useState(false)
  const reconnectAttempts = useRef(0)
  const maxReconnectAttempts = 5
  const reconnectDelay = 3000
  const eventListeners = useRef({})

  const connect = useCallback(() => {
    if (!url || ws.current?.readyState === WebSocket.OPEN) return

    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = url.startsWith('ws')
        ? url
        : `${protocol}//${window.location.host}${url}`

      ws.current = new WebSocket(wsUrl)

      ws.current.onopen = () => {
        console.log('WebSocket conectado:', wsUrl)
        setIsConnected(true)
        reconnectAttempts.current = 0
      }

      ws.current.onerror = (error) => {
        console.error('Erro WebSocket:', error)
        setIsConnected(false)
      }

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          // Disparar eventos registrados
          if (data.type && eventListeners.current[data.type]) {
            eventListeners.current[data.type].forEach(callback => {
              callback(data)
            })
          }
        } catch (error) {
          console.error('Erro ao processar mensagem WebSocket:', error)
        }
      }

      ws.current.onclose = () => {
        console.log('WebSocket desconectado')
        setIsConnected(false)
        
        // Tentar reconectar
        if (reconnectAttempts.current < maxReconnectAttempts) {
          reconnectAttempts.current++
          setTimeout(() => {
            console.log(
              `Tentando reconectar WebSocket (${reconnectAttempts.current}/${maxReconnectAttempts})...`
            )
            connect()
          }, reconnectDelay)
        } else {
          console.error('Máximo de tentativas de reconexão atingido')
        }
      }
    } catch (error) {
      console.error('Erro ao conectar WebSocket:', error)
      setIsConnected(false)
    }
  }, [url])

  // Conectar ao montar
  useEffect(() => {
    connect()

    // Desconectar ao desmontar
    return () => {
      if (ws.current) {
        ws.current.close()
      }
      eventListeners.current = {}
    }
  }, [connect, url])

  const send = useCallback((data) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(data))
    } else {
      console.warn('WebSocket não está conectado')
    }
  }, [])

  return {
    isConnected,
    send,
    ws: ws.current
  }
}

/**
 * Hook para escutar eventos específicos do WebSocket
 * @param {string} event - Nome do evento (ex: 'new_order', 'order_update')
 * @param {Function} callback - Função chamada quando evento ocorre
 * 
 * NOTA: Este hook é mantido apenas para compatibilidade.
 * Use useSharedWebSocketEvent de './useSharedWebSocket' para melhor performance.
 */
export function useWebSocketEvent(event, callback) {
  useEffect(() => {
    // Importar dinamicamente o serviço compartilhado
    import('../services/sharedWebSocket').then((module) => {
      const sharedService = module.default
      if (sharedService && typeof sharedService.on === 'function') {
        const unsubscribe = sharedService.on(event, callback)
        return () => {
          if (unsubscribe) unsubscribe()
        }
      }
    }).catch(() => {
      console.warn(`useWebSocketEvent: Evento '${event}' não pode ser registrado. Use useSharedWebSocketEvent.`)
    })
    
    return () => {}
  }, [event, callback])
}
