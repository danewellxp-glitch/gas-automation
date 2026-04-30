/**
 * Painel de Conversas do Operador — Linear.app / dense inbox style
 * Chat em tempo real para atendimento ao cliente
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import {
  MessageSquare, Send, RefreshCw, User, Bot, Phone,
  UserCheck, CheckCircle, Clock, AlertCircle, X, ArrowRight
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

export function formatTime(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}

export function formatRelativeDate(dateStr) {
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
  waiting: {
    label: 'Aguardando',
    icon: Clock,
    pill: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
    dot: 'bg-amber-400',
  },
  active: {
    label: 'Ativo',
    icon: UserCheck,
    pill: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
    dot: 'bg-emerald-400',
  },
  bot: {
    label: 'Bot',
    icon: Bot,
    pill: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    dot: 'bg-blue-400',
  },
  closed: {
    label: 'Encerrado',
    icon: CheckCircle,
    pill: 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400',
    dot: 'bg-gray-300 dark:bg-gray-600',
  },
}

// Normalize phone (strip @c.us, @lid suffix and non-digit prefix)
export function normalizePhone(value) {
  if (!value) return ''
  return String(value).split('@')[0].replace(/\D/g, '')
}

// "há Xmin" wait time relative to last activity
export function formatWaitTime(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const diffMs = Date.now() - date.getTime()
  if (diffMs < 0) return 'agora'
  const mins = Math.floor(diffMs / 60000)
  if (mins < 1) return 'agora'
  if (mins < 60) return `há ${mins}min`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `há ${hours}h`
  const days = Math.floor(hours / 24)
  return `há ${days}d`
}

// Status pill badge — replaces the small color dot
export function StatusBadge({ status, className = '' }) {
  const cfg = statusConfig[status] || statusConfig.waiting
  const Icon = cfg.icon
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${cfg.pill} ${className}`}
    >
      <Icon className="w-3 h-3" />
      {cfg.label}
    </span>
  )
}

// Animated dots — shown when bot is responding
export function TypingIndicator({ label = 'Bot respondendo' }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
      role="status"
      aria-live="polite"
    >
      <Bot className="w-3 h-3" />
      <span>{label}</span>
      <span className="flex items-center gap-0.5" aria-hidden="true">
        <span className="w-1 h-1 rounded-full bg-current animate-pulse [animation-delay:0ms]" />
        <span className="w-1 h-1 rounded-full bg-current animate-pulse [animation-delay:150ms]" />
        <span className="w-1 h-1 rounded-full bg-current animate-pulse [animation-delay:300ms]" />
      </span>
    </span>
  )
}

// Inline confirmation modal — replaces native confirm()
export function ConfirmDialog({ open, title, description, confirmLabel, cancelLabel, tone = 'primary', onConfirm, onCancel, busy }) {
  if (!open) return null
  const confirmClass =
    tone === 'danger'
      ? 'bg-red-600 hover:bg-red-700 focus:ring-red-500'
      : 'bg-primary-600 hover:bg-primary-700 focus:ring-primary-500'

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/60 dark:bg-black/70 backdrop-blur-sm p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-dialog-title"
      onClick={(e) => { if (e.target === e.currentTarget && !busy) onCancel?.() }}
    >
      <div className="w-full max-w-sm rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-xl">
        <div className="flex items-start justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
          <h3 id="confirm-dialog-title" className="text-sm font-semibold text-gray-900 dark:text-white">
            {title}
          </h3>
          <button
            type="button"
            onClick={onCancel}
            disabled={busy}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 disabled:opacity-50"
            aria-label="Fechar"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="px-4 py-3 text-sm text-gray-600 dark:text-gray-300">
          {description}
        </div>
        <div className="flex items-center justify-end gap-2 px-4 py-3 border-t border-gray-200 dark:border-gray-700">
          <button
            type="button"
            onClick={onCancel}
            disabled={busy}
            className="min-h-[40px] px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 transition-colors"
          >
            {cancelLabel || 'Cancelar'}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={busy}
            className={`min-h-[40px] inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-white rounded-md disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-offset-1 dark:focus:ring-offset-gray-800 transition-colors ${confirmClass}`}
          >
            {busy && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
            {confirmLabel || 'Confirmar'}
          </button>
        </div>
      </div>
    </div>
  )
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

  const renderEmpty = () => {
    if (filter === 'mine') {
      return (
        <div className="flex flex-col items-center justify-center h-full px-4 py-8 text-center">
          <div className="w-12 h-12 rounded-full bg-primary-50 dark:bg-primary-900/20 flex items-center justify-center mb-3">
            <UserCheck className="w-5 h-5 text-primary-500 dark:text-primary-400" />
          </div>
          <p className="text-sm font-medium text-gray-700 dark:text-gray-200 mb-1">
            Nenhuma conversa atribuída
          </p>
          <p className="text-xs text-gray-400 dark:text-gray-500 mb-3">
            Você ainda não assumiu nenhum atendimento.
          </p>
          <button
            type="button"
            onClick={() => onFilterChange('waiting')}
            className="inline-flex items-center gap-1 min-h-[40px] px-3 py-1.5 text-sm font-medium text-white bg-primary-600 rounded-md hover:bg-primary-700 transition-colors"
          >
            Assumir uma conversa
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )
    }
    return (
      <div className="flex flex-col items-center justify-center h-24 text-gray-400">
        <MessageSquare className="w-5 h-5 mb-1" />
        <p className="text-xs">
          {filter === 'waiting' ? 'Sem clientes aguardando' : 'Nenhuma conversa'}
        </p>
      </div>
    )
  }

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
          renderEmpty()
        ) : (
          filtered.map((conv) => {
            const isSelected = selectedId === conv.id
            const lastTs = conv.last_message_at || conv.created_at
            const showAssumeChip = !conv.assigned_to_me && conv.status !== 'closed'

            return (
              <div
                key={conv.id}
                onClick={() => onSelect(conv)}
                className={`flex flex-col gap-1.5 px-3 py-2.5 border-b border-gray-100 dark:border-gray-700 cursor-pointer transition-colors ${
                  isSelected
                    ? 'bg-primary-50 dark:bg-primary-900/20 border-l-2 border-l-primary-500'
                    : 'hover:bg-gray-50 dark:hover:bg-gray-700/50'
                }`}
              >
                <div className="flex items-center justify-between gap-2 min-w-0">
                  <span className="text-sm font-medium text-gray-900 dark:text-white truncate">
                    {conv.name || conv.customer_number}
                  </span>
                  <span className="text-xs text-gray-400 dark:text-gray-500 shrink-0">
                    {formatRelativeDate(lastTs)}
                  </span>
                </div>

                <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                  {conv.last_message || 'Sem mensagens'}
                </p>

                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5 min-w-0">
                    <StatusBadge status={conv.status} />
                    {lastTs && (
                      <span className="text-xs text-gray-400 dark:text-gray-500 truncate">
                        {formatWaitTime(lastTs)}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    {conv.unread_count > 0 && (
                      <span className="flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[10px] font-bold text-white bg-red-500 rounded-full">
                        {conv.unread_count}
                      </span>
                    )}
                    {showAssumeChip && (
                      <button
                        type="button"
                        onClick={(e) => { e.stopPropagation(); onAssign(conv) }}
                        title="Assumir conversa"
                        aria-label="Assumir conversa"
                        className="px-2 py-0.5 text-xs font-medium text-primary-700 dark:text-primary-300 bg-primary-50 dark:bg-primary-900/30 border border-primary-200 dark:border-primary-800 rounded-md hover:bg-primary-100 dark:hover:bg-primary-900/50 transition-colors"
                      >
                        Assumir
                      </button>
                    )}
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
      // Parent (handleSendMessage) already shows a granular toast — don't double-toast.
      // Keep the input intact so the operator can retry without retyping.
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

  const lastTs = conversation.last_message_at || conversation.created_at

  return (
    <div className="flex flex-col h-full">
      {/* Chat header */}
      <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 flex-nowrap overflow-visible">
        <div className="flex items-center gap-3 min-w-0 flex-nowrap">
          <div className="w-9 h-9 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center shrink-0">
            <User className="w-5 h-5 text-primary-600 dark:text-primary-400" />
          </div>
          <div className="min-w-0">
            <p className="text-base font-semibold text-gray-900 dark:text-white truncate">
              {conversation.name || 'Cliente'}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1 mt-0.5">
              <Phone className="w-3 h-3 shrink-0" />
              <span className="truncate">{conversation.customer_number}</span>
            </p>
          </div>
          <div className="flex items-center gap-1.5 shrink-0">
            <StatusBadge status={conversation.status} />
            {conversation.status === 'bot' && <TypingIndicator />}
            {conversation.status === 'waiting' && lastTs && (
              <span className="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">
                {formatWaitTime(lastTs)}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-1.5 shrink-0 flex-nowrap">
          {!isAssignedToMe && conversation.status !== 'closed' && (
            <button
              type="button"
              onClick={onAssign}
              className="min-h-[40px] inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-white bg-primary-600 rounded-md hover:bg-primary-700 transition-colors"
            >
              <UserCheck className="w-4 h-4" />
              Assumir
            </button>
          )}
          {isAssignedToMe && conversation.status !== 'closed' && (
            <>
              <button
                type="button"
                onClick={onTransferToBot}
                className="min-h-[40px] inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-blue-700 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors"
              >
                <Bot className="w-4 h-4" />
                Para Bot
              </button>
              <button
                type="button"
                onClick={onEnd}
                className="min-h-[40px] inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-red-700 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
              >
                <CheckCircle className="w-4 h-4" />
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
    loadConversations()

    const msgData = wsEvent.data || wsEvent
    const phone = msgData.phone
    const message = msgData.message
    const direction = msgData.direction

    const currentConversation = selectedConversationRef.current
    if (!currentConversation) return

    // Compare against the canonical phone field only — never fall back to `id`,
    // which is a UUID on /api/conversations and would never match a phone payload.
    const currentPhone = normalizePhone(currentConversation.customer_number)
    const incomingPhone = normalizePhone(phone)

    if (currentPhone && incomingPhone && incomingPhone === currentPhone) {
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        content: message,
        sender: direction === 'outgoing' ? 'agent' : 'customer',
        timestamp: new Date().toISOString()
      }])
    }
  }, [loadConversations])

  useSharedWebSocketEvent('new_message', handleNewMessage)

  const [confirmAction, setConfirmAction] = useState(null)
  const [confirmBusy, setConfirmBusy] = useState(false)

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
        if (updated) {
          setSelectedConversation({ ...updated, assigned_to_me: true, status: 'active' })
        }
      }
    } catch (error) {
      const statusCode = error?.response?.status
      if (statusCode === 401) toast.error('Sessão expirada. Faça login novamente.')
      else if (statusCode === 403) toast.error('Sem permissão para assumir esta conversa.')
      else if (statusCode >= 500) toast.error('Erro no servidor ao assumir conversa.')
      else toast.error('Erro ao assumir conversa')
    }
  }

  const handleSendMessage = async (message) => {
    if (!selectedConversation) return
    try {
      const result = await replyConversation(selectedConversation.id, message)
      if (result?.success) {
        setMessages(prev => [...prev, {
          id: Date.now().toString(),
          content: message,
          sender: 'agent',
          timestamp: new Date().toISOString()
        }])
      } else {
        throw new Error(result?.message || 'Erro ao enviar mensagem')
      }
    } catch (error) {
      // Granular handling: 401 → session expired, 5xx → server error, others → backend detail
      const statusCode = error?.response?.status
      const detail = error?.response?.data?.detail
      if (statusCode === 401) {
        toast.error('Sessão expirada. Faça login novamente.')
      } else if (statusCode === 403) {
        toast.error('Sem permissão para responder.')
      } else if (statusCode === 503) {
        toast.error(detail || 'WhatsApp desconectado — verifique o WAHA.')
      } else if (statusCode >= 500) {
        toast.error(detail || 'Erro no servidor WAHA.')
      } else if (statusCode >= 400) {
        toast.error(detail || 'Não foi possível enviar a mensagem.')
      } else {
        toast.error(detail || error?.message || 'Erro ao enviar mensagem')
      }
      throw error
    }
  }

  const askEndConversation = () => {
    if (!selectedConversation) return
    setConfirmAction({
      kind: 'end',
      title: 'Encerrar conversa',
      description: 'Esta conversa será marcada como encerrada e devolvida ao bot. Deseja continuar?',
      confirmLabel: 'Encerrar',
      tone: 'danger',
    })
  }

  const askTransferToBot = () => {
    if (!selectedConversation) return
    if (selectedConversation.status === 'bot') {
      toast('Conversa já está com o bot', { icon: '🤖' })
      return
    }
    setConfirmAction({
      kind: 'transfer',
      title: 'Transferir para o bot',
      description: 'O atendimento volta a ser conduzido pelo bot. Você pode reassumir a qualquer momento.',
      confirmLabel: 'Transferir',
      tone: 'primary',
    })
  }

  const performConfirm = async () => {
    if (!confirmAction || !selectedConversation) return
    setConfirmBusy(true)
    try {
      if (confirmAction.kind === 'end') {
        await endConversation(selectedConversation.id)
        toast.success('Conversa encerrada e devolvida ao bot')
        loadConversations()
        setSelectedConversation(prev => ({ ...prev, status: 'closed' }))
      } else if (confirmAction.kind === 'transfer') {
        await transferToBot(selectedConversation.id)
        toast.success('Conversa transferida para o bot')
        loadConversations()
        setSelectedConversation(prev => ({ ...prev, status: 'bot' }))
      }
      setConfirmAction(null)
    } catch (error) {
      const statusCode = error?.response?.status
      if (statusCode === 401) toast.error('Sessão expirada. Faça login novamente.')
      else if (statusCode >= 500) toast.error('Erro no servidor.')
      else toast.error(confirmAction.kind === 'end' ? 'Erro ao encerrar conversa' : 'Erro ao transferir para bot')
    } finally {
      setConfirmBusy(false)
    }
  }

  return (
    <div className="h-[calc(100vh-10rem)] flex rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden">

      {/* Left: conversation list */}
      <div className="w-72 lg:w-80 border-r border-gray-200 dark:border-gray-700 flex flex-col shrink-0">
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
            onEnd={askEndConversation}
            onTransferToBot={askTransferToBot}
            isAssignedToMe={selectedConversation.assigned_to_me}
          />
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-300 dark:text-gray-600">
            <MessageSquare className="w-10 h-10 mb-2" />
            <p className="text-sm text-gray-400 dark:text-gray-500">Selecione uma conversa</p>
          </div>
        )}
      </div>

      <ConfirmDialog
        open={!!confirmAction}
        title={confirmAction?.title}
        description={confirmAction?.description}
        confirmLabel={confirmAction?.confirmLabel}
        tone={confirmAction?.tone}
        busy={confirmBusy}
        onConfirm={performConfirm}
        onCancel={() => { if (!confirmBusy) setConfirmAction(null) }}
      />
    </div>
  )
}
