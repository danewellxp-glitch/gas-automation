import { useState, useEffect, useCallback } from 'react'
import websocketService from '../services/websocket'

/**
 * Hook para usar WebSocket em componentes React.
 */
export function useWebSocket() {
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState(null)

  useEffect(() => {
    // Conectar ao montar
    websocketService.connect()

    // Listeners
    const unsubConnected = websocketService.on('connected', () => {
      setIsConnected(true)
    })

    const unsubDisconnected = websocketService.on('disconnected', () => {
      setIsConnected(false)
    })

    // Cleanup
    return () => {
      unsubConnected()
      unsubDisconnected()
    }
  }, [])

  const subscribe = useCallback((event, callback) => {
    return websocketService.on(event, (data) => {
      setLastMessage(data)
      callback(data)
    })
  }, [])

  const send = useCallback((data) => {
    websocketService.send(data)
  }, [])

  return {
    isConnected,
    lastMessage,
    subscribe,
    send,
  }
}

/**
 * Hook para receber eventos específicos.
 */
export function useWebSocketEvent(event, callback) {
  useEffect(() => {
    const unsubscribe = websocketService.on(event, callback)
    return unsubscribe
  }, [event, callback])
}

export default useWebSocket
