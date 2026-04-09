/**
 * Financeiro › A Receber — Pedidos pendentes de pagamento
 */

import { useState, useEffect } from 'react'
import { ArrowDownCircle, RefreshCw, Download, Phone, AlertCircle, Clock } from 'lucide-react'
import { apiRequest } from '../../utils/api'

const fmt = (v) =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 2 }).format(v || 0)

const METHODS = {
  pix:       'PIX',
  pix_asaas: 'PIX Asaas',
  money:     'Dinheiro',
  fiado:     'Fiado',
  card:      'Cartão',
}

function daysDiff(dateStr) {
  if (!dateStr) return 0
  const diff = Date.now() - new Date(dateStr).getTime()
  return Math.floor(diff / 86400000)
}

export default function FinAReceber() {
  const [loading, setLoading] = useState(true)
  const [items, setItems]     = useState([])
  const [error, setError]     = useState('')

  useEffect(() => { fetchData() }, [])

  const fetchData = async () => {
    try {
      setLoading(true); setError('')
      // Busca orders pendentes de pagamento
      const data = await apiRequest('orders?status=pending,approved,in_delivery')
      const list = Array.isArray(data) ? data : (data?.items || data?.orders || [])
      // Filtra apenas as que têm valor a receber (não entregues / não pagas)
      setItems(list.filter(o => o.status !== 'delivered' && o.status !== 'cancelled'))
    } catch (err) {
      setError(err.message || 'Erro ao carregar contas a receber.')
      setItems([])
    } finally { setLoading(false) }
  }

  const total = items.reduce((s, i) => s + (i.total_price || i.total || 0), 0)
  const overdue = items.filter(i => daysDiff(i.created_at) > 1).length

  const handleExport = () => {
    const header = 'Data,Pedido,Cliente,Telefone,Método,Valor,Dias\n'
    const rows = items.map(i =>
      `${new Date(i.created_at).toLocaleDateString('pt-BR')},#${i.order_number||i.id},"${i.customer_name||''}","${i.customer_phone||''}","${METHODS[i.payment_method]||i.payment_method||''}",${(i.total_price||i.total||0).toFixed(2)},${daysDiff(i.created_at)}`
    ).join('\n')
    const blob = new Blob([header + rows], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url
    a.download = 'a_receber.csv'; a.click(); URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-5">

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">A Receber</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Pedidos aguardando pagamento ou em aberto</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={handleExport} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 transition-colors">
            <Download className="w-3.5 h-3.5" /> CSV
          </button>
          <button onClick={fetchData} disabled={loading} className="p-1.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-500 hover:bg-gray-50 disabled:opacity-50">
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-gray-200 dark:border-gray-700 rounded-xl p-4">
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Total a Receber</p>
          <p className="mt-1 text-2xl font-bold text-blue-600 dark:text-blue-400">{fmt(total)}</p>
          <p className="mt-0.5 text-xs text-gray-400">{items.length} pedidos</p>
        </div>
        <div className="bg-red-50 dark:bg-red-900/20 border border-gray-200 dark:border-gray-700 rounded-xl p-4">
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Em Atraso</p>
          <p className="mt-1 text-2xl font-bold text-red-600 dark:text-red-400">{overdue}</p>
          <p className="mt-0.5 text-xs text-gray-400">+ de 1 dia</p>
        </div>
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4">
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Ticket Médio</p>
          <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">{fmt(items.length ? total / items.length : 0)}</p>
          <p className="mt-0.5 text-xs text-gray-400">por pedido</p>
        </div>
      </div>

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
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Pedido</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Cliente</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Método</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Dias</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Valor</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {loading ? (
                [...Array(5)].map((_, i) => (
                  <tr key={i}>{[...Array(6)].map((_, j) => (
                    <td key={j} className="px-4 py-3"><div className="h-4 bg-gray-100 dark:bg-gray-700 rounded animate-pulse" /></td>
                  ))}</tr>
                ))
              ) : items.length === 0 ? (
                <tr><td colSpan={6} className="px-4 py-10 text-center text-sm text-gray-400 dark:text-gray-500">
                  Sem contas a receber no momento.
                </td></tr>
              ) : (
                items.map((item, idx) => {
                  const days = daysDiff(item.created_at)
                  return (
                    <tr key={item.id || idx} className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                      <td className="px-4 py-3 text-gray-500 dark:text-gray-400 text-xs whitespace-nowrap">
                        {item.created_at ? new Date(item.created_at).toLocaleDateString('pt-BR') : '—'}
                      </td>
                      <td className="px-4 py-3 font-medium text-gray-800 dark:text-gray-200">
                        #{item.order_number || item.id}
                      </td>
                      <td className="px-4 py-3">
                        <div>
                          <p className="text-gray-800 dark:text-gray-200">{item.customer_name || '—'}</p>
                          {item.customer_phone && (
                            <p className="text-xs text-gray-400 flex items-center gap-1 mt-0.5">
                              <Phone className="w-3 h-3" />{item.customer_phone}
                            </p>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400">
                          {METHODS[item.payment_method] || item.payment_method || '—'}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1 text-xs font-medium ${days > 1 ? 'text-red-600 dark:text-red-400' : 'text-gray-500 dark:text-gray-400'}`}>
                          {days > 0 && <Clock className="w-3 h-3" />}
                          {days === 0 ? 'Hoje' : `${days}d`}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right font-semibold text-blue-600 dark:text-blue-400">
                        {fmt(item.total_price || item.total || 0)}
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
            {items.length > 0 && (
              <tfoot>
                <tr className="border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50">
                  <td colSpan={5} className="px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400">{items.length} registros</td>
                  <td className="px-4 py-3 text-right text-sm font-bold text-blue-600 dark:text-blue-400">{fmt(total)}</td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      </div>

    </div>
  )
}
