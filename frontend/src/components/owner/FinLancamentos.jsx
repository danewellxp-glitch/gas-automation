/**
 * Financeiro › Lançamentos — Livro-caixa de movimentações financeiras
 * Exibe entradas (receitas) e saídas (despesas) em ordem cronológica.
 */

import { useState, useEffect } from 'react'
import {
  ArrowUpCircle, ArrowDownCircle, RefreshCw, Search,
  Filter, Download, AlertCircle, Calendar,
} from 'lucide-react'
import { apiRequest } from '../../utils/api'

const fmt = (v) =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 2 }).format(v || 0)

const TYPE_LABELS = {
  income:  { label: 'Entrada', color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-50 dark:bg-emerald-900/20' },
  expense: { label: 'Saída',   color: 'text-red-600 dark:text-red-400',          bg: 'bg-red-50 dark:bg-red-900/20' },
}

const CAT_COLORS = {
  'Venda':     'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  'PIX':       'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
  'Despesa':   'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  'Fiado':     'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  'Comissão':  'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400',
}

export default function FinLancamentos() {
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState('')
  const [items, setItems]       = useState([])
  const [search, setSearch]     = useState('')
  const [typeFilter, setType]   = useState('all')
  const [startDate, setStart]   = useState(() => {
    const d = new Date(); d.setDate(1); return d.toISOString().split('T')[0]
  })
  const [endDate, setEnd]       = useState(() => new Date().toISOString().split('T')[0])
  const [totals, setTotals]     = useState({ income: 0, expense: 0, balance: 0 })

  useEffect(() => { fetchLancamentos() }, [startDate, endDate])

  const fetchLancamentos = async () => {
    try {
      setLoading(true); setError('')
      const data = await apiRequest(`financial/lancamentos?start=${startDate}&end=${endDate}`)
      const list = Array.isArray(data) ? data : (data?.items || data?.lancamentos || [])
      setItems(list)
      const income  = list.filter(i => i.type === 'income').reduce((s, i)  => s + (i.value || i.amount || 0), 0)
      const expense = list.filter(i => i.type === 'expense').reduce((s, i) => s + (i.value || i.amount || 0), 0)
      setTotals({ income, expense, balance: income - expense })
    } catch (err) {
      // endpoint pode não existir ainda — usa orders como fallback
      try {
        const orders = await apiRequest(`orders?start_date=${startDate}&end_date=${endDate}`)
        const list = Array.isArray(orders) ? orders : (orders?.items || [])
        const mapped = list.map(o => ({
          id: o.id,
          date: o.created_at,
          description: `Pedido #${o.order_number || o.id} — ${o.customer_name || o.customer_phone || ''}`,
          category: o.payment_method === 'pix' || o.payment_method === 'pix_asaas' ? 'PIX' : 'Venda',
          type: 'income',
          value: o.total_price || o.total || 0,
          status: o.status,
          payment_method: o.payment_method,
        }))
        setItems(mapped)
        const income = mapped.reduce((s, i) => s + i.value, 0)
        setTotals({ income, expense: 0, balance: income })
      } catch {
        setError('Não foi possível carregar os lançamentos.')
        setItems([])
      }
    } finally {
      setLoading(false)
    }
  }

  const filtered = items.filter(i => {
    const matchType = typeFilter === 'all' || i.type === typeFilter
    const matchSearch = !search ||
      (i.description || '').toLowerCase().includes(search.toLowerCase()) ||
      (i.category || '').toLowerCase().includes(search.toLowerCase())
    return matchType && matchSearch
  })

  const handleExportCSV = () => {
    const header = 'Data,Descrição,Categoria,Tipo,Valor,Método\n'
    const rows = filtered.map(i =>
      `${new Date(i.date).toLocaleDateString('pt-BR')},"${i.description || ''}","${i.category || ''}",${i.type === 'income' ? 'Entrada' : 'Saída'},${(i.value || i.amount || 0).toFixed(2)},${i.payment_method || ''}`
    ).join('\n')
    const blob = new Blob([header + rows], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url
    a.download = `lancamentos_${startDate}_${endDate}.csv`
    a.click(); URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-5">

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Lançamentos</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Livro-caixa de entradas e saídas do período</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={handleExportCSV} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
            <Download className="w-3.5 h-3.5" /> Exportar CSV
          </button>
          <button onClick={fetchLancamentos} disabled={loading} className="p-1.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-500 hover:bg-gray-50 disabled:opacity-50">
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Filtros */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Data inicial</label>
            <input type="date" value={startDate} onChange={e => setStart(e.target.value)}
              className="w-full rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-primary-500" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Data final</label>
            <input type="date" value={endDate} onChange={e => setEnd(e.target.value)}
              className="w-full rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-primary-500" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Tipo</label>
            <div className="flex gap-1 bg-gray-100 dark:bg-gray-700 p-0.5 rounded-lg">
              {[{ v: 'all', l: 'Todos' }, { v: 'income', l: 'Entrada' }, { v: 'expense', l: 'Saída' }].map(({ v, l }) => (
                <button key={v} onClick={() => setType(v)}
                  className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-colors ${typeFilter === v ? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}`}>
                  {l}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Buscar</label>
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 w-3.5 h-3.5 text-gray-400" />
              <input type="text" placeholder="Descrição ou categoria..." value={search} onChange={e => setSearch(e.target.value)}
                className="w-full pl-8 pr-3 py-2 rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-primary-500" />
            </div>
          </div>
        </div>
      </div>

      {/* Totais */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Total Entradas', value: totals.income, color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-50 dark:bg-emerald-900/20', icon: ArrowUpCircle },
          { label: 'Total Saídas',   value: totals.expense, color: 'text-red-600 dark:text-red-400',          bg: 'bg-red-50 dark:bg-red-900/20',          icon: ArrowDownCircle },
          { label: 'Saldo',          value: totals.balance,  color: totals.balance >= 0 ? 'text-gray-900 dark:text-white' : 'text-red-600 dark:text-red-400', bg: 'bg-white dark:bg-gray-800', icon: Filter },
        ].map(({ label, value, color, bg, icon: Icon }) => (
          <div key={label} className={`${bg} border border-gray-200 dark:border-gray-700 rounded-xl p-4`}>
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">{label}</p>
            <p className={`mt-1 text-xl font-bold ${color}`}>{fmt(value)}</p>
          </div>
        ))}
      </div>

      {/* Tabela */}
      {error && (
        <div className="flex items-center gap-2 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl text-sm text-red-600 dark:text-red-400">
          <AlertCircle className="w-4 h-4 shrink-0" /> {error}
        </div>
      )}

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50">
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Data</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Descrição</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Categoria</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Tipo</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Valor</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {loading && items.length === 0 ? (
                [...Array(5)].map((_, i) => (
                  <tr key={i}>
                    {[...Array(5)].map((_, j) => (
                      <td key={j} className="px-4 py-3"><div className="h-4 bg-gray-100 dark:bg-gray-700 rounded animate-pulse" /></td>
                    ))}
                  </tr>
                ))
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-sm text-gray-400 dark:text-gray-500">
                    {search || typeFilter !== 'all' ? 'Nenhum lançamento encontrado com esses filtros.' : 'Nenhum lançamento no período.'}
                  </td>
                </tr>
              ) : (
                filtered.map((item, idx) => {
                  const t = TYPE_LABELS[item.type] || TYPE_LABELS.income
                  const catColor = CAT_COLORS[item.category] || 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
                  return (
                    <tr key={item.id || idx} className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                      <td className="px-4 py-3 text-gray-500 dark:text-gray-400 whitespace-nowrap">
                        <span className="flex items-center gap-1.5">
                          <Calendar className="w-3.5 h-3.5 shrink-0" />
                          {item.date ? new Date(item.date).toLocaleDateString('pt-BR') : '—'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-800 dark:text-gray-200 max-w-xs truncate">{item.description || '—'}</td>
                      <td className="px-4 py-3">
                        {item.category && (
                          <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${catColor}`}>
                            {item.category}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${t.bg} ${t.color}`}>
                          {item.type === 'income' ? <ArrowUpCircle className="w-3 h-3" /> : <ArrowDownCircle className="w-3 h-3" />}
                          {t.label}
                        </span>
                      </td>
                      <td className={`px-4 py-3 text-right font-semibold ${item.type === 'expense' ? 'text-red-600 dark:text-red-400' : 'text-emerald-600 dark:text-emerald-400'}`}>
                        {item.type === 'expense' ? '−' : '+'}{fmt(item.value || item.amount || 0)}
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
            {filtered.length > 0 && (
              <tfoot>
                <tr className="border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50">
                  <td colSpan={4} className="px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">{filtered.length} lançamentos</td>
                  <td className="px-4 py-3 text-right text-sm font-bold text-gray-900 dark:text-white">
                    {fmt(filtered.reduce((s, i) => s + (i.type === 'expense' ? -(i.value||0) : (i.value||0)), 0))}
                  </td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      </div>

    </div>
  )
}
