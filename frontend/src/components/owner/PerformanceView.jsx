/**
 * Performance View - Performance Operacional
 * Entregadores e operadores com rankings e métricas
 */

import { useState, useEffect } from 'react'
import { Truck, Users, RefreshCw, AlertCircle, Award } from 'lucide-react'
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
          <div className="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-gray-200 border-t-primary-600" />
          <p className="mt-4 text-gray-600">Carregando dados de performance...</p>
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

  const drivers = dashboardData?.driver_performance || []
  const operators = dashboardData?.operator_performance || []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Performance Operacional</h1>
          <p className="mt-1 text-sm text-gray-600">
            Rankings e métricas de entregadores e operadores
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

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Entregadores */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">Entregadores</h2>
            <Truck className="h-5 w-5 text-gray-400" />
          </div>
          
          {drivers.length > 0 ? (
            <div className="space-y-3">
              {drivers.map((driver, idx) => (
                <div
                  key={idx}
                  className={`flex items-center justify-between rounded-lg border p-4 ${
                    idx === 0
                      ? 'border-amber-200 bg-amber-50'
                      : 'border-gray-200 bg-gray-50'
                  }`}
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      {idx === 0 && (
                        <Award className="h-4 w-4 text-amber-600" />
                      )}
                      <span className={`text-lg font-bold ${idx === 0 ? 'text-amber-600' : 'text-gray-400'}`}>
                        #{idx + 1}
                      </span>
                      <span className="font-semibold text-gray-900">
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
                    {driver.late_deliveries > 0 && (
                      <div className="mt-2 text-xs text-red-600">
                        {driver.late_deliveries} entregas atrasadas
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-500">Sem dados de entregadores</p>
          )}
        </div>

        {/* Operadores */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">Operadores</h2>
            <Users className="h-5 w-5 text-gray-400" />
          </div>
          
          {operators.length > 0 ? (
            <>
              {/* Filtrar apenas operadores com atividade */}
              {operators.filter(op => op.orders_approved > 0).length > 0 ? (
                <div className="space-y-3">
                  {operators
                    .filter(op => op.orders_approved > 0)
                    .map((op, idx) => (
                      <div
                        key={op.user_id}
                        className={`flex items-center justify-between rounded-lg border p-4 ${
                          idx === 0 && op.orders_approved > 0
                            ? 'border-amber-200 bg-amber-50'
                            : 'border-gray-200 bg-gray-50'
                        }`}
                      >
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            {idx === 0 && op.orders_approved > 0 && (
                              <Award className="h-4 w-4 text-amber-600" />
                            )}
                            <div className="font-semibold text-gray-900">{op.username}</div>
                          </div>
                          <div className="mt-1 text-sm text-gray-600">{op.email}</div>
                          <div className="mt-2 flex items-center gap-4 text-sm">
                            <span className="font-medium text-gray-700">
                              {op.orders_approved} pedidos aprovados
                            </span>
                            {op.errors_count > 0 && (
                              <span className="text-red-600">{op.errors_count} erros</span>
                            )}
                          </div>
                          {op.avg_response_time !== undefined && op.avg_response_time !== null && (
                            <div className="mt-1 text-xs text-gray-500">
                              Tempo médio de resposta: {op.avg_response_time}s
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                </div>
              ) : (
                <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                  <p className="text-sm text-gray-600">
                    Nenhum operador aprovou pedidos neste período.
                  </p>
                  <p className="mt-1 text-xs text-gray-500">
                    Total de operadores cadastrados: {operators.length}
                  </p>
                </div>
              )}
            </>
          ) : (
            <p className="text-sm text-gray-500">Sem dados de operadores</p>
          )}
        </div>
      </div>
    </div>
  )
}
