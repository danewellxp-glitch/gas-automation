/**
 * Executive View - Visão Executiva Completa
 * Cards executivos, gráficos e métricas principais
 */

import { useState, useEffect } from 'react'
import { 
  DollarSign, TrendingUp, TrendingDown, Package, Clock, AlertCircle, 
  Users, MapPin, BarChart3, RefreshCw, Activity, CheckCircle2, XCircle,
  Truck, CreditCard, Wallet, TrendingUp as TrendingUpIcon
} from 'lucide-react'
import { apiRequest } from '../../utils/api'
import RevenueChart from './RevenueChart'
import OrdersByTypeChart from './OrdersByTypeChart'
import BairroChart from './BairroChart'
import TopProductsChart from './TopProductsChart'

export default function ExecutiveView() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [period, setPeriod] = useState('day')
  const [dashboardData, setDashboardData] = useState(null)
  const [lastUpdate, setLastUpdate] = useState(null)

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

  if (loading && !dashboardData) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-gray-200 border-t-primary-600" />
          <p className="mt-4 text-gray-600">Carregando dashboard executivo...</p>
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
    <div className="space-y-8 dark:text-gray-100">
      {/* Header com controles */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Visão Executiva</h1>
          <p className="mt-1 text-sm text-gray-600">
            Visão geral do negócio em tempo real
            {lastUpdate && (
              <span className="ml-2">
                • Atualizado {lastUpdate.toLocaleTimeString('pt-BR')}
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex rounded-lg border border-gray-300 bg-white p-1 dark:bg-gray-800 dark:border-gray-600">
            {['day', 'week', 'month'].map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                  period === p
                    ? 'bg-primary-600 text-white'
                    : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                }`}
              >
                {p === 'day' ? 'Dia' : p === 'week' ? 'Semana' : 'Mês'}
              </button>
            ))}
          </div>
          <button
            onClick={fetchDashboard}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:bg-gray-800 dark:border-gray-600 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Atualizar
          </button>
        </div>
      </div>

      {/* Alertas Executivos */}
      {alerts.length > 0 && (
        <div className="space-y-2">
          {alerts.map((alert, idx) => (
            <div
              key={idx}
              className={`flex items-start gap-3 rounded-lg border p-4 ${
                alert.type === 'critical'
                  ? 'border-red-200 bg-red-50 dark:bg-red-950 dark:border-red-800'
                  : 'border-amber-200 bg-amber-50 dark:bg-amber-950 dark:border-amber-800'
              }`}
            >
              <AlertCircle
                className={`h-5 w-5 mt-0.5 flex-shrink-0 ${
                  alert.type === 'critical' ? 'text-red-600' : 'text-amber-600'
                }`}
              />
              <div className="flex-1">
                <div className="font-semibold text-gray-900 dark:text-white">{alert.title}</div>
                <div className="mt-1 text-sm text-gray-700 dark:text-gray-300">{alert.message}</div>
                {alert.count !== undefined && (
                  <div className="mt-1 text-xs text-gray-600 dark:text-gray-400">Quantidade: {alert.count}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Seção: Financeiro */}
      <section>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Financeiro</h2>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Faturamento Hoje</p>
                <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">
                  {formatCurrency(cards?.financial?.revenue_today || 0)}
                </p>
                {cards?.financial?.growth_vs_yesterday !== undefined && cards?.financial?.growth_vs_yesterday !== null && (
                  <div className={`mt-2 flex items-center gap-1 text-sm ${getTrendColor(cards.financial.growth_vs_yesterday)}`}>
                    {getTrendIcon(cards.financial.growth_vs_yesterday)}
                    <span>{formatPercent(cards.financial.growth_vs_yesterday)} vs ontem</span>
                  </div>
                )}
              </div>
              <div className="rounded-lg bg-green-50 p-3 dark:bg-gray-700">
                <DollarSign className="h-6 w-6 text-green-600" />
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Faturamento Mês</p>
                <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">
                  {formatCurrency(cards?.financial?.revenue_month || 0)}
                </p>
                {cards?.financial?.growth_vs_last_month !== undefined && cards?.financial?.growth_vs_last_month !== null && (
                  <div className={`mt-2 flex items-center gap-1 text-sm ${getTrendColor(cards.financial.growth_vs_last_month)}`}>
                    {getTrendIcon(cards.financial.growth_vs_last_month)}
                    <span>{formatPercent(cards.financial.growth_vs_last_month)} vs mês anterior</span>
                  </div>
                )}
              </div>
              <div className="rounded-lg bg-blue-50 p-3 dark:bg-gray-700">
                <TrendingUpIcon className="h-6 w-6 text-blue-600" />
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Ticket Médio</p>
                <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">
                  {formatCurrency(cards?.financial?.average_ticket || 0)}
                </p>
                <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">Por pedido</p>
              </div>
              <div className="rounded-lg bg-purple-50 p-3 dark:bg-gray-700">
                <BarChart3 className="h-6 w-6 text-purple-600" />
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Crescimento Semanal</p>
                <p className={`mt-2 text-2xl font-bold ${getTrendColor(cards?.financial?.growth_vs_last_week || 0)}`}>
                  {formatPercent(cards?.financial?.growth_vs_last_week || 0)}
                </p>
                <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">vs semana passada</p>
              </div>
              <div className="rounded-lg bg-indigo-50 p-3 dark:bg-gray-700">
                <Activity className="h-6 w-6 text-indigo-600" />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Seção: Operação */}
      <section>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Operação</h2>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Pedidos Hoje</p>
                <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">
                  {cards?.operational?.orders_today || 0}
                </p>
                {cards?.operational?.orders_yesterday !== undefined && (
                  <div className="mt-2 flex items-center gap-1 text-sm text-gray-600">
                    <span>Ontem: {cards.operational.orders_yesterday}</span>
                  </div>
                )}
              </div>
              <div className="rounded-lg bg-blue-50 p-3 dark:bg-gray-700">
                <Package className="h-6 w-6 text-blue-600" />
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Pedidos Concluídos</p>
                <p className="mt-2 text-2xl font-bold text-green-600">
                  {cards?.operational?.orders_completed || 0}
                </p>
                <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">Total entregues</p>
              </div>
              <div className="rounded-lg bg-green-50 p-3 dark:bg-gray-700">
                <CheckCircle2 className="h-6 w-6 text-green-600" />
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Cancelados Hoje</p>
                <p className="mt-2 text-2xl font-bold text-red-600">
                  {cards?.operational?.orders_cancelled_today || 0}
                </p>
                <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                  Total: {cards?.operational?.orders_cancelled || 0}
                </p>
              </div>
              <div className="rounded-lg bg-red-50 p-3 dark:bg-gray-700">
                <XCircle className="h-6 w-6 text-red-600" />
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Tempo Médio de Entrega</p>
                <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">
                  {cards?.operational?.average_delivery_time
                    ? `${Math.round(cards.operational.average_delivery_time)} min`
                    : '-'}
                </p>
                {cards?.operational?.on_time_delivery_rate !== undefined && cards?.operational?.on_time_delivery_rate !== null && (
                  <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                    {(cards.operational.on_time_delivery_rate || 0).toFixed(1)}% no prazo
                  </p>
                )}
              </div>
              <div className="rounded-lg bg-amber-50 p-3 dark:bg-gray-700">
                <Clock className="h-6 w-6 text-amber-600" />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Seção: Pagamentos */}
      <section>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Pagamentos</h2>
        </div>
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Cartão</p>
                <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">
                  {(cards?.payment?.card_percentage || 0).toFixed(1)}%
                </p>
                <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                  {cards?.payment?.card_count || 0} pedidos
                </p>
              </div>
              <div className="rounded-lg bg-blue-50 p-3 dark:bg-gray-700">
                <CreditCard className="h-6 w-6 text-blue-600" />
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Dinheiro</p>
                <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">
                  {(cards?.payment?.cash_percentage || 0).toFixed(1)}%
                </p>
                <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                  {cards?.payment?.cash_count || 0} pedidos
                </p>
              </div>
              <div className="rounded-lg bg-green-50 p-3 dark:bg-gray-700">
                <Wallet className="h-6 w-6 text-green-600" />
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Taxa de Aprovação</p>
                <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">
                  {(cards?.payment?.approval_rate || 0).toFixed(1)}%
                </p>
                <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">Pedidos pagos</p>
              </div>
              <div className="rounded-lg bg-purple-50 p-3 dark:bg-gray-700">
                <CheckCircle2 className="h-6 w-6 text-purple-600" />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Seção: Gráficos */}
      <section>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Análise Visual</h2>
        </div>
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
            <h3 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Receita ao Longo do Tempo</h3>
            {dashboardData?.revenue_chart && (
              <RevenueChart data={dashboardData.revenue_chart} />
            )}
          </div>

          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
            <h3 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Pedidos por Tipo</h3>
            {dashboardData?.orders_by_type && (
              <OrdersByTypeChart data={dashboardData.orders_by_type} />
            )}
          </div>

          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
            <h3 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Pedidos por Bairro</h3>
            {dashboardData?.orders_by_bairro && dashboardData.orders_by_bairro.length > 0 && (
              <BairroChart data={dashboardData.orders_by_bairro} />
            )}
          </div>

          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
            <h3 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Produtos Mais Vendidos</h3>
            {dashboardData?.top_products && dashboardData.top_products.length > 0 && (
              <TopProductsChart data={dashboardData.top_products} />
            )}
          </div>
        </div>
      </section>

      {/* Seção: Performance Operacional */}
      <section>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Performance Operacional</h2>
        </div>
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Entregadores</h3>
            </div>
            {dashboardData?.driver_performance && dashboardData.driver_performance.length > 0 ? (
              <div className="space-y-3">
                {dashboardData.driver_performance.map((driver, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between rounded-lg border border-gray-200 bg-gray-50 p-4"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-lg font-bold text-gray-400">#{idx + 1}</span>
                        <span className="font-semibold text-gray-900 dark:text-white">
                          {driver.driver_name || 'Sem nome'}
                        </span>
                      </div>
                      <div className="mt-1 flex items-center gap-4 text-sm text-gray-600">
                        <span>{driver.deliveries_count} entregas</span>
                        {driver.avg_delivery_time && (
                          <span>{Math.round(driver.avg_delivery_time)} min médio</span>
                        )}
                        {driver.on_time_rate !== undefined && driver.on_time_rate !== null && (
                          <span className="text-green-600">
                            {(driver.on_time_rate || 0).toFixed(0)}% no prazo
                          </span>
                        )}
                      </div>
                    </div>
                    {driver.late_deliveries > 0 && (
                      <div className="rounded-full bg-red-100 px-3 py-1 text-xs font-medium text-red-700">
                        {driver.late_deliveries} atrasos
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500 dark:text-gray-400">Sem dados de entregadores</p>
            )}
          </div>

          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Operadores</h3>
            </div>
            {dashboardData?.operator_performance && dashboardData.operator_performance.length > 0 ? (
              <div className="space-y-3">
                {dashboardData.operator_performance.map((op) => (
                  <div
                    key={op.user_id}
                    className="flex items-center justify-between rounded-lg border border-gray-200 bg-gray-50 p-4"
                  >
                    <div className="flex-1">
                      <div className="font-semibold text-gray-900 dark:text-white">{op.username}</div>
                      <div className="mt-1 text-sm text-gray-600">{op.email}</div>
                      <div className="mt-2 flex items-center gap-4 text-sm">
                        <span className="font-medium text-gray-700">
                          {op.orders_approved} aprovados
                        </span>
                        {op.errors_count > 0 && (
                          <span className="text-red-600">{op.errors_count} erros</span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500 dark:text-gray-400">Sem dados de operadores</p>
            )}
          </div>
        </div>
      </section>

      {/* Seção: Breakdown Financeiro */}
      {dashboardData?.financial_breakdown && (
        <section>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Breakdown Financeiro</h2>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Receita Bruta</p>
              <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">
                {formatCurrency(dashboardData.financial_breakdown.gross_revenue)}
              </p>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Receita Líquida</p>
              <p className="mt-2 text-2xl font-bold text-green-600">
                {formatCurrency(dashboardData.financial_breakdown.net_revenue)}
              </p>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Cancelamentos</p>
              <p className="mt-2 text-2xl font-bold text-red-600">
                {formatCurrency(dashboardData.financial_breakdown.cancelled_revenue)}
              </p>
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                {dashboardData.financial_breakdown.cancelled_count} pedidos
              </p>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Taxa de Repetição</p>
              <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">
                {(dashboardData.financial_breakdown?.repeat_rate || 0).toFixed(1)}%
              </p>
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                {dashboardData.financial_breakdown.repeat_customers_count} clientes recorrentes
              </p>
            </div>
          </div>
        </section>
      )}

      {/* Seção: Clientes & Mercado */}
      {dashboardData?.customer_metrics && (
        <section>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Clientes & Mercado</h2>
          </div>
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
              <h3 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Métricas de Clientes</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-600">Total Ativo</p>
                  <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">
                    {dashboardData.customer_metrics.total_active}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Novos Hoje</p>
                  <p className="mt-1 text-2xl font-bold text-green-600">
                    {dashboardData.customer_metrics.new_today}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Novos no Mês</p>
                  <p className="mt-1 text-2xl font-bold text-blue-600">
                    {dashboardData.customer_metrics.new_month}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Taxa de Repetição</p>
                  <p className="mt-1 text-2xl font-bold text-purple-600">
                    {(dashboardData.customer_metrics?.repeat_rate || 0).toFixed(1)}%
                  </p>
                </div>
              </div>
            </div>

            <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
              <h3 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Top Clientes</h3>
              {dashboardData.customer_metrics.top_customers && dashboardData.customer_metrics.top_customers.length > 0 ? (
                <div className="space-y-2">
                  {dashboardData.customer_metrics.top_customers.slice(0, 5).map((customer, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between rounded-lg border border-gray-200 bg-gray-50 p-3"
                    >
                      <div>
                        <div className="font-medium text-gray-900">{customer.name}</div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">{customer.phone}</div>
                      </div>
                      <div className="text-right">
                        <div className="font-semibold text-gray-900 dark:text-white">
                          {formatCurrency(customer.total_revenue)}
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">{customer.orders_count} pedidos</div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500 dark:text-gray-400">Sem dados de clientes</p>
              )}
            </div>
          </div>
        </section>
      )}

      {/* Seção: Análise por Bairro */}
      {dashboardData?.bairro_metrics && (
        <section>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Análise por Bairro</h2>
          </div>
          <div className="grid gap-6 lg:grid-cols-3">
            <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
              <h3 className="mb-4 font-semibold text-gray-900">Mais Lucrativos</h3>
              {dashboardData.bairro_metrics.most_profitable && dashboardData.bairro_metrics.most_profitable.length > 0 ? (
                <div className="space-y-2">
                  {dashboardData.bairro_metrics.most_profitable.map((b, idx) => (
                    <div key={idx} className="flex items-center justify-between">
                      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{b.bairro}</span>
                      <span className="text-sm font-bold text-green-600">
                        {formatCurrency(b.revenue)}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500 dark:text-gray-400">Sem dados</p>
              )}
            </div>

            <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
              <h3 className="mb-4 font-semibold text-gray-900">Mais Cancelamentos</h3>
              {dashboardData.bairro_metrics.most_cancelled && dashboardData.bairro_metrics.most_cancelled.length > 0 ? (
                <div className="space-y-2">
                  {dashboardData.bairro_metrics.most_cancelled.map((b, idx) => (
                    <div key={idx} className="flex items-center justify-between">
                      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{b.bairro}</span>
                      <span className="text-sm font-bold text-red-600">{b.cancelled}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500 dark:text-gray-400">Sem dados</p>
              )}
            </div>

            <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
              <h3 className="mb-4 font-semibold text-gray-900">Entrega Mais Lenta</h3>
              {dashboardData.bairro_metrics.slowest_delivery && dashboardData.bairro_metrics.slowest_delivery.length > 0 ? (
                <div className="space-y-2">
                  {dashboardData.bairro_metrics.slowest_delivery.map((b, idx) => (
                    <div key={idx} className="flex items-center justify-between">
                      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{b.bairro}</span>
                      <span className="text-sm font-bold text-amber-600">
                        {b.avg_delivery_time ? `${Math.round(b.avg_delivery_time)} min` : '-'}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500 dark:text-gray-400">Sem dados</p>
              )}
            </div>
          </div>
        </section>
      )}
    </div>
  )
}
