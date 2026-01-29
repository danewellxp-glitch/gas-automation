/**
 * Customers View - Clientes & Mercado
 * Métricas de clientes, top clientes, análise por bairro
 */

import { useState, useEffect } from 'react'
import { Users, MapPin, RefreshCw, AlertCircle, TrendingUp } from 'lucide-react'
import { apiRequest } from '../../utils/api'

export default function CustomersView() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [dashboardData, setDashboardData] = useState(null)

  useEffect(() => {
    fetchDashboard()
  }, [])

  const fetchDashboard = async () => {
    try {
      setLoading(true)
      setError('')
      const data = await apiRequest('owner/dashboard?period=month')
      setDashboardData(data)
    } catch (err) {
      console.error('Erro ao buscar dados de clientes:', err)
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
          <p className="mt-4 text-gray-600">Carregando dados de clientes...</p>
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

  const customers = dashboardData?.customer_metrics
  const bairros = dashboardData?.bairro_metrics

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Clientes & Mercado</h1>
          <p className="mt-1 text-sm text-gray-600">
            Análise de clientes e performance por região
          </p>
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

      {/* Métricas de Clientes */}
      {customers && (
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Métricas de Clientes</h2>
              <Users className="h-5 w-5 text-gray-400" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-600">Total Ativo</p>
                <p className="mt-1 text-2xl font-bold text-gray-900">
                  {customers.total_active}
                </p>
                <p className="mt-1 text-xs text-gray-500">Últimos 30 dias</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Novos Hoje</p>
                <p className="mt-1 text-2xl font-bold text-green-600">
                  {customers.new_today}
                </p>
                <p className="mt-1 text-xs text-gray-500">Novos clientes</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Novos no Mês</p>
                <p className="mt-1 text-2xl font-bold text-blue-600">
                  {customers.new_month}
                </p>
                <p className="mt-1 text-xs text-gray-500">Este mês</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Taxa de Repetição</p>
                <p className="mt-1 text-2xl font-bold text-purple-600">
                  {(customers.repeat_rate || 0).toFixed(1)}%
                </p>
                <p className="mt-1 text-xs text-gray-500">Fidelização</p>
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Top Clientes</h2>
              <TrendingUp className="h-5 w-5 text-gray-400" />
            </div>
            {customers.top_customers && customers.top_customers.length > 0 ? (
              <div className="space-y-2">
                {customers.top_customers.slice(0, 5).map((customer, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between rounded-lg border border-gray-200 bg-gray-50 p-3"
                  >
                    <div>
                      <div className="font-medium text-gray-900">{customer.name}</div>
                      <div className="text-xs text-gray-500">{customer.phone}</div>
                    </div>
                    <div className="text-right">
                      <div className="font-semibold text-gray-900">
                        {formatCurrency(customer.total_revenue)}
                      </div>
                      <div className="text-xs text-gray-500">{customer.orders_count} pedidos</div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500">Sem dados de clientes</p>
            )}
          </div>
        </div>
      )}

      {/* Análise por Bairro */}
      {bairros && (
        <div>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">Análise por Bairro</h2>
            <MapPin className="h-5 w-5 text-gray-400" />
          </div>
          <div className="grid gap-6 lg:grid-cols-3">
            <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
              <h3 className="mb-4 font-semibold text-gray-900">Mais Lucrativos</h3>
              {bairros.most_profitable && bairros.most_profitable.length > 0 ? (
                <div className="space-y-2">
                  {bairros.most_profitable.map((b, idx) => (
                    <div key={idx} className="flex items-center justify-between">
                      <span className="text-sm font-medium text-gray-700">{b.bairro}</span>
                      <span className="text-sm font-bold text-green-600">
                        {formatCurrency(b.revenue)}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500">Sem dados</p>
              )}
            </div>

            <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
              <h3 className="mb-4 font-semibold text-gray-900">Mais Cancelamentos</h3>
              {bairros.most_cancelled && bairros.most_cancelled.length > 0 ? (
                <div className="space-y-2">
                  {bairros.most_cancelled.map((b, idx) => (
                    <div key={idx} className="flex items-center justify-between">
                      <span className="text-sm font-medium text-gray-700">{b.bairro}</span>
                      <span className="text-sm font-bold text-red-600">{b.cancelled}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500">Sem dados</p>
              )}
            </div>

            <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
              <h3 className="mb-4 font-semibold text-gray-900">Entrega Mais Lenta</h3>
              {bairros.slowest_delivery && bairros.slowest_delivery.length > 0 ? (
                <div className="space-y-2">
                  {bairros.slowest_delivery.map((b, idx) => (
                    <div key={idx} className="flex items-center justify-between">
                      <span className="text-sm font-medium text-gray-700">{b.bairro}</span>
                      <span className="text-sm font-bold text-amber-600">
                        {b.avg_delivery_time ? `${Math.round(b.avg_delivery_time)} min` : '-'}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500">Sem dados</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
