/**
 * Hook para WebSocket do Driver
 * Conecta e escuta eventos em tempo real
 */

import { useEffect, useState, useCallback, useRef } from 'react'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://192.168.10.156:8000'

export function useWebSocketDriver(onDeliveryAssigned, onDeliveryUpdated, onOperatorMessage) {
  const [connected, setConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState(null)
  const wsRef = useRef(null)

  const connect = useCallback(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      console.warn('WebSocket: Sem token, não conectando')
      return
    }

    console.log('WebSocket: Conectando...')
    const ws = new WebSocket(`${WS_URL}/ws/dashboard?token=${token}`)
    wsRef.current = ws

    ws.onopen = () => {
      console.log('✅ WebSocket conectado')
      setConnected(true)
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        console.log('📨 WebSocket message:', data)
        setLastMessage(data)

        // Processar eventos específicos
        switch (data.type) {
          case 'delivery_assigned':
            console.log('🚚 Nova entrega alocada!')
            showNotification('Nova Entrega!', 'Uma nova entrega foi alocada para você')
            playSound()
            if (onDeliveryAssigned) {
              onDeliveryAssigned(data.data)
            }
            break

          case 'delivery_updated':
            console.log('📦 Status da entrega atualizado')
            if (onDeliveryUpdated) {
              onDeliveryUpdated(data.data)
            }
            break

          case 'operator_message':
            console.log('💬 Mensagem do operador')
            showNotification('Mensagem do Operador', data.data.message)
            if (onOperatorMessage) {
              onOperatorMessage(data.data)
            }
            break

          default:
            console.log('WebSocket evento desconhecido:', data.type)
        }
      } catch (error) {
        console.error('Erro ao processar mensagem WebSocket:', error)
      }
    }

    ws.onerror = (error) => {
      console.error('❌ WebSocket error:', error)
    }

    ws.onclose = () => {
      console.log('🔌 WebSocket desconectado')
      setConnected(false)
      
      // Tentar reconectar após 5 segundos
      setTimeout(() => {
        console.log('🔄 Tentando reconectar WebSocket...')
        connect()
      }, 5000)
    }
  }, [onDeliveryAssigned, onDeliveryUpdated, onOperatorMessage])

  useEffect(() => {
    connect()

    return () => {
      if (wsRef.current) {
        console.log('Fechando conexão WebSocket')
        wsRef.current.close()
      }
    }
  }, [connect])

  return {
    connected,
    lastMessage,
    reconnect: connect
  }
}

/**
 * Mostrar notificação nativa do navegador
 */
function showNotification(title, body) {
  // Solicitar permissão se ainda não tiver
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission()
  }

  // Mostrar notificação se tiver permissão
  if ('Notification' in window && Notification.permission === 'granted') {
    new Notification(title, {
      body,
      icon: '/gas-icon.png',
      badge: '/gas-badge.png'
    })
  }
}

/**
 * Tocar som de notificação
 */
function playSound() {
  try {
    const audio = new Audio('/notification.mp3')
    audio.volume = 0.5
    audio.play().catch(e => console.log('Não foi possível tocar som:', e))
  } catch (e) {
    console.log('Erro ao tocar som:', e)
  }
}

export default useWebSocketDriver
