/**
 * Serviço WebSocket para atualizações em tempo real.
 */

class WebSocketService {
  constructor() {
    this.ws = null
    this.listeners = new Map()
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 3000
  }

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const url = `${protocol}//${host}/ws/dashboard`

    console.log('Conectando WebSocket:', url)

    try {
      this.ws = new WebSocket(url)

      this.ws.onopen = () => {
        console.log('WebSocket conectado')
        this.reconnectAttempts = 0
        this.emit('connected', { timestamp: new Date() })
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          this.emit(data.type, data)
        } catch (e) {
          console.error('Erro ao processar mensagem WebSocket:', e)
        }
      }

      this.ws.onclose = () => {
        console.log('WebSocket desconectado')
        this.emit('disconnected', { timestamp: new Date() })
        this.tryReconnect()
      }

      this.ws.onerror = (error) => {
        console.error('Erro WebSocket:', error)
        this.emit('error', { error })
      }
    } catch (error) {
      console.error('Erro ao criar WebSocket:', error)
      this.tryReconnect()
    }
  }

  tryReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('Maximo de tentativas de reconexao atingido')
      return
    }

    this.reconnectAttempts++
    console.log(`Tentando reconectar (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`)

    setTimeout(() => {
      this.connect()
    }, this.reconnectDelay)
  }

  disconnect() {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  send(data) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    }
  }

  ping() {
    this.send({ type: 'ping' })
  }

  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set())
    }
    this.listeners.get(event).add(callback)

    // Retorna função para remover listener
    return () => {
      this.listeners.get(event)?.delete(callback)
    }
  }

  off(event, callback) {
    this.listeners.get(event)?.delete(callback)
  }

  emit(event, data) {
    this.listeners.get(event)?.forEach((callback) => {
      try {
        callback(data)
      } catch (e) {
        console.error('Erro no listener WebSocket:', e)
      }
    })
  }
}

// Singleton
const websocketService = new WebSocketService()

export default websocketService
