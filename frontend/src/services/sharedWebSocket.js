/**
 * Serviço WebSocket Compartilhado com Deduplicação de Abas
 * 
 * Usa BroadcastChannel API para compartilhar UMA única conexão WebSocket
 * entre TODAS as abas abertas do mesmo origin.
 * 
 * Benefícios:
 * - Reduz tráfego em 80-90% (5 abas = 1 conexão ao invés de 5)
 * - Economia de recursos do servidor
 * - Mensagens sincronizadas entre abas
 */

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://192.168.10.156:8000/ws'
const RECONNECT_DELAY = 3000
const MAX_RECONNECT_ATTEMPTS = 10

class SharedWebSocketService {
  constructor() {
    // Estado da conexão
    this.ws = null
    this.isLeader = false
    this.reconnectAttempts = 0
    this.reconnectTimeout = null
    
    // Listeners de eventos
    this.listeners = new Map()
    
    // BroadcastChannel para comunicação entre abas
    this.channel = null
    this.channelName = 'websocket-shared-channel'
    
    // Heartbeat para detectar líder morto
    this.leaderHeartbeatInterval = null
    this.leaderHeartbeatTimeout = null
    this.HEARTBEAT_INTERVAL = 5000  // 5s
    this.HEARTBEAT_TIMEOUT = 10000  // 10s
    
    // ID único desta aba
    this.tabId = `tab_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    
    this.init()
  }

  init() {
    // Verificar suporte a BroadcastChannel
    if (typeof BroadcastChannel === 'undefined') {
      console.warn('BroadcastChannel não suportado. Cada aba terá sua própria conexão.')
      this.isLeader = true
      this.connect()
      return
    }

    // Criar canal de comunicação entre abas
    this.channel = new BroadcastChannel(this.channelName)
    
    // Escutar mensagens de outras abas
    this.channel.onmessage = (event) => {
      const { type, data, senderId } = event.data
      
      // Ignorar mensagens enviadas por esta própria aba
      if (senderId === this.tabId) return
      
      switch (type) {
        case 'leader-announce':
          // Outra aba se tornou líder
          this.isLeader = false
          this.resetLeaderHeartbeatTimeout()
          break
          
        case 'leader-heartbeat':
          // Líder está vivo
          this.resetLeaderHeartbeatTimeout()
          break
          
        case 'ws-message':
          // Mensagem do WebSocket (enviada pelo líder)
          this.emit(data.type, data)
          break
          
        case 'leader-request':
          // Outra aba está pedindo um líder
          if (this.isLeader) {
            this.announceLeader()
          }
          break
      }
    }

    // Solicitar líder existente
    this.requestLeader()
    
    // Se ninguém responder em 1s, tornar-se líder
    setTimeout(() => {
      if (!this.isLeader && this.ws === null) {
        this.becomeLeader()
      }
    }, 1000)
  }

  requestLeader() {
    if (this.channel) {
      this.channel.postMessage({
        type: 'leader-request',
        senderId: this.tabId,
      })
    }
  }

  becomeLeader() {
    console.log(`[Tab ${this.tabId}] Tornando-se líder`)
    this.isLeader = true
    this.announceLeader()
    this.startLeaderHeartbeat()
    this.connect()
  }

  announceLeader() {
    if (this.channel) {
      this.channel.postMessage({
        type: 'leader-announce',
        senderId: this.tabId,
      })
    }
  }

  startLeaderHeartbeat() {
    if (this.leaderHeartbeatInterval) {
      clearInterval(this.leaderHeartbeatInterval)
    }
    
    this.leaderHeartbeatInterval = setInterval(() => {
      if (this.isLeader && this.channel) {
        this.channel.postMessage({
          type: 'leader-heartbeat',
          senderId: this.tabId,
        })
      }
    }, this.HEARTBEAT_INTERVAL)
  }

  resetLeaderHeartbeatTimeout() {
    if (this.leaderHeartbeatTimeout) {
      clearTimeout(this.leaderHeartbeatTimeout)
    }

    // Se não receber heartbeat do líder em 10s, tornar-se líder
    this.leaderHeartbeatTimeout = setTimeout(() => {
      if (!this.isLeader) {
        console.warn('[SharedWebSocket] Líder não responde. Tornando-se líder.')
        this.becomeLeader()
      }
    }, this.HEARTBEAT_TIMEOUT)
  }

  connect() {
    // Apenas o líder conecta ao WebSocket
    if (!this.isLeader) {
      return
    }

    if (this.ws?.readyState === WebSocket.OPEN) {
      return
    }

    const token = localStorage.getItem('access_token') || localStorage.getItem('token')
    
    // Se não houver token, não tentar conectar (será rejeitado pelo backend)
    if (!token) {
      console.warn(`[Leader Tab ${this.tabId}] Sem token, não conectando WebSocket`)
      return
    }
    
    // WS_URL já inclui /ws, então o endpoint é /ws/dashboard
    // Se WS_URL = 'ws://192.168.10.156:8000/ws', então url = 'ws://192.168.10.156:8000/ws/dashboard'
    const url = `${WS_URL}/dashboard?token=${token}`
    
    console.log(`[Leader Tab ${this.tabId}] Conectando WebSocket:`, url.replace(token, 'TOKEN_HIDDEN'))

    try {
      this.ws = new WebSocket(url)

      this.ws.onopen = () => {
        console.log(`[Leader Tab ${this.tabId}] WebSocket conectado`)
        this.reconnectAttempts = 0
        this.emit('connected', { timestamp: new Date(), isLeader: true })
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          
          // Emitir localmente
          this.emit(data.type, data)
          
          // Broadcast para outras abas
          if (this.channel) {
            this.channel.postMessage({
              type: 'ws-message',
              data: data,
              senderId: this.tabId,
            })
          }
        } catch (e) {
          console.error('[SharedWebSocket] Erro ao processar mensagem:', e)
        }
      }

      this.ws.onclose = (event) => {
        console.log(`[Leader Tab ${this.tabId}] WebSocket fechado:`, event.code, event.reason || '')
        this.ws = null
        this.emit('disconnected', { timestamp: new Date(), code: event.code })
        
        // Se foi 403 (Unauthorized) ou 1008 (Policy Violation), token pode estar expirado
        // Não tentar reconectar infinitamente - usuário precisa fazer login novamente
        if (event.code === 403 || event.code === 1008) {
          console.warn(`[SharedWebSocket] Conexão rejeitada (${event.code}). Token pode estar expirado. Parando tentativas de reconexão.`)
          this.emit('unauthorized', { code: event.code, reason: event.reason })
          return
        }
        
        // Tentar reconectar se não foi fechado intencionalmente
        if (event.code !== 1000 && this.reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
          this.tryReconnect()
        } else if (this.reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
          console.error('[SharedWebSocket] Máximo de tentativas de reconexão atingido')
        }
      }

      this.ws.onerror = (error) => {
        console.error(`[Leader Tab ${this.tabId}] Erro WebSocket:`, error)
        this.emit('error', { error })
      }
    } catch (error) {
      console.error('[SharedWebSocket] Erro ao criar WebSocket:', error)
      this.tryReconnect()
    }
  }

  tryReconnect() {
    if (!this.isLeader) return

    this.reconnectAttempts++
    const delay = RECONNECT_DELAY * Math.min(this.reconnectAttempts, 5)
    
    console.log(`[SharedWebSocket] Tentando reconectar em ${delay}ms (tentativa ${this.reconnectAttempts})`)
    
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout)
    }
    
    this.reconnectTimeout = setTimeout(() => {
      this.connect()
    }, delay)
  }

  send(data) {
    if (this.isLeader && this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    } else {
      console.warn('[SharedWebSocket] Não é possível enviar: não é líder ou conexão fechada')
    }
  }

  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, [])
    }
    this.listeners.get(event).push(callback)
    
    // Retornar função de unsubscribe
    return () => {
      const callbacks = this.listeners.get(event)
      if (callbacks) {
        const index = callbacks.indexOf(callback)
        if (index > -1) {
          callbacks.splice(index, 1)
        }
      }
    }
  }

  emit(event, data) {
    const callbacks = this.listeners.get(event)
    if (callbacks) {
      callbacks.forEach(callback => {
        try {
          callback(data)
        } catch (e) {
          console.error('[SharedWebSocket] Erro no listener:', e)
        }
      })
    }
  }

  disconnect() {
    console.log(`[Tab ${this.tabId}] Desconectando`)
    
    // Limpar heartbeat
    if (this.leaderHeartbeatInterval) {
      clearInterval(this.leaderHeartbeatInterval)
    }
    if (this.leaderHeartbeatTimeout) {
      clearTimeout(this.leaderHeartbeatTimeout)
    }
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout)
    }

    // Fechar WebSocket se for líder
    if (this.isLeader && this.ws) {
      this.ws.close()
      this.ws = null
    }

    // Fechar canal
    if (this.channel) {
      this.channel.close()
      this.channel = null
    }

    this.listeners.clear()
  }
}

// Instância singleton
const sharedWebSocketService = new SharedWebSocketService()

export default sharedWebSocketService
