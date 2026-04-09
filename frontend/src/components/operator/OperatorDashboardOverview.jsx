import { useState, useEffect, useCallback } from 'react'
import { Package, RefreshCw, Clock, Truck, CheckCircle, MessageSquare } from 'lucide-react'
import { getOrdersToday, getConversations } from '../../services/api'
import { useSharedWebSocketEvent } from '../../hooks/useSharedWebSocket'
import OrdersPinMap from './OrdersPinMap'

// Row for status breakdown
function StatusRow({ label, value, max, color }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0
  return (
    <div className="flex items-center gap-3 py-2 border-b border-gray-100 dark:border-gray-700 last:border-0">
      <span className="w-2 h-2 rounded-full shrink-0" style={{ background: color }} />
      <span className="flex-1 text-xs text-gray-600 dark:text-gray-400">{label}</span>
      <span className="text-xs font-medium text-gray-900 dark:text-white w-5 text-right">{value}</span>
      <div className="w-20 h-1 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
        <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  )
}

export default function OperatorDashboardOverview() {
  const [metrics, setMetrics] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetchMetrics = useCallback(async () => {
    try {
      setLoading(true)
      const [todayOrders, conversationsData] = await Promise.all([
        getOrdersToday().catch(() => []),
        getConversations().catch(() => ({ items: [], total: 0 })),
      ])
      const conversations = conversationsData.items || []
      setMetrics({
        orders: {
          pending:    todayOrders.filter(o => o.status === 'pending').length,
          processing: todayOrders.filter(o => o.status === 'preparing').length,
          dispatched: todayOrders.filter(o => o.status === 'dispatched').length,
          delivered:  todayOrders.filter(o => o.status === 'delivered').length,
          total:      todayOrders.length,
        },
        conversations: {
          active: conversations.length,
          total:  conversationsData.total || conversations.length,
        },
      })
    } catch (e) {
      console.error('Erro ao buscar métricas:', e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchMetrics()
    const t = setInterval(fetchMetrics, 30000)
    return () => clearInterval(t)
  }, [fetchMetrics])

  useSharedWebSocketEvent('order_update', fetchMetrics)

  const kpi = [
    { label: 'Hoje',       value: metrics?.orders.total,         icon: Package,       color: 'text-gray-600 dark:text-gray-400' },
    { label: 'Pendentes',  value: metrics?.orders.pending,       icon: Clock,         color: 'text-amber-600 dark:text-amber-400' },
    { label: 'Em preparo', value: metrics?.orders.processing,    icon: RefreshCw,     color: 'text-blue-600 dark:text-blue-400' },
    { label: 'Em rota',    value: metrics?.orders.dispatched,    icon: Truck,         color: 'text-violet-600 dark:text-violet-400' },
    { label: 'Entregues',  value: metrics?.orders.delivered,     icon: CheckCircle,   color: 'text-emerald-600 dark:text-emerald-400' },
    { label: 'Conversas',  value: metrics?.conversations.active, icon: MessageSquare, color: 'text-primary-600 dark:text-primary-400' },
  ]

  return (
    <div className="space-y-4">

      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-sm font-semibold text-gray-900 dark:text-white">Central do Operador</h1>
          <p className="text-xs text-gray-500 dark:text-gray-400">Pedidos e atendimentos em andamento</p>
        </div>
        <button
          onClick={fetchMetrics}
          disabled={loading}
          className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
          Atualizar
        </button>
      </div>

      {/* Thin KPI bar */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 px-4 py-3">
        <div className="flex items-center gap-1 flex-wrap">
          {kpi.map((item, idx) => {
            const Icon = item.icon
            return (
              <div key={item.label} className="flex items-center">
                {idx > 0 && <span className="w-px h-5 bg-gray-200 dark:bg-gray-700 mx-3" />}
                <div className="flex items-center gap-2">
                  <Icon className={`w-3.5 h-3.5 ${item.color}`} />
                  <div>
                    <span className={`text-base font-semibold ${item.color}`}>
                      {loading
                        ? <span className="inline-block w-5 h-4 bg-gray-100 dark:bg-gray-700 rounded animate-pulse" />
                        : (item.value ?? 0)
                      }
                    </span>
                    <span className="ml-1.5 text-xs text-gray-400 dark:text-gray-500">{item.label}</span>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Order breakdown + Conversations */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">

        <div className="lg:col-span-3 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
          <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700 flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">Pedidos de Hoje</span>
            <span className="text-xs text-gray-400 dark:text-gray-500">por status</span>
          </div>
          <div className="px-4 py-1">
            {!loading && metrics ? (
              <>
                <StatusRow label="Pendentes"  value={metrics.orders.pending}    max={metrics.orders.total} color="#f59e0b" />
                <StatusRow label="Em preparo" value={metrics.orders.processing} max={metrics.orders.total} color="#3b82f6" />
                <StatusRow label="Em rota"    value={metrics.orders.dispatched} max={metrics.orders.total} color="#8b5cf6" />
                <StatusRow label="Entregues"  value={metrics.orders.delivered}  max={metrics.orders.total} color="#22c55e" />
              </>
            ) : (
              <div className="py-5 flex justify-center">
                <div className="w-5 h-5 border-2 border-gray-200 border-t-primary-500 rounded-full animate-spin" />
              </div>
            )}
          </div>
          {metrics && (
            <div className="px-4 py-2.5 border-t border-gray-100 dark:border-gray-700">
              <span className="text-xs text-gray-400 dark:text-gray-500">
                Total: <strong className="text-gray-600 dark:text-gray-300">{metrics.orders.total} pedidos</strong>
              </span>
            </div>
          )}
        </div>

        <div className="lg:col-span-2 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
          <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700 flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">Conversas Robô</span>
            <MessageSquare className="w-3.5 h-3.5 text-gray-300 dark:text-gray-600" />
          </div>
          <div className="px-4 py-3">
            {loading ? (
              <div className="flex justify-center py-4">
                <div className="w-5 h-5 border-2 border-gray-200 border-t-primary-500 rounded-full animate-spin" />
              </div>
            ) : (
              <>
                <div className="flex items-center justify-between py-2 border-b border-gray-100 dark:border-gray-700">
                  <span className="text-xs text-gray-500 dark:text-gray-400">Total de chats</span>
                  <span className="text-xs font-semibold text-gray-900 dark:text-white">{metrics?.conversations.total ?? 0}</span>
                </div>
                <div className="flex items-center justify-between py-2">
                  <span className="text-xs text-gray-500 dark:text-gray-400">Chats ativos</span>
                  <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                    {metrics?.conversations.active ?? 0}
                  </span>
                </div>
              </>
            )}
          </div>
        </div>

      </div>

      {/* Mapa de pedidos em andamento */}
      <OrdersPinMap height="380px" />

    </div>
  )
}
