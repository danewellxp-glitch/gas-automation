/**
 * Dashboard Overview — Painel Executivo do Dono
 * Redesenhado para resposta imediata, contexto em tudo, decisão rápida
 */

import { useState, useEffect } from 'react'
import {
  DollarSign, TrendingUp, TrendingDown, Package, AlertCircle,
  RefreshCw, Activity, XCircle, CreditCard, Wallet,
  Zap, Target, X,
} from 'lucide-react'
import { apiRequest } from '../../utils/api'
import { useAuth } from '../../hooks/useAuth'
import CardDetailModal from './CardDetailModal'
import LiveOrdersPanel from './LiveOrdersPanel'
import MonthlySparkline from './MonthlySparkline'

export default function DashboardOverview() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [period, setPeriod] = useState('day')
  const [dashboardData, setDashboardData] = useState(null)
  const [lastUpdate, setLastUpdate] = useState(null)
  const [openModal, setOpenModal] = useState(null)
  const [modalData, setModalData] = useState(null)
  const [goals, setGoals] = useState(null)
  const [dismissedAlerts, setDismissedAlerts] = useState(new Set())
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
    const interval = setInterval(fetchDashboard, 30000)
    return () => clearInterval(interval)
  }, [period])

  const fetchGoals = async () => {
    try {
      const data = await apiRequest('owner/settings')
      setGoals(data?.monthly_goals || null)
    } catch (_) {}
  }

  const fetchDashboard = async () => {
    try {
      setLoading(true)
      setError('')
      const data = await apiRequest(`owner/dashboard?period=${period}`)
      setDashboardData(data)
      setLastUpdate(new Date())
    } catch (err) {
      if (err.message?.includes('401') || err.message?.includes('Sessão')) {
        setError('Sessão expirada.')
        setTimeout(() => { window.location.href = '/login' }, 2000)
      } else if (err.message?.includes('403')) {
        setError('Sem permissão para acessar este dashboard.')
      } else {
        setError(err.message || 'Erro ao carregar dashboard')
      }
    } finally {
      setLoading(false)
    }
  }

  const fmt = (v) =>
    new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(v || 0)

  const fmtFull = (v) =>
    new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 2 }).format(v || 0)

  const fmtPct = (v) => {
    if (v == null || isNaN(v)) return '-'
    const n = parseFloat(v) || 0
    return `${n >= 0 ? '+' : ''}${n.toFixed(1)}%`
  }

  const fetchCardDetails = (cardType) => {
    const c = dashboardData?.cards
    const fin = c?.financial || {}
    const ops = c?.operational || {}
    const pay = c?.payment || {}
    const fb = dashboardData?.financial_breakdown || {}
    const op = dashboardData?.operational_performance || {}
    switch (cardType) {
      case 'revenue_today':
        return { title: 'Faturamento Hoje', items: [
          { label: 'Total', value: fmtFull(fin.revenue_today) },
          { label: 'Pedidos pagos', value: ops.orders_completed || 0 },
          { label: 'Ticket médio', value: fmtFull(fin.average_ticket) },
          { label: 'Crescimento vs ontem', value: fmtPct(fin.growth_vs_yesterday) },
        ]}
      case 'revenue_month':
        return { title: 'Faturamento Mensal', items: [
          { label: 'Total', value: fmtFull(fin.revenue_month) },
          { label: 'Receita bruta', value: fmtFull(fb.gross_revenue) },
          { label: 'Receita líquida', value: fmtFull(fb.net_revenue) },
          { label: 'Crescimento vs mês ant.', value: fmtPct(fin.growth_vs_last_month) },
          { label: 'Pedidos totais', value: ops.orders_completed || 0 },
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
          { label: 'Taxa', value: ops.orders_today > 0 ? `${(((ops.orders_cancelled_today||0)/ops.orders_today)*100).toFixed(1)}%` : '0%' },
          { label: 'Impacto financeiro', value: fmtFull(fb.cancelled_revenue) },
        ]}
      case 'ticket':
        return { title: 'Ticket Médio', items: [
          { label: 'Ticket médio', value: fmtFull(fin.average_ticket) },
          { label: 'Pedidos entregues', value: ops.orders_completed || 0 },
          { label: 'Faturamento total', value: fmtFull(fin.revenue_today) },
        ]}
      default:
        return { title: 'Detalhes', items: [] }
    }
  }

  // ── LOADING ──────────────────────────────────────────────
  if (loading && !dashboardData) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="mx-auto h-10 w-10 animate-spin rounded-full border-4 border-gray-200 border-t-emerald-500" />
          <p className="mt-4 text-gray-400 text-sm">Carregando...</p>
        </div>
      </div>
    )
  }

  if (error && !dashboardData) {
    return (
      <div className="rounded-xl border border-red-300 dark:border-red-500/30 bg-red-50 dark:bg-red-950/40 p-6">
        <div className="flex items-center gap-2 mb-2">
          <AlertCircle className="h-5 w-5 text-red-500" />
          <span className="font-semibold text-red-600 dark:text-red-400">Erro ao carregar</span>
        </div>
        <p className="text-sm text-red-500">{error}</p>
        <button onClick={fetchDashboard} className="mt-4 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-500">
          Tentar novamente
        </button>
      </div>
    )
  }

  if (!dashboardData) return null

  // ── DADOS ─────────────────────────────────────────────────
  const cards = dashboardData?.cards
  const alerts = dashboardData?.alerts || []
  const fin = cards?.financial || {}
  const ops = cards?.operational || {}
  const pay = cards?.payment || {}
  const visibleAlerts = alerts.filter(a => !dismissedAlerts.has(a.title))

  // ── STATUS GERAL ─────────────────────────────────────────
  const growth = period === 'day' ? fin.growth_vs_yesterday : period === 'week' ? fin.growth_vs_last_week : fin.growth_vs_last_month
  const cancelRate = ops.orders_today > 0 ? ((ops.orders_cancelled_today || 0) / ops.orders_today) * 100 : 0
  const hasCritical = alerts.some(a => a.type === 'critical')

  const status = hasCritical || (growth || 0) <= -20 || cancelRate > 20
    ? 'critico'
    : (growth || 0) < 0 || cancelRate > 10 || visibleAlerts.length > 0
    ? 'atencao'
    : 'otimo'

  const STATUS = {
    otimo:   { label: 'DIA BOM',  gradient: 'from-emerald-600 via-teal-600 to-cyan-700',   badgeBg: 'bg-white/20', badgeText: 'text-white', dot: 'bg-emerald-300' },
    atencao: { label: 'ATENÇÃO',  gradient: 'from-amber-600 via-orange-600 to-amber-700',  badgeBg: 'bg-white/20', badgeText: 'text-white', dot: 'bg-amber-300' },
    critico: { label: 'CRÍTICO',  gradient: 'from-red-700 via-rose-600 to-red-700',        badgeBg: 'bg-white/20', badgeText: 'text-white', dot: 'bg-red-300' },
  }
  const sc = STATUS[status]

  // ── FRASES DE CRESCIMENTO ─────────────────────────────────
  const growthPhrase = (g, ref) => {
    const n = parseFloat(g) || 0
    if (n > 30)  return `Alta forte: +${n.toFixed(0)}% vs ${ref}`
    if (n > 5)   return `Cresceu ${n.toFixed(1)}% vs ${ref}`
    if (n > 0)   return `Leve alta de ${n.toFixed(1)}% vs ${ref}`
    if (n === 0) return `Igual a ${ref}`
    if (n > -10) return `Caiu ${Math.abs(n).toFixed(1)}% vs ${ref}`
    if (n > -30) return `Queda de ${Math.abs(n).toFixed(0)}% vs ${ref}`
    return `Queda forte: ${Math.abs(n).toFixed(0)}% vs ${ref}`
  }
  const refLabel = period === 'day' ? 'ontem' : period === 'week' ? 'semana passada' : 'mês anterior'
  const revenueNow = period === 'day' ? fin.revenue_today : period === 'week' ? fin.revenue_week : fin.revenue_month

  // ── META DO MÊS ───────────────────────────────────────────
  const goalRevPct = goals?.revenue > 0 ? Math.min(((fin.revenue_month || 0) / goals.revenue) * 100, 100) : null
  const goalRevLeft = goals?.revenue > 0 ? Math.max(goals.revenue - (fin.revenue_month || 0), 0) : null

  return (
    <div className="space-y-4">

      {/* ════════════════════════════════════════════════════════
           1. HERO EXECUTIVO — STATUS + RECEITA + META
      ════════════════════════════════════════════════════════ */}
      <div className={`relative overflow-hidden rounded-2xl bg-gradient-to-br ${sc.gradient} p-6 sm:p-8 shadow-2xl`}>
        {/* Decorações */}
        <div className="pointer-events-none absolute -top-20 -right-20 h-72 w-72 rounded-full bg-white/10 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-20 -left-20 h-72 w-72 rounded-full bg-white/5 blur-3xl" />

        <div className="relative space-y-5">

          {/* Linha topo: saudação + status + controles */}
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="flex items-center gap-2 mb-0.5">
                <span className={`flex items-center gap-1.5 rounded-full ${sc.badgeBg} border border-white/30 px-3 py-1 text-xs font-black uppercase tracking-widest ${sc.badgeText}`}>
                  <span className={`h-2 w-2 rounded-full ${sc.dot} animate-pulse`} />
                  {sc.label}
                </span>
              </div>
              <p className="text-sm text-white/70 mt-1">
                {getGreeting()}, <span className="font-bold text-white">{user?.full_name?.split(' ')[0] || 'Dono'}</span>
              </p>
              <p className="text-xs text-white/50">
                {new Date().toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' })}
                {lastUpdate && <span className="ml-2">· {lastUpdate.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}</span>}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex rounded-lg border border-white/20 bg-white/10 p-0.5 gap-0.5">
                {[{ key: 'day', label: 'Hoje' }, { key: 'week', label: 'Semana' }, { key: 'month', label: 'Mês' }].map(({ key, label }) => (
                  <button key={key} onClick={() => setPeriod(key)}
                    className={`rounded-md px-3 py-1.5 text-xs font-bold transition-all ${period === key ? 'bg-white text-gray-800 shadow' : 'text-white/70 hover:text-white hover:bg-white/10'}`}>
                    {label}
                  </button>
                ))}
              </div>
              <button onClick={fetchDashboard} disabled={loading}
                className="rounded-lg border border-white/20 bg-white/10 p-2 text-white/70 hover:text-white disabled:opacity-40 transition-all">
                <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>

          {/* Faturamento + crescimento */}
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-white/60 mb-1">
              Faturamento {period === 'day' ? 'Hoje' : period === 'week' ? 'Esta Semana' : 'Este Mês'}
            </p>
            <p className="text-5xl sm:text-6xl font-black text-white tracking-tight leading-none drop-shadow">
              {fmt(revenueNow)}
            </p>
            {growth != null && (
              <p className={`mt-2 text-sm font-semibold flex items-center gap-1.5 ${(growth || 0) >= 0 ? 'text-white/90' : 'text-red-200'}`}>
                {(growth || 0) >= 0
                  ? <TrendingUp className="h-4 w-4 shrink-0" />
                  : <TrendingDown className="h-4 w-4 shrink-0" />
                }
                {growthPhrase(growth, refLabel)}
              </p>
            )}
            {revenueNow === 0 && (
              <p className="mt-1 text-sm text-white/60">Nenhuma venda registrada neste período</p>
            )}
          </div>

          {/* Barra de meta */}
          {goalRevPct !== null && (
            <div className="rounded-xl bg-white/15 backdrop-blur-sm px-4 py-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-white/80">🎯 Meta Mensal</span>
                <span className="text-xs font-black text-white">
                  {goalRevPct >= 100
                    ? '🎉 Meta batida!'
                    : `${goalRevPct.toFixed(0)}% — faltam ${fmt(goalRevLeft)}`}
                </span>
              </div>
              <div className="h-2.5 w-full rounded-full bg-white/20 overflow-hidden">
                <div
                  className={`h-2.5 rounded-full transition-all duration-700 ${goalRevPct >= 100 ? 'bg-yellow-300' : 'bg-white'}`}
                  style={{ width: `${goalRevPct}%` }}
                />
              </div>
            </div>
          )}

          {/* Resumo rápido: pedidos + ticket + cancelados */}
          <div className="grid grid-cols-3 gap-px bg-white/10 rounded-xl overflow-hidden">
            {[
              {
                label: 'Pedidos',
                value: ops.orders_today ?? 0,
                sub: ops.orders_today === 0 ? 'Nenhum ainda' : `${ops.orders_yesterday ?? 0} ontem`,
              },
              {
                label: 'Entregues',
                value: ops.orders_completed ?? 0,
                sub: ops.orders_today > 0 ? `${(((ops.orders_completed||0)/ops.orders_today)*100).toFixed(0)}% do total` : '—',
              },
              {
                label: 'Ticket Médio',
                value: fmt(fin.average_ticket),
                sub: 'por pedido',
              },
            ].map(({ label, value, sub }) => (
              <div key={label} className="bg-white/10 px-4 py-3">
                <p className="text-xs text-white/50 uppercase tracking-wider">{label}</p>
                <p className="text-xl font-black text-white mt-0.5">{value}</p>
                <p className="text-xs text-white/40 mt-0.5">{sub}</p>
              </div>
            ))}
          </div>

        </div>
      </div>

      {/* ════════════════════════════════════════════════════════
           2. ALERTAS — AÇÃO IMEDIATA
      ════════════════════════════════════════════════════════ */}
      {visibleAlerts.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-bold uppercase tracking-widest text-gray-400 dark:text-gray-500 px-1">⚡ Ação imediata</p>
          {visibleAlerts.map((alert) => {
            const crit = alert.type === 'critical'
            return (
              <div key={alert.title}
                className={`flex items-start gap-3 rounded-xl border-l-4 px-4 py-3 ${
                  crit
                    ? 'bg-red-50 dark:bg-red-950/40 border-red-500'
                    : 'bg-amber-50 dark:bg-amber-950/40 border-amber-400'
                }`}>
                <span className="text-lg mt-0.5 shrink-0">{crit ? '🔴' : '🟡'}</span>
                <div className="flex-1 min-w-0">
                  <p className={`text-sm font-bold ${crit ? 'text-red-700 dark:text-red-400' : 'text-amber-700 dark:text-amber-400'}`}>
                    {alert.title}
                  </p>
                  <p className={`text-xs mt-0.5 ${crit ? 'text-red-600 dark:text-red-500' : 'text-amber-600 dark:text-amber-500'}`}>
                    {alert.message}
                  </p>
                  {crit && <p className="text-xs font-bold text-red-500 dark:text-red-400 mt-1">→ Agir agora</p>}
                </div>
                <button
                  onClick={() => setDismissedAlerts(prev => new Set([...prev, alert.title]))}
                  className="shrink-0 rounded-md p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors">
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            )
          })}
        </div>
      )}

      {/* ════════════════════════════════════════════════════════
           3. 4 KPI CARDS — FATURAMENTO · PEDIDOS · TICKET · CANCELAMENTOS
      ════════════════════════════════════════════════════════ */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Faturamento */}
        <button
          onClick={() => { setOpenModal('revenue_today'); setModalData(fetchCardDetails('revenue_today')) }}
          className="rounded-2xl border border-gray-200 dark:border-gray-700/60 bg-white dark:bg-gray-800/60 p-4 shadow-sm text-left hover:shadow-md hover:border-emerald-300 dark:hover:border-emerald-500/40 transition-all">
          <div className="rounded-xl bg-gradient-to-br from-emerald-400 to-green-600 p-2 w-fit shadow-md mb-3">
            <DollarSign className="h-4 w-4 text-white" />
          </div>
          <p className="text-2xl font-black text-gray-900 dark:text-white">{fmt(fin.revenue_today)}</p>
          <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mt-0.5">Faturamento Hoje</p>
          <p className={`text-xs mt-1.5 font-semibold ${(fin.growth_vs_yesterday || 0) >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}`}>
            {fin.growth_vs_yesterday != null
              ? `${(fin.growth_vs_yesterday || 0) >= 0 ? '↑' : '↓'} ${Math.abs(fin.growth_vs_yesterday || 0).toFixed(1)}% vs ontem`
              : 'Sem comparação'}
          </p>
        </button>

        {/* Pedidos */}
        <button
          onClick={() => { setOpenModal('orders_today'); setModalData(fetchCardDetails('orders_today')) }}
          className="rounded-2xl border border-gray-200 dark:border-gray-700/60 bg-white dark:bg-gray-800/60 p-4 shadow-sm text-left hover:shadow-md hover:border-blue-300 dark:hover:border-blue-500/40 transition-all">
          <div className="rounded-xl bg-gradient-to-br from-blue-400 to-indigo-600 p-2 w-fit shadow-md mb-3">
            <Package className="h-4 w-4 text-white" />
          </div>
          <p className="text-2xl font-black text-gray-900 dark:text-white">{ops.orders_today ?? 0}</p>
          <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mt-0.5">Pedidos Hoje</p>
          <p className="text-xs mt-1.5 text-gray-400 dark:text-gray-500">
            {ops.orders_today === 0
              ? 'Nenhuma venda ainda'
              : ops.orders_today > (ops.orders_yesterday || 0)
              ? `↑ +${(ops.orders_today || 0) - (ops.orders_yesterday || 0)} vs ontem`
              : `↓ ${(ops.orders_today || 0) - (ops.orders_yesterday || 0)} vs ontem`}
          </p>
        </button>

        {/* Ticket médio */}
        <button
          onClick={() => { setOpenModal('ticket'); setModalData(fetchCardDetails('ticket')) }}
          className="rounded-2xl border border-gray-200 dark:border-gray-700/60 bg-white dark:bg-gray-800/60 p-4 shadow-sm text-left hover:shadow-md hover:border-violet-300 dark:hover:border-violet-500/40 transition-all">
          <div className="rounded-xl bg-gradient-to-br from-violet-400 to-purple-600 p-2 w-fit shadow-md mb-3">
            <TrendingUp className="h-4 w-4 text-white" />
          </div>
          <p className="text-2xl font-black text-gray-900 dark:text-white">{fmt(fin.average_ticket)}</p>
          <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mt-0.5">Ticket Médio</p>
          <p className="text-xs mt-1.5 text-gray-400 dark:text-gray-500">
            {ops.orders_completed > 0 ? `${ops.orders_completed} pedidos entregues` : 'Sem pedidos entregues'}
          </p>
        </button>

        {/* Cancelamentos */}
        <button
          onClick={() => { setOpenModal('cancelled'); setModalData(fetchCardDetails('cancelled')) }}
          className={`rounded-2xl border p-4 shadow-sm text-left hover:shadow-md transition-all ${
            (ops.orders_cancelled_today || 0) === 0
              ? 'border-gray-200 dark:border-gray-700/60 bg-white dark:bg-gray-800/60 hover:border-emerald-300 dark:hover:border-emerald-500/40'
              : (ops.orders_cancelled_today || 0) > 2
              ? 'border-rose-200 dark:border-rose-500/40 bg-rose-50 dark:bg-rose-950/20 hover:border-rose-400'
              : 'border-amber-200 dark:border-amber-500/40 bg-amber-50 dark:bg-amber-950/20 hover:border-amber-400'
          }`}>
          <div className={`rounded-xl bg-gradient-to-br p-2 w-fit shadow-md mb-3 ${
            (ops.orders_cancelled_today || 0) === 0 ? 'from-emerald-400 to-green-600' : 'from-rose-400 to-red-600'
          }`}>
            <XCircle className="h-4 w-4 text-white" />
          </div>
          <p className={`text-2xl font-black ${
            (ops.orders_cancelled_today || 0) === 0
              ? 'text-gray-900 dark:text-white'
              : (ops.orders_cancelled_today || 0) > 2
              ? 'text-rose-600 dark:text-rose-400'
              : 'text-amber-600 dark:text-amber-400'
          }`}>{ops.orders_cancelled_today ?? 0}</p>
          <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mt-0.5">Cancelamentos</p>
          <p className={`text-xs mt-1.5 font-semibold ${
            (ops.orders_cancelled_today || 0) === 0
              ? 'text-emerald-600 dark:text-emerald-400'
              : 'text-rose-500 dark:text-rose-400'
          }`}>
            {(ops.orders_cancelled_today || 0) === 0
              ? '✅ Nenhum cancelamento hoje'
              : ops.orders_today > 0
              ? `${(((ops.orders_cancelled_today||0)/ops.orders_today)*100).toFixed(0)}% dos pedidos`
              : '—'}
          </p>
        </button>
      </div>

      {/* ════════════════════════════════════════════════════════
           4. METAS DO MÊS — BARRAS DE PROGRESSO
      ════════════════════════════════════════════════════════ */}
      {goals && (goals.revenue > 0 || goals.orders > 0 || goals.new_customers > 0) && (() => {
        const revenueMonth = fin.revenue_month || 0
        const ordersMonth = ops.orders_completed || 0
        const newCust = dashboardData?.customer_metrics?.new_month || 0
        const items = [
          goals.revenue > 0       && { label: 'Receita Mensal',  current: revenueMonth, goal: goals.revenue,       fmt: fmt },
          goals.orders > 0        && { label: 'Pedidos',         current: ordersMonth,  goal: goals.orders,        fmt: v => `${v}` },
          goals.new_customers > 0 && { label: 'Novos Clientes',  current: newCust,      goal: goals.new_customers, fmt: v => `${v}` },
        ].filter(Boolean)
        const anyHit = items.some(({ current, goal }) => current >= goal)
        return (
          <div className={`rounded-2xl border p-6 shadow-sm ${anyHit ? 'border-amber-300 dark:border-amber-500/40 bg-amber-50 dark:bg-amber-950/20' : 'border-gray-200 dark:border-gray-700/60 bg-white dark:bg-gray-800/60'}`}>
            <div className="flex items-center gap-2 mb-5">
              <Target className="h-4 w-4 text-amber-500" />
              <h3 className="text-xs font-bold uppercase tracking-widest text-gray-500 dark:text-gray-400">Metas do Mês</h3>
              {anyHit && <span className="ml-auto rounded-full bg-amber-500 px-2.5 py-0.5 text-xs font-black text-white">🎉 Meta batida!</span>}
            </div>
            <div className="space-y-5">
              {items.map(({ label, current, goal, fmt: f }) => {
                const pct = Math.min((current / goal) * 100, 100)
                const left = Math.max(goal - current, 0)
                const hit = pct >= 100
                return (
                  <div key={label}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">{label}</span>
                      <span className={`text-sm font-black ${hit ? 'text-amber-500' : 'text-gray-900 dark:text-white'}`}>
                        {hit ? '🎉 Atingida!' : `${pct.toFixed(0)}% — faltam ${f(left)}`}
                      </span>
                    </div>
                    <div className="h-3 w-full rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
                      <div
                        className={`h-3 rounded-full transition-all duration-700 ${hit ? 'bg-gradient-to-r from-amber-400 to-yellow-300' : 'bg-gradient-to-r from-indigo-500 to-blue-500'}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <div className="flex justify-between mt-1">
                      <span className="text-xs text-gray-400">{f(current)} atingido</span>
                      <span className="text-xs text-gray-400">meta {f(goal)}</span>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )
      })()}

      {/* ════════════════════════════════════════════════════════
           5. TOP PRODUTOS
      ════════════════════════════════════════════════════════ */}
      {dashboardData?.top_products?.length > 0 && (
        <div className="rounded-2xl border border-gray-200 dark:border-gray-700/60 bg-white dark:bg-gray-800/60 p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-5">
            <div className="rounded-xl bg-gradient-to-br from-orange-400 to-red-500 p-2 shadow-md shadow-orange-500/25">
              <Zap className="h-4 w-4 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 dark:text-white">Produtos em Alta</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">mais vendidos no período</p>
            </div>
          </div>
          <div className="space-y-3">
            {dashboardData.top_products.slice(0, 5).map((p, i) => {
              const maxQty = dashboardData.top_products[0]?.quantity || 1
              return (
                <div key={p.code} className="flex items-center gap-3">
                  <span className={`shrink-0 w-5 text-xs font-black ${i === 0 ? 'text-amber-500' : 'text-gray-400 dark:text-gray-500'}`}>{i + 1}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-semibold text-gray-900 dark:text-white truncate">{p.name || p.code}</span>
                      <div className="shrink-0 flex gap-3 ml-2">
                        <span className="text-xs font-bold text-gray-700 dark:text-gray-300">{p.quantity}x</span>
                        <span className="text-xs text-gray-400 w-20 text-right">{fmt(p.revenue)}</span>
                      </div>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
                      <div
                        className={`h-1.5 rounded-full transition-all duration-700 ${i === 0 ? 'bg-gradient-to-r from-amber-400 to-orange-500' : 'bg-gradient-to-r from-blue-400 to-indigo-500'}`}
                        style={{ width: `${(p.quantity / maxQty) * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* ════════════════════════════════════════════════════════
           6. RECEITA DO MÊS (TENDÊNCIA)
      ════════════════════════════════════════════════════════ */}
      <MonthlySparkline />

      {/* ════════════════════════════════════════════════════════
           7. PEDIDOS AO VIVO
      ════════════════════════════════════════════════════════ */}
      <div>
        <div className="mb-3 flex items-center gap-2">
          <span className="flex items-center gap-1.5 rounded-full border border-emerald-500/40 bg-emerald-500/10 px-2.5 py-1 text-xs font-bold text-emerald-600 dark:text-emerald-400">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            Pedidos ao Vivo · atualiza a cada 30s
          </span>
        </div>
        <LiveOrdersPanel />
      </div>

      {/* ════════════════════════════════════════════════════════
           MODAL DE DETALHES
      ════════════════════════════════════════════════════════ */}
      <CardDetailModal
        isOpen={openModal !== null}
        onClose={() => { setOpenModal(null); setModalData(null) }}
        title={modalData?.title || 'Detalhes'}
      >
        {modalData?.items ? (
          <div className="space-y-3">
            {modalData.items.map((item, idx) => (
              <div key={idx} className="flex items-center justify-between rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-4 py-3">
                <span className="text-sm font-medium text-gray-600 dark:text-gray-400">{item.label}</span>
                <span className="text-sm font-bold text-gray-900 dark:text-white">{item.value}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center text-gray-500 py-4">Carregando...</div>
        )}
      </CardDetailModal>

    </div>
  )
}
