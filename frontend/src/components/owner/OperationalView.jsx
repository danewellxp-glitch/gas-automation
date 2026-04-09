/**
 * Operational View — Métricas Operacionais
 * Design Preline-inspired: cards brancos, sem glassmorphism.
 */

import { useState, useEffect } from 'react'
import { RefreshCw, AlertCircle, Activity, MapPin, Package } from 'lucide-react'
import { apiRequest } from '../../utils/api'
import OrdersByTypeChart from './OrdersByTypeChart'
import BairroChart from './BairroChart'
import TopProductsChart from './TopProductsChart'

const PERIODS = [{ key: 'day', label: 'Dia' }, { key: 'week', label: 'Semana' }, { key: 'month', label: 'Mês' }]

export default function OperationalView() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [period, setPeriod] = useState('day')
  const [dashboardData, setDashboardData] = useState(null)

  useEffect(() => { fetchDashboard() }, [period])

  const fetchDashboard = async () => {
    try {
      setLoading(true)
      setError('')
      const data = await apiRequest(`owner/dashboard?period=${period}`)
      setDashboardData(data)
    } catch (err) {
      setError(err.message || 'Erro ao carregar dados')
    } finally {
      setLoading(false)
    }
  }

  if (loading && !dashboardData) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 animate-spin rounded-full border-2 border-gray-200 border-t-primary-500" />
      </div>
    )
  }

  if (error && !dashboardData) {
    return (
      <div className="rounded-xl border border-red-200 dark:border-red-700/40 bg-red-50 dark:bg-red-900/10 p-5">
        <div className="flex items-center gap-2 mb-2">
          <AlertCircle className="w-4 h-4 text-red-500" />
          <span className="text-sm font-semibold text-red-700 dark:text-red-400">Erro ao carregar dados</span>
        </div>
        <p className="text-sm text-red-600 dark:text-red-400 mb-3">{error}</p>
        <button onClick={fetchDashboard} className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm font-medium hover:bg-red-500 transition-colors">
          Tentar novamente
        </button>
      </div>
    )
  }

  if (!dashboardData) return null

  return (
    <div className="space-y-4">

      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Operação</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Pedidos por tipo, bairro e produtos mais vendidos</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 p-1 gap-1">
            {PERIODS.map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setPeriod(key)}
                className={`rounded-md px-3 py-1 text-xs font-medium transition-all ${
                  period === key
                    ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                    : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                }`}
              >{label}</button>
            ))}
          </div>
          <button
            onClick={fetchDashboard}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Atualizar
          </button>
        </div>
      </div>

      {/* Gráficos */}
      <div className="grid gap-4 lg:grid-cols-2">

        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-lg bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center">
              <Activity className="w-4 h-4 text-blue-500" />
            </div>
            <span className="text-sm font-semibold text-gray-900 dark:text-white">Pedidos por Tipo</span>
          </div>
          <div className="h-72">
            {dashboardData?.orders_by_type ? (
              <OrdersByTypeChart data={dashboardData.orders_by_type} />
            ) : (
              <div className="flex h-full items-center justify-center">
                <p className="text-sm text-gray-400 dark:text-gray-500">Sem dados disponíveis</p>
              </div>
            )}
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-lg bg-cyan-50 dark:bg-cyan-900/20 flex items-center justify-center">
              <MapPin className="w-4 h-4 text-cyan-500" />
            </div>
            <span className="text-sm font-semibold text-gray-900 dark:text-white">Pedidos por Bairro</span>
          </div>
          <div className="h-72">
            {dashboardData?.orders_by_bairro?.length > 0 ? (
              <BairroChart data={dashboardData.orders_by_bairro} />
            ) : (
              <div className="flex h-full items-center justify-center">
                <p className="text-sm text-gray-400 dark:text-gray-500">Sem dados disponíveis</p>
              </div>
            )}
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 lg:col-span-2">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 flex items-center justify-center">
              <Package className="w-4 h-4 text-emerald-500" />
            </div>
            <span className="text-sm font-semibold text-gray-900 dark:text-white">Produtos Mais Vendidos</span>
          </div>
          <div className="h-80">
            {dashboardData?.top_products?.length > 0 ? (
              <TopProductsChart data={dashboardData.top_products} />
            ) : (
              <div className="flex h-full items-center justify-center">
                <p className="text-sm text-gray-400 dark:text-gray-500">Sem dados disponíveis</p>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  )
}
