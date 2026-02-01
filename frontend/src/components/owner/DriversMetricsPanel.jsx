/**
 * Painel de Métricas dos Entregadores para Owner/Manager
 */

import { useState, useEffect } from 'react'
import api from '../../services/api'

export default function DriversMetricsPanel() {
  const [period, setPeriod] = useState('today')
  const [metricsData, setMetricsData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchMetrics()
  }, [period])

  const fetchMetrics = async () => {
    try {
      setLoading(true)
      const { data } = await api.get(`/drivers/metrics/dashboard`, { params: { period } })
      setMetricsData(data)
    } catch (error) {
      console.error('Erro ao buscar métricas:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <p className="text-gray-500 text-center">Carregando métricas...</p>
      </div>
    )
  }

  if (!metricsData) {
    return null
  }

  const periodLabels = {
    'today': 'Hoje',
    'week': 'Esta Semana',
    'month': 'Este Mês'
  }

  const { summary, ranking, drivers_time } = metricsData

  return (
    <div className="space-y-6">
      {/* Header com Filtros */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-800">🚚 Métricas dos Entregadores</h2>
          
          {/* Filtro de Período */}
          <div className="flex gap-2">
            {['today', 'week', 'month'].map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  period === p
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {periodLabels[p]}
              </button>
            ))}
          </div>
        </div>

        {/* Cards de Resumo */}
        <div className="grid grid-cols-4 gap-4 mt-6">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-gray-600 mb-1">Total de Drivers</p>
            <p className="text-3xl font-bold text-blue-600">{summary.total_drivers}</p>
          </div>
          
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <p className="text-sm text-gray-600 mb-1">Entregas ({periodLabels[period]})</p>
            <p className="text-3xl font-bold text-green-600">{summary.total_deliveries}</p>
          </div>
          
          <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
            <p className="text-sm text-gray-600 mb-1">Horas Trabalhadas</p>
            <p className="text-3xl font-bold text-purple-600">{summary.total_hours_worked}h</p>
          </div>
          
          <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
            <p className="text-sm text-gray-600 mb-1">Média por Driver</p>
            <p className="text-3xl font-bold text-orange-600">{summary.average_hours_per_driver}h</p>
          </div>
        </div>
      </div>

      {/* Ranking de Entregas */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-xl font-bold text-gray-800 mb-4">🏆 Ranking de Entregas (Hoje)</h3>
        
        {ranking && ranking.length > 0 ? (
          <div className="space-y-3">
            {ranking.map((driver, index) => {
              const medalIcons = ['🥇', '🥈', '🥉']
              const bgColors = ['bg-yellow-50 border-yellow-300', 'bg-gray-50 border-gray-300', 'bg-orange-50 border-orange-300']
              
              return (
                <div
                  key={driver.driver_id}
                  className={`flex items-center justify-between p-4 rounded-lg border-2 ${
                    index < 3 ? bgColors[index] : 'bg-white border-gray-200'
                  }`}
                >
                  <div className="flex items-center gap-4">
                    <div className="text-3xl">
                      {index < 3 ? medalIcons[index] : `#${index + 1}`}
                    </div>
                    <div>
                      <p className="font-bold text-gray-800">
                        {driver.driver_name}
                        {driver.driver_id && (
                          <span className="text-xs text-gray-400 ml-2">
                            ({driver.driver_id.substring(0, 8)}...)
                          </span>
                        )}
                      </p>
                      <p className="text-sm text-gray-500">
                        {driver.vehicle_type || '-'} • ⭐ {(driver.rating ?? 0).toFixed(1)}
                      </p>
                    </div>
                  </div>
                  
                  <div className="text-right">
                    <p className="text-2xl font-bold text-green-600">{driver.deliveries_count}</p>
                    <p className="text-sm text-gray-500">entregas</p>
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <p className="text-gray-500 text-center py-8">
            Nenhuma entrega registrada hoje
          </p>
        )}
      </div>

      {/* Tabela de Tempo Trabalhado */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-xl font-bold text-gray-800 mb-4">
          ⏱️ Tempo Trabalhado ({periodLabels[period]})
        </h3>
        
        {drivers_time && drivers_time.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Entregador
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Status Atual
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Total Horas
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Disponível
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Ocupado
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Pausa
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {drivers_time.map((driver) => {
                  const statusColors = {
                    'available': 'text-green-600',
                    'busy': 'text-blue-600',
                    'break': 'text-yellow-600',
                    'offline': 'text-gray-600'
                  }
                  
                  return (
                    <tr key={driver.driver_id}>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div>
                          <div className="font-medium text-gray-900">
                            {driver.driver_name}
                            {driver.driver_id && (
                              <span className="text-xs text-gray-400 ml-2">
                                (ID: {driver.driver_id.substring(0, 8)}...)
                              </span>
                            )}
                          </div>
                          <div className="text-sm text-gray-500">⭐ {(driver.rating ?? 0).toFixed(1)}</div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`font-semibold ${statusColors[driver.current_status] || 'text-gray-600'}`}>
                          {driver.current_status || '-'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="text-lg font-bold text-gray-800">{driver.total_hours}h</span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                        {driver.by_status?.available?.hours || 0}h
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                        {driver.by_status?.busy?.hours || 0}h
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                        {driver.by_status?.break?.hours || 0}h
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-gray-500 text-center py-8">
            Nenhum dado de tempo disponível para {periodLabels[period].toLowerCase()}
          </p>
        )}
      </div>
    </div>
  )
}
