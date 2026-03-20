/**
 * Dashboard Overview — Command Center Dark Premium
 */

import { useState, useEffect } from 'react'
import {
  DollarSign, TrendingUp, TrendingDown, Package, Clock, AlertCircle,
  RefreshCw, Activity, CheckCircle2, XCircle, CreditCard, Wallet,
  Zap, Target, Users, Award, Star
} from 'lucide-react'
import { apiRequest } from '../../utils/api'
import { useAuth } from '../../hooks/useAuth'
import CardDetailModal from './CardDetailModal'
import RevenueChart from './RevenueChart'

function CircleProgress({ pct, color }) {
  const r = 20
  const circ = +(2 * Math.PI * r).toFixed(3)
  const offset = +(circ - (Math.min(pct, 100) / 100) * circ).toFixed(3)
  return (
    <svg width="56" height="56" viewBox="0 0 56 56" style={{ flexShrink: 0 }}>
      <circle cx="28" cy="28" r={r} fill="none" strokeWidth="4" stroke="#1f2937" />
      <circle
        cx="28" cy="28" r={r} fill="none" strokeWidth="4"
        stroke={color}
        strokeDasharray={circ}
        strokeDashoffset={offset}
        strokeLinecap="round"
        transform="rotate(-90 28 28)"
        style={{ transition: 'stroke-dashoffset 0.7s ease' }}
      />
      <text x="28" y="33" textAnchor="middle" fontSize="11" fontWeight="700" fill="#f9fafb">
        {Math.min(pct, 100).toFixed(0)}%
      </text>
    </svg>
  )
}

export default function DashboardOverview() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [period, setPeriod] = useState('day')
  const [dashboardData, setDashboardData] = useState(null)
  const [lastUpdate, setLastUpdate] = useState(null)
  const [openModal, setOpenModal] = useState(null)
  const [modalData, setModalData] = useState(null)
  const [goals, setGoals] = useState(null)
  const [countdown, setCountdown] = useState(30)
  const { user } = useAuth()

  const getGreeting = () => {
    const hour = new Date().getHours()
    if (hour < 12) return 'Bom dia'
    if (hour < 18) return 'Boa tarde'
    return 'Boa noite'
  }

  useEffect(() => {
    fetchDashboard()
    fetchGoals()
    const interval = setInterval(fetchDashboard, 30000)
    return () => clearInterval(interval)
  }, [period])

  useEffect(() => {
    if (!lastUpdate) return
    setCountdown(30)
    const timer = setInterval(() => setCountdown(p => (p <= 1 ? 30 : p - 1)), 1000)
    return () => clearInterval(timer)
  }, [lastUpdate])

  const fetchGoals = async () => {
    try {
      const data = await apiRequest('owner/settings')
      setGoals(data?.monthly_goals || null)
    } catch (err) {
      console.error('Erro ao buscar metas:', err)
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
      if (err.message.includes('credenciais') || err.message.includes('401') || err.message.includes('Sessão expirada')) {
        setError('Sessão expirada. Por favor, faça login novamente.')
        setTimeout(() => { window.location.href = '/login' }, 2000)
      } else if (err.message.includes('403') || err.message.includes('Acesso negado')) {
        setError('Você não tem permissão para acessar este dashboard.')
      } else {
        setError(err.message || 'Erro ao carregar dashboard')
      }
    } finally {
      setLoading(false)
    }
  }

  const formatCurrency = (value) =>
    new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 2 }).format(value || 0)

  const formatPercent = (value) => {
    if (value === null || value === undefined || isNaN(value)) return '-'
    const n = parseFloat(value) || 0
    return `${n >= 0 ? '+' : ''}${n.toFixed(1)}%`
  }

  const getTrendIcon = (value) => {
    if (value > 0) return <TrendingUp className="h-3.5 w-3.5 text-emerald-400" />
    if (value < 0) return <TrendingDown className="h-3.5 w-3.5 text-red-400" />
    return <Activity className="h-3.5 w-3.5 text-gray-500" />
  }

  const getTrendColor = (value) => {
    if (value > 0) return 'text-emerald-400'
    if (value < 0) return 'text-red-400'
    return 'text-gray-500'
  }

  const handleCardClick = (cardType) => {
    setOpenModal(cardType)
    setModalData(fetchCardDetails(cardType))
  }

  const fetchCardDetails = (cardType) => {
    const cards = dashboardData?.cards
    const financial = dashboardData?.financial_breakdown
    const operational = dashboardData?.operational_performance
    switch (cardType) {
      case 'revenue_today': return { title: 'Faturamento Hoje', items: [
        { label: 'Total', value: formatCurrency(cards?.financial?.revenue_today || 0) },
        { label: 'Pedidos Pagos', value: cards?.operational?.orders_completed || 0 },
        { label: 'Ticket Médio', value: formatCurrency(cards?.financial?.average_ticket || 0) },
        { label: 'vs Ontem', value: formatPercent(cards?.financial?.growth_vs_yesterday || 0) },
      ]}
      case 'revenue_month': return { title: 'Faturamento Mensal', items: [
        { label: 'Total Mês', value: formatCurrency(cards?.financial?.revenue_month || 0) },
        { label: 'Receita Bruta', value: formatCurrency(financial?.gross_revenue || 0) },
        { label: 'Receita Líquida', value: formatCurrency(financial?.net_revenue || 0) },
        { label: 'vs Mês Anterior', value: formatPercent(cards?.financial?.growth_vs_last_month || 0) },
      ]}
      case 'average_ticket': return { title: 'Ticket Médio', items: [
        { label: 'Ticket Médio', value: formatCurrency(cards?.financial?.average_ticket || 0) },
        { label: 'Total Pedidos', value: cards?.operational?.orders_completed || 0 },
        { label: 'Faturamento', value: formatCurrency(cards?.financial?.revenue_today || 0) },
      ]}
      case 'orders_today': return { title: 'Pedidos Hoje', items: [
        { label: 'Total', value: cards?.operational?.orders_today || 0 },
        { label: 'Ontem', value: cards?.operational?.orders_yesterday || 0 },
        { label: 'Concluídos', value: cards?.operational?.orders_completed || 0 },
        { label: 'Cancelados', value: cards?.operational?.orders_cancelled_today || 0 },
      ]}
      case 'orders_completed': return { title: 'Pedidos Concluídos', items: [
        { label: 'Total Concluídos', value: cards?.operational?.orders_completed || 0 },
        { label: 'Taxa', value: (cards?.operational?.orders_today || 0) > 0 ? `${(((cards?.operational?.orders_completed || 0) / (cards?.operational?.orders_today || 1)) * 100).toFixed(1)}%` : '0%' },
        { label: 'Tempo Médio', value: cards?.operational?.average_delivery_time ? `${Math.round(cards.operational.average_delivery_time)} min` : '-' },
        { label: 'No Prazo', value: `${(cards?.operational?.on_time_delivery_rate || 0).toFixed(1)}%` },
      ]}
      case 'orders_cancelled': return { title: 'Cancelamentos', items: [
        { label: 'Cancelados Hoje', value: cards?.operational?.orders_cancelled_today || 0 },
        { label: 'Total', value: cards?.operational?.orders_cancelled || 0 },
        { label: 'Impacto', value: formatCurrency(financial?.cancelled_revenue || 0) },
      ]}
      case 'delivery_time': return { title: 'Tempo de Entrega', items: [
        { label: 'Tempo Médio', value: cards?.operational?.average_delivery_time ? `${Math.round(cards.operational.average_delivery_time)} min` : '-' },
        { label: 'No Prazo', value: `${(cards?.operational?.on_time_delivery_rate || 0).toFixed(1)}%` },
        { label: 'Atrasadas', value: operational?.late_deliveries || 0 },
      ]}
      case 'card_payment': return { title: 'Pagamento em Cartão', items: [
        { label: 'Percentual', value: `${(cards?.payment?.card_percentage || 0).toFixed(1)}%` },
        { label: 'Pedidos', value: cards?.payment?.card_count || 0 },
        { label: 'Valor Total', value: formatCurrency(cards?.payment?.card_value || 0) },
      ]}
      case 'cash_payment': return { title: 'Pagamento em Dinheiro', items: [
        { label: 'Percentual', value: `${(cards?.payment?.cash_percentage || 0).toFixed(1)}%` },
        { label: 'Pedidos', value: cards?.payment?.cash_count || 0 },
        { label: 'Valor Total', value: formatCurrency(cards?.payment?.cash_value || 0) },
      ]}
      case 'approval_rate': return { title: 'Taxa de Aprovação', items: [
        { label: 'Taxa', value: `${(cards?.payment?.approval_rate || 0).toFixed(1)}%` },
        { label: 'Pagos', value: cards?.payment?.paid_count || 0 },
        { label: 'Pendentes', value: cards?.payment?.pending_count || 0 },
      ]}
      default: return { title: 'Detalhes', items: [] }
    }
  }

  // ── LOADING ────────────────────────────────────────────────────────────────
  if (loading && !dashboardData) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-gray-700 border-t-emerald-500" />
          <p className="mt-4 text-sm text-gray-500 tracking-widest uppercase">Carregando central...</p>
        </div>
      </div>
    )
  }

  // ── ERROR ──────────────────────────────────────────────────────────────────
  if (error && !dashboardData) {
    return (
      <div className="rounded-2xl border border-red-500/30 bg-red-950/40 p-6">
        <div className="flex items-center gap-2">
          <AlertCircle className="h-5 w-5 text-red-400" />
          <span className="font-semibold text-red-300">Erro ao carregar dashboard</span>
        </div>
        <p className="mt-2 text-sm text-red-400">{error}</p>
        <button onClick={fetchDashboard} className="mt-4 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-500">
          Tentar novamente
        </button>
      </div>
    )
  }

  if (!dashboardData) return null

  const cards = dashboardData?.cards
  const alerts = dashboardData?.alerts || []

  // projeção do mês
  const now = new Date()
  const dayOfMonth = now.getDate()
  const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate()
  const revenueMonth = cards?.financial?.revenue_month || 0
  const projection = dayOfMonth > 0 ? (revenueMonth / dayOfMonth) * daysInMonth : 0

  return (
    <div className="space-y-4">

      {/* ── HEADER ──────────────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-2xl font-black tracking-tight text-white">
              {getGreeting()},{' '}
              <span className="text-emerald-400">
                {user?.full_name?.split(' ')[0] || user?.username || 'Dono'}
              </span>
            </h1>
            <span className="flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-xs font-bold text-emerald-400 uppercase tracking-widest">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Ao Vivo
            </span>
          </div>
          <p className="mt-1 text-xs text-gray-500">
            {now.toLocaleDateString('pt-BR', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
            {lastUpdate && (
              <> · atualizado {lastUpdate.toLocaleTimeString('pt-BR')} ·{' '}
                <span className="text-emerald-500">próx. em {countdown}s</span>
              </>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border border-gray-700 bg-gray-900/80 p-1 gap-1">
            {[{ key: 'day', label: 'Dia' }, { key: 'week', label: 'Semana' }, { key: 'month', label: 'Mês' }].map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setPeriod(key)}
                className={`rounded-md px-4 py-1.5 text-xs font-bold transition-all ${
                  period === key
                    ? 'bg-emerald-600 text-white shadow-sm shadow-emerald-500/30'
                    : 'text-gray-400 hover:text-white'
                }`}
              >{label}</button>
            ))}
          </div>
          <button
            onClick={fetchDashboard}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-700 bg-gray-900/80 px-3 py-2 text-xs font-medium text-gray-400 hover:text-white hover:border-gray-600 disabled:opacity-40 transition-all"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            Atualizar
          </button>
        </div>
      </div>

      {/* ── ALERTAS ─────────────────────────────────────────────────────────── */}
      {alerts.length > 0 && (
        <div className="space-y-2">
          {alerts.map((alert, idx) => (
            <div key={idx} className={`flex items-start gap-3 rounded-xl border-l-4 p-4 ${
              alert.type === 'critical'
                ? 'border-l-red-500 border border-red-500/20 bg-red-950/30'
                : 'border-l-amber-500 border border-amber-500/20 bg-amber-950/20'
            }`}>
              <AlertCircle className={`h-5 w-5 mt-0.5 flex-shrink-0 ${alert.type === 'critical' ? 'text-red-400' : 'text-amber-400'}`} />
              <div>
                <div className="font-semibold text-white">{alert.title}</div>
                <div className="mt-0.5 text-sm text-gray-400">{alert.message}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── HERO: 3 GRANDES MÉTRICAS ────────────────────────────────────────── */}
      <div className="grid gap-4 sm:grid-cols-3">

        {/* Faturamento */}
        <button
          onClick={() => handleCardClick('revenue_today')}
          className="relative overflow-hidden rounded-2xl border border-emerald-500/20 bg-gray-900 p-6 text-left shadow-lg shadow-emerald-500/10 transition-all hover:-translate-y-1 hover:shadow-emerald-500/20 hover:border-emerald-500/40"
        >
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/8 via-transparent to-transparent pointer-events-none" />
          <div className="absolute -right-6 -bottom-6 h-28 w-28 rounded-full bg-emerald-500/5 pointer-events-none" />
          <div className="relative">
            <div className="flex items-center justify-between mb-4">
              <p className="text-xs font-bold uppercase tracking-widest text-emerald-400/80">Faturamento Hoje</p>
              <div className="rounded-lg bg-emerald-500/10 p-2 ring-1 ring-emerald-500/20">
                <DollarSign className="h-4 w-4 text-emerald-400" />
              </div>
            </div>
            <p className="text-4xl font-black tracking-tight text-white">
              {formatCurrency(cards?.financial?.revenue_today || 0)}
            </p>
            {cards?.financial?.growth_vs_yesterday !== undefined && (
              <div className={`mt-2 flex items-center gap-1.5 text-sm font-semibold ${getTrendColor(cards.financial.growth_vs_yesterday)}`}>
                {getTrendIcon(cards.financial.growth_vs_yesterday)}
                {formatPercent(cards.financial.growth_vs_yesterday)} vs ontem
              </div>
            )}
            <div className="mt-4 border-t border-gray-700/50 pt-3 flex justify-between text-xs">
              <span className="text-gray-500">Este mês</span>
              <span className="font-semibold text-gray-300">{formatCurrency(cards?.financial?.revenue_month || 0)}</span>
            </div>
          </div>
        </button>

        {/* Pedidos */}
        <button
          onClick={() => handleCardClick('orders_today')}
          className="relative overflow-hidden rounded-2xl border border-blue-500/20 bg-gray-900 p-6 text-left shadow-lg shadow-blue-500/10 transition-all hover:-translate-y-1 hover:shadow-blue-500/20 hover:border-blue-500/40"
        >
          <div className="absolute inset-0 bg-gradient-to-br from-blue-500/8 via-transparent to-transparent pointer-events-none" />
          <div className="absolute -right-6 -bottom-6 h-28 w-28 rounded-full bg-blue-500/5 pointer-events-none" />
          <div className="relative">
            <div className="flex items-center justify-between mb-4">
              <p className="text-xs font-bold uppercase tracking-widest text-blue-400/80">Pedidos Hoje</p>
              <div className="rounded-lg bg-blue-500/10 p-2 ring-1 ring-blue-500/20">
                <Package className="h-4 w-4 text-blue-400" />
              </div>
            </div>
            <p className="text-4xl font-black tracking-tight text-white">
              {cards?.operational?.orders_today || 0}
            </p>
            <div className="mt-2 flex items-center gap-1.5 text-sm text-gray-400">
              <span className="text-emerald-400 font-semibold">{cards?.operational?.orders_completed || 0} entregues</span>
              <span>·</span>
              <span className="text-red-400">{cards?.operational?.orders_cancelled_today || 0} cancelados</span>
            </div>
            <div className="mt-4 border-t border-gray-700/50 pt-3 flex justify-between text-xs">
              <span className="text-gray-500">Ontem</span>
              <span className="font-semibold text-gray-300">{cards?.operational?.orders_yesterday || 0} pedidos</span>
            </div>
          </div>
        </button>

        {/* Ticket Médio */}
        <button
          onClick={() => handleCardClick('average_ticket')}
          className="relative overflow-hidden rounded-2xl border border-violet-500/20 bg-gray-900 p-6 text-left shadow-lg shadow-violet-500/10 transition-all hover:-translate-y-1 hover:shadow-violet-500/20 hover:border-violet-500/40"
        >
          <div className="absolute inset-0 bg-gradient-to-br from-violet-500/8 via-transparent to-transparent pointer-events-none" />
          <div className="absolute -right-6 -bottom-6 h-28 w-28 rounded-full bg-violet-500/5 pointer-events-none" />
          <div className="relative">
            <div className="flex items-center justify-between mb-4">
              <p className="text-xs font-bold uppercase tracking-widest text-violet-400/80">Ticket Médio</p>
              <div className="rounded-lg bg-violet-500/10 p-2 ring-1 ring-violet-500/20">
                <Activity className="h-4 w-4 text-violet-400" />
              </div>
            </div>
            <p className="text-4xl font-black tracking-tight text-white">
              {formatCurrency(cards?.financial?.average_ticket || 0)}
            </p>
            <p className="mt-2 text-sm text-gray-500">Por pedido</p>
            <div className="mt-4 border-t border-gray-700/50 pt-3 flex justify-between text-xs">
              <span className="text-gray-500">Cresc. semanal</span>
              <span className={`font-bold ${getTrendColor(cards?.financial?.growth_vs_last_week || 0)}`}>
                {formatPercent(cards?.financial?.growth_vs_last_week || 0)}
              </span>
            </div>
          </div>
        </button>

      </div>

      {/* ── SECUNDÁRIO: 4 CARDS ─────────────────────────────────────────────── */}
      <div className="grid gap-3 grid-cols-2 lg:grid-cols-4">

        <button onClick={() => handleCardClick('orders_completed')}
          className="rounded-xl border border-emerald-500/15 bg-gray-900 px-4 py-4 text-left hover:border-emerald-500/30 hover:bg-gray-800/80 transition-all">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Concluídos</p>
            <CheckCircle2 className="h-4 w-4 text-emerald-500/60" />
          </div>
          <p className="mt-2 text-2xl font-black text-emerald-400">{cards?.operational?.orders_completed || 0}</p>
          <p className="mt-1 text-xs text-gray-600">Total entregues</p>
        </button>

        <button onClick={() => handleCardClick('orders_cancelled')}
          className="rounded-xl border border-red-500/15 bg-gray-900 px-4 py-4 text-left hover:border-red-500/30 hover:bg-gray-800/80 transition-all">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Cancelados</p>
            <XCircle className="h-4 w-4 text-red-500/60" />
          </div>
          <p className="mt-2 text-2xl font-black text-red-400">{cards?.operational?.orders_cancelled_today || 0}</p>
          <p className="mt-1 text-xs text-gray-600">Hoje · total: {cards?.operational?.orders_cancelled || 0}</p>
        </button>

        <button onClick={() => handleCardClick('delivery_time')}
          className="rounded-xl border border-amber-500/15 bg-gray-900 px-4 py-4 text-left hover:border-amber-500/30 hover:bg-gray-800/80 transition-all">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Tempo Médio</p>
            <Clock className="h-4 w-4 text-amber-500/60" />
          </div>
          <p className="mt-2 text-2xl font-black text-amber-400">
            {cards?.operational?.average_delivery_time ? `${Math.round(cards.operational.average_delivery_time)}min` : '--'}
          </p>
          <p className="mt-1 text-xs text-gray-600">
            {cards?.operational?.on_time_delivery_rate !== undefined
              ? `${(cards.operational.on_time_delivery_rate || 0).toFixed(0)}% no prazo`
              : 'por entrega'}
          </p>
        </button>

        <button onClick={() => handleCardClick('approval_rate')}
          className="rounded-xl border border-cyan-500/15 bg-gray-900 px-4 py-4 text-left hover:border-cyan-500/30 hover:bg-gray-800/80 transition-all">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Aprovação</p>
            <Zap className="h-4 w-4 text-cyan-500/60" />
          </div>
          <p className="mt-2 text-2xl font-black text-cyan-400">
            {(cards?.payment?.approval_rate || 0).toFixed(0)}%
          </p>
          <p className="mt-1 text-xs text-gray-600">Taxa de pagamentos</p>
        </button>

      </div>

      {/* ── GRÁFICO ─────────────────────────────────────────────────────────── */}
      {dashboardData?.revenue_chart && (
        <div className="rounded-2xl border border-gray-700/40 bg-gray-900 p-5">
          <div className="mb-4 flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-blue-400" />
            <span className="text-xs font-bold uppercase tracking-widest text-gray-400">Receita Recente</span>
          </div>
          <div className="h-56">
            <RevenueChart data={dashboardData.revenue_chart} />
          </div>
        </div>
      )}

      {/* ── LINHA INFERIOR: Pagamentos | Metas | Destaques ──────────────────── */}
      <div className="grid gap-4 lg:grid-cols-3">

        {/* Pagamentos */}
        <div className="rounded-2xl border border-gray-700/40 bg-gray-900 p-5">
          <div className="mb-4 flex items-center gap-2">
            <CreditCard className="h-4 w-4 text-violet-400" />
            <span className="text-xs font-bold uppercase tracking-widest text-gray-400">Pagamentos</span>
          </div>
          <div className="space-y-4">
            <button onClick={() => handleCardClick('card_payment')} className="w-full text-left hover:opacity-80 transition-opacity">
              <div className="flex justify-between text-xs mb-1">
                <span className="text-gray-400 flex items-center gap-1.5"><CreditCard className="h-3 w-3 text-blue-400" /> Cartão</span>
                <span className="font-bold text-white">{(cards?.payment?.card_percentage || 0).toFixed(0)}%</span>
              </div>
              <div className="h-2 rounded-full bg-gray-800 overflow-hidden">
                <div className="h-2 rounded-full bg-gradient-to-r from-blue-500 to-blue-400 transition-all duration-700"
                  style={{ width: `${cards?.payment?.card_percentage || 0}%` }} />
              </div>
              <p className="mt-1 text-xs text-gray-600">{cards?.payment?.card_count || 0} pedidos</p>
            </button>
            <button onClick={() => handleCardClick('cash_payment')} className="w-full text-left hover:opacity-80 transition-opacity">
              <div className="flex justify-between text-xs mb-1">
                <span className="text-gray-400 flex items-center gap-1.5"><Wallet className="h-3 w-3 text-emerald-400" /> Dinheiro</span>
                <span className="font-bold text-white">{(cards?.payment?.cash_percentage || 0).toFixed(0)}%</span>
              </div>
              <div className="h-2 rounded-full bg-gray-800 overflow-hidden">
                <div className="h-2 rounded-full bg-gradient-to-r from-emerald-500 to-emerald-400 transition-all duration-700"
                  style={{ width: `${cards?.payment?.cash_percentage || 0}%` }} />
              </div>
              <p className="mt-1 text-xs text-gray-600">{cards?.payment?.cash_count || 0} pedidos</p>
            </button>
          </div>
        </div>

        {/* Metas */}
        {goals && (goals.revenue > 0 || goals.orders > 0 || goals.new_customers > 0) ? (
          <div className="rounded-2xl border border-gray-700/40 bg-gray-900 p-5">
            <div className="mb-4 flex items-center gap-2">
              <Target className="h-4 w-4 text-amber-400" />
              <span className="text-xs font-bold uppercase tracking-widest text-gray-400">Metas do Mês</span>
            </div>
            <div className="space-y-4">
              {goals.revenue > 0 && (() => {
                const current = cards?.financial?.revenue_month || 0
                const pct = Math.min((current / goals.revenue) * 100, 100)
                const color = pct >= 100 ? '#10b981' : pct >= 70 ? '#f59e0b' : '#3b82f6'
                return (
                  <div className="flex items-center gap-3">
                    <CircleProgress pct={pct} color={color} />
                    <div className="min-w-0">
                      <p className="text-xs font-semibold text-gray-300">Receita</p>
                      <p className="text-xs text-gray-500 truncate">{formatCurrency(current)} / {formatCurrency(goals.revenue)}</p>
                    </div>
                  </div>
                )
              })()}
              {goals.orders > 0 && (() => {
                const current = cards?.operational?.orders_completed || 0
                const pct = Math.min((current / goals.orders) * 100, 100)
                const color = pct >= 100 ? '#10b981' : pct >= 70 ? '#f59e0b' : '#3b82f6'
                return (
                  <div className="flex items-center gap-3">
                    <CircleProgress pct={pct} color={color} />
                    <div className="min-w-0">
                      <p className="text-xs font-semibold text-gray-300">Pedidos</p>
                      <p className="text-xs text-gray-500">{current} / {goals.orders}</p>
                    </div>
                  </div>
                )
              })()}
              {goals.new_customers > 0 && (() => {
                const current = dashboardData?.financial_breakdown?.new_customers_count || 0
                const pct = Math.min((current / goals.new_customers) * 100, 100)
                const color = pct >= 100 ? '#10b981' : pct >= 70 ? '#f59e0b' : '#8b5cf6'
                return (
                  <div className="flex items-center gap-3">
                    <CircleProgress pct={pct} color={color} />
                    <div className="min-w-0">
                      <p className="text-xs font-semibold text-gray-300">Novos Clientes</p>
                      <p className="text-xs text-gray-500">{current} / {goals.new_customers}</p>
                    </div>
                  </div>
                )
              })()}
            </div>
          </div>
        ) : (
          <div className="rounded-2xl border border-gray-700/40 bg-gray-900 p-5 flex items-center justify-center">
            <p className="text-xs text-gray-600">Configure metas em Configurações</p>
          </div>
        )}

        {/* Destaques */}
        <div className="rounded-2xl border border-gray-700/40 bg-gray-900 p-5">
          <div className="mb-4 flex items-center gap-2">
            <Star className="h-4 w-4 text-amber-400" />
            <span className="text-xs font-bold uppercase tracking-widest text-gray-400">Destaques</span>
          </div>
          <div className="space-y-3">

            {/* Top Entregador */}
            {dashboardData?.driver_performance?.[0] && (
              <div className="flex items-center gap-3 rounded-xl border border-amber-500/15 bg-amber-500/5 px-3 py-3">
                <div className="rounded-lg bg-amber-500/10 p-2 ring-1 ring-amber-500/20">
                  <Award className="h-4 w-4 text-amber-400" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-xs text-gray-500 uppercase tracking-wider">Top Entregador</p>
                  <p className="font-bold text-white truncate text-sm">{dashboardData.driver_performance[0].driver_name || 'Sem nome'}</p>
                  <p className="text-xs text-gray-500">
                    {dashboardData.driver_performance[0].deliveries_count} entregas
                    {dashboardData.driver_performance[0].on_time_rate !== undefined && (
                      <> · <span className="text-emerald-400">{(dashboardData.driver_performance[0].on_time_rate || 0).toFixed(0)}% no prazo</span></>
                    )}
                  </p>
                </div>
              </div>
            )}

            {/* Produto mais vendido */}
            {dashboardData?.top_products?.[0] && (
              <div className="flex items-center gap-3 rounded-xl border border-emerald-500/15 bg-emerald-500/5 px-3 py-3">
                <div className="rounded-lg bg-emerald-500/10 p-2 ring-1 ring-emerald-500/20">
                  <Package className="h-4 w-4 text-emerald-400" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-xs text-gray-500 uppercase tracking-wider">Top Produto</p>
                  <p className="font-bold text-white truncate text-sm">
                    {dashboardData.top_products[0].product_name || dashboardData.top_products[0].product_code}
                  </p>
                  <p className="text-xs text-gray-500">{dashboardData.top_products[0].quantity} un. · {formatCurrency(dashboardData.top_products[0].revenue)}</p>
                </div>
              </div>
            )}

            {/* Projeção */}
            <div className="flex items-center gap-3 rounded-xl border border-blue-500/15 bg-blue-500/5 px-3 py-3">
              <div className="rounded-lg bg-blue-500/10 p-2 ring-1 ring-blue-500/20">
                <TrendingUp className="h-4 w-4 text-blue-400" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs text-gray-500 uppercase tracking-wider">Projeção do Mês</p>
                <p className="font-bold text-white text-sm">{formatCurrency(projection)}</p>
                <p className="text-xs text-gray-500">
                  Dia {dayOfMonth}/{daysInMonth}
                  {goals?.revenue > 0 && (
                    <> · <span className={projection >= goals.revenue ? 'text-emerald-400' : 'text-amber-400'}>
                      {((projection / goals.revenue) * 100).toFixed(0)}% da meta
                    </span></>
                  )}
                </p>
              </div>
            </div>

          </div>
        </div>

      </div>

      {/* ── MODAL ───────────────────────────────────────────────────────────── */}
      <CardDetailModal
        isOpen={openModal !== null}
        onClose={() => { setOpenModal(null); setModalData(null) }}
        title={modalData?.title || 'Detalhes'}
      >
        {modalData?.items ? (
          <div className="space-y-2">
            {modalData.items.map((item, idx) => (
              <div key={idx} className="flex items-center justify-between rounded-xl border border-gray-700 bg-gray-800/60 px-4 py-3">
                <span className="text-sm text-gray-400">{item.label}</span>
                <span className="text-sm font-bold text-white">{item.value}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center text-gray-500">Carregando...</div>
        )}
      </CardDetailModal>

    </div>
  )
}
