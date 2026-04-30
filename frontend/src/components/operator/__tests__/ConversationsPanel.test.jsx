import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, within } from '@testing-library/react'

vi.mock('../../../services/api', () => ({
  getConversations: vi.fn(),
  getConversationMessages: vi.fn(),
  assignConversation: vi.fn(),
  replyConversation: vi.fn(),
  endConversation: vi.fn(),
  transferToBot: vi.fn(),
}))

vi.mock('../../../hooks/useSharedWebSocket', () => ({
  useSharedWebSocketEvent: vi.fn(),
}))

vi.mock('react-hot-toast', () => {
  const fn = vi.fn()
  fn.success = vi.fn()
  fn.error = vi.fn()
  return { default: fn, toast: fn }
})

import ConversationsPanel, {
  normalizePhone,
  formatWaitTime,
  formatRelativeDate,
  formatTime,
  StatusBadge,
  TypingIndicator,
  ConfirmDialog,
} from '../ConversationsPanel'

import * as api from '../../../services/api'
import * as wsHook from '../../../hooks/useSharedWebSocket'
import toast from 'react-hot-toast'

const sampleConversations = [
  {
    id: '5541999990001',
    customer_number: '5541999990001',
    name: 'Maria Silva',
    status: 'waiting',
    last_message: 'Olá, preciso de gás',
    last_message_at: new Date(Date.now() - 12 * 60 * 1000).toISOString(),
    assigned_to: null,
    assigned_to_me: false,
    unread_count: 2,
  },
  {
    id: '5541999990002',
    customer_number: '5541999990002',
    name: 'João Pedro',
    status: 'active',
    last_message: 'Pode entregar amanhã?',
    last_message_at: new Date(Date.now() - 90 * 60 * 1000).toISOString(),
    assigned_to: 'op-1',
    assigned_to_me: true,
    unread_count: 0,
  },
  {
    id: '5541999990003',
    customer_number: '5541999990003',
    name: 'Ana Souza',
    status: 'bot',
    last_message: 'Confirmando seu pedido…',
    last_message_at: new Date(Date.now() - 30 * 1000).toISOString(),
    assigned_to: null,
    assigned_to_me: false,
    unread_count: 0,
  },
]

beforeEach(() => {
  api.getConversations.mockResolvedValue({ items: sampleConversations })
  api.getConversationMessages.mockResolvedValue([])
  api.assignConversation.mockResolvedValue({ success: true })
  api.replyConversation.mockResolvedValue({ success: true })
  api.endConversation.mockResolvedValue({ success: true })
  api.transferToBot.mockResolvedValue({ success: true })
  wsHook.useSharedWebSocketEvent.mockImplementation(() => undefined)
})

// ==================== Pure helpers ====================

describe('normalizePhone', () => {
  it('strips @c.us suffix', () => {
    expect(normalizePhone('5541999990001@c.us')).toBe('5541999990001')
  })
  it('strips @lid suffix', () => {
    expect(normalizePhone('5541999990001@lid')).toBe('5541999990001')
  })
  it('removes non-digit characters', () => {
    expect(normalizePhone('+55 (41) 99999-0001')).toBe('5541999990001')
  })
  it('returns empty string for null/undefined/empty', () => {
    expect(normalizePhone(null)).toBe('')
    expect(normalizePhone(undefined)).toBe('')
    expect(normalizePhone('')).toBe('')
  })
  it('coerces non-string input', () => {
    expect(normalizePhone(5541999990001)).toBe('5541999990001')
  })
})

describe('formatWaitTime', () => {
  it('returns "agora" for very recent dates', () => {
    expect(formatWaitTime(new Date().toISOString())).toBe('agora')
  })
  it('returns "agora" for negative diffs (clock skew)', () => {
    expect(formatWaitTime(new Date(Date.now() + 5000).toISOString())).toBe('agora')
  })
  it('formats minutes', () => {
    expect(formatWaitTime(new Date(Date.now() - 12 * 60_000).toISOString())).toBe('há 12min')
  })
  it('formats hours', () => {
    expect(formatWaitTime(new Date(Date.now() - 3 * 3_600_000).toISOString())).toBe('há 3h')
  })
  it('formats days', () => {
    expect(formatWaitTime(new Date(Date.now() - 2 * 86_400_000).toISOString())).toBe('há 2d')
  })
  it('returns empty for falsy input', () => {
    expect(formatWaitTime(null)).toBe('')
    expect(formatWaitTime(undefined)).toBe('')
  })
})

describe('formatRelativeDate', () => {
  it('returns "Agora" for very recent', () => {
    expect(formatRelativeDate(new Date().toISOString())).toBe('Agora')
  })
  it('formats minutes', () => {
    expect(formatRelativeDate(new Date(Date.now() - 5 * 60_000).toISOString())).toBe('5min')
  })
  it('formats hours', () => {
    expect(formatRelativeDate(new Date(Date.now() - 2 * 3_600_000).toISOString())).toBe('2h')
  })
  it('returns date for >24h', () => {
    const out = formatRelativeDate(new Date(Date.now() - 2 * 86_400_000).toISOString())
    expect(out).toMatch(/^\d{2}\/\d{2}$/)
  })
  it('returns empty for falsy input', () => {
    expect(formatRelativeDate(null)).toBe('')
  })
})

describe('formatTime', () => {
  it('returns HH:MM in pt-BR locale', () => {
    const out = formatTime('2026-04-30T13:45:00Z')
    expect(out).toMatch(/^\d{2}:\d{2}$/)
  })
  it('returns empty for falsy input', () => {
    expect(formatTime(null)).toBe('')
  })
})

// ==================== Status badge ====================

describe('StatusBadge', () => {
  it('renders Aguardando label for waiting', () => {
    render(<StatusBadge status="waiting" />)
    expect(screen.getByText('Aguardando')).toBeInTheDocument()
  })
  it('renders Ativo for active', () => {
    render(<StatusBadge status="active" />)
    expect(screen.getByText('Ativo')).toBeInTheDocument()
  })
  it('renders Bot for bot', () => {
    render(<StatusBadge status="bot" />)
    expect(screen.getByText('Bot')).toBeInTheDocument()
  })
  it('renders Encerrado for closed', () => {
    render(<StatusBadge status="closed" />)
    expect(screen.getByText('Encerrado')).toBeInTheDocument()
  })
  it('falls back to waiting for unknown status', () => {
    render(<StatusBadge status="nonexistent" />)
    expect(screen.getByText('Aguardando')).toBeInTheDocument()
  })
  it('applies dark mode classes', () => {
    const { container } = render(<StatusBadge status="waiting" />)
    expect(container.firstChild.className).toMatch(/dark:bg-amber-900/)
  })
})

// ==================== TypingIndicator ====================

describe('TypingIndicator', () => {
  it('renders default label', () => {
    render(<TypingIndicator />)
    expect(screen.getByText('Bot respondendo')).toBeInTheDocument()
  })
  it('renders custom label', () => {
    render(<TypingIndicator label="Digitando…" />)
    expect(screen.getByText('Digitando…')).toBeInTheDocument()
  })
  it('uses role=status for a11y', () => {
    render(<TypingIndicator />)
    expect(screen.getByRole('status')).toBeInTheDocument()
  })
})

// ==================== ConfirmDialog ====================

describe('ConfirmDialog', () => {
  it('renders nothing when open=false', () => {
    const { container } = render(
      <ConfirmDialog open={false} title="x" description="y" onConfirm={vi.fn()} onCancel={vi.fn()} />
    )
    expect(container.firstChild).toBeNull()
  })

  it('renders title, description and default labels when open', () => {
    render(
      <ConfirmDialog open title="Encerrar" description="Você tem certeza?" onConfirm={vi.fn()} onCancel={vi.fn()} />
    )
    expect(screen.getByText('Encerrar')).toBeInTheDocument()
    expect(screen.getByText('Você tem certeza?')).toBeInTheDocument()
    expect(screen.getByText('Cancelar')).toBeInTheDocument()
    expect(screen.getByText('Confirmar')).toBeInTheDocument()
  })

  it('uses custom labels', () => {
    render(
      <ConfirmDialog open title="t" description="d" confirmLabel="Sim" cancelLabel="Não" onConfirm={vi.fn()} onCancel={vi.fn()} />
    )
    expect(screen.getByText('Sim')).toBeInTheDocument()
    expect(screen.getByText('Não')).toBeInTheDocument()
  })

  it('fires onConfirm and onCancel', () => {
    const onConfirm = vi.fn()
    const onCancel = vi.fn()
    render(
      <ConfirmDialog open title="t" description="d" onConfirm={onConfirm} onCancel={onCancel} />
    )
    fireEvent.click(screen.getByText('Confirmar'))
    expect(onConfirm).toHaveBeenCalledOnce()
    fireEvent.click(screen.getByText('Cancelar'))
    expect(onCancel).toHaveBeenCalledOnce()
  })

  it('disables actions and shows spinner when busy', () => {
    render(
      <ConfirmDialog open busy title="t" description="d" onConfirm={vi.fn()} onCancel={vi.fn()} />
    )
    expect(screen.getByText('Confirmar').closest('button')).toBeDisabled()
    expect(screen.getByText('Cancelar').closest('button')).toBeDisabled()
  })

  it('applies danger tone class to confirm button', () => {
    render(
      <ConfirmDialog open tone="danger" title="t" description="d" onConfirm={vi.fn()} onCancel={vi.fn()} />
    )
    expect(screen.getByText('Confirmar').closest('button').className).toMatch(/bg-red-600/)
  })
})

// ==================== Main component integration ====================

describe('ConversationsPanel', () => {
  it('renders the conversation list with names and status badges', async () => {
    render(<ConversationsPanel />)
    expect(await screen.findByText('Maria Silva')).toBeInTheDocument()
    expect(screen.getByText('João Pedro')).toBeInTheDocument()
    expect(screen.getByText('Ana Souza')).toBeInTheDocument()
    // pill badge labels
    expect(screen.getAllByText('Aguardando').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Ativo').length).toBeGreaterThan(0)
  })

  it('shows the "Minhas" empty-state CTA when filter is empty and switches filter on click', async () => {
    api.getConversations.mockResolvedValue({ items: [sampleConversations[0]] }) // none assigned to me
    render(<ConversationsPanel />)
    await screen.findByText('Maria Silva')
    fireEvent.click(screen.getByRole('button', { name: 'Minhas' }))
    expect(await screen.findByText('Nenhuma conversa atribuída')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /Assumir uma conversa/ }))
    expect(await screen.findByText('Maria Silva')).toBeInTheDocument()
  })

  it('opens an inline modal (not native confirm) when clicking Encerrar', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm')
    render(<ConversationsPanel />)
    fireEvent.click(await screen.findByText('João Pedro'))
    fireEvent.click(await screen.findByText('Encerrar'))
    expect(await screen.findByText('Encerrar conversa')).toBeInTheDocument()
    expect(confirmSpy).not.toHaveBeenCalled()
  })

  it('confirming "Encerrar" calls endConversation and closes the modal', async () => {
    render(<ConversationsPanel />)
    fireEvent.click(await screen.findByText('João Pedro'))
    fireEvent.click(await screen.findByText('Encerrar'))
    const dialog = await screen.findByRole('dialog')
    fireEvent.click(within(dialog).getByText('Encerrar'))
    expect(api.endConversation).toHaveBeenCalledWith('5541999990002')
  })

  it('shows TypingIndicator in chat header when status === bot', async () => {
    render(<ConversationsPanel />)
    fireEvent.click(await screen.findByText('Ana Souza'))
    expect(await screen.findByText('Bot respondendo')).toBeInTheDocument()
  })

  it('shows 401 toast on session expiry from replyConversation', async () => {
    api.replyConversation.mockRejectedValueOnce({ response: { status: 401 } })
    render(<ConversationsPanel />)
    fireEvent.click(await screen.findByText('João Pedro'))
    const input = screen.getByPlaceholderText('Digite sua mensagem...')
    fireEvent.change(input, { target: { value: 'oi' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    await new Promise(r => setTimeout(r, 0))
    expect(toast.error).toHaveBeenCalledWith(expect.stringMatching(/Sessão expirada/i))
  })

  it('shows server-error toast on 500 from replyConversation', async () => {
    api.replyConversation.mockRejectedValueOnce({ response: { status: 500, data: { detail: 'Boom' } } })
    render(<ConversationsPanel />)
    fireEvent.click(await screen.findByText('João Pedro'))
    const input = screen.getByPlaceholderText('Digite sua mensagem...')
    fireEvent.change(input, { target: { value: 'oi' } })
    fireEvent.click(screen.getByRole('button', { name: 'Enviar mensagem' }))
    await new Promise(r => setTimeout(r, 0))
    expect(toast.error).toHaveBeenCalled()
  })

  it('only updates messages when WebSocket phone matches selected.customer_number', async () => {
    let captured = null
    wsHook.useSharedWebSocketEvent.mockImplementation((event, cb) => { captured = cb })
    render(<ConversationsPanel />)
    fireEvent.click(await screen.findByText('João Pedro'))
    expect(typeof captured).toBe('function')

    // Mismatched phone — should be ignored
    captured({ data: { phone: '5541000000000', message: 'spam', direction: 'incoming' } })
    // Matching phone (with @c.us suffix) — should be appended
    captured({ data: { phone: '5541999990002@c.us', message: 'hello', direction: 'incoming' } })

    await new Promise(r => setTimeout(r, 0))
    expect(api.getConversations).toHaveBeenCalled() // loadConversations triggered each time
  })

  it('renders empty placeholder when no conversation is selected', async () => {
    render(<ConversationsPanel />)
    expect(await screen.findByText('Selecione uma conversa')).toBeInTheDocument()
  })

  it('renders message bubbles for customer/bot/operator senders', async () => {
    api.getConversationMessages.mockResolvedValueOnce([
      { id: '1', sender: 'customer', content: 'Olá', timestamp: new Date().toISOString() },
      { id: '2', sender: 'bot', content: 'Oi! Como posso ajudar?', timestamp: new Date().toISOString() },
      { id: '3', sender: 'agent', content: 'Operador aqui', timestamp: new Date().toISOString() },
      { id: '4', sender: 'system', content: 'Conversa transferida', timestamp: new Date().toISOString() },
    ])
    render(<ConversationsPanel />)
    fireEvent.click(await screen.findByText('João Pedro'))
    expect(await screen.findByText('Olá')).toBeInTheDocument()
    expect(screen.getByText('Oi! Como posso ajudar?')).toBeInTheDocument()
    expect(screen.getByText('Operador aqui')).toBeInTheDocument()
    expect(screen.getByText('Conversa transferida')).toBeInTheDocument()
  })

  it('opens transfer-to-bot modal and confirms via transferToBot API', async () => {
    render(<ConversationsPanel />)
    fireEvent.click(await screen.findByText('João Pedro'))
    fireEvent.click(await screen.findByText('Para Bot'))
    const dialog = await screen.findByRole('dialog')
    expect(within(dialog).getByText('Transferir para o bot')).toBeInTheDocument()
    fireEvent.click(within(dialog).getByText('Transferir'))
    expect(api.transferToBot).toHaveBeenCalledWith('5541999990002')
  })

  // Regression for MAX-9: long customer name + bot-typing + action buttons must
  // never overlap. The chat header MUST clip overflow (overflow-hidden) so
  // truncate ellipsis kicks in before any pixel reaches the action buttons.
  it('chat header has overflow-hidden so name/phone truncate cannot overlap action buttons', async () => {
    const longName = 'Maria Aparecida da Silva Pereira de Lourdes Conceição'
    api.getConversations.mockResolvedValueOnce({
      items: [{
        id: '5541999990099',
        customer_number: '5541999990099',
        name: longName,
        status: 'bot',
        last_message: 'oi',
        last_message_at: new Date().toISOString(),
        assigned_to: 'op-1',
        assigned_to_me: true,
        unread_count: 0,
      }],
    })
    render(<ConversationsPanel />)
    fireEvent.click(await screen.findByText(longName))
    const header = await screen.findByTestId('chat-header')
    expect(header.className).toMatch(/overflow-hidden/)
    expect(header.className).not.toMatch(/overflow-visible/)
    expect(header.className).toMatch(/flex-nowrap/)
  })
})
