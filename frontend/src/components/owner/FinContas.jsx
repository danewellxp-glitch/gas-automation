/**
 * Financeiro › Contas — Caixas e contas bancárias
 */

import { useState, useEffect } from 'react'
import { Landmark, RefreshCw, Plus, AlertCircle, TrendingUp, Banknote, CreditCard, Smartphone, X } from 'lucide-react'
import { apiRequest } from '../../utils/api'

const fmt = (v) =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 2 }).format(v || 0)

const ACCOUNT_ICONS = {
  cash:   Banknote,
  bank:   Landmark,
  pix:    Smartphone,
  card:   CreditCard,
}

const ACCOUNT_COLORS = {
  cash:   { bg: 'bg-emerald-50 dark:bg-emerald-900/20', color: 'text-emerald-600 dark:text-emerald-400', border: 'border-emerald-200 dark:border-emerald-800' },
  bank:   { bg: 'bg-blue-50 dark:bg-blue-900/20',       color: 'text-blue-600 dark:text-blue-400',       border: 'border-blue-200 dark:border-blue-800' },
  pix:    { bg: 'bg-violet-50 dark:bg-violet-900/20',   color: 'text-violet-600 dark:text-violet-400',   border: 'border-violet-200 dark:border-violet-800' },
  card:   { bg: 'bg-amber-50 dark:bg-amber-900/20',     color: 'text-amber-600 dark:text-amber-400',     border: 'border-amber-200 dark:border-amber-800' },
}

const DEFAULT_ACCOUNTS = [
  { id: 1, name: 'Caixa Físico', type: 'cash',   balance: 0, description: 'Dinheiro em espécie no caixa' },
  { id: 2, name: 'Conta Bancária', type: 'bank', balance: 0, description: 'Conta corrente principal' },
  { id: 3, name: 'Recebimentos PIX', type: 'pix', balance: 0, description: 'Saldo PIX disponível' },
]

export default function FinContas() {
  const [loading, setLoading] = useState(true)
  const [accounts, setAccounts] = useState([])
  const [error, setError]       = useState('')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', type: 'cash', balance: '', description: '' })

  useEffect(() => { fetchData() }, [])

  const fetchData = async () => {
    try {
      setLoading(true); setError('')
      const data = await apiRequest('financial/accounts')
      setAccounts(Array.isArray(data) ? data : (data?.items || data?.accounts || DEFAULT_ACCOUNTS))
    } catch {
      // endpoint não existe ainda — usa dados do dashboard como base
      try {
        const dash = await apiRequest('owner/dashboard?period=day')
        const pix = dash?.pix_today?.total || 0
        const revenue = dash?.cards?.financial?.revenue_today || 0
        setAccounts([
          { id: 1, name: 'Caixa Físico', type: 'cash', balance: 0, description: 'Saldo a confirmar' },
          { id: 2, name: 'Recebimentos PIX (hoje)', type: 'pix', balance: pix, description: 'PIX recebido hoje' },
          { id: 3, name: 'Total Faturado (hoje)', type: 'bank', balance: revenue, description: 'Faturamento do dia' },
        ])
      } catch {
        setAccounts(DEFAULT_ACCOUNTS)
        setError('Configure suas contas para controle preciso de saldo.')
      }
    } finally { setLoading(false) }
  }

  const total = accounts.reduce((s, a) => s + (a.balance || 0), 0)

  return (
    <div className="space-y-5">

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Contas</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Caixas, contas bancárias e saldos disponíveis</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setShowForm(v => !v)} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary-600 text-white text-xs font-medium hover:bg-primary-700 transition-colors">
            <Plus className="w-3.5 h-3.5" /> Nova conta
          </button>
          <button onClick={fetchData} disabled={loading} className="p-1.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-500 hover:bg-gray-50 disabled:opacity-50">
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Saldo total */}
      <div className="bg-gradient-to-br from-primary-600 to-primary-700 rounded-xl p-6 text-white">
        <p className="text-sm font-medium text-white/70">Saldo Total em Caixa</p>
        <p className="mt-1 text-4xl font-bold tracking-tight">{fmt(total)}</p>
        <p className="mt-2 text-sm text-white/60">{accounts.length} conta{accounts.length !== 1 ? 's' : ''} cadastrada{accounts.length !== 1 ? 's' : ''}</p>
      </div>

      {/* Form */}
      {showForm && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-primary-200 dark:border-primary-800 p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Nova Conta</h3>
            <button onClick={() => setShowForm(false)} className="text-gray-400 hover:text-gray-600"><X className="w-4 h-4" /></button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {[
              { k: 'name', label: 'Nome da conta', type: 'text', placeholder: 'Ex: Caixa 01' },
              { k: 'balance', label: 'Saldo inicial (R$)', type: 'number', placeholder: '0,00' },
            ].map(({ k, label, type, placeholder }) => (
              <div key={k}>
                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">{label}</label>
                <input type={type} placeholder={placeholder} value={form[k]} onChange={e => setForm(p => ({ ...p, [k]: e.target.value }))}
                  className="w-full rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-primary-500" />
              </div>
            ))}
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Tipo</label>
              <select value={form.type} onChange={e => setForm(p => ({ ...p, type: e.target.value }))}
                className="w-full rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-primary-500">
                <option value="cash">Caixa físico</option>
                <option value="bank">Conta bancária</option>
                <option value="pix">PIX</option>
                <option value="card">Máquina de cartão</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Descrição</label>
              <input type="text" placeholder="Observação..." value={form.description} onChange={e => setForm(p => ({ ...p, description: e.target.value }))}
                className="w-full rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-primary-500" />
            </div>
          </div>
          <div className="mt-4 flex justify-end gap-2">
            <button onClick={() => setShowForm(false)} className="px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-800 transition-colors">Cancelar</button>
            <button className="px-4 py-2 bg-primary-600 text-white text-sm font-medium rounded-lg hover:bg-primary-700 transition-colors">Salvar</button>
          </div>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl text-sm text-amber-700 dark:text-amber-400">
          <AlertCircle className="w-4 h-4 shrink-0" /> {error}
        </div>
      )}

      {/* Cards de contas */}
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => <div key={i} className="h-36 bg-gray-100 dark:bg-gray-700 rounded-xl animate-pulse" />)}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {accounts.map((acc) => {
            const style = ACCOUNT_COLORS[acc.type] || ACCOUNT_COLORS.bank
            const Icon = ACCOUNT_ICONS[acc.type] || Landmark
            const pct = total > 0 ? (acc.balance / total) * 100 : 0
            return (
              <div key={acc.id} className={`bg-white dark:bg-gray-800 rounded-xl border ${style.border} p-5`}>
                <div className="flex items-start justify-between gap-3 mb-4">
                  <div className={`w-10 h-10 rounded-lg ${style.bg} flex items-center justify-center shrink-0`}>
                    <Icon className={`w-5 h-5 ${style.color}`} />
                  </div>
                  <div className="text-right">
                    <p className={`text-xl font-bold ${style.color}`}>{fmt(acc.balance || 0)}</p>
                    <p className="text-xs text-gray-400 mt-0.5">{pct.toFixed(1)}% do total</p>
                  </div>
                </div>
                <p className="text-sm font-semibold text-gray-800 dark:text-gray-200">{acc.name}</p>
                {acc.description && <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">{acc.description}</p>}
                <div className="mt-3 h-1 w-full rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
                  <div className={`h-full rounded-full ${style.color.replace('text-', 'bg-').replace('-600', '-500').replace('-400', '-500')}`} style={{ width: `${pct}%` }} />
                </div>
              </div>
            )
          })}
        </div>
      )}

    </div>
  )
}
