/**
 * Operação › Pedidos Pendentes — Fila de pedidos aguardando ação
 */

import { useState, useEffect } from 'react'
import { Clock, RefreshCw, Phone, AlertCircle, Zap } from 'lucide-react'
import { apiRequest } from '../../utils/api'

const fmt = (v) =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 2 }).format(v || 0)

function minutesSince(dateStr) {
  if (!dateStr) return 0
  return Math.floor((Date.now() - new Date(dateStr).getTime()) / 60000)
}

function WaitBadge({ minutes }) {
  if (minutes < 5)  return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-400"><Clock className="w-3 h-3" />{minutes}min</span>
  if (minutes < 15) return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400"><Clock className="w-3 h-3" />{minutes}min</span>
  return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400"><AlertCircle className="w-3 h-3" />{minutes}min</span>
}

const PAYMENT_LABELS = { pix: 'PIX', pix_asaas: 'PIX Asaas', money: 'Dinheiro', fiado: 'Fiado', card: 'Cartão' }

export default function OpPendentes() {
  const [loading, setLoading] = useState(true)
  const [orders, setOrders]   = useState([])
  const [error, setError]     = useState('')

  useEffect(() => {
    fetchData()
    const t = setInterval(fetchData, 30000)
    return () => clearInterval(t)
  }, [])

  const fetchData = async () => {
    try {
      setLoading(true); setError('')
      const data = await apiRequest('orders?status=pending')
      const list = Array.isArray(data) ? data : (data?.items || data?.orders || [])
      setOrders(list.sort((a, b) => new Date(a.created_at) - new Date(b.created_at)))
    } catch (err) {
      // fallback: orders/today e filtra pending
      try {
        const data = await apiRequest('orders/today')
        const list = Array.isArray(data) ? data : (data?.items || data?.orders || [])
        setOrders(list.filter(o => o.status === 'pending').sort((a, b) => new Date(a.created_at) - new Date(b.created_at)))
      } catch {
        setError(err.message || 'Erro ao carregar pedidos pendentes'); setOrders([])
      }
    } finally { setLoading(false) }
  }

  const urgentCount = orders.filter(o => minutesSince(o.created_at) >= 15).length

  return (
    <div className="space-y-5">

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Pedidos Pendentes</h1>
            {orders.length > 0 && (
              <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-amber-500 text-white text-xs font-bold">
                {orders.length}
              </span>
            )}
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400">Fila aguardando aprovação · atualiza a cada 30s</p>
        </div>
        <button onClick={fetchData} disabled={loading} className="p-1.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-500 hover:bg-gray-50 disabled:opacity-50">
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {urgentCount > 0 && (
        <div className="flex items-center gap-3 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl">
          <AlertCircle className="w-5 h-5 text-red-500 shrink-0" />
          <div>
            <p className="text-sm font-semibold text-red-700 dark:text-red-400">{urgentCount} pedido{urgentCount !== 1 ? 's' : ''} aguardando há mais de 15 minutos</p>
            <p className="text-xs text-red-600 dark:text-red-400 mt-0.5">Atenção imediata necessária.</p>
          </div>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl text-sm text-amber-700 dark:text-amber-400">
          <AlertCircle className="w-4 h-4 shrink-0" /> {error}
        </div>
      )}

      {loading && orders.length === 0 ? (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => <div key={i} className="h-24 bg-gray-100 dark:bg-gray-700 rounded-xl animate-pulse" />)}
        </div>
      ) : orders.length === 0 ? (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-12 text-center">
          <Zap className="mx-auto w-10 h-10 text-gray-300 dark:text-gray-600 mb-3" />
          <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Nenhum pedido pendente</p>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">Todos os pedidos foram processados.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {orders.map((order) => {
            const mins = minutesSince(order.created_at)
            const isUrgent = mins >= 15
            return (
              <div key={order.id} className={`bg-white dark:bg-gray-800 rounded-xl border p-4 transition-colors ${isUrgent ? 'border-red-200 dark:border-red-800' : 'border-gray-200 dark:border-gray-700'}`}>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-semibold text-gray-800 dark:text-gray-200">#{order.order_number || order.id}</span>
                      <WaitBadge minutes={mins} />
                      <span className="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400">
                        {PAYMENT_LABELS[order.payment_method] || order.payment_method || '—'}
                      </span>
                    </div>
                    <div className="mt-1 flex items-center gap-3 text-sm text-gray-600 dark:text-gray-400">
                      <span className="font-medium text-gray-800 dark:text-gray-200">{order.customer_name || '—'}</span>
                      {order.customer_phone && (
                        <a href={`tel:${order.customer_phone}`} className="flex items-center gap-1 text-xs text-primary-600 dark:text-primary-400 hover:underline">
                          <Phone className="w-3 h-3" />{order.customer_phone}
                        </a>
                      )}
                    </div>
                    {order.address && (
                      <p className="mt-0.5 text-xs text-gray-400 dark:text-gray-500 truncate">{order.address}</p>
                    )}
                    {(order.items || order.products) && (
                      <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                        {(order.items || order.products || []).map(i => `${i.quantity}x ${i.name || i.product_name || i.code}`).join(', ')}
                      </p>
                    )}
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-lg font-bold text-gray-900 dark:text-white">{fmt(order.total_price || order.total || 0)}</p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {order.created_at ? new Date(order.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }) : '—'}
                    </p>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

    </div>
  )
}
