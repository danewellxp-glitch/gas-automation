/**
 * Financeiro › PIX — Transações PIX recebidas (não Asaas, direto)
 */

import { useState, useEffect } from 'react'
import { QrCode, RefreshCw, Download, CheckCircle, Clock, XCircle, AlertCircle } from 'lucide-react'
import { apiRequest } from '../../utils/api'

const fmt = (v) =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 2 }).format(v || 0)

const STATUS = {
  paid:     { label: 'Pago',       color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-50 dark:bg-emerald-900/20', icon: CheckCircle },
  pending:  { label: 'Pendente',   color: 'text-amber-600 dark:text-amber-400',     bg: 'bg-amber-50 dark:bg-amber-900/20',     icon: Clock },
  failed:   { label: 'Falhou',     color: 'text-red-600 dark:text-red-400',          bg: 'bg-red-50 dark:bg-red-900/20',          icon: XCircle },
  received: { label: 'Recebido',   color: 'text-blue-600 dark:text-blue-400',        bg: 'bg-blue-50 dark:bg-blue-900/20',        icon: CheckCircle },
}

export default function FinPIX() {
  const [loading, setLoading] = useState(true)
  const [items, setItems]     = useState([])
  const [error, setError]     = useState('')
  const [startDate, setStart] = useState(() => { const d = new Date(); d.setDate(1); return d.toISOString().split('T')[0] })
  const [endDate, setEnd]     = useState(() => new Date().toISOString().split('T')[0])
  const [totals, setTotals]   = useState({ total: 0, count: 0 })

  useEffect(() => { fetch() }, [startDate, endDate])

  const fetch = async () => {
    try {
      setLoading(true); setError('')
      // Tenta endpoint dedicado
      const data = await apiRequest(`financial/pix?start=${startDate}&end=${endDate}`)
      const list = Array.isArray(data) ? data : (data?.items || data?.transactions || [])
      setItems(list)
      const total = list.filter(i => i.status === 'paid' || i.status === 'received').reduce((s, i) => s + (i.amount || i.value || 0), 0)
      setTotals({ total, count: list.length })
    } catch {
      // fallback: orders com payment_method=pix
      try {
        const orders = await apiRequest(`orders?payment_method=pix&start_date=${startDate}&end_date=${endDate}`)
        const list = Array.isArray(orders) ? orders : (orders?.items || [])
        const mapped = list.map(o => ({
          id: o.id,
          created_at: o.created_at,
          description: `Pedido #${o.order_number || o.id}`,
          payer: o.customer_name || o.customer_phone || '—',
          amount: o.total_price || o.total || 0,
          status: o.status === 'delivered' ? 'paid' : o.status === 'cancelled' ? 'failed' : 'pending',
          key_type: 'telefone',
        }))
        setItems(mapped)
        const total = mapped.filter(i => i.status === 'paid').reduce((s, i) => s + i.amount, 0)
        setTotals({ total, count: mapped.length })
      } catch (e2) {
        setError('Sem dados PIX disponíveis.'); setItems([])
      }
    } finally { setLoading(false) }
  }

  const handleExport = () => {
    const header = 'Data,Descrição,Pagador,Valor,Status,Chave\n'
    const rows = items.map(i =>
      `${new Date(i.created_at).toLocaleDateString('pt-BR')},"${i.description||''}","${i.payer||''}",${(i.amount||i.value||0).toFixed(2)},${i.status||''},${i.key_type||''}`
    ).join('\n')
    const blob = new Blob([header + rows], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url; a.download = `pix_${startDate}_${endDate}.csv`
    a.click(); URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-5">

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">PIX</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Transações PIX recebidas no período</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={handleExport} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 transition-colors">
            <Download className="w-3.5 h-3.5" /> CSV
          </button>
          <button onClick={fetch} disabled={loading} className="p-1.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-500 hover:bg-gray-50 disabled:opacity-50">
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Date filter */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <div className="grid grid-cols-2 gap-3 max-w-sm">
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">De</label>
            <input type="date" value={startDate} onChange={e => setStart(e.target.value)}
              className="w-full rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-primary-500" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Até</label>
            <input type="date" value={endDate} onChange={e => setEnd(e.target.value)}
              className="w-full rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-primary-500" />
          </div>
        </div>
      </div>

      {/* Totais */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        {[
          { label: 'Total recebido', value: fmt(totals.total), sub: `${totals.count} transações`, icon: QrCode, bg: 'bg-emerald-50 dark:bg-emerald-900/20', color: 'text-emerald-600 dark:text-emerald-400' },
          { label: 'Pagas', value: items.filter(i => i.status === 'paid' || i.status === 'received').length, sub: 'confirmadas', icon: CheckCircle, bg: 'bg-blue-50 dark:bg-blue-900/20', color: 'text-blue-600 dark:text-blue-400' },
          { label: 'Pendentes', value: items.filter(i => i.status === 'pending').length, sub: 'aguardando', icon: Clock, bg: 'bg-amber-50 dark:bg-amber-900/20', color: 'text-amber-600 dark:text-amber-400' },
        ].map(({ label, value, sub, icon: Icon, bg, color }) => (
          <div key={label} className={`${bg} border border-gray-200 dark:border-gray-700 rounded-xl p-4`}>
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">{label}</p>
                <p className={`mt-1 text-2xl font-bold ${color}`}>{value}</p>
                <p className="mt-0.5 text-xs text-gray-400 dark:text-gray-500">{sub}</p>
              </div>
              <Icon className={`w-5 h-5 shrink-0 mt-0.5 ${color}`} />
            </div>
          </div>
        ))}
      </div>

      {error && (
        <div className="flex items-center gap-2 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl text-sm text-amber-700 dark:text-amber-400">
          <AlertCircle className="w-4 h-4 shrink-0" /> {error}
        </div>
      )}

      {/* Tabela */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50">
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Data/Hora</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Descrição</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Pagador</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Status</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Valor</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {loading && items.length === 0 ? (
                [...Array(5)].map((_, i) => (
                  <tr key={i}>{[...Array(5)].map((_, j) => (
                    <td key={j} className="px-4 py-3"><div className="h-4 bg-gray-100 dark:bg-gray-700 rounded animate-pulse" /></td>
                  ))}</tr>
                ))
              ) : items.length === 0 ? (
                <tr><td colSpan={5} className="px-4 py-10 text-center text-sm text-gray-400 dark:text-gray-500">Nenhuma transação PIX no período.</td></tr>
              ) : (
                items.map((item, idx) => {
                  const st = STATUS[item.status] || STATUS.pending
                  const StIcon = st.icon
                  return (
                    <tr key={item.id || idx} className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                      <td className="px-4 py-3 text-gray-500 dark:text-gray-400 whitespace-nowrap text-xs">
                        {item.created_at ? new Date(item.created_at).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—'}
                      </td>
                      <td className="px-4 py-3 text-gray-800 dark:text-gray-200">{item.description || `PIX #${item.id}`}</td>
                      <td className="px-4 py-3 text-gray-600 dark:text-gray-400">{item.payer || '—'}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${st.bg} ${st.color}`}>
                          <StIcon className="w-3 h-3" /> {st.label}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right font-semibold text-emerald-600 dark:text-emerald-400">
                        {fmt(item.amount || item.value || 0)}
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
            {items.length > 0 && (
              <tfoot>
                <tr className="border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50">
                  <td colSpan={4} className="px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400">{items.length} transações</td>
                  <td className="px-4 py-3 text-right text-sm font-bold text-emerald-600 dark:text-emerald-400">{fmt(totals.total)}</td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      </div>

    </div>
  )
}
