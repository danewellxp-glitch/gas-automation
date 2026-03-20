/**
 * Performance View - Performance Operacional
 * Entregadores e operadores com rankings e métricas
 */

import { useState, useEffect } from 'react'
import { Truck, Users, RefreshCw, AlertCircle, Award, Star } from 'lucide-react'
import { apiRequest } from '../../utils/api'

export default function PerformanceView() {
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
      console.error('Erro ao buscar dados de performance:', err)
      setError(err.message || 'Erro ao carregar dados')
    } finally {
      setLoading(false)
    }
  }

  if (loading && !dashboardData) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-gray-700 border-t-amber-500" />
          <p className="mt-4 text-xs text-gray-500 tracking-widest uppercase">Carregando performance...</p>
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

  const drivers = dashboardData?.driver_performance || []
  const operators = dashboardData?.operator_performance || []

  return (
    <div className="space-y-4">

      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-black tracking-tight text-white">Performance Operacional</h1>
          <p className="mt-1 text-xs text-gray-500">Rankings e métricas de entregadores e operadores</p>
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

      <div className="grid gap-4 lg:grid-cols-2">

        {/* Entregadores */}
        <div className="rounded-2xl border border-amber-500/20 bg-gray-900 p-5 shadow-lg shadow-amber-500/10">
          <div className="mb-4 flex items-center gap-3">
            <div className="rounded-lg bg-amber-500/10 p-2 ring-1 ring-amber-500/20">
              <Truck className="h-4 w-4 text-amber-400" />
            </div>
            <span className="text-xs font-bold uppercase tracking-widest text-amber-400/80">Entregadores</span>
          </div>

          {drivers.length > 0 ? (
            <div className="space-y-2">
              {drivers.map((driver, idx) => (
                <div
                  key={idx}
                  className={`rounded-xl border px-4 py-3 ${
                    idx === 0
                      ? 'border-amber-500/30 bg-amber-500/10'
                      : 'border-gray-700/50 bg-gray-800/40'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    {idx === 0 && <Award className="h-4 w-4 text-amber-400" />}
                    <span className={`text-lg font-black ${idx === 0 ? 'text-amber-400' : 'text-gray-600'}`}>
                      #{idx + 1}
                    </span>
                    <span className="font-bold text-white">{driver.driver_name || 'Sem nome'}</span>
                  </div>
                  <div className="mt-1 flex items-center gap-4">
                    <span className="text-xs text-gray-500">{driver.deliveries_count} entregas</span>
                    {driver.avg_delivery_time && (
                      <span className="text-xs text-gray-500">{Math.round(driver.avg_delivery_time)} min médio</span>
                    )}
                    {driver.on_time_rate !== undefined && driver.on_time_rate !== null && (
                      <span className="text-xs text-emerald-400">
                        {(driver.on_time_rate || 0).toFixed(0)}% no prazo
                      </span>
                    )}
                  </div>
                  {driver.late_deliveries > 0 && (
                    <div className="mt-1 text-xs text-red-400">
                      {driver.late_deliveries} entregas atrasadas
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-600">Sem dados de entregadores</p>
          )}
        </div>

        {/* Operadores */}
        <div className="rounded-2xl border border-violet-500/20 bg-gray-900 p-5 shadow-lg shadow-violet-500/10">
          <div className="mb-4 flex items-center gap-3">
            <div className="rounded-lg bg-violet-500/10 p-2 ring-1 ring-violet-500/20">
              <Users className="h-4 w-4 text-violet-400" />
            </div>
            <span className="text-xs font-bold uppercase tracking-widest text-violet-400/80">Operadores</span>
          </div>

          {operators.length > 0 ? (
            <>
              {operators.filter(op => op.orders_approved > 0).length > 0 ? (
                <div className="space-y-2">
                  {operators
                    .filter(op => op.orders_approved > 0)
                    .map((op, idx) => (
                      <div
                        key={op.user_id}
                        className={`rounded-xl border px-4 py-3 ${
                          idx === 0
                            ? 'border-violet-500/30 bg-violet-500/10'
                            : 'border-gray-700/50 bg-gray-800/40'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          {idx === 0 && <Star className="h-4 w-4 text-violet-400" />}
                          <span className="font-bold text-white">{op.username || op.email?.split('@')[0]}</span>
                        </div>
                        <div className="mt-0.5 text-xs text-gray-500">{op.email}</div>
                        <div className="mt-1 flex items-center gap-4">
                          <span className="text-sm font-bold text-violet-400">
                            {op.orders_approved} pedidos aprovados
                          </span>
                          {op.errors_count > 0 && (
                            <span className="text-xs text-red-400">{op.errors_count} erros</span>
                          )}
                        </div>
                        {op.avg_response_time !== undefined && op.avg_response_time !== null && (
                          <div className="mt-0.5 text-xs text-gray-600">
                            Tempo médio de resposta: {op.avg_response_time}s
                          </div>
                        )}
                      </div>
                    ))}
                </div>
              ) : (
                <div className="rounded-xl border border-gray-700/50 bg-gray-800/40 p-4">
                  <p className="text-sm text-gray-500">Nenhum operador aprovou pedidos neste período.</p>
                  <p className="mt-1 text-xs text-gray-600">Total de operadores cadastrados: {operators.length}</p>
                </div>
              )}
            </>
          ) : (
            <p className="text-sm text-gray-600">Sem dados de operadores</p>
          )}
        </div>

      </div>
    </div>
  )
}
