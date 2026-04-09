/**
 * Customers View — Clientes & Mercado
 * Design Preline-inspired: cards brancos, sem glassmorphism.
 */

import { useState, useEffect } from 'react'
import { Users, MapPin, RefreshCw, AlertCircle, TrendingUp } from 'lucide-react'
import { apiRequest } from '../../utils/api'

export default function CustomersView() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [dashboardData, setDashboardData] = useState(null)

  useEffect(() => { fetchDashboard() }, [])

  const fetchDashboard = async () => {
    try {
      setLoading(true)
      setError('')
      const data = await apiRequest('owner/dashboard?period=month')
      setDashboardData(data)
    } catch (err) {
      setError(err.message || 'Erro ao carregar dados')
    } finally {
      setLoading(false)
    }
  }

  const fmtCurrency = (v) =>
    new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 2 }).format(v || 0)

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

  const customers = dashboardData?.customer_metrics
  const bairros = dashboardData?.bairro_metrics

  return (
    <div className="space-y-4">

      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Clientes & Mercado</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Análise de clientes e performance por região</p>
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

      {/* Métricas + Top Clientes */}
      {customers && (
        <div className="grid gap-4 lg:grid-cols-2">

          {/* Métricas de Clientes */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
            <div className="flex items-center gap-2 mb-4 pb-3 border-b border-gray-100 dark:border-gray-700">
              <div className="w-8 h-8 rounded-lg bg-cyan-50 dark:bg-cyan-900/20 flex items-center justify-center">
                <Users className="w-4 h-4 text-cyan-500" />
              </div>
              <span className="text-sm font-semibold text-gray-900 dark:text-white">Métricas de Clientes</span>
            </div>
            <div className="grid grid-cols-2 gap-4">
              {[
                { value: customers.total_active, label: 'Total Ativo', sub: 'Últimos 30 dias', color: 'text-gray-900 dark:text-white' },
                { value: customers.new_today,    label: 'Novos Hoje',  sub: 'Novos clientes',  color: 'text-emerald-600 dark:text-emerald-400' },
                { value: customers.new_month,    label: 'Novos no Mês', sub: 'Este mês',       color: 'text-blue-600 dark:text-blue-400' },
                { value: `${(customers.repeat_rate || 0).toFixed(1)}%`, label: 'Taxa de Repetição', sub: 'Fidelização', color: 'text-violet-600 dark:text-violet-400' },
              ].map(({ value, label, sub, color }) => (
                <div key={label}>
                  <p className={`text-2xl font-bold ${color}`}>{value}</p>
                  <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mt-0.5">{label}</p>
                  <p className="text-xs text-gray-400 dark:text-gray-500">{sub}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Top Clientes */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
            <div className="flex items-center gap-2 mb-4 pb-3 border-b border-gray-100 dark:border-gray-700">
              <div className="w-8 h-8 rounded-lg bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center">
                <TrendingUp className="w-4 h-4 text-blue-500" />
              </div>
              <span className="text-sm font-semibold text-gray-900 dark:text-white">Top Clientes</span>
            </div>
            {customers.top_customers?.length > 0 ? (
              <div className="space-y-2">
                {customers.top_customers.slice(0, 5).map((customer, idx) => (
                  <div
                    key={idx}
                    className={`flex items-center justify-between px-3 py-2.5 rounded-lg border ${
                      idx === 0
                        ? 'border-blue-200 dark:border-blue-700/40 bg-blue-50 dark:bg-blue-900/10'
                        : 'border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/30'
                    }`}
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{customer.name}</p>
                      <p className="text-xs text-gray-400 dark:text-gray-500">{customer.phone}</p>
                    </div>
                    <div className="text-right shrink-0 ml-3">
                      <p className="text-sm font-semibold text-emerald-600 dark:text-emerald-400">{fmtCurrency(customer.total_revenue)}</p>
                      <p className="text-xs text-gray-400 dark:text-gray-500">{customer.orders_count} pedidos</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-400 dark:text-gray-500 py-4 text-center">Sem dados de clientes</p>
            )}
          </div>

        </div>
      )}

      {/* Análise por Bairro */}
      {bairros && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <MapPin className="w-4 h-4 text-gray-400 dark:text-gray-500" />
            <span className="text-sm font-semibold text-gray-900 dark:text-white">Análise por Bairro</span>
          </div>
          <div className="grid gap-4 lg:grid-cols-3">

            {[
              { title: 'Mais Lucrativos', items: bairros.most_profitable, valueKey: 'revenue', valueColor: 'text-emerald-600 dark:text-emerald-400', renderValue: (b) => fmtCurrency(b.revenue) },
              { title: 'Mais Cancelamentos', items: bairros.most_cancelled, valueKey: 'cancelled', valueColor: 'text-red-600 dark:text-red-400', renderValue: (b) => `${b.cancelled} cancel.` },
              { title: 'Entrega Mais Lenta', items: bairros.slowest_delivery, valueKey: 'avg_delivery_time', valueColor: 'text-amber-600 dark:text-amber-400', renderValue: (b) => b.avg_delivery_time ? `${Math.round(b.avg_delivery_time)} min` : '-' },
            ].map(({ title, items, valueColor, renderValue }) => (
              <div key={title} className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
                <p className="text-sm font-semibold text-gray-900 dark:text-white mb-3">{title}</p>
                {items?.length > 0 ? (
                  <div className="space-y-0">
                    {items.map((b, idx) => (
                      <div key={idx} className="flex justify-between items-center py-2 border-b border-gray-100 dark:border-gray-700 last:border-0">
                        <span className="text-sm text-gray-600 dark:text-gray-400 truncate">{b.bairro}</span>
                        <span className={`text-sm font-semibold shrink-0 ml-2 ${valueColor}`}>{renderValue(b)}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-400 dark:text-gray-500">Sem dados</p>
                )}
              </div>
            ))}

          </div>
        </div>
      )}

    </div>
  )
}
