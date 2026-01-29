/**
 * Painel de Conversas do Operador com WebSocket
 * Chat em tempo real para atendimento ao cliente
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import {
  MessageSquare, Send, RefreshCw, User, Bot, Phone,
  UserCheck, UserX, CheckCircle, Clock, AlertCircle,
  Search, Filter, X
} from 'lucide-react'
import toast from 'react-hot-toast'
import {
  getConversations,
  getConversationMessages,
  assignConversation,
  replyConversation,
  endConversation
} from '../../services/api'
import { useSharedWebSocketEvent } from '../../hooks/useSharedWebSocket'

// Formatar hora
function formatTime(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}

// Formatar data relativa
function formatRelativeDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)

  if (diffMins < 1) return 'Agora'
  if (diffMins < 60) return `${diffMins}min`
  if (diffHours < 24) return `${diffHours}h`
  return date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
}

// Status badges
const statusConfig = {
  waiting: { label: 'Aguardando', color: 'bg-yellow-100 text-yellow-800', icon: Clock },
  active: { label: 'Em atendimento', color: 'bg-green-100 text-green-800', icon: UserCheck },
  bot: { label: 'Com bot', color: 'bg-blue-100 text-blue-800', icon: Bot },
  closed: { label: 'Encerrada', color: 'bg-gray-100 text-gray-600', icon: CheckCircle },
}

// Componente de lista de conversas
function ConversationList({ conversations, selectedId, onSelect, loading, filter, onFilterChange }) {
  const filteredConversations = conversations.filter(conv => {
    if (filter === 'all') return true
    if (filter === 'waiting') return conv.status === 'waiting' || !conv.assigned_to
    if (filter === 'mine') return conv.assigned_to_me
    if (filter === 'active') return conv.status === 'active'
    return true
  })

  return (
    <div className="flex flex-col h-full">
      {/* Filtros */}
      <div className="p-3 border-b border-gray-200 space-y-2">
        <div className="flex gap-1">
          {[
            { key: 'all', label: 'Todas' },
            { key: 'waiting', label: 'Aguardando' },
            { key: 'mine', label: 'Minhas' },
          ].map(f => (
            <button
              key={f.key}
              onClick={() => onFilterChange(f.key)}
              className={`px-3 py-1 text-xs font-medium rounded-full transition-colors ${
                filter === f.key
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Lista */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <RefreshCw className="w-6 h-6 animate-spin text-gray-400" />
          </div>
        ) : filteredConversations.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-gray-400">
            <MessageSquare className="w-8 h-8 mb-2" />
            <p className="text-sm">Nenhuma conversa</p>
          </div>
        ) : (
          filteredConversations.map((conv) => {
            const status = statusConfig[conv.status] || statusConfig.waiting
            const StatusIcon = status.icon

            return (
              <div
                key={conv.id}
                onClick={() => onSelect(conv)}
                className={`p-3 border-b border-gray-100 cursor-pointer hover:bg-gray-50 transition-colors ${
                  selectedId === conv.id ? 'bg-primary-50 border-l-4 border-l-primary-500' : ''
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-900 truncate">
                        {conv.name || conv.customer_number}
                      </span>
                      {conv.unread_count > 0 && (
                        <span className="flex-shrink-0 w-5 h-5 flex items-center justify-center text-xs font-bold text-white bg-red-500 rounded-full">
                          {conv.unread_count}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-500 truncate mt-0.5">
                      {conv.last_message || 'Sem mensagens'}
                    </p>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <span className="text-xs text-gray-400">
                      {formatRelativeDate(conv.last_message_at || conv.created_at)}
                    </span>
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full ${status.color}`}>
                      <StatusIcon className="w-3 h-3" />
                      {status.label}
                    </span>
                  </div>
                </div>
                {conv.assigned_to_name && (
                  <div className="mt-1 flex items-center gap-1 text-xs text-gray-400">
                    <UserCheck className="w-3 h-3" />
                    {conv.assigned_to_name}
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}

// Componente de bolha de mensagem
function MessageBubble({ message }) {
  const isFromCustomer = message.sender === 'customer'
  const isFromBot = message.sender === 'bot'
  const isFromSystem = message.sender === 'system'

  if (isFromSystem) {
    return (
      <div className="flex justify-center my-2">
        <span className="px-3 py-1 text-xs text-gray-500 bg-gray-100 rounded-full">
          {message.content}
        </span>
      </div>
    )
  }

  return (
    <div className={`flex ${isFromCustomer ? 'justify-start' : 'justify-end'} mb-3`}>
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-2 ${
          isFromCustomer
            ? 'bg-white border border-gray-200 text-gray-900 rounded-bl-sm'
            : isFromBot
            ? 'bg-blue-500 text-white rounded-br-sm'
            : 'bg-primary-600 text-white rounded-br-sm'
        }`}
      >
        <div className="flex items-center gap-1.5 mb-1">
          {isFromCustomer ? (
            <User className="w-3 h-3 text-gray-400" />
          ) : isFromBot ? (
            <Bot className="w-3 h-3 text-blue-200" />
          ) : (
            <UserCheck className="w-3 h-3 text-primary-200" />
          )}
          <span className={`text-xs ${isFromCustomer ? 'text-gray-400' : 'opacity-75'}`}>
            {isFromCustomer ? 'Cliente' : isFromBot ? 'Bot' : 'Operador'}
          </span>
        </div>
        <p className="whitespace-pre-wrap break-words text-sm">{message.content}</p>
        <p className={`text-xs mt-1 ${isFromCustomer ? 'text-gray-400' : 'opacity-60'}`}>
          {formatTime(message.timestamp || message.created_at)}
        </p>
      </div>
    </div>
  )
}

// Componente da janela de chat
function ChatWindow({ conversation, messages, loading, onSend, onAssign, onEnd, isAssignedToMe }) {
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
      await onSend(inputMessage)
      setInputMessage('')
    } catch (error) {
      toast.error('Erro ao enviar mensagem')
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

  const status = statusConfig[conversation.status] || statusConfig.waiting

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 bg-white border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-primary-100 flex items-center justify-center">
              <User className="w-5 h-5 text-primary-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">
                {conversation.name || 'Cliente'}
              </h3>
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <Phone className="w-3 h-3" />
                {conversation.customer_number}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className={`inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full ${status.color}`}>
              {status.label}
            </span>
            {!isAssignedToMe && conversation.status !== 'closed' && (
              <button
                onClick={onAssign}
                className="px-3 py-1.5 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 transition-colors"
              >
                Assumir
              </button>
            )}
            {isAssignedToMe && conversation.status !== 'closed' && (
              <button
                onClick={onEnd}
                className="px-3 py-1.5 text-sm font-medium text-red-600 bg-red-50 rounded-lg hover:bg-red-100 transition-colors"
              >
                Encerrar
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Mensagens */}
      <div className="flex-1 p-4 overflow-y-auto bg-gray-50">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <RefreshCw className="w-6 h-6 animate-spin text-gray-400" />
          </div>
        ) : messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-400">
            <MessageSquare className="w-12 h-12 mb-2" />
            <p>Nenhuma mensagem</p>
          </div>
        ) : (
          <>
            {messages.map((msg, idx) => (
              <MessageBubble key={msg.id || idx} message={msg} />
            ))}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input - sempre visível para permitir envio */}
      {conversation.status === 'closed' ? (
        <div className="p-4 bg-gray-100 border-t border-gray-200 text-center text-gray-500 text-sm">
          Esta conversa foi encerrada
        </div>
      ) : (
        <div className="p-4 bg-white border-t border-gray-200">
          {!isAssignedToMe && (
            <div className="mb-2 px-3 py-1.5 bg-yellow-50 border border-yellow-200 rounded-lg text-yellow-700 text-xs flex items-center gap-1">
              <AlertCircle className="w-3 h-3" />
              Clique em "Assumir" para registrar como responsável
            </div>
          )}
          <div className="flex gap-2">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Digite sua mensagem..."
              disabled={sending}
              className="flex-1 px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50 transition-all"
            />
            <button
              onClick={handleSend}
              disabled={sending || !inputMessage.trim()}
              className="px-4 py-2.5 bg-primary-600 text-white rounded-xl hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {sending ? (
                <RefreshCw className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// Componente principal
export default function ConversationsPanel() {
  const [conversations, setConversations] = useState([])
  const [selectedConversation, setSelectedConversation] = useState(null)
  const [messages, setMessages] = useState([])
  const [loadingConversations, setLoadingConversations] = useState(true)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const [filter, setFilter] = useState('all')

  // Carregar conversas
  const loadConversations = useCallback(async () => {
    setLoadingConversations(true)
    try {
      const data = await getConversations()
      setConversations(Array.isArray(data) ? data : data.conversations || [])
    } catch (error) {
      console.error('Erro ao carregar conversas:', error)
      toast.error('Erro ao carregar conversas')
    } finally {
      setLoadingConversations(false)
    }
  }, [])

  // Carregar mensagens
  const loadMessages = useCallback(async (conversationId) => {
    setLoadingMessages(true)
    try {
      const data = await getConversationMessages(conversationId)
      setMessages(Array.isArray(data) ? data : data.messages || [])
    } catch (error) {
      console.error('Erro ao carregar mensagens:', error)
      setMessages([])
    } finally {
      setLoadingMessages(false)
    }
  }, [])

  // Carregar ao montar
  useEffect(() => {
    loadConversations()
  }, [loadConversations])

  // Carregar mensagens ao selecionar conversa
  useEffect(() => {
    if (selectedConversation) {
      loadMessages(selectedConversation.id)
    } else {
      setMessages([])
    }
  }, [selectedConversation, loadMessages])

  // WebSocket: nova mensagem
  const handleNewMessage = useCallback((data) => {
    console.log('Nova mensagem via WebSocket:', data)
    loadConversations()

    // Se for da conversa selecionada, adicionar mensagem
    if (selectedConversation && data.conversation_id === selectedConversation.id) {
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        content: data.message || data.content,
        sender: data.from_me ? 'agent' : 'customer',
        timestamp: new Date().toISOString()
      }])
    }
  }, [selectedConversation, loadConversations])

  useSharedWebSocketEvent('new_message', handleNewMessage)

  // Assumir conversa
  const handleAssign = async () => {
    if (!selectedConversation) return

    try {
      await assignConversation(selectedConversation.id)
      toast.success('Conversa assumida')
      loadConversations()
      // Atualizar conversa selecionada
      setSelectedConversation(prev => ({ ...prev, assigned_to_me: true, status: 'active' }))
    } catch (error) {
      console.error('Erro ao assumir conversa:', error)
      toast.error('Erro ao assumir conversa')
    }
  }

  // Enviar mensagem
  const handleSendMessage = async (message) => {
    if (!selectedConversation) return

    await replyConversation(selectedConversation.id, message)

    // Adicionar mensagem localmente
    setMessages(prev => [...prev, {
      id: Date.now().toString(),
      content: message,
      sender: 'agent',
      timestamp: new Date().toISOString()
    }])
  }

  // Encerrar conversa
  const handleEndConversation = async () => {
    if (!selectedConversation) return

    if (!confirm('Deseja encerrar esta conversa?')) return

    try {
      await endConversation(selectedConversation.id)
      toast.success('Conversa encerrada')
      loadConversations()
      setSelectedConversation(prev => ({ ...prev, status: 'closed' }))
    } catch (error) {
      console.error('Erro ao encerrar conversa:', error)
      toast.error('Erro ao encerrar conversa')
    }
  }

  return (
    <div className="h-[calc(100vh-12rem)] flex rounded-lg border border-gray-200 bg-white shadow-sm overflow-hidden">
      {/* Lista de conversas */}
      <div className="w-80 border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200 flex items-center justify-between bg-gray-50">
          <h2 className="text-lg font-semibold text-gray-900">Conversas</h2>
          <button
            onClick={loadConversations}
            disabled={loadingConversations}
            className="p-2 text-gray-500 hover:text-primary-600 hover:bg-primary-50 rounded-lg transition-colors disabled:opacity-50"
            title="Atualizar"
          >
            <RefreshCw className={`w-4 h-4 ${loadingConversations ? 'animate-spin' : ''}`} />
          </button>
        </div>
        <ConversationList
          conversations={conversations}
          selectedId={selectedConversation?.id}
          onSelect={setSelectedConversation}
          loading={loadingConversations}
          filter={filter}
          onFilterChange={setFilter}
        />
      </div>

      {/* Janela de chat */}
      <div className="flex-1 flex flex-col bg-gray-50">
        {selectedConversation ? (
          <ChatWindow
            conversation={selectedConversation}
            messages={messages}
            loading={loadingMessages}
            onSend={handleSendMessage}
            onAssign={handleAssign}
            onEnd={handleEndConversation}
            isAssignedToMe={selectedConversation.assigned_to_me}
          />
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-400">
            <MessageSquare className="w-16 h-16 mb-4" />
            <p className="text-lg font-medium">Selecione uma conversa</p>
            <p className="text-sm mt-1">Escolha uma conversa na lista ao lado</p>
          </div>
        )}
      </div>
    </div>
  )
}
