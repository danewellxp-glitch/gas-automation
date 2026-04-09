/**
 * Dashboard Overview — Painel Executivo do Dono
 * Inclui: KPIs, PIX Hoje, Tendência Mensal, Top Formatos,
 *         Metas, Pedidos Tempo Real, Drivers Online + Mapa
 */

import { useState, useEffect } from 'react'
import {
  DollarSign, TrendingUp, TrendingDown, Package, AlertCircle, AlertTriangle,
  RefreshCw, XCircle, Scale, Target, X, Zap, QrCode, Truck, Wifi, WifiOff,
  MapPin, User,
} from 'lucide-react'
import { apiRequest } from '../../utils/api'
import { useAuth } from '../../hooks/useAuth'
import CardDetailModal from './CardDetailModal'
import LiveOrdersPanel from './LiveOrdersPanel'
import MonthlySparkline from './MonthlySparkline'
import DeliveryMap from '../map/DeliveryMap'

// ── formatadores ────────────────────────────────────────────────────────────
const fmt = (v) =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 0 }).format(v || 0)

const fmtFull = (v) =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 2 }).format(v || 0)

const fmtPct = (v) => {
  const n = parseFloat(v) || 0
  return `${n >= 0 ? '+' : ''}${n.toFixed(1)}%`
}

const growthPhrase = (g, ref) => {
  const n = parseFloat(g) || 0
  if (n > 30)  return `Alta forte: +${n.toFixed(0)}% vs ${ref}`
  if (n > 5)   return `Cresceu ${n.toFixed(1)}% vs ${ref}`
  if (n > 0)   return `Leve alta de ${n.toFixed(1)}% vs ${ref}`
  if (n === 0) return `Igual a ${ref}`
  if (n > -10) return `Caiu ${Math.abs(n).toFixed(1)}% vs ${ref}`
  return `Queda de ${Math.abs(n).toFixed(0)}% vs ${ref}`
}

// ── KPI Card ────────────────────────────────────────────────────────────────
function KpiCard({ title, value, sub, icon: Icon, iconBg, iconColor, trend, onClick, loading }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="text-left bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 hover:border-primary-300 dark:hover:border-primary-700 transition-colors group"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">{title}</p>
          <p className="mt-1.5 text-2xl font-bold text-gray-900 dark:text-white truncate">
            {loading ? <span className="inline-block w-20 h-7 bg-gray-100 dark:bg-gray-700 rounded animate-pulse" /> : value}
          </p>
          {sub && <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">{sub}</p>}
        </div>
        <div className={`shrink-0 w-10 h-10 rounded-lg flex items-center justify-center ${iconBg}`}>
          <Icon className={`w-5 h-5 ${iconColor}`} />
        </div>
      </div>
      {trend != null && (
        <div className={`mt-3 inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${trend >= 0 ? 'bg-green-50 text-green-600 dark:bg-green-900/20 dark:text-green-400' : 'bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-400'}`}>
          {trend >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
          {fmtPct(trend)}
        </div>
      )}
    </button>
  )
}

// ── Meta Progress Bar ────────────────────────────────────────────────────────
function GoalBar({ label, current, goal, fmtFn }) {
  const pct = goal > 0 ? Math.min((current / goal) * 100, 100) : 0
  const hit = pct >= 100
  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-sm text-gray-600 dark:text-gray-400">{label}</span>
        <span className={`text-sm font-semibold ${hit ? 'text-primary-600' : 'text-gray-700 dark:text-gray-300'}`}>
          {hit ? '✓ Meta' : `${pct.toFixed(0)}%`}
        </span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${hit ? 'bg-primary-500' : 'bg-blue-500'}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="mt-1 flex justify-between text-xs text-gray-400 dark:text-gray-500">
        <span>{fmtFn(current)}</span>
        <span>{fmtFn(goal)}</span>
      </div>
    </div>
  )
}

// ── Driver Online Badge ──────────────────────────────────────────────────────
function DriverBadge({ driver }) {
  const isOnline = driver.is_online || driver.status === 'online' || driver.status === 'available'
  return (
    <div className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg bg-gray-50 dark:bg-gray-700/50 border border-gray-100 dark:border-gray-700">
      <div className="relative shrink-0">
        <div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-600 flex items-center justify-center">
          <User className="w-4 h-4 text-gray-500 dark:text-gray-400" />
        </div>
        <span className={`absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-white dark:border-gray-800 ${isOnline ? 'bg-green-500' : 'bg-gray-400'}`} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-xs font-semibold text-gray-800 dark:text-gray-200 truncate">{driver.name || driver.full_name || 'Motorista'}</p>
        <p className={`text-[10px] font-medium ${isOnline ? 'text-green-600 dark:text-green-400' : 'text-gray-400'}`}>
          {isOnline ? 'Online' : 'Offline'}
        </p>
      </div>
    </div>
  )
}

// ── Componente principal ─────────────────────────────────────────────────────
export default function DashboardOverview() {
  const [loading, setLoading]             = useState(true)
  const [error, setError]                 = useState('')
  const [period, setPeriod]               = useState('day')
  const [dashboardData, setDashboardData] = useState(null)
  const [lastUpdate, setLastUpdate]       = useState(null)
  const [openModal, setOpenModal]         = useState(null)
  const [modalData, setModalData]         = useState(null)
  const [goals, setGoals]                 = useState(null)
  const [dismissedAlerts, setDismissedAlerts] = useState(new Set())
  const [drivers, setDrivers]             = useState([])
  const [driversLoading, setDriversLoading] = useState(false)
  const [showMap, setShowMap]             = useState(false)
  const { user } = useAuth()

  const getGreeting = () => {
    const h = new Date().getHours()
    if (h < 12) return 'Bom dia'
    if (h < 18) return 'Boa tarde'
    return 'Boa noite'
  }

  useEffect(() => {
    fetchDashboard()
    fetchGoals()
    fetchDrivers()
    const t = setInterval(() => {
      fetchDashboard()
      fetchDrivers()
    }, 30000)
    return () => clearInterval(t)
  }, [period])

  const fetchGoals = async () => {
    try {
      const data = await apiRequest('owner/settings')
      setGoals(data?.monthly_goals || null)
    } catch (_) {}
  }

  const fetchDrivers = async () => {
    try {
      setDriversLoading(true)
      const data = await apiRequest('drivers')
      setDrivers(Array.isArray(data) ? data : (data?.drivers || data?.items || []))
    } catch (_) {
      setDrivers([])
    } finally {
      setDriversLoading(false)
    }
  }

  const fetchDashboard = async () => {
    try {
      setLoading(true)
      setError('')
      const data = await apiRequest(`owner/dashboard?period=${period}`)
      setDashboardData(data)
      setLastUpdate(new Date())
    } catch (err) {
      if (err.message?.includes('401')) {
        setError('Sessão expirada.')
        setTimeout(() => { window.location.href = '/login' }, 2000)
      } else {
        setError(err.message || 'Erro ao carregar dashboard')
      }
    } finally {
      setLoading(false)
    }
  }

  const fetchCardDetails = (cardType) => {
    const c = dashboardData?.cards
    const fin = c?.financial || {}
    const ops = c?.operational || {}
    const fb = dashboardData?.financial_breakdown || {}
    const vol = dashboardData?.volume || {}
    switch (cardType) {
      case 'revenue_today':
        return { title: 'Faturamento Hoje', items: [
          { label: 'Total', value: fmtFull(fin.revenue_today) },
          { label: 'Pedidos pagos', value: ops.orders_completed || 0 },
          { label: 'Ticket médio', value: fmtFull(fin.average_ticket) },
          { label: 'Crescimento vs ontem', value: fmtPct(fin.growth_vs_yesterday) },
        ]}
      case 'orders_today':
        return { title: 'Pedidos Hoje', items: [
          { label: 'Hoje', value: ops.orders_today || 0 },
          { label: 'Ontem', value: ops.orders_yesterday || 0 },
          { label: 'Concluídos', value: ops.orders_completed || 0 },
          { label: 'Cancelados', value: ops.orders_cancelled_today || 0 },
        ]}
      case 'cancelled':
        return { title: 'Cancelamentos', items: [
          { label: 'Cancelados hoje', value: ops.orders_cancelled_today || 0 },
          { label: 'Taxa', value: ops.orders_today > 0 ? `${(((ops.orders_cancelled_today || 0) / ops.orders_today) * 100).toFixed(1)}%` : '0%' },
        ]}
      case 'ticket':
        return { title: 'Ticket Médio', items: [
          { label: 'Ticket médio', value: fmtFull(fin.average_ticket) },
          { label: 'Pedidos entregues', value: ops.orders_completed || 0 },
        ]}
      case 'volume':
        return { title: 'Volume Vendido', items: [
          { label: 'Total kg', value: vol?.total_kg ? `${vol.total_kg.toLocaleString('pt-BR')} kg` : '0 kg' },
          { label: 'Total ton', value: vol?.total_ton ? `${vol.total_ton.toFixed(3)} ton` : '0 ton' },
        ]}
      case 'pix_today':
        return { title: 'PIX Hoje', items: [
          { label: 'Total recebido', value: fmtFull(dashboardData?.pix_today?.total || 0) },
          { label: 'Transações', value: dashboardData?.pix_today?.count || 0 },
        ]}
      default:
        return { title: 'Detalhes', items: [] }
    }
  }

  // ── loading / error states ─────────────────────────────────────────────────
  if (loading && !dashboardData) {
    return (
      <div className="flex items-center justify-center h-80">
        <div className="text-center">
          <div className="mx-auto w-8 h-8 border-2 border-gray-200 border-t-primary-500 rounded-full animate-spin" />
          <p className="mt-3 text-sm text-gray-500 dark:text-gray-400">Carregando dados...</p>
        </div>
      </div>
    )
  }

  if (error && !dashboardData) {
    return (
      <div className="rounded-xl border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 p-6">
        <div className="flex items-center gap-2 mb-2">
          <AlertCircle className="w-5 h-5 text-red-500" />
          <span className="font-semibold text-red-600 dark:text-red-400">Erro ao carregar</span>
        </div>
        <p className="text-sm text-red-500">{error}</p>
        <button onClick={fetchDashboard} className="mt-4 px-4 py-2 bg-red-600 text-white text-sm rounded-lg hover:bg-red-500">
          Tentar novamente
        </button>
      </div>
    )
  }

  if (!dashboardData) return null

  // ── dados ─────────────────────────────────────────────────────────────────
  const cards = dashboardData?.cards
  const alerts = dashboardData?.alerts || []
  const fin = cards?.financial || {}
  const ops = cards?.operational || {}
  const vol = dashboardData?.volume || {}
  const pixToday = dashboardData?.pix_today || {}
  const visibleAlerts = alerts.filter(a => !dismissedAlerts.has(a.title))
  const growth = period === 'day' ? fin.growth_vs_yesterday : period === 'week' ? fin.growth_vs_last_week : fin.growth_vs_last_month
  const refLabel = period === 'day' ? 'ontem' : period === 'week' ? 'sem. passada' : 'mês anterior'
  const revenueNow = period === 'day' ? fin.revenue_today : period === 'week' ? fin.revenue_week : fin.revenue_month

  const onlineDrivers = drivers.filter(d => d.is_online || d.status === 'online' || d.status === 'available')
  const offlineDrivers = drivers.filter(d => !d.is_online && d.status !== 'online' && d.status !== 'available')

  const goalItems = goals ? [
    goals.revenue > 0 && { label: 'Receita mensal', current: fin.revenue_month || 0, goal: goals.revenue, fmtFn: fmt },
    goals.orders  > 0 && { label: 'Pedidos',        current: ops.orders_completed || 0, goal: goals.orders, fmtFn: v => `${v}` },
    vol?.meta_kg  > 0 && { label: 'Volume (kg)',    current: vol.total_kg || 0,  goal: vol.meta_kg, fmtFn: v => `${(v||0).toLocaleString('pt-BR')} kg` },
  ].filter(Boolean) : []

  // pedidos com coordenadas para o mapa
  const mapOrders = (dashboardData?.recent_orders || []).filter(o => o.latitude && o.longitude)
  const mapDrivers = drivers.filter(d => d.location?.latitude && d.location?.longitude)

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto">

      {/* ── Page header ───────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {getGreeting()},{' '}
            <span className="font-medium text-gray-700 dark:text-gray-300">
              {user?.full_name?.split(' ')[0] || 'Dono'}
            </span>
          </p>
          <h1 className="text-xl font-bold text-gray-900 dark:text-white mt-0.5">Visão Geral do Negócio</h1>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex bg-gray-100 dark:bg-gray-800 rounded-lg p-0.5">
            {[{ key: 'day', label: 'Hoje' }, { key: 'week', label: 'Semana' }, { key: 'month', label: 'Mês' }].map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setPeriod(key)}
                className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  period === key
                    ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-xs'
                    : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <button
            onClick={() => { fetchDashboard(); fetchDrivers() }}
            disabled={loading}
            className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* ── Alertas ───────────────────────────────────────────── */}
      {visibleAlerts.length > 0 && (
        <div className="space-y-2">
          {visibleAlerts.map(alert => {
            const isCrit = alert.type === 'critical'
            return (
              <div
                key={alert.title}
                className={`flex items-start gap-3 px-4 py-3 rounded-xl border text-sm ${
                  isCrit
                    ? 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800'
                    : 'bg-amber-50 border-amber-200 dark:bg-amber-900/20 dark:border-amber-800'
                }`}
              >
                {isCrit
                  ? <AlertCircle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                  : <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />}
                <div className="flex-1 min-w-0">
                  <p className={`font-semibold ${isCrit ? 'text-red-700 dark:text-red-400' : 'text-amber-700 dark:text-amber-400'}`}>{alert.title}</p>
                  <p className={`mt-0.5 text-xs ${isCrit ? 'text-red-600 dark:text-red-300' : 'text-amber-600 dark:text-amber-300'}`}>{alert.message}</p>
                </div>
                <button onClick={() => setDismissedAlerts(prev => new Set([...prev, alert.title]))} className="shrink-0 text-gray-400 hover:text-gray-600">
                  <X className="w-4 h-4" />
                </button>
              </div>
            )
          })}
        </div>
      )}

      {/* ── Hero revenue card ─────────────────────────────────── */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
          <div>
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">
              Faturamento · {period === 'day' ? 'Hoje' : period === 'week' ? 'Esta semana' : 'Este mês'}
            </p>
            <p className="text-4xl font-bold text-gray-900 dark:text-white tracking-tight">
              {fmt(revenueNow)}
            </p>
            {growth != null && (
              <div className={`mt-2 inline-flex items-center gap-1.5 text-sm font-medium px-3 py-1 rounded-full ${
                growth >= 0
                  ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400'
                  : 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400'
              }`}>
                {growth >= 0 ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
                {growthPhrase(growth, refLabel)}
              </div>
            )}
          </div>
          {lastUpdate && (
            <p className="text-xs text-gray-400 dark:text-gray-500 shrink-0">
              Atualizado às {lastUpdate.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
            </p>
          )}
        </div>
      </div>

      {/* ── KPI grid (5 cards: pedidos, ticket, cancelamentos, volume, PIX) ── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-5 gap-4">
        <KpiCard
          title="Pedidos Hoje"
          value={ops.orders_today ?? 0}
          sub={`${ops.orders_completed ?? 0} entregues`}
          icon={Package}
          iconBg="bg-blue-50 dark:bg-blue-900/20"
          iconColor="text-blue-500"
          trend={ops.orders_today != null && ops.orders_yesterday != null
            ? ((ops.orders_today - ops.orders_yesterday) / Math.max(ops.orders_yesterday, 1)) * 100
            : null}
          onClick={() => { setOpenModal('orders_today'); setModalData(fetchCardDetails('orders_today')) }}
          loading={loading}
        />
        <KpiCard
          title="Ticket Médio"
          value={fmt(fin.average_ticket)}
          sub="por pedido entregue"
          icon={DollarSign}
          iconBg="bg-green-50 dark:bg-green-900/20"
          iconColor="text-green-500"
          onClick={() => { setOpenModal('ticket'); setModalData(fetchCardDetails('ticket')) }}
          loading={loading}
        />
        <KpiCard
          title="Cancelamentos"
          value={ops.orders_cancelled_today ?? 0}
          sub={ops.orders_today > 0 ? `${(((ops.orders_cancelled_today || 0) / ops.orders_today) * 100).toFixed(1)}% taxa` : '0% taxa'}
          icon={XCircle}
          iconBg={(ops.orders_cancelled_today || 0) > 0 ? 'bg-red-50 dark:bg-red-900/20' : 'bg-gray-50 dark:bg-gray-700'}
          iconColor={(ops.orders_cancelled_today || 0) > 0 ? 'text-red-500' : 'text-gray-400'}
          onClick={() => { setOpenModal('cancelled'); setModalData(fetchCardDetails('cancelled')) }}
          loading={loading}
        />
        <KpiCard
          title="Volume Vendido"
          value={vol?.total_kg >= 1000
            ? `${(vol.total_ton || 0).toFixed(2)} ton`
            : `${(vol?.total_kg || 0).toLocaleString('pt-BR')} kg`}
          sub={`${(vol?.total_kg || 0).toLocaleString('pt-BR')} kg total`}
          icon={Scale}
          iconBg="bg-violet-50 dark:bg-violet-900/20"
          iconColor="text-violet-500"
          onClick={() => { setOpenModal('volume'); setModalData(fetchCardDetails('volume')) }}
          loading={loading}
        />
        {/* PIX Hoje */}
        <KpiCard
          title="PIX Hoje"
          value={fmt(pixToday.total ?? fin.pix_today ?? 0)}
          sub={`${pixToday.count ?? 0} transações`}
          icon={QrCode}
          iconBg="bg-emerald-50 dark:bg-emerald-900/20"
          iconColor="text-emerald-500"
          onClick={() => { setOpenModal('pix_today'); setModalData(fetchCardDetails('pix_today')) }}
          loading={loading}
        />
      </div>

      {/* ── Tendência + Top Formatos ───────────────────────────── */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">

        <div className="xl:col-span-2 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Tendência Mensal</h3>
          </div>
          <MonthlySparkline />
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Top Formatos</h3>
            <Zap className="w-4 h-4 text-gray-300 dark:text-gray-600" />
          </div>
          {dashboardData?.top_products?.length > 0 ? (
            <div className="space-y-3">
              {dashboardData.top_products.slice(0, 5).map((p, i) => (
                <div key={p.code} className="flex items-center gap-3">
                  <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${i === 0 ? 'bg-primary-100 text-primary-600 dark:bg-primary-900/30 dark:text-primary-400' : 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400'}`}>
                    {i + 1}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-gray-900 dark:text-white truncate">{p.name || p.code}</span>
                      <span className="text-xs text-gray-500 dark:text-gray-400 shrink-0 ml-2">{p.quantity} un</span>
                    </div>
                    <div className="h-1 w-full bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${i === 0 ? 'bg-primary-500' : 'bg-blue-400'}`}
                        style={{ width: `${(p.quantity / dashboardData.top_products[0].quantity) * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-400 dark:text-gray-500">Sem vendas registradas.</p>
          )}
        </div>
      </div>

      {/* ── Metas + Tempo Real ────────────────────────────────── */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        {goalItems.length > 0 && (
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
            <div className="flex items-center gap-2 mb-4">
              <Target className="w-4 h-4 text-gray-400" />
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Metas do Mês</h3>
            </div>
            <div className="space-y-4">
              {goalItems.map(g => <GoalBar key={g.label} {...g} />)}
            </div>
          </div>
        )}

        <div className={`bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden ${goalItems.length > 0 ? 'xl:col-span-2' : 'xl:col-span-3'}`}>
          <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-700 flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
            </span>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Pedidos em Tempo Real</h3>
          </div>
          <LiveOrdersPanel />
        </div>
      </div>

      {/* ── Drivers Online ────────────────────────────────────── */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Truck className="w-4 h-4 text-blue-500" />
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Motoristas</h3>
            <span className="ml-1 inline-flex items-center gap-1 text-xs font-medium bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400 px-2 py-0.5 rounded-full">
              <Wifi className="w-3 h-3" />
              {onlineDrivers.length} online
            </span>
            {offlineDrivers.length > 0 && (
              <span className="inline-flex items-center gap-1 text-xs font-medium bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400 px-2 py-0.5 rounded-full">
                <WifiOff className="w-3 h-3" />
                {offlineDrivers.length} offline
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowMap(v => !v)}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                showMap
                  ? 'bg-primary-50 border-primary-200 text-primary-700 dark:bg-primary-900/20 dark:border-primary-700 dark:text-primary-400'
                  : 'bg-white dark:bg-gray-700 border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-600'
              }`}
            >
              <MapPin className="w-3.5 h-3.5" />
              {showMap ? 'Ocultar mapa' : 'Ver mapa'}
            </button>
          </div>
        </div>

        {driversLoading && drivers.length === 0 ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-2">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-14 rounded-lg bg-gray-100 dark:bg-gray-700 animate-pulse" />
            ))}
          </div>
        ) : drivers.length === 0 ? (
          <p className="text-sm text-gray-400 dark:text-gray-500">Nenhum motorista cadastrado.</p>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-2">
            {[...onlineDrivers, ...offlineDrivers].map(d => (
              <DriverBadge key={d.id} driver={d} />
            ))}
          </div>
        )}

        {/* Mapa de rastreamento */}
        {showMap && (
          <div className="mt-4 rounded-xl overflow-hidden border border-gray-200 dark:border-gray-700">
            <DeliveryMap
              drivers={mapDrivers}
              orders={mapOrders}
              height="420px"
              autoRefresh
            />
          </div>
        )}
      </div>

      {/* ── Modal detalhes ─────────────────────────────────────── */}
      <CardDetailModal
        isOpen={openModal !== null}
        onClose={() => { setOpenModal(null); setModalData(null) }}
        title={modalData?.title || 'Detalhes'}
      >
        {modalData?.items ? (
          <div className="space-y-2">
            {modalData.items.map((item, idx) => (
              <div key={idx} className="flex items-center justify-between px-4 py-3 rounded-lg bg-gray-50 dark:bg-gray-700 border border-gray-100 dark:border-gray-600">
                <span className="text-sm text-gray-600 dark:text-gray-400">{item.label}</span>
                <span className="text-sm font-semibold text-gray-900 dark:text-white">{item.value}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-center text-gray-500 py-4">Carregando...</p>
        )}
      </CardDetailModal>

    </div>
  )
}
