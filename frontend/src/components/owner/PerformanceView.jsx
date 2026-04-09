/**
 * Performance View — Performance Operacional
 * Design Preline-inspired: cards brancos, sem glassmorphism.
 */

import { useState, useEffect } from 'react'
import { Truck, Users, RefreshCw, AlertCircle, Award, Star } from 'lucide-react'
import { apiRequest } from '../../utils/api'

export default function PerformanceView() {
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

  const drivers = dashboardData?.driver_performance || []
  const operators = dashboardData?.operator_performance || []

  return (
    <div className="space-y-4">

      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Performance Operacional</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Rankings e métricas de entregadores e operadores</p>
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

      <div className="grid gap-4 lg:grid-cols-2">

        {/* Entregadores */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
          <div className="flex items-center gap-2 mb-4 pb-3 border-b border-gray-100 dark:border-gray-700">
            <div className="w-8 h-8 rounded-lg bg-amber-50 dark:bg-amber-900/20 flex items-center justify-center">
              <Truck className="w-4 h-4 text-amber-500" />
            </div>
            <span className="text-sm font-semibold text-gray-900 dark:text-white">Entregadores</span>
          </div>

          {drivers.length > 0 ? (
            <div className="space-y-2">
              {drivers.map((driver, idx) => (
                <div
                  key={idx}
                  className={`rounded-lg border px-4 py-3 ${
                    idx === 0
                      ? 'border-amber-200 dark:border-amber-700/40 bg-amber-50 dark:bg-amber-900/10'
                      : 'border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/30'
                  }`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    {idx === 0 ? (
                      <Award className="w-4 h-4 text-amber-500 shrink-0" />
                    ) : (
                      <span className="text-sm font-bold text-gray-400 dark:text-gray-500 w-4 text-center">#{idx + 1}</span>
                    )}
                    <span className="font-medium text-gray-900 dark:text-white truncate">{driver.driver_name || 'Sem nome'}</span>
                  </div>
                  <div className="flex items-center gap-3 mt-1.5 flex-wrap">
                    <span className="text-xs text-gray-500 dark:text-gray-400 bg-white dark:bg-gray-700 px-2 py-0.5 rounded border border-gray-200 dark:border-gray-600">
                      {driver.deliveries_count} entregas
                    </span>
                    {driver.avg_delivery_time && (
                      <span className="text-xs text-gray-500 dark:text-gray-400">{Math.round(driver.avg_delivery_time)} min médio</span>
                    )}
                    {driver.on_time_rate != null && (
                      <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                        {(driver.on_time_rate || 0).toFixed(0)}% no prazo
                      </span>
                    )}
                  </div>
                  {driver.late_deliveries > 0 && (
                    <p className="mt-1.5 text-xs text-rose-600 dark:text-rose-400">
                      {driver.late_deliveries} entregas atrasadas
                    </p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-400 dark:text-gray-500 py-4 text-center">Sem dados de entregadores</p>
          )}
        </div>

        {/* Operadores */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
          <div className="flex items-center gap-2 mb-4 pb-3 border-b border-gray-100 dark:border-gray-700">
            <div className="w-8 h-8 rounded-lg bg-violet-50 dark:bg-violet-900/20 flex items-center justify-center">
              <Users className="w-4 h-4 text-violet-500" />
            </div>
            <span className="text-sm font-semibold text-gray-900 dark:text-white">Operadores</span>
          </div>

          {operators.length > 0 ? (
            operators.filter(op => op.orders_approved > 0).length > 0 ? (
              <div className="space-y-2">
                {operators
                  .filter(op => op.orders_approved > 0)
                  .map((op, idx) => (
                    <div
                      key={op.user_id}
                      className={`rounded-lg border px-4 py-3 ${
                        idx === 0
                          ? 'border-violet-200 dark:border-violet-700/40 bg-violet-50 dark:bg-violet-900/10'
                          : 'border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/30'
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-0.5">
                        {idx === 0 && <Star className="w-4 h-4 text-violet-500 shrink-0" />}
                        <span className="font-medium text-gray-900 dark:text-white truncate">
                          {op.username || op.email?.split('@')[0]}
                        </span>
                      </div>
                      <p className="text-xs text-gray-400 dark:text-gray-500 mb-2">{op.email}</p>
                      <div className="flex items-center gap-3 flex-wrap">
                        <span className="text-xs font-medium text-violet-700 dark:text-violet-300 bg-violet-100 dark:bg-violet-900/30 px-2 py-0.5 rounded">
                          {op.orders_approved} aprovados
                        </span>
                        {op.errors_count > 0 && (
                          <span className="text-xs font-medium text-rose-600 dark:text-rose-400">
                            {op.errors_count} erros
                          </span>
                        )}
                        {op.avg_response_time != null && (
                          <span className="text-xs text-gray-400 dark:text-gray-500">
                            {op.avg_response_time}s resposta
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
              </div>
            ) : (
              <div className="rounded-lg border border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/30 p-4">
                <p className="text-sm text-gray-500 dark:text-gray-400">Nenhum operador aprovou pedidos neste período.</p>
                <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">{operators.length} operadores cadastrados</p>
              </div>
            )
          ) : (
            <p className="text-sm text-gray-400 dark:text-gray-500 py-4 text-center">Sem dados de operadores</p>
          )}
        </div>

      </div>
    </div>
  )
}
