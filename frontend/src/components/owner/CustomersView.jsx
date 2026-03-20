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

  const formatCurrency = (value) =>
    new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 2 }).format(value || 0)

  if (loading && !dashboardData) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-gray-700 border-t-cyan-500" />
          <p className="mt-4 text-xs text-gray-500 tracking-widest uppercase">Carregando clientes...</p>
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

  const customers = dashboardData?.customer_metrics
  const bairros = dashboardData?.bairro_metrics

  return (
    <div className="space-y-4">

      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-black tracking-tight text-white">Clientes & Mercado</h1>
          <p className="mt-1 text-xs text-gray-500">Análise de clientes e performance por região</p>
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

      {/* Métricas + Top Clientes */}
      {customers && (
        <div className="grid gap-4 lg:grid-cols-2">

          {/* Métricas de Clientes */}
          <div className="rounded-2xl border border-cyan-500/20 bg-gray-900 p-5 shadow-lg shadow-cyan-500/10">
            <div className="mb-5 flex items-center gap-3">
              <div className="rounded-lg bg-cyan-500/10 p-2 ring-1 ring-cyan-500/20">
                <Users className="h-4 w-4 text-cyan-400" />
              </div>
              <span className="text-xs font-bold uppercase tracking-widest text-cyan-400/80">Métricas de Clientes</span>
            </div>
            <div className="grid grid-cols-2 gap-5">
              <div>
                <p className="text-3xl font-black text-white">{customers.total_active}</p>
                <p className="mt-1 text-xs text-gray-500 uppercase tracking-wider">Total Ativo</p>
                <p className="text-xs text-gray-600">Últimos 30 dias</p>
              </div>
              <div>
                <p className="text-3xl font-black text-emerald-400">{customers.new_today}</p>
                <p className="mt-1 text-xs text-gray-500 uppercase tracking-wider">Novos Hoje</p>
                <p className="text-xs text-gray-600">Novos clientes</p>
              </div>
              <div>
                <p className="text-3xl font-black text-blue-400">{customers.new_month}</p>
                <p className="mt-1 text-xs text-gray-500 uppercase tracking-wider">Novos no Mês</p>
                <p className="text-xs text-gray-600">Este mês</p>
              </div>
              <div>
                <p className="text-3xl font-black text-violet-400">{(customers.repeat_rate || 0).toFixed(1)}%</p>
                <p className="mt-1 text-xs text-gray-500 uppercase tracking-wider">Taxa de Repetição</p>
                <p className="text-xs text-gray-600">Fidelização</p>
              </div>
            </div>
          </div>

          {/* Top Clientes */}
          <div className="rounded-2xl border border-blue-500/20 bg-gray-900 p-5 shadow-lg shadow-blue-500/10">
            <div className="mb-5 flex items-center gap-3">
              <div className="rounded-lg bg-blue-500/10 p-2 ring-1 ring-blue-500/20">
                <TrendingUp className="h-4 w-4 text-blue-400" />
              </div>
              <span className="text-xs font-bold uppercase tracking-widest text-blue-400/80">Top Clientes</span>
            </div>
            {customers.top_customers && customers.top_customers.length > 0 ? (
              <div className="space-y-2">
                {customers.top_customers.slice(0, 5).map((customer, idx) => (
                  <div
                    key={idx}
                    className={`flex items-center justify-between rounded-xl border px-4 py-3 ${
                      idx === 0
                        ? 'border-blue-500/30 bg-blue-500/10'
                        : 'border-gray-700/50 bg-gray-800/40'
                    }`}
                  >
                    <div>
                      <div className="font-bold text-white text-sm">{customer.name}</div>
                      <div className="text-xs text-gray-500">{customer.phone}</div>
                    </div>
                    <div className="text-right">
                      <div className="font-bold text-emerald-400 text-sm">{formatCurrency(customer.total_revenue)}</div>
                      <div className="text-xs text-gray-500">{customer.orders_count} pedidos</div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-600">Sem dados de clientes</p>
            )}
          </div>

        </div>
      )}

      {/* Análise por Bairro */}
      {bairros && (
        <div>
          <div className="mb-4 flex items-center gap-2">
            <MapPin className="h-4 w-4 text-cyan-400" />
            <span className="text-xs font-bold uppercase tracking-widest text-gray-400">Análise por Bairro</span>
          </div>
          <div className="grid gap-4 lg:grid-cols-3">

            <div className="rounded-2xl border border-emerald-500/20 bg-gray-900 p-5 shadow-lg shadow-emerald-500/10">
              <p className="mb-4 text-xs font-bold uppercase tracking-widest text-emerald-400/80">Mais Lucrativos</p>
              {bairros.most_profitable && bairros.most_profitable.length > 0 ? (
                <div>
                  {bairros.most_profitable.map((b, idx) => (
                    <div key={idx} className="flex justify-between items-center py-1.5 border-b border-gray-800 last:border-0">
                      <span className="text-sm font-medium text-gray-300">{b.bairro}</span>
                      <span className="text-sm font-bold text-emerald-400">{formatCurrency(b.revenue)}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-600">Sem dados</p>
              )}
            </div>

            <div className="rounded-2xl border border-red-500/20 bg-gray-900 p-5 shadow-lg shadow-red-500/10">
              <p className="mb-4 text-xs font-bold uppercase tracking-widest text-red-400/80">Mais Cancelamentos</p>
              {bairros.most_cancelled && bairros.most_cancelled.length > 0 ? (
                <div>
                  {bairros.most_cancelled.map((b, idx) => (
                    <div key={idx} className="flex justify-between items-center py-1.5 border-b border-gray-800 last:border-0">
                      <span className="text-sm font-medium text-gray-300">{b.bairro}</span>
                      <span className="text-sm font-bold text-red-400">{b.cancelled}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-600">Sem dados</p>
              )}
            </div>

            <div className="rounded-2xl border border-amber-500/20 bg-gray-900 p-5 shadow-lg shadow-amber-500/10">
              <p className="mb-4 text-xs font-bold uppercase tracking-widest text-amber-400/80">Entrega Mais Lenta</p>
              {bairros.slowest_delivery && bairros.slowest_delivery.length > 0 ? (
                <div>
                  {bairros.slowest_delivery.map((b, idx) => (
                    <div key={idx} className="flex justify-between items-center py-1.5 border-b border-gray-800 last:border-0">
                      <span className="text-sm font-medium text-gray-300">{b.bairro}</span>
                      <span className="text-sm font-bold text-amber-400">
                        {b.avg_delivery_time ? `${Math.round(b.avg_delivery_time)} min` : '-'}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-600">Sem dados</p>
              )}
            </div>

          </div>
        </div>
      )}

    </div>
  )
}
