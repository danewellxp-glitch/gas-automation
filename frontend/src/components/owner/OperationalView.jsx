/**
 * Operational View - Métricas Operacionais
 * Gráficos de pedidos por tipo, por bairro, produtos mais vendidos
 */

import { useState, useEffect } from 'react'
import { RefreshCw, AlertCircle, Activity, MapPin, Package } from 'lucide-react'
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
          <div className="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-gray-700 border-t-blue-500" />
          <p className="mt-4 text-xs text-gray-500 tracking-widest uppercase">Carregando operação...</p>
        </div>
      </div>
    )
  }

  if (error && !dashboardData) {
    return (
      <div className="rounded-2xl border border-red-500/30 bg-red-950/40 p-6">
        <div className="flex items-center gap-2">
          <AlertCircle className="h-5 w-5 text-red-400" />
          <span className="font-semibold text-red-300">Erro ao carregar dados</span>
        </div>
        <p className="mt-2 text-sm text-red-400">{error}</p>
        <button
          onClick={fetchDashboard}
          className="mt-4 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-500"
        >
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
          <h1 className="text-2xl font-black tracking-tight text-white">Operação</h1>
          <p className="mt-1 text-xs text-gray-500">Análise visual de pedidos, produtos e bairros</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border border-gray-700 bg-gray-900/80 p-1 gap-1">
            {[{ key: 'day', label: 'Dia' }, { key: 'week', label: 'Semana' }, { key: 'month', label: 'Mês' }].map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setPeriod(key)}
                className={`rounded-md px-4 py-1.5 text-xs font-bold transition-all ${
                  period === key
                    ? 'bg-blue-600 text-white shadow-sm shadow-blue-500/30'
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

      {/* Gráficos */}
      <div className="grid gap-4 lg:grid-cols-2">

        {/* Pedidos por Tipo */}
        <div className="rounded-2xl border border-blue-500/20 bg-gray-900 p-5 shadow-lg shadow-blue-500/10">
          <div className="mb-4 flex items-center gap-2">
            <div className="rounded-lg bg-blue-500/10 p-2 ring-1 ring-blue-500/20">
              <Activity className="h-4 w-4 text-blue-400" />
            </div>
            <span className="text-xs font-bold uppercase tracking-widest text-gray-400">Pedidos por Tipo</span>
          </div>
          <div className="h-80">
            {dashboardData?.orders_by_type ? (
              <OrdersByTypeChart data={dashboardData.orders_by_type} />
            ) : (
              <div className="flex h-full items-center justify-center">
                <p className="text-sm text-gray-600">Sem dados disponíveis</p>
              </div>
            )}
          </div>
        </div>

        {/* Pedidos por Bairro */}
        <div className="rounded-2xl border border-cyan-500/20 bg-gray-900 p-5 shadow-lg shadow-cyan-500/10">
          <div className="mb-4 flex items-center gap-2">
            <div className="rounded-lg bg-cyan-500/10 p-2 ring-1 ring-cyan-500/20">
              <MapPin className="h-4 w-4 text-cyan-400" />
            </div>
            <span className="text-xs font-bold uppercase tracking-widest text-gray-400">Pedidos por Bairro</span>
          </div>
          <div className="h-80">
            {dashboardData?.orders_by_bairro && dashboardData.orders_by_bairro.length > 0 ? (
              <BairroChart data={dashboardData.orders_by_bairro} />
            ) : (
              <div className="flex h-full items-center justify-center">
                <p className="text-sm text-gray-600">Sem dados disponíveis</p>
              </div>
            )}
          </div>
        </div>

        {/* Produtos Mais Vendidos */}
        <div className="rounded-2xl border border-emerald-500/20 bg-gray-900 p-5 shadow-lg shadow-emerald-500/10 lg:col-span-2">
          <div className="mb-4 flex items-center gap-2">
            <div className="rounded-lg bg-emerald-500/10 p-2 ring-1 ring-emerald-500/20">
              <Package className="h-4 w-4 text-emerald-400" />
            </div>
            <span className="text-xs font-bold uppercase tracking-widest text-gray-400">Produtos Mais Vendidos</span>
          </div>
          <div className="h-96">
            {dashboardData?.top_products && dashboardData.top_products.length > 0 ? (
              <TopProductsChart data={dashboardData.top_products} />
            ) : (
              <div className="flex h-full items-center justify-center">
                <p className="text-sm text-gray-600">Sem dados disponíveis</p>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  )
}
