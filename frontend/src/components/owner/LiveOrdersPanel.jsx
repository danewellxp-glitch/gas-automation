/**
 * LiveOrdersPanel - Pedidos por hora + Últimos pedidos ao vivo + ações rápidas
 */

import { useState, useEffect, useRef } from 'react'
import { Package, TrendingUp, RefreshCw, Bell, ChevronRight, X } from 'lucide-react'
import { apiRequest } from '../../utils/api'

const STATUS_CONFIG = {
  pending:    { label: 'Pendente',   color: 'bg-amber-500' },
  paid:       { label: 'Confirmado', color: 'bg-blue-500' },
  preparing:  { label: 'Preparando', color: 'bg-violet-500' },
  dispatched: { label: 'Em rota',    color: 'bg-cyan-500' },
  delivered:  { label: 'Entregue',   color: 'bg-emerald-500' },
  cancelled:  { label: 'Cancelado',  color: 'bg-rose-500' },
}

// Próxima ação principal por status
const NEXT_ACTION = {
  pending:    { status: 'paid',       label: 'Confirmar',  btn: 'bg-blue-500 hover:bg-blue-600' },
  paid:       { status: 'preparing',  label: 'Preparar',   btn: 'bg-violet-500 hover:bg-violet-600' },
  preparing:  { status: 'dispatched', label: 'Em rota',    btn: 'bg-cyan-500 hover:bg-cyan-600' },
  dispatched: { status: 'delivered',  label: 'Entregue',   btn: 'bg-emerald-500 hover:bg-emerald-600' },
}

const CANCELLABLE = new Set(['pending', 'paid', 'preparing', 'dispatched'])

function playBeep() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)()
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.connect(gain)
    gain.connect(ctx.destination)
    osc.type = 'sine'
    osc.frequency.value = 880
    gain.gain.setValueAtTime(0.35, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.45)
    osc.start()
    osc.stop(ctx.currentTime + 0.45)
    const osc2 = ctx.createOscillator()
    const gain2 = ctx.createGain()
    osc2.connect(gain2)
    gain2.connect(ctx.destination)
    osc2.type = 'sine'
    osc2.frequency.value = 1100
    gain2.gain.setValueAtTime(0.25, ctx.currentTime + 0.2)
    gain2.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.6)
    osc2.start(ctx.currentTime + 0.2)
    osc2.stop(ctx.currentTime + 0.6)
  } catch (_) { /* AudioContext não suportado */ }
}

export default function LiveOrdersPanel() {
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [newCount, setNewCount] = useState(0)
  const [updatingId, setUpdatingId] = useState(null)
  const prevIdsRef = useRef(new Set())
  const badgeTimeoutRef = useRef(null)
  const isFirstFetchRef = useRef(true)

  useEffect(() => {
    fetchOrders()
    const interval = setInterval(fetchOrders, 30000)
    return () => {
      clearInterval(interval)
      clearTimeout(badgeTimeoutRef.current)
    }
  }, [])

  const fetchOrders = async () => {
    try {
      const data = await apiRequest('orders/today')
      const incoming = Array.isArray(data) ? data : []

      if (!isFirstFetchRef.current) {
        const newOrders = incoming.filter((o) => !prevIdsRef.current.has(o.id))
        if (newOrders.length > 0) {
          playBeep()
          setNewCount(newOrders.length)
          clearTimeout(badgeTimeoutRef.current)
          badgeTimeoutRef.current = setTimeout(() => setNewCount(0), 10000)
        }
      }

      isFirstFetchRef.current = false
      prevIdsRef.current = new Set(incoming.map((o) => o.id))
      setOrders(incoming)
    } catch (err) {
      console.error('Erro ao buscar pedidos:', err)
    } finally {
      setLoading(false)
    }
  }

  const updateStatus = async (orderId, newStatus) => {
    if (updatingId) return
    setUpdatingId(orderId)
    try {
      await apiRequest(`orders/${orderId}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      })
      // Atualiza localmente sem esperar próximo poll
      setOrders((prev) =>
        prev.map((o) => (o.id === orderId ? { ...o, status: newStatus } : o))
      )
    } catch (err) {
      console.error('Erro ao atualizar status:', err)
    } finally {
      setUpdatingId(null)
    }
  }

  // Agrupa pedidos por hora (últimas 12h)
  const buildHourlyData = () => {
    const counts = {}
    orders.forEach(o => {
      const h = new Date(o.created_at).getHours()
      counts[h] = (counts[h] || 0) + 1
    })
    const now = new Date().getHours()
    return Array.from({ length: 12 }, (_, i) => {
      const h = (now - 11 + i + 24) % 24
      return { hour: h, count: counts[h] || 0, label: `${String(h).padStart(2, '0')}h` }
    })
  }

  const hourlyData = buildHourlyData()
  const maxCount = Math.max(...hourlyData.map(h => h.count), 1)
  const recentOrders = [...orders].slice(0, 8)

  const fmt = (v) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(v || 0)
  const fmtTime = (dt) => new Date(dt).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
  const isStuckPaid = (order) =>
    order.status === 'paid' &&
    Date.now() - new Date(order.created_at).getTime() > 15 * 60 * 1000

  return (
    <div className="grid gap-4 lg:grid-cols-2">

      {/* ── PEDIDOS POR HORA ─────────────────────────────────── */}
      <div className="rounded-2xl border border-gray-200 dark:border-gray-700/60 bg-white dark:bg-gray-800/60 p-6 shadow-sm">
        <div className="mb-5 flex items-center gap-3">
          <div className="rounded-xl bg-gradient-to-br from-blue-400 to-indigo-600 p-2.5 shadow-md shadow-blue-500/25">
            <TrendingUp className="h-4 w-4 text-white" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">Pedidos por Hora</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">Últimas 12h — {orders.length} pedidos hoje</p>
          </div>
        </div>

        {/* Gráfico de barras CSS */}
        <div className="flex items-end gap-1.5 h-28">
          {hourlyData.map(({ hour, count, label }) => {
            const pct = (count / maxCount) * 100
            const isNow = hour === new Date().getHours()
            return (
              <div key={hour} className="flex flex-1 flex-col items-center gap-1">
                {count > 0 && (
                  <span className="text-xs font-bold text-gray-600 dark:text-gray-300">{count}</span>
                )}
                <div className="w-full flex-1 flex items-end">
                  <div
                    className={`w-full rounded-t-md transition-all duration-700 ${
                      isNow
                        ? 'bg-gradient-to-t from-emerald-600 to-emerald-400'
                        : 'bg-gradient-to-t from-blue-600 to-indigo-400'
                    }`}
                    style={{ height: count > 0 ? `${Math.max(pct, 8)}%` : '3px', opacity: count > 0 ? 1 : 0.2 }}
                  />
                </div>
                <span className={`text-xs ${isNow ? 'font-bold text-emerald-500' : 'text-gray-400'}`}>
                  {label}
                </span>
              </div>
            )
          })}
        </div>
      </div>

      {/* ── ÚLTIMOS PEDIDOS + AÇÕES RÁPIDAS ──────────────────── */}
      <div className="rounded-2xl border border-gray-200 dark:border-gray-700/60 bg-white dark:bg-gray-800/60 p-6 shadow-sm">
        <div className="mb-5 flex items-center gap-3">
          <div className="rounded-xl bg-gradient-to-br from-emerald-400 to-teal-600 p-2.5 shadow-md shadow-emerald-500/25">
            <Package className="h-4 w-4 text-white" />
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-gray-900 dark:text-white">Últimos Pedidos</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">Atualiza a cada 30s</p>
          </div>
          {newCount > 0 && (
            <div className="flex items-center gap-1.5 rounded-full bg-emerald-500/15 border border-emerald-500/40 px-2.5 py-1 text-xs font-bold text-emerald-600 dark:text-emerald-400 animate-pulse">
              <Bell className="h-3 w-3" />
              +{newCount} novo{newCount > 1 ? 's' : ''}
            </div>
          )}
          <button
            onClick={fetchOrders}
            className="rounded-lg p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {recentOrders.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-gray-400">
            <Package className="h-8 w-8 mb-2 opacity-30" />
            <span className="text-sm">Nenhum pedido hoje</span>
          </div>
        ) : (
          <div className="space-y-2">
            {recentOrders.map((order) => {
              const st = STATUS_CONFIG[order.status] || { label: order.status, color: 'bg-gray-500' }
              const next = NEXT_ACTION[order.status]
              const canCancel = CANCELLABLE.has(order.status)
              const isUpdating = updatingId === order.id
              const stuck = isStuckPaid(order)

              return (
                <div
                  key={order.id}
                  className={`rounded-xl px-3 py-2 ${
                    stuck
                      ? 'bg-amber-50 dark:bg-amber-900/20 border border-amber-300 dark:border-amber-500/40'
                      : 'bg-gray-50 dark:bg-gray-700/50'
                  }`}
                >
                  {/* Linha principal */}
                  <div className="flex items-center gap-2">
                    <span className="w-8 text-xs font-bold text-gray-400 shrink-0">
                      #{order.order_number}
                    </span>
                    <span className="flex-1 text-sm font-medium text-gray-900 dark:text-white truncate">
                      {order.customer_name || order.customer_phone || '—'}
                    </span>
                    <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold text-white ${st.color}`}>
                      {st.label}
                    </span>
                    {stuck && (
                      <span className="shrink-0 rounded-full bg-amber-500 px-2 py-0.5 text-xs font-bold text-white animate-pulse">
                        ⚠ parado
                      </span>
                    )}
                    <span className="shrink-0 text-sm font-bold text-gray-900 dark:text-white">
                      {fmt(order.total_amount)}
                    </span>
                    <span className="shrink-0 w-10 text-right text-xs text-gray-400">
                      {fmtTime(order.created_at)}
                    </span>
                  </div>

                  {/* Botões de ação (apenas para status acionáveis) */}
                  {(next || canCancel) && (
                    <div className="mt-1.5 flex items-center gap-1.5 pl-10">
                      {next && (
                        <button
                          onClick={() => updateStatus(order.id, next.status)}
                          disabled={isUpdating}
                          className={`flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-semibold text-white transition-colors disabled:opacity-50 ${next.btn}`}
                        >
                          {isUpdating ? (
                            <span className="h-3 w-3 animate-spin rounded-full border border-white border-t-transparent" />
                          ) : (
                            <ChevronRight className="h-3 w-3" />
                          )}
                          {next.label}
                        </button>
                      )}
                      {canCancel && (
                        <button
                          onClick={() => updateStatus(order.id, 'cancelled')}
                          disabled={isUpdating}
                          className="flex items-center gap-1 rounded-md px-2 py-1 text-xs font-semibold text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-900/30 transition-colors disabled:opacity-50"
                        >
                          <X className="h-3 w-3" />
                          Cancelar
                        </button>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

    </div>
  )
}
