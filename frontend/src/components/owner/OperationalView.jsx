/**
 * Operational View - Métricas Operacionais
 * Gráficos de pedidos por tipo, por bairro, produtos mais vendidos
 */

import { useState, useEffect } from 'react'
import { RefreshCw, AlertCircle } from 'lucide-react'
import { apiRequest } from '../../utils/api'
import OrdersByTypeChart from './OrdersByTypeChart'
import BairroChart from './BairroChart'
import TopProductsChart from './TopProductsChart'

export default function OperationalView() {
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
      console.error('Erro ao buscar dados operacionais:', err)
      setError(err.message || 'Erro ao carregar dados')
    } finally {
      setLoading(false)
    }
  }

  if (loading && !dashboardData) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-gray-200 border-t-primary-600" />
          <p className="mt-4 text-gray-600 dark:text-gray-400">Carregando dados operacionais...</p>
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

  return (
    <div className="space-y-6 dark:text-gray-100">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Operação</h1>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            Análise visual de pedidos, produtos e bairros
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

      {/* Gráficos */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Pedidos por Tipo */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Pedidos por Tipo</h3>
          </div>
          <div className="h-80">
            {dashboardData?.orders_by_type ? (
              <OrdersByTypeChart data={dashboardData.orders_by_type} />
            ) : (
              <div className="flex h-full items-center justify-center">
                <p className="text-sm text-gray-500 dark:text-gray-400">Carregando dados...</p>
              </div>
            )}
          </div>
        </div>

        {/* Pedidos por Bairro */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Pedidos por Bairro</h3>
          </div>
          <div className="h-80">
            {dashboardData?.orders_by_bairro && dashboardData.orders_by_bairro.length > 0 ? (
              <BairroChart data={dashboardData.orders_by_bairro} />
            ) : (
              <div className="flex h-full items-center justify-center">
                <p className="text-sm text-gray-500 dark:text-gray-400">Sem dados disponíveis</p>
              </div>
            )}
          </div>
        </div>

        {/* Produtos Mais Vendidos */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm lg:col-span-2 dark:bg-gray-800 dark:border-gray-700">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Produtos Mais Vendidos</h3>
          </div>
          <div className="h-96">
            {dashboardData?.top_products && dashboardData.top_products.length > 0 ? (
              <TopProductsChart data={dashboardData.top_products} />
            ) : (
              <div className="flex h-full items-center justify-center">
                <p className="text-sm text-gray-500 dark:text-gray-400">Sem dados disponíveis</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
