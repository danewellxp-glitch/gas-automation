/**
 * Operação › Pedidos — Todos os pedidos com filtros avançados
 */

import { useState, useEffect } from 'react'
import { ShoppingCart, RefreshCw, Search, Download, Phone, MapPin, AlertCircle } from 'lucide-react'
import { apiRequest } from '../../utils/api'

const fmt = (v) =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 2 }).format(v || 0)

const STATUS_CONFIG = {
  pending:    { label: 'Pendente',      bg: 'bg-amber-50 dark:bg-amber-900/20',    color: 'text-amber-700 dark:text-amber-400' },
  approved:   { label: 'Aprovado',      bg: 'bg-blue-50 dark:bg-blue-900/20',      color: 'text-blue-700 dark:text-blue-400' },
  in_delivery:{ label: 'Em Entrega',    bg: 'bg-violet-50 dark:bg-violet-900/20',  color: 'text-violet-700 dark:text-violet-400' },
  delivered:  { label: 'Entregue',      bg: 'bg-emerald-50 dark:bg-emerald-900/20',color: 'text-emerald-700 dark:text-emerald-400' },
  cancelled:  { label: 'Cancelado',     bg: 'bg-red-50 dark:bg-red-900/20',        color: 'text-red-700 dark:text-red-400' },
  paid:       { label: 'Pago',          bg: 'bg-emerald-50 dark:bg-emerald-900/20',color: 'text-emerald-700 dark:text-emerald-400' },
}

const PAYMENT_LABELS = {
  pix: 'PIX', pix_asaas: 'PIX Asaas', money: 'Dinheiro', fiado: 'Fiado', card: 'Cartão',
}

export default function OpPedidos() {
  const [loading, setLoading] = useState(true)
  const [orders, setOrders]   = useState([])
  const [error, setError]     = useState('')
  const [search, setSearch]   = useState('')
  const [statusFilter, setStatus] = useState('all')
  const [period, setPeriod]   = useState('today')

  useEffect(() => { fetchOrders() }, [period])

  const fetchOrders = async () => {
    try {
      setLoading(true); setError('')
      let endpoint = 'orders'
      if (period === 'today') endpoint = 'orders/today'
      else if (period === 'week') endpoint = 'orders?days=7'
      else if (period === 'month') endpoint = 'orders?days=30'
      const data = await apiRequest(endpoint)
      setOrders(Array.isArray(data) ? data : (data?.items || data?.orders || []))
    } catch (err) {
      setError(err.message || 'Erro ao carregar pedidos')
      setOrders([])
    } finally { setLoading(false) }
  }

  const filtered = orders.filter(o => {
    const matchStatus = statusFilter === 'all' || o.status === statusFilter
    const q = search.toLowerCase()
    const matchSearch = !search ||
      (o.customer_name || '').toLowerCase().includes(q) ||
      (o.customer_phone || '').includes(q) ||
      String(o.order_number || o.id).includes(q)
    return matchStatus && matchSearch
  })

  const handleExport = () => {
    const header = 'Data,Pedido,Cliente,Telefone,Status,Pagamento,Total\n'
    const rows = filtered.map(o =>
      `${new Date(o.created_at).toLocaleDateString('pt-BR')},#${o.order_number||o.id},"${o.customer_name||''}","${o.customer_phone||''}","${STATUS_CONFIG[o.status]?.label||o.status||''}","${PAYMENT_LABELS[o.payment_method]||o.payment_method||''}",${(o.total_price||o.total||0).toFixed(2)}`
    ).join('\n')
    const blob = new Blob([header + rows], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url
    a.download = `pedidos_${period}.csv`; a.click(); URL.revokeObjectURL(url)
  }

  const totalValue = filtered.reduce((s, o) => s + (o.total_price || o.total || 0), 0)

  return (
    <div className="space-y-5">

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Pedidos</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Todos os pedidos com filtros por período e status</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={handleExport} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 transition-colors">
            <Download className="w-3.5 h-3.5" /> CSV
          </button>
          <button onClick={fetchOrders} disabled={loading} className="p-1.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-500 hover:bg-gray-50 disabled:opacity-50">
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Filtros */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex flex-col sm:flex-row gap-3">
          {/* Período */}
          <div className="flex bg-gray-100 dark:bg-gray-700 rounded-lg p-0.5 gap-1">
            {[{ v: 'today', l: 'Hoje' }, { v: 'week', l: '7 dias' }, { v: 'month', l: '30 dias' }, { v: 'all', l: 'Todos' }].map(({ v, l }) => (
              <button key={v} onClick={() => setPeriod(v)}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${period === v ? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}`}>
                {l}
              </button>
            ))}
          </div>
          {/* Status */}
          <select value={statusFilter} onChange={e => setStatus(e.target.value)}
            className="rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-primary-500">
            <option value="all">Todos os status</option>
            {Object.entries(STATUS_CONFIG).map(([v, { label }]) => <option key={v} value={v}>{label}</option>)}
          </select>
          {/* Busca */}
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-2.5 w-3.5 h-3.5 text-gray-400" />
            <input type="text" placeholder="Buscar por nome, telefone ou nº..." value={search} onChange={e => setSearch(e.target.value)}
              className="w-full pl-8 pr-3 py-2 rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-primary-500" />
          </div>
        </div>
      </div>

      {/* Stats rápidas */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Total filtrado', value: filtered.length, sub: 'pedidos' },
          { label: 'Entregues', value: filtered.filter(o => o.status === 'delivered').length, sub: 'concluídos' },
          { label: 'Em andamento', value: filtered.filter(o => ['approved','in_delivery'].includes(o.status)).length, sub: 'ativos' },
          { label: 'Valor total', value: fmt(totalValue), sub: 'faturado' },
        ].map(({ label, value, sub }) => (
          <div key={label} className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">{label}</p>
            <p className="mt-1 text-xl font-bold text-gray-900 dark:text-white">{value}</p>
            <p className="text-xs text-gray-400 mt-0.5">{sub}</p>
          </div>
        ))}
      </div>

      {error && (
        <div className="flex items-center gap-2 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl text-sm text-red-600 dark:text-red-400">
          <AlertCircle className="w-4 h-4 shrink-0" /> {error}
        </div>
      )}

      {/* Tabela */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50">
                {['Pedido', 'Data/Hora', 'Cliente', 'Endereço', 'Status', 'Pagamento', 'Total'].map((h, i) => (
                  <th key={h} className={`px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide ${i === 6 ? 'text-right' : 'text-left'}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {loading && orders.length === 0 ? (
                [...Array(6)].map((_, i) => (
                  <tr key={i}>{[...Array(7)].map((_, j) => (
                    <td key={j} className="px-4 py-3"><div className="h-4 bg-gray-100 dark:bg-gray-700 rounded animate-pulse" /></td>
                  ))}</tr>
                ))
              ) : filtered.length === 0 ? (
                <tr><td colSpan={7} className="px-4 py-12 text-center">
                  <ShoppingCart className="mx-auto w-8 h-8 text-gray-300 dark:text-gray-600 mb-2" />
                  <p className="text-sm text-gray-400 dark:text-gray-500">Nenhum pedido encontrado.</p>
                </td></tr>
              ) : (
                filtered.map((order) => {
                  const st = STATUS_CONFIG[order.status] || { label: order.status, bg: 'bg-gray-50', color: 'text-gray-600' }
                  return (
                    <tr key={order.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                      <td className="px-4 py-3 font-semibold text-gray-800 dark:text-gray-200 whitespace-nowrap">
                        #{order.order_number || order.id}
                      </td>
                      <td className="px-4 py-3 text-gray-500 dark:text-gray-400 text-xs whitespace-nowrap">
                        {order.created_at ? new Date(order.created_at).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—'}
                      </td>
                      <td className="px-4 py-3">
                        <div>
                          <p className="text-gray-800 dark:text-gray-200 font-medium">{order.customer_name || '—'}</p>
                          {order.customer_phone && (
                            <p className="text-xs text-gray-400 flex items-center gap-1 mt-0.5">
                              <Phone className="w-3 h-3" />{order.customer_phone}
                            </p>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 max-w-xs">
                        {order.address ? (
                          <p className="text-xs text-gray-500 dark:text-gray-400 truncate flex items-center gap-1">
                            <MapPin className="w-3 h-3 shrink-0" />{order.address}
                          </p>
                        ) : <span className="text-gray-400">—</span>}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${st.bg} ${st.color}`}>{st.label}</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400">
                          {PAYMENT_LABELS[order.payment_method] || order.payment_method || '—'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right font-semibold text-gray-800 dark:text-gray-200 whitespace-nowrap">
                        {fmt(order.total_price || order.total || 0)}
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
            {filtered.length > 0 && (
              <tfoot>
                <tr className="border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50">
                  <td colSpan={6} className="px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400">{filtered.length} pedidos</td>
                  <td className="px-4 py-3 text-right text-sm font-bold text-gray-900 dark:text-white">{fmt(totalValue)}</td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      </div>

    </div>
  )
}
