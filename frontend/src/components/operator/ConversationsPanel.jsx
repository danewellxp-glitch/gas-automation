/**
 * Painel de Conversas do Operador — Linear.app / dense inbox style
 * Chat em tempo real para atendimento ao cliente
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import {
  MessageSquare, Send, RefreshCw, User, Bot, Phone,
  UserCheck, CheckCircle, Clock, AlertCircle
} from 'lucide-react'
import toast from 'react-hot-toast'
import {
  getConversations,
  getConversationMessages,
  assignConversation,
  replyConversation,
  endConversation,
  transferToBot
} from '../../services/api'
import { useSharedWebSocketEvent } from '../../hooks/useSharedWebSocket'

function formatTime(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}

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

const statusConfig = {
  waiting: { label: 'Aguardando', dot: 'bg-amber-400',  icon: Clock },
  active:  { label: 'Atendendo',  dot: 'bg-emerald-400', icon: UserCheck },
  bot:     { label: 'Bot',        dot: 'bg-blue-400',    icon: Bot },
  closed:  { label: 'Encerrada',  dot: 'bg-gray-300 dark:bg-gray-600',    icon: CheckCircle },
}

// Dense conversation list
function ConversationList({ conversations, selectedId, onSelect, onAssign, loading, filter, onFilterChange }) {
  const filtered = conversations.filter(conv => {
    if (filter === 'all') return true
    if (filter === 'waiting') return conv.status === 'waiting' || !conv.assigned_to
    if (filter === 'mine') return conv.assigned_to_me
    if (filter === 'active') return conv.status === 'active'
    return true
  })

  return (
    <div className="flex flex-col h-full">
      {/* Filter tabs */}
      <div className="flex items-center gap-1 px-2 py-1.5 border-b border-gray-200 dark:border-gray-700">
        {[
          { key: 'all', label: 'Todas' },
          { key: 'waiting', label: 'Aguardando' },
          { key: 'mine', label: 'Minhas' },
        ].map(f => (
          <button
            key={f.key}
            onClick={() => onFilterChange(f.key)}
            className={`px-2 py-0.5 text-xs font-medium rounded transition-colors ${
              filter === f.key
                ? 'bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900'
                : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center h-24">
            <RefreshCw className="w-4 h-4 animate-spin text-gray-400" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-24 text-gray-400">
            <MessageSquare className="w-5 h-5 mb-1" />
            <p className="text-xs">Nenhuma conversa</p>
          </div>
        ) : (
          filtered.map((conv) => {
            const status = statusConfig[conv.status] || statusConfig.waiting
            const StatusIcon = status.icon
            const isSelected = selectedId === conv.id

            return (
              <div
                key={conv.id}
                onClick={() => onSelect(conv)}
                className={`flex items-start gap-2 px-3 py-2 border-b border-gray-100 dark:border-gray-700 cursor-pointer transition-colors ${
                  isSelected
                    ? 'bg-primary-50 dark:bg-primary-900/20 border-l-2 border-l-primary-500'
                    : 'hover:bg-gray-50 dark:hover:bg-gray-700/50'
                }`}
              >
                {/* Status dot */}
                <span className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${status.dot}`} />

                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-1">
                    <span className="text-xs font-medium text-gray-900 dark:text-white truncate">
                      {conv.name || conv.customer_number}
                    </span>
                    <span className="text-xs text-gray-400 dark:text-gray-500 shrink-0">
                      {formatRelativeDate(conv.last_message_at || conv.created_at)}
                    </span>
                  </div>
                  <p className="text-xs text-gray-400 dark:text-gray-500 truncate mt-0.5">
                    {conv.last_message || 'Sem mensagens'}
                  </p>
                  <div className="flex items-center justify-between mt-1">
                    <span className="text-xs text-gray-400 dark:text-gray-500 flex items-center gap-0.5">
                      <StatusIcon className="w-3 h-3" />
                      {status.label}
                    </span>
                    <div className="flex items-center gap-1">
                      {conv.unread_count > 0 && (
                        <span className="flex items-center justify-center w-4 h-4 text-xs font-bold text-white bg-red-500 rounded-full">
                          {conv.unread_count}
                        </span>
                      )}
                      {!conv.assigned_to_me && conv.status !== 'closed' && (
                        <button
                          onClick={(e) => { e.stopPropagation(); onAssign(conv) }}
                          className="px-1.5 py-0.5 text-xs font-medium text-white bg-primary-600 rounded hover:bg-primary-700 transition-colors"
                        >
                          Assumir
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}

// Message bubble
function MessageBubble({ message }) {
  const isFromCustomer = message.sender === 'customer'
  const isFromBot = message.sender === 'bot'
  const isFromSystem = message.sender === 'system'

  if (isFromSystem) {
    return (
      <div className="flex justify-center my-2">
        <span className="px-3 py-1 text-xs text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 rounded-full">
          {message.content}
        </span>
      </div>
    )
  }

  return (
    <div className={`flex ${isFromCustomer ? 'justify-start' : 'justify-end'} mb-2`}>
      <div
        className={`max-w-[75%] rounded-2xl px-3 py-2 ${
          isFromCustomer
            ? 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-900 dark:text-white rounded-bl-sm'
            : isFromBot
            ? 'bg-blue-500 text-white rounded-br-sm'
            : 'bg-primary-600 text-white rounded-br-sm'
        }`}
      >
        <div className="flex items-center gap-1 mb-0.5">
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
        <p className={`text-xs mt-0.5 ${isFromCustomer ? 'text-gray-400' : 'opacity-60'}`}>
          {formatTime(message.timestamp || message.created_at)}
        </p>
      </div>
    </div>
  )
}

// Chat window
function ChatWindow({ conversation, messages, loading, onSend, onAssign, onEnd, onTransferToBot, isAssignedToMe }) {
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
      const detail = error?.response?.data?.detail || error?.message || 'Erro desconhecido'
      toast.error(`Erro ao enviar: ${detail}`)
      console.error('Erro ao enviar mensagem:', error)
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
      {/* Chat header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center shrink-0">
            <User className="w-4 h-4 text-primary-600 dark:text-primary-400" />
          </div>
          <div>
            <p className="text-sm font-medium text-gray-900 dark:text-white leading-none">
              {conversation.name || 'Cliente'}
            </p>
            <p className="text-xs text-gray-400 dark:text-gray-500 flex items-center gap-1 mt-0.5">
              <Phone className="w-2.5 h-2.5" />
              {conversation.customer_number}
            </p>
          </div>
          <span className={`ml-1 inline-flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400`}>
            <span className={`w-1.5 h-1.5 rounded-full ${status.dot}`} />
            {status.label}
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          {!isAssignedToMe && conversation.status !== 'closed' && (
            <button
              onClick={onAssign}
              className="px-2.5 py-1 text-xs font-medium text-white bg-primary-600 rounded-md hover:bg-primary-700 transition-colors"
            >
              Assumir
            </button>
          )}
          {isAssignedToMe && conversation.status !== 'closed' && (
            <>
              <button
                onClick={onTransferToBot}
                className="px-2.5 py-1 text-xs font-medium text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors flex items-center gap-1"
              >
                <Bot className="w-3 h-3" />
                Para Bot
              </button>
              <button
                onClick={onEnd}
                className="px-2.5 py-1 text-xs font-medium text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
              >
                Encerrar
              </button>
            </>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 p-3 overflow-y-auto bg-gray-50 dark:bg-gray-700/30">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <RefreshCw className="w-5 h-5 animate-spin text-gray-400" />
          </div>
        ) : messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-400">
            <MessageSquare className="w-8 h-8 mb-2" />
            <p className="text-sm">Nenhuma mensagem</p>
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

      {/* Input */}
      {conversation.status === 'closed' ? (
        <div className="px-4 py-2.5 bg-gray-50 dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 text-center text-xs text-gray-400 dark:text-gray-500">
          Esta conversa foi encerrada
        </div>
      ) : (
        <div className="p-3 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
          {!isAssignedToMe && (
            <div className="mb-2 px-2.5 py-1 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-md text-amber-700 dark:text-amber-400 text-xs flex items-center gap-1">
              <AlertCircle className="w-3 h-3 shrink-0" />
              Clique em "Assumir" para registrar como responsável
            </div>
          )}
          <div className="flex gap-2">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder="Digite sua mensagem..."
              disabled={sending}
              className="flex-1 px-3 py-2 border border-gray-200 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:placeholder-gray-400 rounded-lg text-sm focus:ring-1 focus:ring-primary-500 focus:border-primary-500 disabled:opacity-50 transition-colors"
            />
            <button
              onClick={handleSend}
              disabled={sending || !inputMessage.trim()}
              className="px-3 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {sending
                ? <RefreshCw className="w-4 h-4 animate-spin" />
                : <Send className="w-4 h-4" />
              }
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// Main component
export default function ConversationsPanel() {
  const [conversations, setConversations] = useState([])
  const [selectedConversation, setSelectedConversation] = useState(null)
  const [messages, setMessages] = useState([])
  const [loadingConversations, setLoadingConversations] = useState(true)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const [filter, setFilter] = useState('all')

  const selectedConversationRef = useRef(selectedConversation)

  const loadConversations = useCallback(async () => {
    setLoadingConversations(true)
    try {
      const data = await getConversations()
      setConversations(data.items || [])
    } catch (error) {
      console.error('Erro ao carregar conversas:', error)
      toast.error('Erro ao carregar conversas')
    } finally {
      setLoadingConversations(false)
    }
  }, [])

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

  useEffect(() => { loadConversations() }, [loadConversations])

  useEffect(() => {
    if (selectedConversation) loadMessages(selectedConversation.id)
    else setMessages([])
  }, [selectedConversation, loadMessages])

  useEffect(() => {
    selectedConversationRef.current = selectedConversation
  }, [selectedConversation])

  const handleNewMessage = useCallback((wsEvent) => {
    console.log('Nova mensagem via WebSocket:', wsEvent)
    loadConversations()

    const msgData = wsEvent.data || wsEvent
    const phone = msgData.phone
    const message = msgData.message
    const direction = msgData.direction

    const currentConversation = selectedConversationRef.current
    if (currentConversation && phone === currentConversation.id) {
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        content: message,
        sender: direction === 'outgoing' ? 'agent' : 'customer',
        timestamp: new Date().toISOString()
      }])
    }
  }, [loadConversations])

  useSharedWebSocketEvent('new_message', handleNewMessage)

  const handleAssign = async (conv) => {
    const target = conv || selectedConversation
    if (!target) return
    try {
      await assignConversation(target.id)
      toast.success('Conversa assumida')
      if (selectedConversation && selectedConversation.id === target.id) {
        setSelectedConversation(prev => ({ ...prev, assigned_to_me: true, status: 'active' }))
      }
      const data = await getConversations()
      const items = data.items || []
      setConversations(items)
      if (selectedConversation && selectedConversation.id === target.id) {
        const updated = items.find(c => c.id === target.id)
        if (updated) setSelectedConversation({ ...updated, assigned_to_me: true, status: 'active' })
      }
    } catch (error) {
      console.error('Erro ao assumir conversa:', error)
      toast.error('Erro ao assumir conversa')
    }
  }

  const handleSendMessage = async (message) => {
    if (!selectedConversation) return
    const result = await replyConversation(selectedConversation.id, message)
    if (result.success) {
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        content: message,
        sender: 'agent',
        timestamp: new Date().toISOString()
      }])
    } else {
      throw new Error(result.message || 'Erro ao enviar mensagem')
    }
  }

  const handleEndConversation = async () => {
    if (!selectedConversation) return
    if (!confirm('Deseja encerrar esta conversa e devolver ao bot?')) return
    try {
      await endConversation(selectedConversation.id)
      toast.success('Conversa encerrada e devolvida ao bot')
      loadConversations()
      setSelectedConversation(prev => ({ ...prev, status: 'closed' }))
    } catch (error) {
      console.error('Erro ao encerrar conversa:', error)
      toast.error('Erro ao encerrar conversa')
    }
  }

  const handleTransferToBot = async () => {
    if (!selectedConversation) return
    if (!confirm('Transferir conversa de volta para o bot?')) return
    try {
      await transferToBot(selectedConversation.id)
      toast.success('Conversa transferida para o bot')
      loadConversations()
      setSelectedConversation(prev => ({ ...prev, status: 'bot' }))
    } catch (error) {
      console.error('Erro ao transferir para bot:', error)
      toast.error('Erro ao transferir para bot')
    }
  }

  return (
    <div className="h-[calc(100vh-10rem)] flex rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden">

      {/* Left: conversation list */}
      <div className="w-64 border-r border-gray-200 dark:border-gray-700 flex flex-col shrink-0">
        <div className="flex items-center justify-between px-3 py-2 border-b border-gray-200 dark:border-gray-700">
          <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">Conversas</span>
          <button
            onClick={loadConversations}
            disabled={loadingConversations}
            className="p-1 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 rounded hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingConversations ? 'animate-spin' : ''}`} />
          </button>
        </div>
        <ConversationList
          conversations={conversations}
          selectedId={selectedConversation?.id}
          onSelect={setSelectedConversation}
          onAssign={handleAssign}
          loading={loadingConversations}
          filter={filter}
          onFilterChange={setFilter}
        />
      </div>

      {/* Right: chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {selectedConversation ? (
          <ChatWindow
            conversation={selectedConversation}
            messages={messages}
            loading={loadingMessages}
            onSend={handleSendMessage}
            onAssign={() => handleAssign()}
            onEnd={handleEndConversation}
            onTransferToBot={handleTransferToBot}
            isAssignedToMe={selectedConversation.assigned_to_me}
          />
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-300 dark:text-gray-600">
            <MessageSquare className="w-10 h-10 mb-2" />
            <p className="text-sm text-gray-400 dark:text-gray-500">Selecione uma conversa</p>
          </div>
        )}
      </div>

    </div>
  )
}
