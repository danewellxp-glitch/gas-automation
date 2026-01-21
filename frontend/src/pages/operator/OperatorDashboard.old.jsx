/**
 * ✨ OperatorDashboard.jsx - VERSÃO COMPLETA COM FUNCIONALIDADES TSX
 * 
 * Este arquivo demonstra como migrar todas as funcionalidades do TSX original
 * mantendo a autenticação JWT do novo sistema.
 * 
 * Funcionalidades:
 * - WebSocket com reconexão automática
 * - Chat em tempo real
 * - Gerenciamento de conversas (minhas + todas)
 * - Carregamento de pedidos
 * - Notificações avançadas
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import { useAuth } from '../../hooks/useAuth'
import { apiRequest } from '../../utils/api'
import { showToast, debounce, formatDateTime } from '../../utils/adminHelpers'

// ===== CONFIGURAÇÕES DE ENDPOINTS =====
const API_BASE = '/api'
const ENDPOINTS = {
  conversations: `${API_BASE}/conversations`,
  myConversations: `${API_BASE}/my-conversations`,
  orders: `${API_BASE}/orders/pending`,
  botInteractions: `${API_BASE}/bot-interactions`,
  conversationMessages: (id) => `${API_BASE}/conversations/${id}/messages`,
  conversationAssign: (id) => `${API_BASE}/conversations/${id}/assign`,
  conversationReply: (id) => `${API_BASE}/conversations/${id}/reply`,
  conversationEnd: (id) => `${API_BASE}/conversations/${id}/end`,
}

// ===== COMPONENTE DE MENSAGEM INDIVIDUAL =====
function MessageComponent({ message }) {
  const formatTime = (timestamp) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  const getMessageClass = () => {
    if (message.isFromCurrentUser) return "bg-blue-100 text-blue-900 ml-auto"
    if (message.message_type === "bot" || message.sender === "bot") return "bg-gray-100 text-gray-900"
    return "bg-gray-50 text-gray-800"
  }

  const getSenderDisplay = () => {
    if (message.isFromCurrentUser) return "Você"
    if (message.message_type === "bot" || message.sender === "bot") return "Bot"
    if (message.message_type === "agent" || message.sender === "agent") return "Atendente"
    if (message.message_type === "customer" || message.sender === "customer") return "Cliente"
    return message.sender
  }

  const getBotBadge = () => {
    if ((message.message_type === "bot" || message.sender === "bot") && message.bot_service) {
      return (
        <span className="inline-block ml-2 px-2 py-1 bg-blue-500 text-white text-xs rounded">
          {message.bot_service}
        </span>
      )
    }
    return null
  }

  return (
    <div className={`p-3 rounded-lg mb-2 w-fit max-w-xs ${getMessageClass()}`}>
      <div className="flex items-center gap-2 mb-1">
        <span className="font-semibold text-sm">{getSenderDisplay()}</span>
        {getBotBadge()}
      </div>
      <div className="break-words">{message.content}</div>
      <div className="text-xs opacity-70 mt-1">{formatTime(message.timestamp)}</div>
    </div>
  )
}

// ===== COMPONENTE PRINCIPAL =====
export default function OperatorDashboard() {
  const { user, logout } = useAuth()

  // ===== ESTADOS =====
  const [myConversations, setMyConversations] = useState([])
  const [allConversations, setAllConversations] = useState([])
  const [chatMessages, setChatMessages] = useState([])
  const [orders, setOrders] = useState([])
  const [botInteractions, setBotInteractions] = useState([])
  
  const [showBotInteractions, setShowBotInteractions] = useState(false)
  const [showOrdersPanel, setShowOrdersPanel] = useState(false)
  const [messageInput, setMessageInput] = useState('')
  const [filterValue, setFilterValue] = useState('all')
  const [notification, setNotification] = useState(null)
  const [showConfirmDialog, setShowConfirmDialog] = useState(false)
  const [loading, setLoading] = useState(true)

  // ===== REFS =====
  const currentConversationIdRef = useRef(null)
  const wsRef = useRef(null)
  const isSendingRef = useRef(false)
  const chatMessagesRef = useRef(null)
  const messageInputRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)
  const reconnectAttemptsRef = useRef(0)

  const MAX_RECONNECT_ATTEMPTS = 5
  const RECONNECT_DELAY = 3000
  const token = localStorage.getItem('access_token')

  // ===== UTILITÁRIOS DE NOTIFICAÇÃO =====
  const showError = useCallback((message) => {
    setNotification({ type: 'error', message })
    setTimeout(() => setNotification(null), 5000)
  }, [])

  const showSuccess = useCallback((message) => {
    setNotification({ type: 'success', message })
    setTimeout(() => setNotification(null), 3000)
  }, [])

  // Notificação de novo pedido
  const showOrderNotification = useCallback((order) => {
    try {
      // Som
      const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdH2JkZiYl5eSjImEf35/goeMkZaZmpmYlZGNiYWBf4CGi5CUl5mZmJaSkY2JhYKAg4iNkpWYmZiWk5CL')
      audio.volume = 0.3
      audio.play().catch(() => {})
    } catch (e) {
      console.error('Erro ao tocar som:', e)
    }

    // Notificação do navegador
    if (Notification.permission === 'granted') {
      new Notification('Novo Pedido!', {
        body: `#${order.id} - ${order.customer_name}\nR$ ${order.total.toFixed(2)}`,
        icon: '/static/icon.png'
      })
    }

    showToast(`Novo pedido #${order.id}: ${order.customer_name}`, 'success')
  }, [])

  // ===== WEBSOCKET COM RECONEXÃO =====
  const connectWebSocket = useCallback(() => {
    if (!token) {
      console.error('Token ausente')
      return
    }

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${wsProtocol}//${window.location.host}/ws?token=${token}`

    console.log('Conectando WebSocket:', wsUrl)
    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      console.log('WebSocket conectado')
      reconnectAttemptsRef.current = 0
      showSuccess('Conexão estabelecida')
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        console.log('WebSocket message:', data)

        // Novo pedido
        if (data.type === 'new_order') {
          showOrderNotification(data.order)
          loadOrders()
          return
        }

        // Atualização de pedido
        if (data.type === 'order_update') {
          console.log('Pedido atualizado:', data)
          loadOrders()
          return
        }

        // Mensagens da conversa atual
        if (!data.conversation_id || data.conversation_id !== currentConversationIdRef.current) {
          return
        }

        appendMessageToChat(data)
      } catch (error) {
        console.error('Erro ao processar WebSocket:', error)
      }
    }

    ws.onerror = (error) => {
      console.error('Erro WebSocket:', error)
    }

    ws.onclose = (event) => {
      console.log('WebSocket fechado:', event.code, event.reason)
      wsRef.current = null

      if (event.code !== 1000 && reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
        reconnectAttemptsRef.current++
        console.log(`Tentando reconectar (${reconnectAttemptsRef.current}/${MAX_RECONNECT_ATTEMPTS})`)
        
        reconnectTimeoutRef.current = setTimeout(() => {
          connectWebSocket()
        }, RECONNECT_DELAY * reconnectAttemptsRef.current)
      } else if (reconnectAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS) {
        showError('Não foi possível restabelecer conexão. Recarregue a página.')
      }
    }

    wsRef.current = ws
  }, [token, showSuccess, showError, showOrderNotification])

  // Adicionar mensagem ao chat
  const appendMessageToChat = useCallback((data) => {
    const newMessage = {
      id: data.id,
      sender: data.sender,
      content: data.message || data.content || '',
      message_type: data.message_type,
      bot_service: data.bot_service,
      timestamp: data.timestamp || new Date().toISOString(),
      isFromCurrentUser: false
    }

    setChatMessages(prev => [...prev, newMessage])

    setTimeout(() => {
      if (chatMessagesRef.current) {
        chatMessagesRef.current.scrollTop = chatMessagesRef.current.scrollHeight
      }
    }, 100)
  }, [])

  // ===== CARREGAR DADOS =====

  const loadOrders = useCallback(async () => {
    try {
      const response = await fetch(ENDPOINTS.orders, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      
      if (response.ok) {
        const ordersData = await response.json()
        setOrders(ordersData)
      } else if (response.status === 401) {
        showError('Sessão expirada. Faça login novamente.')
        localStorage.removeItem('access_token')
      }
    } catch (error) {
      console.error('Erro ao carregar pedidos:', error)
      showError('Erro ao carregar pedidos')
    }
  }, [token, showError])

  const toggleOrders = useCallback(() => {
    setShowOrdersPanel(prev => {
      if (!prev) {
        loadOrders()
      }
      return !prev
    })
  }, [loadOrders])

  const highlightSelected = useCallback((conversationId) => {
    document.querySelectorAll('.conversation-item').forEach(div => {
      if (parseInt(div.dataset.id) === conversationId) {
        div.classList.add('bg-blue-50', 'border-l-4', 'border-blue-500')
      } else {
        div.classList.remove('bg-blue-50', 'border-l-4', 'border-blue-500')
      }
    })
  }, [])

  const fetchMyConversations = useCallback(async () => {
    try {
      const res = await fetch(ENDPOINTS.myConversations, {
        headers: { Authorization: `Bearer ${token}` }
      })

      if (res.status === 401) {
        showError('Sessão expirada')
        localStorage.removeItem('access_token')
        return
      }

      const myData = await res.json()
      setMyConversations(myData)
    } catch (error) {
      console.error('Erro ao carregar minhas conversas:', error)
    }
  }, [token, showError])

  const fetchAllConversations = useCallback(async () => {
    try {
      const res = await fetch(ENDPOINTS.conversations, {
        headers: { Authorization: `Bearer ${token}` }
      })

      if (res.status === 401) {
        showError('Sessão expirada')
        localStorage.removeItem('access_token')
        return
      }

      const data = await res.json()
      setAllConversations(data.filter(c => c.status === 'pending'))
    } catch (error) {
      console.error('Erro ao carregar conversas:', error)
    }
  }, [token, showError])

  const loadChat = useCallback(async (conversationId) => {
    if (currentConversationIdRef.current !== conversationId) {
      currentConversationIdRef.current = conversationId

      try {
        const assignRes = await fetch(ENDPOINTS.conversationAssign(conversationId), {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` }
        })

        if (!assignRes.ok) {
          console.error('Erro ao atribuir conversa:', assignRes.status)
          showError('Erro ao atribuir conversa')
          return
        }

        fetchMyConversations()
        fetchAllConversations()
      } catch (error) {
        console.error('Erro ao atribuir conversa:', error)
        showError('Erro ao atribuir conversa')
        return
      }
    }

    highlightSelected(conversationId)

    try {
      const res = await fetch(ENDPOINTS.conversationMessages(conversationId), {
        headers: { Authorization: `Bearer ${token}` }
      })

      const messagesData = await res.json()
      const formattedMessages = messagesData.map(msg => ({
        ...msg,
        isFromCurrentUser: false
      }))
      setChatMessages(formattedMessages)

      setTimeout(() => {
        if (chatMessagesRef.current) {
          chatMessagesRef.current.scrollTop = chatMessagesRef.current.scrollHeight
        }
      }, 100)
    } catch (error) {
      console.error('Erro ao carregar mensagens:', error)
    }
  }, [token, showError, fetchMyConversations, fetchAllConversations, highlightSelected])

  // ===== AÇÕES DE CHAT =====

  const sendMessage = useCallback(async () => {
    if (isSendingRef.current) {
      console.log('Já está enviando mensagem')
      return
    }

    const content = messageInput.trim()

    if (!content || !currentConversationIdRef.current) {
      console.warn('Mensagem vazia ou conversa não selecionada')
      return
    }

    isSendingRef.current = true
    if (messageInputRef.current) messageInputRef.current.disabled = true

    try {
      const res = await fetch(ENDPOINTS.conversationReply(currentConversationIdRef.current), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ message: content })
      })

      if (!res.ok) {
        const errorText = await res.text()
        console.error('Erro ao enviar:', res.status, errorText)
        showError('Erro ao enviar mensagem')
        return
      }

      // Adicionar mensagem do usuário ao chat
      const userMessage = {
        sender: 'agent',
        content: content,
        message_type: 'agent',
        timestamp: new Date().toISOString(),
        isFromCurrentUser: true
      }
      setChatMessages(prev => [...prev, userMessage])

      setTimeout(() => {
        if (chatMessagesRef.current) {
          chatMessagesRef.current.scrollTop = chatMessagesRef.current.scrollHeight
        }
      }, 100)

      setMessageInput('')
      highlightSelected(currentConversationIdRef.current)
    } catch (error) {
      console.error('Erro ao enviar mensagem:', error)
      showError('Erro ao enviar mensagem')
    } finally {
      isSendingRef.current = false
      if (messageInputRef.current) messageInputRef.current.disabled = false
      messageInputRef.current?.focus()
    }
  }, [messageInput, token, showError, highlightSelected])

  const endConversation = useCallback(async () => {
    if (!currentConversationIdRef.current) {
      showError('Nenhuma conversa selecionada')
      return
    }
    setShowConfirmDialog(true)
  }, [showError])

  const confirmEndConversation = useCallback(async () => {
    setShowConfirmDialog(false)

    if (!currentConversationIdRef.current) return

    try {
      const res = await fetch(ENDPOINTS.conversationEnd(currentConversationIdRef.current), {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
      })

      if (!res.ok) {
        const errorText = await res.text()
        console.error('Erro:', res.status, errorText)
        showError('Erro ao encerrar conversa')
        return
      }

      showSuccess('Conversa encerrada com sucesso')
      setChatMessages([])
      currentConversationIdRef.current = null
      fetchMyConversations()
      fetchAllConversations()
    } catch (error) {
      console.error('Erro ao encerrar conversa:', error)
      showError('Erro de conexão: ' + error.message)
    }
  }, [token, showError, showSuccess, fetchMyConversations, fetchAllConversations])

  const fetchBotInteractions = useCallback(async () => {
    try {
      const res = await fetch(ENDPOINTS.botInteractions, {
        headers: { Authorization: `Bearer ${token}` }
      })

      if (res.status === 401) {
        showError('Sessão expirada')
        localStorage.removeItem('access_token')
        return
      }

      const data = await res.json()
      setBotInteractions(data)
    } catch (error) {
      console.error('Erro:', error)
      setBotInteractions([])
    }
  }, [token, showError])

  // ===== EFEITOS =====

  useEffect(() => {
    const init = async () => {
      setLoading(true)
      await fetchMyConversations()
      await fetchAllConversations()
      setLoading(false)
    }
    init()
  }, [])

  useEffect(() => {
    // Solicitar permissão para notificações
    if (Notification.permission === 'default') {
      Notification.requestPermission()
    }

    connectWebSocket()

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
    }
  }, [token, connectWebSocket])

  // ===== RENDER =====

  return (
    <div className="flex h-screen bg-gray-100">
      {/* SIDEBAR */}
      <div className="w-64 bg-white shadow-lg flex flex-col">
        {/* Header */}
        <div className="p-6 border-b">
          <h1 className="text-xl font-bold text-gray-800">Gas Automation</h1>
          <p className="text-sm text-gray-500">Painel do Operador</p>
        </div>

        {/* Notificação */}
        {notification && (
          <div className={`m-4 p-3 rounded text-sm ${
            notification.type === 'success' ? 'bg-green-100 text-green-800' :
            notification.type === 'error' ? 'bg-red-100 text-red-800' :
            'bg-blue-100 text-blue-800'
          }`}>
            {notification.message}
          </div>
        )}

        {/* Menu */}
        <nav className="flex-1 p-4">
          <div className="space-y-2">
            <button 
              onClick={() => setShowBotInteractions(false)}
              className="w-full text-left px-4 py-3 bg-blue-500 text-white rounded hover:bg-blue-600"
            >
              💬 Conversas
            </button>
            <button 
              onClick={toggleOrders}
              className={`w-full text-left px-4 py-3 rounded ${
                showOrdersPanel ? 'bg-blue-500 text-white' : 'hover:bg-gray-100'
              }`}
            >
              📦 Pedidos ({orders.length})
            </button>
            <button 
              onClick={() => {
                setShowBotInteractions(true)
                fetchBotInteractions()
              }}
              className="w-full text-left px-4 py-3 hover:bg-gray-100 rounded"
            >
              🤖 Bot Interactions
            </button>
          </div>
        </nav>

        {/* User Info */}
        <div className="border-t p-4">
          <div className="flex items-center justify-between gap-2">
            <div className="text-sm min-w-0">
              <p className="font-semibold text-gray-800 truncate">{user?.email}</p>
              <p className="text-gray-500 text-xs uppercase">Operador</p>
            </div>
            <button 
              onClick={logout}
              className="px-3 py-1 bg-red-500 text-white rounded text-xs hover:bg-red-600 whitespace-nowrap"
            >
              Sair
            </button>
          </div>
        </div>
      </div>

      {/* MAIN CONTENT */}
      <div className="flex-1 flex overflow-hidden">
        {/* Conversas / Interações Bot */}
        <div className="w-80 border-r border-gray-200 bg-white overflow-y-auto">
          {loading ? (
            <div className="p-8 text-center">
              <p className="text-gray-500">Carregando...</p>
            </div>
          ) : showBotInteractions ? (
            <div className="p-4">
              <h3 className="font-bold mb-4">Bot Interactions</h3>
              {botInteractions.length === 0 ? (
                <p className="text-gray-500 text-sm">Sem interações</p>
              ) : (
                <div className="space-y-2">
                  {botInteractions.map((interaction, idx) => (
                    <div key={idx} className="p-3 border rounded bg-gray-50">
                      <p className="text-sm font-semibold">{interaction.customer_name}</p>
                      <p className="text-xs text-gray-600 mt-1">{interaction.user_message}</p>
                      <p className="text-xs text-gray-500 mt-1">Bot: {interaction.bot_type}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div>
              {/* Minhas Conversas */}
              <div className="border-b">
                <h3 className="font-bold p-4 text-sm">📥 Minhas Conversas ({myConversations.length})</h3>
                <div className="space-y-1">
                  {myConversations.map(conv => (
                    <div
                      key={conv.id}
                      data-id={conv.id}
                      className="conversation-item p-3 hover:bg-gray-50 cursor-pointer border-l-4 border-transparent"
                      onClick={() => loadChat(conv.id)}
                    >
                      <p className="text-sm font-semibold">{conv.customer_number}</p>
                      <p className="text-xs text-gray-600">{conv.name || 'Sem nome'}</p>
                      <span className={`inline-block mt-1 px-2 py-0.5 rounded text-xs text-white ${
                        conv.status === 'pending' ? 'bg-yellow-500' : 'bg-green-500'
                      }`}>
                        {conv.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Todas Conversas */}
              <div>
                <h3 className="font-bold p-4 text-sm">📨 Conversas Disponíveis ({allConversations.length})</h3>
                <div className="space-y-1">
                  {allConversations.map(conv => (
                    <div
                      key={conv.id}
                      data-id={conv.id}
                      className="conversation-item p-3 hover:bg-gray-50 cursor-pointer border-l-4 border-transparent"
                      onClick={() => loadChat(conv.id)}
                    >
                      <p className="text-sm font-semibold">{conv.customer_number}</p>
                      <p className="text-xs text-gray-600">{conv.name || 'Sem nome'}</p>
                      <span className="inline-block mt-1 px-2 py-0.5 rounded text-xs bg-blue-500 text-white">
                        Disponível
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Chat ou Pedidos */}
        <div className="flex-1 flex flex-col">
          {showOrdersPanel ? (
            // Panel de Pedidos
            <div className="p-6 overflow-y-auto">
              <h2 className="text-2xl font-bold mb-6">Pedidos Pendentes</h2>
              {orders.length === 0 ? (
                <p className="text-gray-500 text-center py-12">Nenhum pedido pendente</p>
              ) : (
                <div className="grid gap-4">
                  {orders.map(order => (
                    <div key={order.id} className="bg-white p-4 rounded-lg shadow">
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <h3 className="font-bold text-lg">Pedido #{order.id}</h3>
                          <p className="text-sm text-gray-600">{order.customer_name}</p>
                        </div>
                        <span className="inline-block px-3 py-1 rounded text-sm font-semibold bg-yellow-100 text-yellow-800">
                          {order.status}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600">Entrega: {order.endereco_entrega}, {order.numero_entrega}</p>
                      <p className="text-sm text-gray-600">Bairro: {order.bairro_entrega}</p>
                      <p className="text-xl font-bold text-green-600 mt-2">R$ {order.total.toFixed(2)}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            // Chat
            currentConversationIdRef.current ? (
              <div className="flex flex-col h-full">
                {/* Chat Messages */}
                <div 
                  ref={chatMessagesRef}
                  className="flex-1 p-6 overflow-y-auto bg-gray-50"
                >
                  <div className="space-y-4">
                    {chatMessages.map((msg, idx) => (
                      <MessageComponent key={idx} message={msg} />
                    ))}
                  </div>
                </div>

                {/* Input Area */}
                <div className="border-t bg-white p-4">
                  <div className="flex gap-2">
                    <input
                      ref={messageInputRef}
                      type="text"
                      value={messageInput}
                      onChange={(e) => setMessageInput(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
                      placeholder="Digite sua mensagem..."
                      className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:border-blue-500"
                    />
                    <button
                      onClick={sendMessage}
                      className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                    >
                      Enviar
                    </button>
                    <button
                      onClick={endConversation}
                      className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
                    >
                      Encerrar
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-full">
                <p className="text-gray-500 text-center">
                  👈 Selecione uma conversa para começar
                </p>
              </div>
            )
          )}
        </div>
      </div>

      {/* Confirm Dialog */}
      {showConfirmDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg shadow-xl max-w-sm">
            <h3 className="text-lg font-bold mb-2">Encerrar Conversa?</h3>
            <p className="text-gray-600 mb-6">
              Tem certeza que deseja encerrar esta conversa? Esta ação não pode ser desfeita.
            </p>
            <div className="flex gap-4">
              <button
                onClick={() => setShowConfirmDialog(false)}
                className="flex-1 px-4 py-2 bg-gray-300 text-gray-800 rounded hover:bg-gray-400"
              >
                Cancelar
              </button>
              <button
                onClick={confirmEndConversation}
                className="flex-1 px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
              >
                Confirmar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
