/**
 * Financial View - Breakdown Financeiro Completo
 * Receita bruta/líquida, cancelamentos, inadimplência, repetição de clientes
 */

import { useState, useEffect } from 'react'
import { DollarSign, TrendingDown, AlertCircle, RefreshCw, Users } from 'lucide-react'
import { apiRequest } from '../../utils/api'
import RevenueChart from './RevenueChart'

export default function FinancialView() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [period, setPeriod] = useState('day')
  const [dashboardData, setDashboardData] = useState(null)

  useEffect(() => {
    fetchDashboard()
  }, [period])

  const fetchDashboard = async () => {
    try {
      setLoading(true)
      setError('')
      const data = await apiRequest(`owner/dashboard?period=${period}`)
      setDashboardData(data)
    } catch (err) {
      console.error('Erro ao buscar dados financeiros:', err)
      setError(err.message || 'Erro ao carregar dados')
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

  if (loading && !dashboardData) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-gray-200 border-t-primary-600" />
          <p className="mt-4 text-gray-600 dark:text-gray-400">Carregando dados financeiros...</p>
        </div>
      </div>
    )
  }

  if (error && !dashboardData) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6">
        <div className="flex items-center gap-2">
          <AlertCircle className="h-5 w-5 text-red-600" />
          <span className="font-semibold text-red-800">Erro ao carregar dados</span>
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

  const financial = dashboardData?.financial_breakdown
  const revenueChart = dashboardData?.revenue_chart

  return (
    <div className="space-y-6 dark:text-gray-100">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Financeiro</h1>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            Breakdown completo de receita, cancelamentos e inadimplência
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

      {/* Receita ao Longo do Tempo */}
      {revenueChart && (
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
          <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Receita ao Longo do Tempo</h2>
          <div className="h-72">
            <RevenueChart data={revenueChart} />
          </div>
        </div>
      )}

      {/* Breakdown de Receita */}
      {financial && (
        <>
          <div>
            <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Breakdown de Receita</h2>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Receita Bruta</p>
                    <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">
                      {formatCurrency(financial.gross_revenue)}
                    </p>
                    <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">Total de pedidos não cancelados</p>
                  </div>
                  <div className="rounded-lg bg-blue-50 p-3 dark:bg-gray-700">
                    <DollarSign className="h-6 w-6 text-blue-600" />
                  </div>
                </div>
              </div>

              <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Receita Líquida</p>
                    <p className="mt-2 text-2xl font-bold text-green-600">
                      {formatCurrency(financial.net_revenue)}
                    </p>
                    <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">Apenas pedidos entregues</p>
                  </div>
                  <div className="rounded-lg bg-green-50 p-3 dark:bg-gray-700">
                    <DollarSign className="h-6 w-6 text-green-600" />
                  </div>
                </div>
              </div>

              <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Cancelamentos</p>
                    <p className="mt-2 text-2xl font-bold text-red-600">
                      {formatCurrency(financial.cancelled_revenue)}
                    </p>
                    <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                      {financial.cancelled_count} pedidos
                    </p>
                  </div>
                  <div className="rounded-lg bg-red-50 p-3 dark:bg-gray-700">
                    <TrendingDown className="h-6 w-6 text-red-600" />
                  </div>
                </div>
              </div>

              <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Taxa de Repetição</p>
                    <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">
                      {(financial.repeat_rate || 0).toFixed(1)}%
                    </p>
                    <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                      {financial.repeat_customers_count} clientes recorrentes
                    </p>
                  </div>
                  <div className="rounded-lg bg-purple-50 p-3 dark:bg-gray-700">
                    <Users className="h-6 w-6 text-purple-600" />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Motivos de Cancelamento */}
          {financial.cancelled_reasons && Object.keys(financial.cancelled_reasons).length > 0 && (
            <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
              <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Motivos de Cancelamento</h2>
              <div className="space-y-2">
                {Object.entries(financial.cancelled_reasons).map(([reason, count]) => (
                  <div
                    key={reason}
                    className="flex items-center justify-between rounded-lg border border-gray-200 bg-gray-50 p-3 dark:bg-gray-700 dark:border-gray-600"
                  >
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{reason}</span>
                    <span className="text-sm font-bold text-red-600">{count} pedidos</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Inadimplência */}
          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
            <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Inadimplência</h2>
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 dark:bg-gray-700 dark:border-gray-600">
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Pedidos Pendentes</p>
                <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">
                  {financial.pending_payments_count}
                </p>
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  Valor: {formatCurrency(financial.pending_payments_value)}
                </p>
              </div>
              <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 dark:bg-gray-700 dark:border-gray-600">
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Clientes Novos</p>
                <p className="mt-2 text-2xl font-bold text-blue-600">
                  {financial.new_customers_count}
                </p>
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Este mês</p>
              </div>
              <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 dark:bg-gray-700 dark:border-gray-600">
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Clientes Recorrentes</p>
                <p className="mt-2 text-2xl font-bold text-green-600">
                  {financial.repeat_customers_count}
                </p>
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  Taxa: {(financial.repeat_rate || 0).toFixed(1)}%
                </p>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
