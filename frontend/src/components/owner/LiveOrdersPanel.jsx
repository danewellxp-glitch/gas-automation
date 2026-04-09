/**
 * LiveOrdersPanel — Pedidos por hora + Últimos pedidos ao vivo + ações rápidas
 * Design Preline-inspired: cards brancos, sem glassmorphism.
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

const NEXT_ACTION = {
  pending:   { status: 'paid',       label: 'Confirmar', cls: 'bg-blue-500 hover:bg-blue-600 text-white' },
  paid:      { status: 'preparing',  label: 'Preparar',  cls: 'bg-violet-500 hover:bg-violet-600 text-white' },
  preparing: { status: 'dispatched', label: 'Em rota',   cls: 'bg-cyan-500 hover:bg-cyan-600 text-white' },
  dispatched:{ status: 'delivered',  label: 'Entregue',  cls: 'bg-emerald-500 hover:bg-emerald-600 text-white' },
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
  } catch (_) {}
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
      setOrders((prev) =>
        prev.map((o) => (o.id === orderId ? { ...o, status: newStatus } : o))
      )
    } catch (err) {
      console.error('Erro ao atualizar status:', err)
    } finally {
      setUpdatingId(null)
    }
  }

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
    <div className="flex flex-col gap-6 w-full h-full overflow-y-auto">

      {/* ── ATIVIDADE POR HORA ─── */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center">
              <TrendingUp className="w-4 h-4 text-blue-500" />
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-900 dark:text-white">Atividade Recente</p>
              <p className="text-xs text-gray-400 dark:text-gray-500">{orders.length} pedidos hoje</p>
            </div>
          </div>
        </div>

        <div className="flex items-end gap-1 h-24">
          {hourlyData.map(({ hour, count, label }) => {
            const pct = (count / maxCount) * 100
            const isNow = hour === new Date().getHours()
            return (
              <div key={hour} className="flex flex-1 flex-col items-center gap-0.5">
                {count > 0 && (
                  <span className="text-[9px] text-gray-400 dark:text-gray-500">{count}</span>
                )}
                <div className="w-full flex-1 flex items-end">
                  <div
                    className={`w-full rounded-t transition-all duration-500 ${
                      isNow ? 'bg-primary-500' : 'bg-gray-200 dark:bg-gray-700'
                    }`}
                    style={{ height: count > 0 ? `${Math.max(pct, 8)}%` : '2px', opacity: count > 0 ? 1 : 0.4 }}
                  />
                </div>
                <span className={`text-[9px] ${isNow ? 'text-primary-500 font-semibold' : 'text-gray-400 dark:text-gray-600'}`}>
                  {label}
                </span>
              </div>
            )
          })}
        </div>
      </div>

      <div className="h-px bg-gray-100 dark:bg-gray-700" />

      {/* ── ÚLTIMOS PEDIDOS ─── */}
      <div className="flex-1">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 flex items-center justify-center">
              <Package className="w-4 h-4 text-emerald-500" />
            </div>
            <p className="text-sm font-semibold text-gray-900 dark:text-white">Últimos Pedidos</p>
          </div>
          <div className="flex items-center gap-2">
            {newCount > 0 && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-700 text-xs font-medium text-emerald-600 dark:text-emerald-400">
                <Bell className="w-3 h-3" />
                +{newCount}
              </span>
            )}
            <button
              onClick={fetchOrders}
              className="p-1.5 rounded-lg border border-gray-200 dark:border-gray-700 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {recentOrders.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 text-gray-400 dark:text-gray-600">
            <Package className="w-8 h-8 mb-2 opacity-40" />
            <span className="text-xs">Nenhum pedido hoje</span>
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
                  className={`rounded-xl border p-3 transition-colors ${
                    stuck
                      ? 'bg-amber-50 dark:bg-amber-900/10 border-amber-200 dark:border-amber-700/40'
                      : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <span className="text-sm font-medium text-gray-900 dark:text-white truncate">
                      {order.customer_name || order.customer_phone || 'Cliente S/N'}
                    </span>
                    <span className={`shrink-0 text-[10px] font-medium text-white rounded-full px-2 py-0.5 ${st.color}`}>
                      {st.label}
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                    <span className="font-semibold text-gray-700 dark:text-gray-300">{fmt(order.total_amount)}</span>
                    <span>{fmtTime(order.created_at)} · #{order.order_number}</span>
                  </div>

                  {stuck && (
                    <p className="mt-1.5 text-[10px] font-medium text-amber-600 dark:text-amber-400">
                      Parado há mais de 15 min
                    </p>
                  )}

                  {(next || canCancel) && (
                    <div className="mt-2 pt-2 border-t border-gray-100 dark:border-gray-700 flex items-center gap-1.5">
                      {next && (
                        <button
                          onClick={() => updateStatus(order.id, next.status)}
                          disabled={isUpdating}
                          className={`flex flex-1 items-center justify-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors disabled:opacity-40 ${next.cls}`}
                        >
                          {isUpdating
                            ? <span className="w-3 h-3 animate-spin rounded-full border border-white border-t-transparent" />
                            : <ChevronRight className="w-3 h-3" />
                          }
                          {next.label}
                        </button>
                      )}
                      {canCancel && (
                        <button
                          onClick={() => updateStatus(order.id, 'cancelled')}
                          disabled={isUpdating}
                          className="flex items-center justify-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-medium text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-700/40 hover:bg-rose-100 dark:hover:bg-rose-900/30 transition-colors disabled:opacity-40"
                        >
                          <X className="w-3 h-3" />
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
