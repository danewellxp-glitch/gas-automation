/**
 * Operação › Pedidos Agendados — Entregas com data/hora marcada
 */

import { useState, useEffect } from 'react'
import { CalendarDays, RefreshCw, Phone, AlertCircle, Clock } from 'lucide-react'
import { apiRequest } from '../../utils/api'

const fmt = (v) =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 2 }).format(v || 0)

const PAYMENT_LABELS = { pix: 'PIX', pix_asaas: 'PIX Asaas', money: 'Dinheiro', fiado: 'Fiado', card: 'Cartão' }

function hoursUntil(dateStr) {
  if (!dateStr) return null
  const diff = new Date(dateStr).getTime() - Date.now()
  const hours = diff / 3600000
  if (hours < 0) return { label: 'Atrasado', color: 'text-red-600 dark:text-red-400', bg: 'bg-red-50 dark:bg-red-900/20' }
  if (hours < 2) return { label: `${Math.floor(hours * 60)}min`, color: 'text-amber-600 dark:text-amber-400', bg: 'bg-amber-50 dark:bg-amber-900/20' }
  if (hours < 24) return { label: `${Math.floor(hours)}h`, color: 'text-blue-600 dark:text-blue-400', bg: 'bg-blue-50 dark:bg-blue-900/20' }
  const days = Math.floor(hours / 24)
  return { label: `${days}d`, color: 'text-gray-600 dark:text-gray-400', bg: 'bg-gray-50 dark:bg-gray-700' }
}

export default function OpAgendados() {
  const [loading, setLoading] = useState(true)
  const [orders, setOrders]   = useState([])
  const [error, setError]     = useState('')

  useEffect(() => { fetchData() }, [])

  const fetchData = async () => {
    try {
      setLoading(true); setError('')
      const data = await apiRequest('orders?status=scheduled')
      const list = Array.isArray(data) ? data : (data?.items || data?.orders || [])
      setOrders(list.sort((a, b) => new Date(a.scheduled_at || a.delivery_date) - new Date(b.scheduled_at || b.delivery_date)))
    } catch {
      try {
        const data = await apiRequest('orders/today')
        const list = Array.isArray(data) ? data : (data?.items || [])
        const scheduled = list.filter(o => o.status === 'scheduled' || o.scheduled_at)
        setOrders(scheduled)
        if (scheduled.length === 0) setError('Nenhum pedido agendado encontrado.')
      } catch (e2) {
        setError(e2.message || 'Erro ao carregar pedidos agendados')
        setOrders([])
      }
    } finally { setLoading(false) }
  }

  const upcoming = orders.filter(o => {
    const d = o.scheduled_at || o.delivery_date
    return d && new Date(d) > new Date()
  })
  const late = orders.filter(o => {
    const d = o.scheduled_at || o.delivery_date
    return d && new Date(d) <= new Date()
  })

  const Section = ({ title, items, emptyMsg }) => (
    <div>
      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
        {title}
        <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-gray-100 dark:bg-gray-700 text-xs font-bold text-gray-600 dark:text-gray-400">
          {items.length}
        </span>
      </h3>
      {items.length === 0 ? (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 text-center text-sm text-gray-400 dark:text-gray-500">
          {emptyMsg}
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((order) => {
            const schedDate = order.scheduled_at || order.delivery_date
            const until = hoursUntil(schedDate)
            return (
              <div key={order.id} className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-semibold text-gray-800 dark:text-gray-200">#{order.order_number || order.id}</span>
                      {until && (
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${until.bg} ${until.color}`}>
                          <Clock className="w-3 h-3" /> {until.label}
                        </span>
                      )}
                      <span className="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400">
                        {PAYMENT_LABELS[order.payment_method] || '—'}
                      </span>
                    </div>
                    <div className="mt-1 flex items-center gap-3 flex-wrap">
                      <span className="text-sm font-medium text-gray-800 dark:text-gray-200">{order.customer_name || '—'}</span>
                      {order.customer_phone && (
                        <a href={`tel:${order.customer_phone}`} className="flex items-center gap-1 text-xs text-primary-600 dark:text-primary-400 hover:underline">
                          <Phone className="w-3 h-3" />{order.customer_phone}
                        </a>
                      )}
                    </div>
                    {schedDate && (
                      <div className="mt-1 flex items-center gap-1 text-xs text-primary-600 dark:text-primary-400">
                        <CalendarDays className="w-3 h-3" />
                        <span className="font-medium">
                          {new Date(schedDate).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                    )}
                    {order.address && <p className="mt-0.5 text-xs text-gray-400 dark:text-gray-500 truncate">{order.address}</p>}
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-lg font-bold text-gray-900 dark:text-white">{fmt(order.total_price || order.total || 0)}</p>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )

  return (
    <div className="space-y-5">

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Pedidos Agendados</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Entregas com data e hora programadas</p>
        </div>
        <button onClick={fetchData} disabled={loading} className="p-1.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-500 hover:bg-gray-50 disabled:opacity-50">
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl text-sm text-amber-700 dark:text-amber-400">
          <AlertCircle className="w-4 h-4 shrink-0" /> {error}
        </div>
      )}

      {loading && orders.length === 0 ? (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => <div key={i} className="h-24 bg-gray-100 dark:bg-gray-700 rounded-xl animate-pulse" />)}
        </div>
      ) : orders.length === 0 && !error ? (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-12 text-center">
          <CalendarDays className="mx-auto w-10 h-10 text-gray-300 dark:text-gray-600 mb-3" />
          <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Nenhum agendamento ativo</p>
          <p className="text-xs text-gray-400 mt-1">Pedidos agendados aparecerão aqui.</p>
        </div>
      ) : (
        <div className="space-y-6">
          {late.length > 0 && <Section title="Em Atraso" items={late} emptyMsg="" />}
          <Section title="Próximos" items={upcoming} emptyMsg="Nenhum agendamento futuro." />
        </div>
      )}

    </div>
  )
}
