import { useState, useEffect, useCallback, useRef } from 'react'
import { MessageSquare, Send, RefreshCw, User, Bot, RotateCcw } from 'lucide-react'
import { getChats, getChatMessages, sendChatMessage, resetChatContext } from '../services/api'
import { useWebSocketEvent } from '../hooks/useWebSocket'

function formatTime(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const today = new Date()
  if (date.toDateString() === today.toDateString()) {
    return 'Hoje'
  }
  return date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
}

function ChatList({ chats, selectedChat, onSelectChat, loading }) {
  const stateLabels = {
    start: 'Inicio',
    awaiting_product: 'Produto',
    awaiting_quantity: 'Quantidade',
    confirming_address: 'Endereco',
    awaiting_address: 'Endereco',
    awaiting_payment: 'Pagamento',
    awaiting_pix: 'Pix',
    order_confirmed: 'Confirmado',
    tracking_order: 'Rastreio',
    talking_to_human: 'Atendente',
  }

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <RefreshCw className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    )
  }

  if (chats.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center p-4">
        <p className="text-gray-400 text-center">Nenhuma conversa ativa</p>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto">
      {chats.map((chat) => (
        <div
          key={chat.phone}
          onClick={() => onSelectChat(chat)}
          className={`p-4 border-b border-gray-100 cursor-pointer hover:bg-gray-50 ${
            selectedChat?.phone === chat.phone ? 'bg-orange-50' : ''
          }`}
        >
          <div className="flex items-center justify-between mb-1">
            <span className="font-medium text-gray-900">
              {chat.customer_name || chat.phone}
            </span>
            <span className="text-xs text-gray-500">
              {formatTime(chat.last_message_time)}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-500 truncate flex-1 mr-2">
              {chat.last_message || 'Sem mensagens'}
            </p>
            <span className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-600">
              {stateLabels[chat.state] || chat.state}
            </span>
          </div>
        </div>
      ))}
    </div>
  )
}

function MessageBubble({ message }) {
  const isFromMe = message.from_me

  return (
    <div className={`flex ${isFromMe ? 'justify-end' : 'justify-start'} mb-3`}>
      <div
        className={`max-w-[70%] rounded-lg px-4 py-2 ${
          isFromMe
            ? 'bg-orange-500 text-white'
            : 'bg-white border border-gray-200 text-gray-900'
        }`}
      >
        <div className="flex items-center gap-1 mb-1">
          {isFromMe ? (
            <Bot className="w-3 h-3" />
          ) : (
            <User className="w-3 h-3" />
          )}
          <span className="text-xs opacity-75">
            {isFromMe ? 'Bot' : 'Cliente'}
          </span>
        </div>
        <p className="whitespace-pre-wrap break-words">{message.text}</p>
        <p className={`text-xs mt-1 ${isFromMe ? 'text-orange-100' : 'text-gray-400'}`}>
          {formatTime(message.timestamp)}
        </p>
      </div>
    </div>
  )
}

function ChatWindow({ chat, messages, loading, onSendMessage, onResetContext }) {
  const [inputMessage, setInputMessage] = useState('')
  const [sending, setSending] = useState(false)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    if (!inputMessage.trim() || sending) return

    setSending(true)
    try {
      await onSendMessage(inputMessage)
      setInputMessage('')
    } finally {
      setSending(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <>
      {/* Header */}
      <div className="p-4 bg-white border-b border-gray-200 flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-gray-900">
            {chat.customer_name || chat.phone}
          </h3>
          <p className="text-sm text-gray-500">{chat.phone}</p>
        </div>
        <button
          onClick={onResetContext}
          className="p-2 text-gray-500 hover:text-orange-500 hover:bg-orange-50 rounded-lg transition-colors"
          title="Resetar conversa"
        >
          <RotateCcw className="w-5 h-5" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 p-4 overflow-y-auto bg-gray-50">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <RefreshCw className="w-6 h-6 animate-spin text-gray-400" />
          </div>
        ) : messages.length === 0 ? (
          <div className="text-center text-gray-400 text-sm">
            Nenhuma mensagem ainda
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input */}
      <div className="p-4 bg-white border-t border-gray-200">
        <div className="flex gap-2">
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Digite uma mensagem..."
            disabled={sending}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={sending || !inputMessage.trim()}
            className="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {sending ? (
              <RefreshCw className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
      </div>
    </>
  )
}

function Chats() {
  const [chats, setChats] = useState([])
  const [selectedChat, setSelectedChat] = useState(null)
  const [messages, setMessages] = useState([])
  const [loadingChats, setLoadingChats] = useState(true)
  const [loadingMessages, setLoadingMessages] = useState(false)

  // Carregar lista de chats
  const loadChats = useCallback(async () => {
    try {
      const data = await getChats()
      setChats(data)
    } catch (error) {
      console.error('Erro ao carregar chats:', error)
    } finally {
      setLoadingChats(false)
    }
  }, [])

  // Carregar mensagens do chat selecionado
  const loadMessages = useCallback(async (phone) => {
    setLoadingMessages(true)
    try {
      const data = await getChatMessages(phone)
      setMessages(data)
    } catch (error) {
      console.error('Erro ao carregar mensagens:', error)
    } finally {
      setLoadingMessages(false)
    }
  }, [])

  // Carregar chats ao montar
  useEffect(() => {
    loadChats()
  }, [loadChats])

  // Carregar mensagens quando selecionar chat
  useEffect(() => {
    if (selectedChat) {
      loadMessages(selectedChat.phone)
    } else {
      setMessages([])
    }
  }, [selectedChat, loadMessages])

  // WebSocket: nova mensagem
  const handleNewMessage = useCallback((data) => {
    console.log('Nova mensagem via WebSocket:', data)

    // Atualizar lista de chats
    loadChats()

    // Se for do chat selecionado, adicionar mensagem
    if (selectedChat && data.phone === selectedChat.phone) {
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        phone: data.phone,
        text: data.message,
        from_me: data.from_me || false,
        timestamp: new Date().toISOString()
      }])
    }
  }, [selectedChat, loadChats])

  useWebSocketEvent('new_message', handleNewMessage)

  // Enviar mensagem
  const handleSendMessage = async (message) => {
    if (!selectedChat) return

    try {
      await sendChatMessage(selectedChat.phone, message)

      // Adicionar mensagem localmente
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        phone: selectedChat.phone,
        text: message,
        from_me: true,
        timestamp: new Date().toISOString()
      }])
    } catch (error) {
      console.error('Erro ao enviar mensagem:', error)
      alert('Erro ao enviar mensagem')
    }
  }

  // Resetar contexto
  const handleResetContext = async () => {
    if (!selectedChat) return

    if (confirm('Resetar conversa? O cliente voltara ao inicio do fluxo.')) {
      try {
        await resetChatContext(selectedChat.phone)
        loadChats()
      } catch (error) {
        console.error('Erro ao resetar contexto:', error)
      }
    }
  }

  // Selecionar chat
  const handleSelectChat = (chat) => {
    setSelectedChat(chat)
  }

  return (
    <div className="h-[calc(100vh-4rem)] flex">
      {/* Chat List */}
      <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Conversas</h2>
          <button
            onClick={loadChats}
            className="p-2 text-gray-500 hover:text-orange-500 hover:bg-orange-50 rounded-lg transition-colors"
            title="Atualizar"
          >
            <RefreshCw className={`w-4 h-4 ${loadingChats ? 'animate-spin' : ''}`} />
          </button>
        </div>
        <ChatList
          chats={chats}
          selectedChat={selectedChat}
          onSelectChat={handleSelectChat}
          loading={loadingChats}
        />
      </div>

      {/* Chat Window */}
      <div className="flex-1 flex flex-col bg-gray-50">
        {selectedChat ? (
          <ChatWindow
            chat={selectedChat}
            messages={messages}
            loading={loadingMessages}
            onSendMessage={handleSendMessage}
            onResetContext={handleResetContext}
          />
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center text-gray-400">
              <MessageSquare className="w-16 h-16 mx-auto mb-4" />
              <p>Selecione uma conversa</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default Chats
