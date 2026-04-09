import { useState, useEffect, useCallback, useRef } from 'react'
import { useAuth } from '../../hooks/useAuth'
import api from '../../api/client'
import { FINANCEIRO } from '../../api/endpoints'
import { toast } from 'react-hot-toast'

import MetricCard from './components/MetricCard'
import CashFlowChart from './components/CashFlowChart'
import DREChart from './components/DREChart'
import RecentTransactions from './components/RecentTransactions'
import BillsWidget from './components/BillsWidget'
import TransactionModal from './components/TransactionModal'
import TransactionTable from './components/TransactionTable'
import ReceivableTable from './components/ReceivableTable'
import PayableTable from './components/PayableTable'
import PixConciliacao from './PixConciliacao'
import VasilhamesEstoque from './VasilhamesEstoque'
import FiadoPanel from './FiadoPanel'
import NotasFiscais from './NotasFiscais'
import DespesasPanel from '../../components/operator/DespesasPanel'
import PIXAsaasPanel from '../../components/operator/PIXAsaasPanel'
import EstoqueContagem from '../../components/EstoqueContagem'

// ── SVG Icons ──────────────────────────────────────────────
function IconWallet() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12V7H5a2 2 0 0 1 0-4h14v4" /><path d="M3 5v14a2 2 0 0 0 2 2h16v-5" /><path d="M18 12a2 2 0 0 0 0 4h4v-4Z" />
    </svg>
  )
}
function IconTrendingUp() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" /><polyline points="16 7 22 7 22 13" />
    </svg>
  )
}
function IconTrendingDown() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 17 13.5 8.5 8.5 13.5 2 7" /><polyline points="16 17 22 17 22 11" />
    </svg>
  )
}
function IconActivity() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  )
}
function IconAlertCircle() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  )
}
function IconPlus() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
      <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  )
}
function IconRefresh() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" /><path d="M21 3v5h-5" /><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" /><path d="M8 16H3v5" />
    </svg>
  )
}

// ── helpers ───────────────────────────────────────────────
function fmt(val) {
  const n = parseFloat(val) || 0
  return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}
function fmtK(val) {
  const n = parseFloat(val) || 0
  if (Math.abs(n) >= 1_000_000) return `R$ ${(n / 1_000_000).toFixed(2)}M`
  if (Math.abs(n) >= 1_000)     return `R$ ${(n / 1_000).toFixed(1)}k`
  return fmt(n)
}

// ── Card wrapper ──────────────────────────────────────────
function Card({ children, className = '' }) {
  return (
    <div className={`rounded-xl border border-gray-200 bg-white ${className}`}>
      {children}
    </div>
  )
}
function CardHeader({ title, description, action }) {
  return (
    <div className="flex items-start justify-between px-6 pt-6 pb-4">
      <div>
        <h3 className="text-base font-semibold text-gray-900">{title}</h3>
        {description && <p className="text-sm text-gray-400 mt-0.5">{description}</p>}
      </div>
      {action && <div className="ml-4 flex-shrink-0">{action}</div>}
    </div>
  )
}

// ── Contas Panel ─────────────────────────────────────────
const TIPO_LABELS = {
  conta_corrente: 'Conta Corrente',
  poupanca:       'Poupança',
  caixa:          'Caixa',
  cartao_credito: 'Cartão de Crédito',
  investimento:   'Investimento',
  outros:         'Outros',
}
const TIPO_ICONS = {
  conta_corrente: '🏦',
  poupanca:       '💰',
  caixa:          '🏧',
  cartao_credito: '💳',
  investimento:   '📈',
  outros:         '🗂️',
}

const EMPTY_CONTA = { name: '', type: 'conta_corrente', initial_balance: '', description: '', is_active: true }

function ContasPanel({ accounts, onRefresh }) {
  const [modal, setModal] = useState(null) // null | 'new' | account-obj
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState(EMPTY_CONTA)
  const token = localStorage.getItem('access_token')

  const openNew  = () => { setForm(EMPTY_CONTA); setModal('new') }
  const openEdit = (acc) => {
    setForm({ name: acc.name, type: acc.type || 'conta_corrente', initial_balance: acc.initial_balance ?? '', description: acc.description || '', is_active: acc.is_active })
    setModal(acc)
  }

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const save = async () => {
    if (!form.name.trim()) return toast?.error?.('Nome obrigatório')
    setSaving(true)
    try {
      const body = { ...form, initial_balance: parseFloat(form.initial_balance) || 0 }
      const isNew = modal === 'new'
      const url = isNew ? '/api/financeiro/accounts' : `/api/financeiro/accounts/${modal.id}`
      const res = await fetch(url, {
        method: isNew ? 'POST' : 'PUT',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) throw new Error()
      onRefresh()
      setModal(null)
    } catch {
      alert('Erro ao salvar conta')
    } finally {
      setSaving(false)
    }
  }

  const total = accounts.filter(a => a.is_active).reduce((s, a) => s + parseFloat(a.balance || 0), 0)
  const fmtC  = v => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(v || 0)

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Contas Cadastradas</h2>
          <p className="text-xs text-gray-400 mt-0.5">Gerencie contas bancárias, caixa e carteiras</p>
        </div>
        <button onClick={openNew}
          className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-gray-900 text-xs font-semibold text-white hover:bg-gray-700">
          <span className="text-base leading-none">+</span> Nova Conta
        </button>
      </div>

      {/* Saldo total */}
      <div className={`rounded-xl px-5 py-4 flex items-center justify-between ${total >= 0 ? 'bg-emerald-50 border border-emerald-200' : 'bg-red-50 border border-red-200'}`}>
        <div>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Saldo Total Consolidado</p>
          <p className={`text-2xl font-bold mt-0.5 ${total >= 0 ? 'text-emerald-700' : 'text-red-600'}`}>{fmtC(total)}</p>
        </div>
        <p className="text-xs text-gray-400">{accounts.filter(a => a.is_active).length} conta(s) ativa(s)</p>
      </div>

      {/* Cards */}
      {accounts.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-200 bg-white py-16 text-center">
          <p className="text-sm text-gray-400">Nenhuma conta cadastrada</p>
          <button onClick={openNew} className="mt-3 inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-gray-900 text-xs font-semibold text-white hover:bg-gray-700">
            + Criar conta
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {accounts.map(acc => {
            const bal = parseFloat(acc.balance || 0)
            const pct = total !== 0 ? Math.abs((bal / total) * 100).toFixed(0) : 0
            return (
              <div key={acc.id} className={`rounded-xl border bg-white p-5 flex flex-col gap-3 hover:shadow-md transition-shadow ${!acc.is_active ? 'opacity-60' : ''}`}>
                {/* Top row */}
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2.5">
                    <span className="text-2xl">{TIPO_ICONS[acc.type] || '🗂️'}</span>
                    <div>
                      <p className="text-sm font-semibold text-gray-900 leading-tight">{acc.name}</p>
                      <p className="text-xs text-gray-400">{TIPO_LABELS[acc.type] || acc.type?.replace(/_/g,' ')}</p>
                    </div>
                  </div>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold uppercase tracking-wider ${
                    acc.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-400'
                  }`}>{acc.is_active ? 'Ativa' : 'Inativa'}</span>
                </div>

                {/* Balance */}
                <div>
                  <p className={`text-2xl font-bold tracking-tight ${bal >= 0 ? 'text-gray-900' : 'text-red-500'}`}>
                    {fmtC(bal)}
                  </p>
                  <p className="text-xs text-gray-400 mt-0.5">Saldo inicial: {fmtC(acc.initial_balance)}</p>
                </div>

                {/* Share bar */}
                {total !== 0 && acc.is_active && (
                  <div>
                    <div className="flex justify-between text-[10px] text-gray-400 mb-1">
                      <span>Participação</span><span>{pct}%</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-gray-100 overflow-hidden">
                      <div className="h-full rounded-full bg-emerald-400" style={{ width: `${Math.min(pct, 100)}%` }} />
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-2 pt-1 border-t border-gray-100">
                  <button onClick={() => openEdit(acc)}
                    className="flex-1 rounded-lg border border-gray-200 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 transition-colors">
                    ✏️ Editar
                  </button>
                  <button onClick={() => { onRefresh(); alert('Extrato: em breve') }}
                    className="flex-1 rounded-lg border border-blue-200 bg-blue-50 py-1.5 text-xs font-medium text-blue-700 hover:bg-blue-100 transition-colors">
                    📋 Extrato
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Modal */}
      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl bg-white shadow-xl">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
              <h3 className="text-base font-semibold text-gray-900">
                {modal === 'new' ? 'Nova Conta' : 'Editar Conta'}
              </h3>
              <button onClick={() => setModal(null)} className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100">
                <span className="text-lg leading-none">×</span>
              </button>
            </div>
            <div className="px-6 py-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Nome da Conta *</label>
                <input value={form.name} onChange={e => set('name', e.target.value)}
                  placeholder="Ex: Bradesco Corrente, Caixa Loja…"
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-gray-400 focus:ring-1 focus:ring-gray-400 focus:outline-none" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Tipo</label>
                <select value={form.type} onChange={e => set('type', e.target.value)}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-gray-400 focus:outline-none">
                  {Object.entries(TIPO_LABELS).map(([v, l]) => (
                    <option key={v} value={v}>{TIPO_ICONS[v]} {l}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Saldo Inicial (R$)</label>
                <input type="number" step="0.01" value={form.initial_balance} onChange={e => set('initial_balance', e.target.value)}
                  placeholder="0,00"
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-gray-400 focus:outline-none" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Observação</label>
                <input value={form.description} onChange={e => set('description', e.target.value)}
                  placeholder="Banco, agência, finalidade…"
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-gray-400 focus:outline-none" />
              </div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={form.is_active} onChange={e => set('is_active', e.target.checked)}
                  className="rounded border-gray-300" />
                <span className="text-sm text-gray-700">Conta ativa</span>
              </label>
            </div>
            <div className="flex justify-end gap-2 px-6 py-4 border-t border-gray-100">
              <button onClick={() => setModal(null)} disabled={saving}
                className="px-4 py-2 rounded-lg border border-gray-200 text-sm font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-50">
                Cancelar
              </button>
              <button onClick={save} disabled={saving}
                className="px-4 py-2 rounded-lg bg-gray-900 text-sm font-medium text-white hover:bg-gray-700 disabled:opacity-50">
                {saving ? 'Salvando…' : modal === 'new' ? 'Criar Conta' : 'Salvar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Nav items (sidebar) ───────────────────────────────────
const NAV_ITEMS = [
  { key: 'overview',        label: 'Visão Geral' },
  { key: 'lancamentos',     label: 'Lançamentos' },
  { key: 'despesas',        label: 'Despesas' },
  {
    key: 'pix',
    label: 'PIX',
    type: 'group',
    children: [
      { key: 'conciliacao_pix', label: 'Conciliação PIX' },
      { key: 'pix_asaas',       label: 'PIX Asaas' },
    ],
  },
  { key: 'receber',         label: 'A Receber',      badge: 'overdue_receivables' },
  { key: 'pagar',           label: 'A Pagar',        badge: 'overdue_payables' },
  { key: 'fiado',           label: 'Fiado' },
  { key: 'lucratividade',   label: 'Lucratividade' },
  { key: 'contas',          label: 'Contas' },
  { key: 'notas_fiscais',   label: 'NF-e' },
]

// flat list of tab keys (for content rendering)
const TABS = NAV_ITEMS.flatMap(i => i.type === 'group' ? i.children : [i])

// ── Main component ────────────────────────────────────────
export default function FinanceiroDashboard() {
  const { user, logout } = useAuth()
  const [activeTab, setActiveTab] = useState('overview')
  const [pixOpen, setPixOpen] = useState(false)
  const [kpis, setKpis]           = useState(null)
  const [cashFlow, setCashFlow]   = useState(null)
  const [dre, setDre]             = useState(null)
  const [transactions, setTx]     = useState([])
  const [txTotal, setTxTotal]     = useState(0)
  const [txPage, setTxPage]       = useState(1)
  const [receivables, setRec]     = useState([])
  const [payables, setPay]        = useState([])
  const [accounts, setAcc]        = useState([])
  const [loading, setLoading]     = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [showContagem, setShowContagem] = useState(false)
  const [debtors, setDebtors]     = useState([])
  const [profits, setProfits]     = useState([])
  const [bairros, setBairros]     = useState([])
  const [expensive, setExpensive] = useState([])

  const loadAll = useCallback(async () => {
    setLoading(true)
    const now = new Date()
    const y = now.getFullYear()
    const m = String(now.getMonth() + 1).padStart(2, '0')
    const lastDay = new Date(y, now.getMonth() + 1, 0).getDate()
    const dreStart = `${y}-${m}-01`
    const dreEnd   = `${y}-${m}-${lastDay}`
    try {
      const [kpiR, cfR, dreR, accR, txR, recR, payR, debtR, profitR, bairroR, expR] = await Promise.all([
        api.get(FINANCEIRO.DASHBOARD).catch(() => ({ data: null })),
        api.get(FINANCEIRO.CASH_FLOW).catch(() => ({ data: null })),
        api.get(FINANCEIRO.DRE, { params: { start: dreStart, end: dreEnd } }).catch(() => ({ data: null })),
        api.get(FINANCEIRO.ACCOUNTS).catch(() => ({ data: [] })),
        api.get(FINANCEIRO.TRANSACTIONS, { params: { page: 1, per_page: 50 } }).catch(() => ({ data: { items: [], total: 0 } })),
        api.get(FINANCEIRO.RECEIVABLES).catch(() => ({ data: [] })),
        api.get(FINANCEIRO.PAYABLES).catch(() => ({ data: [] })),
        api.get(FINANCEIRO.CUSTOMERS_DEBT).catch(() => ({ data: [] })),
        api.get(FINANCEIRO.ORDERS_PROFIT, { params: { limit: 50 } }).catch(() => ({ data: [] })),
        api.get(FINANCEIRO.INSIGHTS_BAIRROS).catch(() => ({ data: [] })),
        api.get(FINANCEIRO.INSIGHTS_EXPENSIVE).catch(() => ({ data: [] })),
      ])
      setKpis(kpiR.data)
      setCashFlow(cfR.data)
      setDre(dreR.data)
      setAcc(accR.data || [])
      setTx(txR.data?.items || [])
      setTxTotal(txR.data?.total || 0)
      setRec(recR.data || [])
      setPay(payR.data || [])
      setDebtors(debtR.data || [])
      setProfits(profitR.data || [])
      setBairros(bairroR.data || [])
      setExpensive(expR.data || [])
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadAll() }, [loadAll])

  // WebSocket: atualizar painel quando Estoque altera vasilhames
  const wsRef = useRef(null)
  useEffect(() => {
    const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token')
    if (!token) return
    const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://192.168.10.167:5688'
    const wsUrl = API_BASE.replace('http', 'ws') + `/ws/dashboard?token=${token}`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        if (msg.type === 'vasilhame_update') loadAll()
      } catch {}
    }
    return () => ws.close()
  }, [loadAll])

  const handleTxPage = async (page) => {
    const r = await api.get(FINANCEIRO.TRANSACTIONS, { params: { page, per_page: 50 } })
    setTx(r.data?.items || [])
    setTxTotal(r.data?.total || 0)
    setTxPage(page)
  }

  const handleReceive = async (id) => { await api.post(FINANCEIRO.RECEIVABLE_RECEIVE(id)); loadAll() }
  const handlePay     = async (id) => { await api.post(FINANCEIRO.PAYABLE_PAY(id));     loadAll() }

  const profit       = kpis ? parseFloat(kpis.revenue_month || 0) - parseFloat(kpis.expense_month || 0) : 0
  const marginPct    = kpis?.revenue_month > 0 ? ((profit / parseFloat(kpis.revenue_month)) * 100).toFixed(1) : '0.0'
  const overdueCount = (kpis?.overdue_receivables || 0) + (kpis?.overdue_payables || 0)

  return (
    <div className="flex min-h-screen bg-gray-50 text-gray-900">
      {/* ── Sidebar (Desktop) ── */}
      <aside className="hidden w-64 flex-col bg-[#14283b] text-white md:flex flex-shrink-0 border-r border-[#14283b]">
        <div className="flex flex-col items-center justify-center p-6 border-b border-white/10">
          <img src="/logo_sistema.png" alt="Mercury Gas" className="h-[136px] object-contain max-w-full mb-6 brightness-0 invert opacity-90" />
          
          <div className="w-full bg-white/5 rounded-xl border border-white/10 p-4 text-center mb-4">
            <h2 className="text-[10px] font-bold text-white/50 tracking-widest uppercase mb-1">Operador Logado</h2>
            <p className="text-base font-bold text-white truncate w-full" title={user?.full_name || user?.username}>
              {user?.full_name || user?.username}
            </p>
            <span className="mt-2 inline-flex items-center rounded-full bg-[#f54e00]/20 px-2.5 py-0.5 text-xs font-medium text-[#f54e00] capitalize">
              {user?.role || 'Financeiro'}
            </span>
          </div>

          <button
            onClick={logout}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-red-500/10 px-4 py-2.5 text-sm font-semibold text-red-500 hover:bg-red-500/20 hover:text-red-400 transition-colors"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path><polyline points="16 17 21 12 16 7"></polyline><line x1="21" y1="12" x2="9" y2="12"></line></svg>
            Sair do Sistema
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto px-3 py-3">
          <nav className="space-y-0.5">
            {NAV_ITEMS.map(item => {
              if (item.type === 'group') {
                const hasActiveChild = item.children.some(c => c.key === activeTab)
                return (
                  <div key={item.key}>
                    <button
                      onClick={() => setPixOpen(v => !v)}
                      className={[
                        'w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors text-left',
                        hasActiveChild ? 'text-white font-medium' : 'text-white/60 hover:bg-white/10 hover:text-white',
                      ].join(' ')}
                    >
                      <span className="flex-1 truncate">{item.label}</span>
                      <svg className={`w-3.5 h-3.5 transition-transform duration-150 ${pixOpen || hasActiveChild ? 'rotate-90' : ''} text-white/30`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="9 18 15 12 9 6"/></svg>
                    </button>
                    {(pixOpen || hasActiveChild) && (
                      <div className="ml-3 mt-0.5 pl-3 border-l border-white/10 space-y-0.5">
                        {item.children.map(child => {
                          const isActive = activeTab === child.key
                          return (
                            <button
                              key={child.key}
                              onClick={() => setActiveTab(child.key)}
                              className={[
                                'w-full flex items-center px-3 py-2 rounded-lg text-sm transition-colors text-left',
                                isActive ? 'bg-white/15 text-white font-medium' : 'text-white/60 hover:bg-white/10 hover:text-white',
                              ].join(' ')}
                            >
                              {child.label}
                            </button>
                          )
                        })}
                      </div>
                    )}
                  </div>
                )
              }
              const badgeCount = item.badge ? (kpis?.[item.badge] || 0) : 0
              const isActive = activeTab === item.key
              return (
                <button
                  key={item.key}
                  onClick={() => setActiveTab(item.key)}
                  className={[
                    'w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors text-left',
                    isActive ? 'bg-white/15 text-white font-medium' : 'text-white/60 hover:bg-white/10 hover:text-white',
                  ].join(' ')}
                >
                  <span className="flex-1 truncate">{item.label}</span>
                  {badgeCount > 0 && (
                    <span className="inline-flex h-4 min-w-[16px] items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
                      {badgeCount}
                    </span>
                  )}
                </button>
              )
            })}
          </nav>
        </div>
      </aside>

      {/* ── Main Content ── */}
      <main className="flex-1 w-full overflow-y-auto">
        <div className="mx-auto max-w-screen-xl px-4 md:px-8 py-8">

        {/* ── Page header ─────────────────────────────────── */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-gray-900">Dashboard Financeiro</h1>
            <p className="text-sm text-gray-500 mt-1">
              Controle de caixa, receitas e despesas da distribuidora
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={loadAll}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-gray-200 bg-white text-gray-500 hover:text-gray-900 hover:border-gray-300 text-sm transition-colors"
            >
              <IconRefresh />
              Atualizar
            </button>
            <button
              onClick={() => setShowContagem(true)}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100 text-sm font-medium transition-colors"
              title="Contar estoque físico"
            >
              📦 Contar Estoque
            </button>
            <button
              onClick={() => setShowModal(true)}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-gray-900 text-white hover:bg-gray-800 text-sm font-medium transition-colors"
            >
              <IconPlus />
              Novo Lançamento
            </button>
          </div>
        </div>

        {/* ── Alert banner ────────────────────────────────── */}
        {!loading && overdueCount > 0 && (
          <div className="flex flex-wrap sm:flex-nowrap items-center gap-3 px-4 py-3 rounded-lg border border-red-200 bg-red-50 text-sm mb-6">
            <span className="text-red-500"><IconAlertCircle /></span>
            <span className="text-red-600 font-medium">Atenção:</span>
            <span className="text-red-500">
              {kpis?.overdue_receivables > 0 && `${kpis.overdue_receivables} recebível(is) vencido(s)`}
              {kpis?.overdue_receivables > 0 && kpis?.overdue_payables > 0 && ' · '}
              {kpis?.overdue_payables > 0 && `${kpis.overdue_payables} pagamento(s) vencido(s)`}
            </span>
            <button
              onClick={() => setActiveTab('receber')}
              className="ml-auto text-xs text-red-500 hover:text-red-700 underline underline-offset-2 transition-colors"
            >
              Ver detalhes
            </button>
          </div>
        )}


        {/* ══════════════════════════════════════════════════
            VISÃO GERAL
        ══════════════════════════════════════════════════ */}
        {activeTab === 'overview' && (
          <div className="space-y-6">

            {/* Stat cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <MetricCard
                title="Saldo Total"
                value={loading ? '—' : fmtK(kpis?.total_balance)}
                changeLabel={`${accounts.length} conta(s) ativa(s)`}
                icon={IconWallet}
                loading={loading}
              />
              <MetricCard
                title="Receita do Mês"
                value={loading ? '—' : fmtK(kpis?.revenue_month)}
                change={null}
                changeLabel={`Hoje: ${fmtK(kpis?.revenue_today || 0)}`}
                icon={IconTrendingUp}
                loading={loading}
              />
              <MetricCard
                title="Despesas do Mês"
                value={loading ? '—' : fmtK(kpis?.expense_month)}
                changeLabel={`Hoje: ${fmtK(kpis?.expense_today || 0)}`}
                icon={IconTrendingDown}
                loading={loading}
              />
              <MetricCard
                title="Lucro Líquido"
                value={loading ? '—' : fmtK(profit)}
                changeLabel={`Margem ${marginPct}%`}
                icon={IconActivity}
                loading={loading}
              />
            </div>

            {/* Secondary row */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { label: 'A Receber', value: fmtK(kpis?.pending_receivables_total || 0), sub: `${receivables.filter(r => r.status !== 'recebido').length} pendentes`, tab: 'receber' },
                { label: 'Recebíveis Vencidos', value: `${kpis?.overdue_receivables || 0}`, sub: 'contas em atraso', tab: 'receber', warn: (kpis?.overdue_receivables || 0) > 0 },
                { label: 'A Pagar', value: fmtK(kpis?.pending_payables_total || 0), sub: `${payables.filter(p => p.status !== 'pago').length} pendentes`, tab: 'pagar' },
                { label: 'Pagamentos Vencidos', value: `${kpis?.overdue_payables || 0}`, sub: 'contas em atraso', tab: 'pagar', warn: (kpis?.overdue_payables || 0) > 0 },
              ].map((s, i) => (
                <button
                  key={i}
                  onClick={() => setActiveTab(s.tab)}
                  className="rounded-xl border border-gray-200 bg-white p-4 text-left hover:border-gray-300 hover:shadow-sm transition-all"
                >
                  <p className="text-xs text-gray-500 mb-1.5">{s.label}</p>
                  <p className={`text-xl font-bold ${s.warn ? 'text-red-500' : 'text-gray-900'}`}>{s.value}</p>
                  <p className="text-xs text-gray-400 mt-1">{s.sub}</p>
                </button>
              ))}
            </div>

            {/* Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-7 gap-4">
              <Card className="lg:col-span-4">
                <CardHeader
                  title="Fluxo de Caixa"
                  description="Entradas e saídas — 15 dias reais + 15 dias projetados"
                />
                <div className="px-6 pb-6">
                  <CashFlowChart data={cashFlow?.days || []} />
                </div>
              </Card>

              <Card className="lg:col-span-3">
                <CardHeader
                  title="Despesas por Categoria"
                  description={dre?.period || 'Mês atual'}
                />
                <div className="px-6 pb-6">
                  {dre ? (
                    <>
                      <DREChart data={dre} />
                      <div className="mt-4 pt-4 border-t border-gray-100 grid grid-cols-1 sm:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x divide-gray-100 text-center gap-2 sm:gap-0">
                        <div className="pr-4">
                          <p className="text-xs text-gray-400 mb-1">Receita</p>
                          <p className="text-sm font-semibold text-emerald-600">{fmtK(dre.revenue)}</p>
                        </div>
                        <div className="px-4">
                          <p className="text-xs text-gray-400 mb-1">Despesa</p>
                          <p className="text-sm font-semibold text-gray-900">{fmtK(dre.total_expense)}</p>
                        </div>
                        <div className="pl-4">
                          <p className="text-xs text-gray-400 mb-1">Margem</p>
                          <p className={`text-sm font-semibold ${parseFloat(dre.margin_percent) >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                            {parseFloat(dre.margin_percent || 0).toFixed(1)}%
                          </p>
                        </div>
                      </div>
                    </>
                  ) : (
                    <div className="flex items-center justify-center h-52 text-sm text-gray-400">
                      Sem dados de DRE
                    </div>
                  )}
                </div>
              </Card>
            </div>

            {/* Bottom row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <Card>
                <CardHeader
                  title="Transações Recentes"
                  description="Últimos 8 lançamentos"
                  action={
                    <button
                      onClick={() => setActiveTab('lancamentos')}
                      className="text-xs text-gray-400 hover:text-gray-700 transition-colors"
                    >
                      Ver todos
                    </button>
                  }
                />
                <div className="px-6 pb-6">
                  <RecentTransactions transactions={transactions} />
                </div>
              </Card>

              <Card>
                <CardHeader
                  title="Contas Urgentes"
                  description="Vencidos e próximos 7 dias"
                  action={
                    <button
                      onClick={() => setActiveTab('pagar')}
                      className="text-xs text-gray-400 hover:text-gray-700 transition-colors"
                    >
                      Gerenciar
                    </button>
                  }
                />
                <div className="px-6 pb-6">
                  <BillsWidget
                    payables={payables}
                    receivables={receivables}
                    onPay={handlePay}
                    onReceive={handleReceive}
                  />
                </div>
              </Card>
            </div>
          </div>
        )}

        {/* ══════════════════════════════════════════════════
            LANÇAMENTOS
        ══════════════════════════════════════════════════ */}
        {activeTab === 'lancamentos' && (
          <Card>
            <CardHeader
              title="Lançamentos"
              description={`${txTotal} registros`}
              action={
                <button
                  onClick={() => setShowModal(true)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-900 text-white hover:bg-gray-800 text-sm font-medium transition-colors"
                >
                  <IconPlus /> Novo
                </button>
              }
            />
            <div className="px-6 pb-6">
              <TransactionTable
                transactions={transactions}
                total={txTotal}
                page={txPage}
                onPageChange={handleTxPage}
                fmt={fmt}
                onRefresh={() => { handleTxPage(1); loadAll() }}
              />
            </div>
          </Card>
        )}

        {/* ══════════════════════════════════════════════════
            A RECEBER
        ══════════════════════════════════════════════════ */}
        {activeTab === 'receber' && (
          <Card>
            <CardHeader
              title="Contas a Receber"
              description={`${receivables.filter(r => r.status !== 'recebido').length} pendentes`}
            />
            <div className="px-6 pb-6">
              <ReceivableTable receivables={receivables} onReceive={handleReceive} fmt={fmt} />
            </div>
          </Card>
        )}

        {/* ══════════════════════════════════════════════════
            A PAGAR
        ══════════════════════════════════════════════════ */}
        {activeTab === 'pagar' && (
          <Card>
            <CardHeader
              title="Contas a Pagar"
              description={`${payables.filter(p => p.status !== 'pago').length} pendentes`}
            />
            <div className="px-6 pb-6">
              <PayableTable payables={payables} onPay={handlePay} fmt={fmt} />
            </div>
          </Card>
        )}

        {/* ══════════════════════════════════════════════════
            FIADO — detalhamento e alertas
        ══════════════════════════════════════════════════ */}
        {activeTab === 'fiado' && <FiadoPanel />}

        {/* ══════════════════════════════════════════════════
            LUCRATIVIDADE — lucro por pedido
        ══════════════════════════════════════════════════ */}
        {activeTab === 'lucratividade' && (
          <Card>
            <CardHeader
              title="Lucratividade por Pedido"
              description={`${profits.length} pedido(s) calculado(s)`}
            />
            <div className="px-6 pb-6 overflow-x-auto w-full">
              {profits.length === 0 ? (
                <p className="py-12 text-center text-sm text-gray-400">
                  Nenhum cálculo disponível. Os dados são gerados automaticamente após cada entrega.
                </p>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200">
                      <th className="py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Pedido</th>
                      <th className="py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Bairro</th>
                      <th className="py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wide">Receita</th>
                      <th className="py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wide">CMV</th>
                      <th className="py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wide">Entrega</th>
                      <th className="py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wide">Lucro</th>
                      <th className="py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wide">Margem</th>
                    </tr>
                  </thead>
                  <tbody>
                    {profits.map((p, i) => (
                      <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
                        <td className="py-3 font-medium text-gray-900">#{p.order_number}</td>
                        <td className="py-3 text-gray-500">{p.bairro || '—'}</td>
                        <td className="py-3 text-right text-gray-900">{fmt(p.revenue)}</td>
                        <td className="py-3 text-right text-gray-500">{fmt(p.product_cost)}</td>
                        <td className="py-3 text-right text-gray-500">{fmt(p.delivery_cost)}</td>
                        <td className={`py-3 text-right font-semibold ${p.profit >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                          {fmt(p.profit)}
                        </td>
                        <td className="py-3 text-right">
                          <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${
                            p.margin_percentage >= 20
                              ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                              : p.margin_percentage >= 10
                              ? 'bg-amber-50 text-amber-700 border-amber-200'
                              : 'bg-red-50 text-red-600 border-red-200'
                          }`}>
                            {parseFloat(p.margin_percentage).toFixed(1)}%
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </Card>
        )}

        {/* ══════════════════════════════════════════════════
            INSIGHTS — bairros e rotas caras
        ══════════════════════════════════════════════════ */}
        {activeTab === 'insights' && (
          <div className="space-y-4">
            {/* Top bairros */}
            <Card>
              <CardHeader
                title="Top Bairros por Lucro"
                description="Bairros mais rentáveis para a operação"
              />
              <div className="px-6 pb-6 overflow-x-auto w-full">
                {bairros.length === 0 ? (
                  <p className="py-8 text-center text-sm text-gray-400">
                    Sem dados — gerado automaticamente após entregas calculadas
                  </p>
                ) : (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-200">
                        <th className="py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Bairro</th>
                        <th className="py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wide">Pedidos</th>
                        <th className="py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wide">Receita</th>
                        <th className="py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wide">Lucro</th>
                        <th className="py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wide">Margem média</th>
                      </tr>
                    </thead>
                    <tbody>
                      {bairros.map((b, i) => (
                        <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
                          <td className="py-3 font-medium text-gray-900 flex items-center gap-2">
                            <span className="text-xs text-gray-400 w-5">{i + 1}</span>
                            {b.bairro}
                          </td>
                          <td className="py-3 text-right text-gray-500">{b.total_orders}</td>
                          <td className="py-3 text-right text-gray-700">{fmtK(b.total_revenue)}</td>
                          <td className={`py-3 text-right font-semibold ${b.total_profit >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                            {fmtK(b.total_profit)}
                          </td>
                          <td className="py-3 text-right">
                            <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${
                              b.avg_margin >= 20 ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                              : b.avg_margin >= 10 ? 'bg-amber-50 text-amber-700 border-amber-200'
                              : 'bg-red-50 text-red-600 border-red-200'
                            }`}>
                              {parseFloat(b.avg_margin).toFixed(1)}%
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </Card>

            {/* Entregas mais caras */}
            <Card>
              <CardHeader
                title="Entregas com Maior Custo"
                description="Rotas menos eficientes — candidatas a revisão"
              />
              <div className="px-6 pb-6 overflow-x-auto w-full">
                {expensive.length === 0 ? (
                  <p className="py-8 text-center text-sm text-gray-400">Sem dados disponíveis</p>
                ) : (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-200">
                        <th className="py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Pedido</th>
                        <th className="py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Bairro</th>
                        <th className="py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wide">Receita</th>
                        <th className="py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wide">Custo total</th>
                        <th className="py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wide">Lucro</th>
                        <th className="py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wide">Margem</th>
                      </tr>
                    </thead>
                    <tbody>
                      {expensive.map((e, i) => (
                        <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
                          <td className="py-3 font-medium text-gray-900">#{e.order_number}</td>
                          <td className="py-3 text-gray-500">{e.bairro || '—'}</td>
                          <td className="py-3 text-right text-gray-700">{fmt(e.revenue)}</td>
                          <td className="py-3 text-right text-red-500 font-medium">{fmt(e.estimated_cost)}</td>
                          <td className={`py-3 text-right font-semibold ${e.profit >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                            {fmt(e.profit)}
                          </td>
                          <td className="py-3 text-right">
                            <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${
                              e.margin >= 20 ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                              : e.margin >= 10 ? 'bg-amber-50 text-amber-700 border-amber-200'
                              : 'bg-red-50 text-red-600 border-red-200'
                            }`}>
                              {parseFloat(e.margin).toFixed(1)}%
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </Card>
          </div>
        )}

        {/* ══════════════════════════════════════════════════
            CONTAS
        ══════════════════════════════════════════════════ */}
        {activeTab === 'contas' && (
          <ContasPanel accounts={accounts} onRefresh={loadAll} />
        )}

        {/* ══════════════════════════════════════════════════
            CONCILIAÇÃO PIX
        ══════════════════════════════════════════════════ */}
        {activeTab === 'conciliacao_pix' && <PixConciliacao />}

        {/* ══════════════════════════════════════════════════
            VASILHAMES
        ══════════════════════════════════════════════════ */}
        {activeTab === 'vasilhames' && <VasilhamesEstoque />}

        {/* ══════════════════════════════════════════════════
            NOTAS FISCAIS
        ══════════════════════════════════════════════════ */}
        {activeTab === 'notas_fiscais' && <NotasFiscais />}

        {/* DESPESAS OPERACIONAIS */}
        {activeTab === 'despesas' && <DespesasPanel />}

        {/* PIX ASAAS */}
        {activeTab === 'pix_asaas' && <PIXAsaasPanel />}

      </div>

      {/* ── Modal ─────────────────────────────────────────── */}
      {showModal && (
        <TransactionModal
          accounts={accounts}
          onClose={() => setShowModal(false)}
          onCreated={() => { setShowModal(false); loadAll() }}
        />
      )}
      {showContagem && (
        <EstoqueContagem
          onClose={() => setShowContagem(false)}
          onSaved={() => { setShowContagem(false); loadAll() }}
        />
      )}
      </main>
    </div>
  )
}
