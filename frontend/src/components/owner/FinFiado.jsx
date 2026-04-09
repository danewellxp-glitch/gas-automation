/**
 * Financeiro › Fiado — Clientes com saldo devedor (vendas a crédito)
 */

import { useState, useEffect } from 'react'
import { CreditCard, RefreshCw, Download, Phone, AlertCircle, TrendingUp, User } from 'lucide-react'
import { apiRequest } from '../../utils/api'

const fmt = (v) =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 2 }).format(v || 0)

export default function FinFiado() {
  const [loading, setLoading] = useState(true)
  const [customers, setCustomers] = useState([])
  const [orders, setOrders]       = useState([])
  const [error, setError]         = useState('')
  const [selected, setSelected]   = useState(null)

  useEffect(() => { fetchData() }, [])

  const fetchData = async () => {
    try {
      setLoading(true); setError('')
      // busca pedidos com payment_method=fiado que não foram quitados
      const data = await apiRequest('orders?payment_method=fiado&status=delivered')
      const list = Array.isArray(data) ? data : (data?.items || data?.orders || [])
      setOrders(list)

      // agrupa por cliente
      const map = {}
      list.forEach(o => {
        const key = o.customer_phone || o.customer_name || 'Desconhecido'
        if (!map[key]) map[key] = { name: o.customer_name || 'Cliente', phone: o.customer_phone || key, total: 0, count: 0, lastDate: o.created_at, orders: [] }
        map[key].total += o.total_price || o.total || 0
        map[key].count += 1
        map[key].orders.push(o)
        if (o.created_at && (!map[key].lastDate || o.created_at > map[key].lastDate)) map[key].lastDate = o.created_at
      })
      setCustomers(Object.values(map).sort((a, b) => b.total - a.total))
    } catch {
      setError('Sem dados de fiado disponíveis ou nenhum pedido fiado encontrado.')
      setCustomers([])
    } finally { setLoading(false) }
  }

  const totalFiado = customers.reduce((s, c) => s + c.total, 0)

  const handleExport = () => {
    const header = 'Cliente,Telefone,Pedidos,Total Fiado,Último Pedido\n'
    const rows = customers.map(c =>
      `"${c.name}","${c.phone}",${c.count},${c.total.toFixed(2)},${c.lastDate ? new Date(c.lastDate).toLocaleDateString('pt-BR') : ''}`
    ).join('\n')
    const blob = new Blob([header + rows], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url
    a.download = 'fiado.csv'; a.click(); URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-5">

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Fiado</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Clientes com saldo devedor em vendas a crédito</p>
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
        <div className="bg-amber-50 dark:bg-amber-900/20 border border-gray-200 dark:border-gray-700 rounded-xl p-4">
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Total em Fiado</p>
          <p className="mt-1 text-2xl font-bold text-amber-600 dark:text-amber-400">{fmt(totalFiado)}</p>
          <p className="mt-0.5 text-xs text-gray-400">{orders.length} pedidos</p>
        </div>
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4">
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Clientes</p>
          <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">{customers.length}</p>
          <p className="mt-0.5 text-xs text-gray-400">com saldo</p>
        </div>
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4">
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Média por cliente</p>
          <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">{fmt(customers.length ? totalFiado / customers.length : 0)}</p>
          <p className="mt-0.5 text-xs text-gray-400">por devedor</p>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl text-sm text-amber-700 dark:text-amber-400">
          <AlertCircle className="w-4 h-4 shrink-0" /> {error}
        </div>
      )}

      {/* Grid de clientes */}
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {[...Array(6)].map((_, i) => <div key={i} className="h-28 bg-gray-100 dark:bg-gray-700 rounded-xl animate-pulse" />)}
        </div>
      ) : customers.length === 0 ? (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-10 text-center">
          <CreditCard className="mx-auto w-10 h-10 text-gray-300 dark:text-gray-600 mb-3" />
          <p className="text-sm text-gray-500 dark:text-gray-400">Nenhum cliente com fiado em aberto.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {customers.map((c, idx) => (
            <button
              key={idx}
              onClick={() => setSelected(selected?.phone === c.phone ? null : c)}
              className={`text-left bg-white dark:bg-gray-800 rounded-xl border p-4 hover:border-amber-300 dark:hover:border-amber-700 transition-colors ${selected?.phone === c.phone ? 'border-amber-300 dark:border-amber-700' : 'border-gray-200 dark:border-gray-700'}`}
            >
              <div className="flex items-start gap-3">
                <div className="w-9 h-9 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center shrink-0">
                  <User className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold text-gray-800 dark:text-gray-200 truncate">{c.name}</p>
                  {c.phone && <p className="text-xs text-gray-400 flex items-center gap-1 mt-0.5"><Phone className="w-3 h-3" />{c.phone}</p>}
                  <p className="text-xs text-gray-400 mt-0.5">{c.count} pedido{c.count !== 1 ? 's' : ''}</p>
                </div>
                <div className="text-right shrink-0">
                  <p className="text-sm font-bold text-amber-600 dark:text-amber-400">{fmt(c.total)}</p>
                  <p className="text-xs text-gray-400 mt-0.5">em aberto</p>
                </div>
              </div>

              {/* detalhe expandido */}
              {selected?.phone === c.phone && c.orders.length > 0 && (
                <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-700 space-y-1.5">
                  {c.orders.map((o, oi) => (
                    <div key={oi} className="flex items-center justify-between text-xs">
                      <span className="text-gray-500 dark:text-gray-400">
                        {o.created_at ? new Date(o.created_at).toLocaleDateString('pt-BR') : '—'} · #{o.order_number || o.id}
                      </span>
                      <span className="font-medium text-gray-700 dark:text-gray-300">{fmt(o.total_price || o.total || 0)}</span>
                    </div>
                  ))}
                </div>
              )}
            </button>
          ))}
        </div>
      )}

    </div>
  )
}
