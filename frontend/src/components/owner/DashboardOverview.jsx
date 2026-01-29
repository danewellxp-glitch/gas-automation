/**
 * Dashboard Overview - Visão Geral Executiva
 * Cards principais e alertas
 */

import { useState, useEffect } from 'react'
import { 
  DollarSign, TrendingUp, TrendingDown, Package, Clock, AlertCircle, 
  RefreshCw, Activity, CheckCircle2, XCircle, CreditCard, Wallet, ChevronRight
} from 'lucide-react'
import { apiRequest } from '../../utils/api'
import CardDetailModal from './CardDetailModal'

export default function DashboardOverview() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [period, setPeriod] = useState('day')
  const [dashboardData, setDashboardData] = useState(null)
  const [lastUpdate, setLastUpdate] = useState(null)
  const [openModal, setOpenModal] = useState(null)
  const [modalData, setModalData] = useState(null)

  useEffect(() => {
    fetchDashboard()
    const interval = setInterval(fetchDashboard, 30000)
    return () => clearInterval(interval)
  }, [period])

  const fetchDashboard = async () => {
    try {
      setLoading(true)
      setError('')
      const data = await apiRequest(`owner/dashboard?period=${period}`)
      setDashboardData(data)
      setLastUpdate(new Date())
    } catch (err) {
      console.error('Erro ao buscar dashboard:', err)
      setError(err.message || 'Erro ao carregar dashboard')
    } finally {
      setLoading(false)
    }
  }

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
      minimumFractionDigits: 2,
    }).format(value || 0)
  }

  const formatPercent = (value) => {
    if (value === null || value === undefined || isNaN(value)) return '-'
    const numValue = parseFloat(value) || 0
    const sign = numValue >= 0 ? '+' : ''
    return `${sign}${numValue.toFixed(1)}%`
  }

  const getTrendIcon = (value) => {
    if (value > 0) return <TrendingUp className="h-4 w-4 text-green-600" />
    if (value < 0) return <TrendingDown className="h-4 w-4 text-red-600" />
    return <Activity className="h-4 w-4 text-gray-400" />
  }

  const getTrendColor = (value) => {
    if (value > 0) return 'text-green-600'
    if (value < 0) return 'text-red-600'
    return 'text-gray-500'
  }

  const handleCardClick = (cardType, title) => {
    setOpenModal(cardType)
    // Buscar detalhes específicos baseado no tipo de card
    const details = fetchCardDetails(cardType)
    setModalData(details)
  }

  const fetchCardDetails = (cardType) => {
    const cards = dashboardData?.cards
    const financial = dashboardData?.financial_breakdown
    const operational = dashboardData?.operational_performance
    
    switch (cardType) {
      case 'revenue_today':
        return {
          title: 'Detalhes do Faturamento Hoje',
          items: [
            { label: 'Faturamento Total', value: formatCurrency(cards?.financial?.revenue_today || 0) },
            { label: 'Pedidos Pagos', value: cards?.operational?.orders_completed || 0 },
            { label: 'Ticket Médio', value: formatCurrency(cards?.financial?.average_ticket || 0) },
            { label: 'Crescimento vs Ontem', value: formatPercent(cards?.financial?.growth_vs_yesterday || 0) },
          ],
        }
      case 'revenue_month':
        return {
          title: 'Detalhes do Faturamento Mensal',
          items: [
            { label: 'Faturamento Total', value: formatCurrency(cards?.financial?.revenue_month || 0) },
            { label: 'Receita Bruta', value: formatCurrency(financial?.gross_revenue || 0) },
            { label: 'Receita Líquida', value: formatCurrency(financial?.net_revenue || 0) },
            { label: 'Crescimento vs Mês Anterior', value: formatPercent(cards?.financial?.growth_vs_last_month || 0) },
            { label: 'Pedidos Totais', value: cards?.operational?.orders_completed || 0 },
          ],
        }
      case 'average_ticket':
        const totalOrders = cards?.operational?.orders_completed || 0
        const totalRevenue = cards?.financial?.revenue_today || 0
        return {
          title: 'Detalhes do Ticket Médio',
          items: [
            { label: 'Ticket Médio', value: formatCurrency(cards?.financial?.average_ticket || 0) },
            { label: 'Pedidos Totais', value: totalOrders },
            { label: 'Faturamento Total', value: formatCurrency(totalRevenue) },
            { label: 'Cálculo', value: totalOrders > 0 ? formatCurrency(totalRevenue / totalOrders) : formatCurrency(0) },
          ],
        }
      case 'growth_week':
        return {
          title: 'Detalhes do Crescimento Semanal',
          items: [
            { label: 'Crescimento', value: formatPercent(cards?.financial?.growth_vs_last_week || 0) },
            { label: 'Faturamento Semana Atual', value: formatCurrency(cards?.financial?.revenue_week || cards?.financial?.revenue_today || 0) },
            { label: 'Faturamento Semana Anterior', value: formatCurrency(cards?.financial?.revenue_last_week || 0) },
            { label: 'Diferença', value: formatCurrency((cards?.financial?.revenue_week || cards?.financial?.revenue_today || 0) - (cards?.financial?.revenue_last_week || 0)) },
          ],
        }
      case 'orders_today':
        return {
          title: 'Detalhes dos Pedidos Hoje',
          items: [
            { label: 'Pedidos Hoje', value: cards?.operational?.orders_today || 0 },
            { label: 'Pedidos Ontem', value: cards?.operational?.orders_yesterday || 0 },
            { label: 'Pedidos Concluídos', value: cards?.operational?.orders_completed || 0 },
            { label: 'Pedidos Pendentes', value: (cards?.operational?.orders_today || 0) - (cards?.operational?.orders_completed || 0) },
            { label: 'Pedidos Cancelados', value: cards?.operational?.orders_cancelled_today || 0 },
          ],
        }
      case 'orders_completed':
        const ordersToday = cards?.operational?.orders_today || 0
        const ordersCompleted = cards?.operational?.orders_completed || 0
        return {
          title: 'Detalhes dos Pedidos Concluídos',
          items: [
            { label: 'Total Concluídos', value: ordersCompleted },
            { label: 'Taxa de Conclusão', value: ordersToday > 0 ? `${((ordersCompleted / ordersToday) * 100).toFixed(1)}%` : '0%' },
            { label: 'Tempo Médio de Entrega', value: cards?.operational?.average_delivery_time ? `${Math.round(cards.operational.average_delivery_time)} min` : '-' },
            { label: 'Taxa de Entrega no Prazo', value: `${(cards?.operational?.on_time_delivery_rate || 0).toFixed(1)}%` },
          ],
        }
      case 'orders_cancelled':
        const cancelledToday = cards?.operational?.orders_cancelled_today || 0
        const totalOrdersToday = cards?.operational?.orders_today || 0
        return {
          title: 'Detalhes dos Cancelamentos',
          items: [
            { label: 'Cancelados Hoje', value: cancelledToday },
            { label: 'Total Cancelados', value: cards?.operational?.orders_cancelled || 0 },
            { label: 'Taxa de Cancelamento', value: totalOrdersToday > 0 ? `${((cancelledToday / totalOrdersToday) * 100).toFixed(1)}%` : '0%' },
            { label: 'Impacto Financeiro', value: formatCurrency(financial?.cancelled_revenue || 0) },
          ],
        }
      case 'delivery_time':
        return {
          title: 'Detalhes do Tempo de Entrega',
          items: [
            { label: 'Tempo Médio', value: cards?.operational?.average_delivery_time ? `${Math.round(cards.operational.average_delivery_time)} min` : '-' },
            { label: 'Taxa de Entrega no Prazo', value: `${(cards?.operational?.on_time_delivery_rate || 0).toFixed(1)}%` },
            { label: 'Entregas Atrasadas', value: operational?.late_deliveries || 0 },
            { label: 'Informações', value: 'Detalhes completos disponíveis na aba Performance' },
          ],
        }
      case 'card_payment':
        const cardCount = cards?.payment?.card_count || 0
        const cardValue = cards?.payment?.card_value || 0
        return {
          title: 'Detalhes de Pagamentos em Cartão',
          items: [
            { label: 'Percentual', value: `${(cards?.payment?.card_percentage || 0).toFixed(1)}%` },
            { label: 'Quantidade de Pedidos', value: cardCount },
            { label: 'Valor Total', value: formatCurrency(cardValue) },
            { label: 'Ticket Médio Cartão', value: cardCount > 0 ? formatCurrency(cardValue / cardCount) : formatCurrency(0) },
          ],
        }
      case 'cash_payment':
        const cashCount = cards?.payment?.cash_count || 0
        const cashValue = cards?.payment?.cash_value || 0
        return {
          title: 'Detalhes de Pagamentos em Dinheiro',
          items: [
            { label: 'Percentual', value: `${(cards?.payment?.cash_percentage || 0).toFixed(1)}%` },
            { label: 'Quantidade de Pedidos', value: cashCount },
            { label: 'Valor Total', value: formatCurrency(cashValue) },
            { label: 'Ticket Médio Dinheiro', value: cashCount > 0 ? formatCurrency(cashValue / cashCount) : formatCurrency(0) },
          ],
        }
      case 'approval_rate':
        const paidCount = cards?.payment?.paid_count || cards?.operational?.orders_completed || 0
        const pendingCount = cards?.payment?.pending_count || ((cards?.operational?.orders_today || 0) - (cards?.operational?.orders_completed || 0))
        return {
          title: 'Detalhes da Taxa de Aprovação',
          items: [
            { label: 'Taxa de Aprovação', value: `${(cards?.payment?.approval_rate || 0).toFixed(1)}%` },
            { label: 'Pedidos Pagos', value: paidCount },
            { label: 'Pedidos Pendentes', value: pendingCount },
            { label: 'Total de Pedidos', value: paidCount + pendingCount },
          ],
        }
      default:
        return { title: 'Detalhes', items: [] }
    }
  }

  if (loading && !dashboardData) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-gray-200 border-t-primary-600" />
          <p className="mt-4 text-gray-600">Carregando dashboard...</p>
        </div>
      </div>
    )
  }

  if (error && !dashboardData) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6">
        <div className="flex items-center gap-2">
          <AlertCircle className="h-5 w-5 text-red-600" />
          <span className="font-semibold text-red-800">Erro ao carregar dashboard</span>
        </div>
        <p className="mt-2 text-sm text-red-700">{error}</p>
        <button
          onClick={fetchDashboard}
          className="mt-4 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
        >
          Tentar novamente
        </button>
      </div>
    )
  }

  if (!dashboardData) return null

  const cards = dashboardData?.cards
  const alerts = dashboardData?.alerts || []

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Visão Geral</h1>
          <p className="mt-1 text-sm text-gray-600">
            Resumo executivo do negócio
            {lastUpdate && (
              <span className="ml-2">
                • Atualizado {lastUpdate.toLocaleTimeString('pt-BR')}
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex rounded-lg border border-gray-300 bg-white p-1">
            {['day', 'week', 'month'].map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                  period === p
                    ? 'bg-primary-600 text-white'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                {p === 'day' ? 'Dia' : p === 'week' ? 'Semana' : 'Mês'}
              </button>
            ))}
          </div>
          <button
            onClick={fetchDashboard}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Atualizar
          </button>
        </div>
      </div>

      {alerts.length > 0 && (
        <div className="space-y-2">
          {alerts.map((alert, idx) => (
            <div
              key={idx}
              className={`flex items-start gap-3 rounded-lg border p-4 ${
                alert.type === 'critical'
                  ? 'border-red-200 bg-red-50'
                  : 'border-amber-200 bg-amber-50'
              }`}
            >
              <AlertCircle
                className={`h-5 w-5 mt-0.5 flex-shrink-0 ${
                  alert.type === 'critical' ? 'text-red-600' : 'text-amber-600'
                }`}
              />
              <div className="flex-1">
                <div className="font-semibold text-gray-900">{alert.title}</div>
                <div className="mt-1 text-sm text-gray-700">{alert.message}</div>
                {alert.count !== undefined && (
                  <div className="mt-1 text-xs text-gray-600">Quantidade: {alert.count}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      <div>
        <h2 className="mb-4 text-lg font-semibold text-gray-900">Financeiro</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-600">Faturamento Hoje</p>
                <p className="mt-2 text-2xl font-bold text-gray-900">
                  {formatCurrency(cards?.financial?.revenue_today || 0)}
                </p>
                {cards?.financial?.growth_vs_yesterday !== undefined && cards?.financial?.growth_vs_yesterday !== null && (
                  <div className={`mt-2 flex items-center gap-1 text-sm ${getTrendColor(cards.financial.growth_vs_yesterday)}`}>
                    {getTrendIcon(cards.financial.growth_vs_yesterday)}
                    <span>{formatPercent(cards.financial.growth_vs_yesterday)} vs ontem</span>
                  </div>
                )}
              </div>
              <div className="rounded-lg bg-green-50 p-3">
                <DollarSign className="h-6 w-6 text-green-600" />
              </div>
            </div>
          </div>

          <button
            onClick={() => handleCardClick('revenue_month', 'Faturamento Mês')}
            className="rounded-lg border border-gray-200 bg-white p-6 text-left shadow-sm transition-all hover:border-primary-300 hover:shadow-md cursor-pointer"
          >
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-600">Faturamento Mês</p>
                <p className="mt-2 text-2xl font-bold text-gray-900">
                  {formatCurrency(cards?.financial?.revenue_month || 0)}
                </p>
                {cards?.financial?.growth_vs_last_month !== undefined && cards?.financial?.growth_vs_last_month !== null && (
                  <div className={`mt-2 flex items-center gap-1 text-sm ${getTrendColor(cards.financial.growth_vs_last_month)}`}>
                    {getTrendIcon(cards.financial.growth_vs_last_month)}
                    <span>{formatPercent(cards.financial.growth_vs_last_month)} vs mês anterior</span>
                  </div>
                )}
              </div>
              <div className="flex items-center gap-2">
                <div className="rounded-lg bg-blue-50 p-3">
                  <TrendingUp className="h-6 w-6 text-blue-600" />
                </div>
                <ChevronRight className="h-5 w-5 text-gray-400" />
              </div>
            </div>
          </button>

          <button
            onClick={() => handleCardClick('average_ticket', 'Ticket Médio')}
            className="rounded-lg border border-gray-200 bg-white p-6 text-left shadow-sm transition-all hover:border-primary-300 hover:shadow-md cursor-pointer"
          >
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-600">Ticket Médio</p>
                <p className="mt-2 text-2xl font-bold text-gray-900">
                  {formatCurrency(cards?.financial?.average_ticket || 0)}
                </p>
                <p className="mt-2 text-xs text-gray-500">Por pedido</p>
              </div>
              <div className="flex items-center gap-2">
                <div className="rounded-lg bg-purple-50 p-3">
                  <Activity className="h-6 w-6 text-purple-600" />
                </div>
                <ChevronRight className="h-5 w-5 text-gray-400" />
              </div>
            </div>
          </button>

          <button
            onClick={() => handleCardClick('growth_week', 'Crescimento Semanal')}
            className="rounded-lg border border-gray-200 bg-white p-6 text-left shadow-sm transition-all hover:border-primary-300 hover:shadow-md cursor-pointer"
          >
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-600">Crescimento Semanal</p>
                <p className={`mt-2 text-2xl font-bold ${getTrendColor(cards?.financial?.growth_vs_last_week || 0)}`}>
                  {formatPercent(cards?.financial?.growth_vs_last_week || 0)}
                </p>
                <p className="mt-2 text-xs text-gray-500">vs semana passada</p>
              </div>
              <div className="flex items-center gap-2">
                <div className="rounded-lg bg-indigo-50 p-3">
                  <Activity className="h-6 w-6 text-indigo-600" />
                </div>
                <ChevronRight className="h-5 w-5 text-gray-400" />
              </div>
            </div>
          </button>
        </div>
      </div>

      <div>
        <h2 className="mb-4 text-lg font-semibold text-gray-900">Operação</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <button
            onClick={() => handleCardClick('orders_today', 'Pedidos Hoje')}
            className="rounded-lg border border-gray-200 bg-white p-6 text-left shadow-sm transition-all hover:border-primary-300 hover:shadow-md cursor-pointer"
          >
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-600">Pedidos Hoje</p>
                <p className="mt-2 text-2xl font-bold text-gray-900">
                  {cards?.operational?.orders_today || 0}
                </p>
                {cards?.operational?.orders_yesterday !== undefined && (
                  <div className="mt-2 flex items-center gap-1 text-sm text-gray-600">
                    <span>Ontem: {cards.operational.orders_yesterday}</span>
                  </div>
                )}
              </div>
              <div className="flex items-center gap-2">
                <div className="rounded-lg bg-blue-50 p-3">
                  <Package className="h-6 w-6 text-blue-600" />
                </div>
                <ChevronRight className="h-5 w-5 text-gray-400" />
              </div>
            </div>
          </button>

          <button
            onClick={() => handleCardClick('orders_completed', 'Pedidos Concluídos')}
            className="rounded-lg border border-gray-200 bg-white p-6 text-left shadow-sm transition-all hover:border-primary-300 hover:shadow-md cursor-pointer"
          >
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-600">Pedidos Concluídos</p>
                <p className="mt-2 text-2xl font-bold text-green-600">
                  {cards?.operational?.orders_completed || 0}
                </p>
                <p className="mt-2 text-xs text-gray-500">Total entregues</p>
              </div>
              <div className="flex items-center gap-2">
                <div className="rounded-lg bg-green-50 p-3">
                  <CheckCircle2 className="h-6 w-6 text-green-600" />
                </div>
                <ChevronRight className="h-5 w-5 text-gray-400" />
              </div>
            </div>
          </button>

          <button
            onClick={() => handleCardClick('orders_cancelled', 'Cancelados Hoje')}
            className="rounded-lg border border-gray-200 bg-white p-6 text-left shadow-sm transition-all hover:border-primary-300 hover:shadow-md cursor-pointer"
          >
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-600">Cancelados Hoje</p>
                <p className="mt-2 text-2xl font-bold text-red-600">
                  {cards?.operational?.orders_cancelled_today || 0}
                </p>
                <p className="mt-2 text-xs text-gray-500">
                  Total: {cards?.operational?.orders_cancelled || 0}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <div className="rounded-lg bg-red-50 p-3">
                  <XCircle className="h-6 w-6 text-red-600" />
                </div>
                <ChevronRight className="h-5 w-5 text-gray-400" />
              </div>
            </div>
          </button>

          <button
            onClick={() => handleCardClick('delivery_time', 'Tempo Médio de Entrega')}
            className="rounded-lg border border-gray-200 bg-white p-6 text-left shadow-sm transition-all hover:border-primary-300 hover:shadow-md cursor-pointer"
          >
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-600">Tempo Médio</p>
                <p className="mt-2 text-2xl font-bold text-gray-900">
                  {cards?.operational?.average_delivery_time
                    ? `${Math.round(cards.operational.average_delivery_time)} min`
                    : '-'}
                </p>
                {cards?.operational?.on_time_delivery_rate !== undefined && cards?.operational?.on_time_delivery_rate !== null && (
                  <p className="mt-2 text-xs text-gray-500">
                    {(cards.operational.on_time_delivery_rate || 0).toFixed(1)}% no prazo
                  </p>
                )}
              </div>
              <div className="flex items-center gap-2">
                <div className="rounded-lg bg-amber-50 p-3">
                  <Clock className="h-6 w-6 text-amber-600" />
                </div>
                <ChevronRight className="h-5 w-5 text-gray-400" />
              </div>
            </div>
          </button>
        </div>
      </div>

      <div>
        <h2 className="mb-4 text-lg font-semibold text-gray-900">Pagamentos</h2>
        <div className="grid gap-4 sm:grid-cols-3">
          <button
            onClick={() => handleCardClick('card_payment', 'Pagamentos em Cartão')}
            className="rounded-lg border border-gray-200 bg-white p-6 text-left shadow-sm transition-all hover:border-primary-300 hover:shadow-md cursor-pointer"
          >
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-600">Cartão</p>
                <p className="mt-2 text-2xl font-bold text-gray-900">
                  {(cards?.payment?.card_percentage || 0).toFixed(1)}%
                </p>
                <p className="mt-2 text-xs text-gray-500">
                  {cards?.payment?.card_count || 0} pedidos
                </p>
              </div>
              <div className="flex items-center gap-2">
                <div className="rounded-lg bg-blue-50 p-3">
                  <CreditCard className="h-6 w-6 text-blue-600" />
                </div>
                <ChevronRight className="h-5 w-5 text-gray-400" />
              </div>
            </div>
          </button>

          <button
            onClick={() => handleCardClick('cash_payment', 'Pagamentos em Dinheiro')}
            className="rounded-lg border border-gray-200 bg-white p-6 text-left shadow-sm transition-all hover:border-primary-300 hover:shadow-md cursor-pointer"
          >
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-600">Dinheiro</p>
                <p className="mt-2 text-2xl font-bold text-gray-900">
                  {(cards?.payment?.cash_percentage || 0).toFixed(1)}%
                </p>
                <p className="mt-2 text-xs text-gray-500">
                  {cards?.payment?.cash_count || 0} pedidos
                </p>
              </div>
              <div className="flex items-center gap-2">
                <div className="rounded-lg bg-green-50 p-3">
                  <Wallet className="h-6 w-6 text-green-600" />
                </div>
                <ChevronRight className="h-5 w-5 text-gray-400" />
              </div>
            </div>
          </button>

          <button
            onClick={() => handleCardClick('approval_rate', 'Taxa de Aprovação')}
            className="rounded-lg border border-gray-200 bg-white p-6 text-left shadow-sm transition-all hover:border-primary-300 hover:shadow-md cursor-pointer"
          >
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-600">Taxa de Aprovação</p>
                <p className="mt-2 text-2xl font-bold text-gray-900">
                  {(cards?.payment?.approval_rate || 0).toFixed(1)}%
                </p>
                <p className="mt-2 text-xs text-gray-500">Pedidos pagos</p>
              </div>
              <div className="flex items-center gap-2">
                <div className="rounded-lg bg-purple-50 p-3">
                  <CheckCircle2 className="h-6 w-6 text-purple-600" />
                </div>
                <ChevronRight className="h-5 w-5 text-gray-400" />
              </div>
            </div>
          </button>
        </div>
      </div>

      {/* Modal de Detalhes */}
      <CardDetailModal
        isOpen={openModal !== null}
        onClose={() => {
          setOpenModal(null)
          setModalData(null)
        }}
        title={modalData?.title || 'Detalhes'}
      >
        {modalData?.error ? (
          <div className="text-center text-red-600">{modalData.error}</div>
        ) : modalData?.items ? (
          <div className="space-y-4">
            {modalData.items.map((item, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between rounded-lg border border-gray-200 bg-gray-50 px-4 py-3"
              >
                <span className="text-sm font-medium text-gray-700">{item.label}</span>
                <span className="text-sm font-semibold text-gray-900">{item.value}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center text-gray-500">Carregando detalhes...</div>
        )}
      </CardDetailModal>
    </div>
  )
}
