/**
 * Painel "Meu Tempo Trabalhado" para o Dashboard do Driver
 */

import { useState, useEffect } from 'react'
import { driverApi } from '../../utils/driverApi'

export default function MyTimePanel() {
  const [period, setPeriod] = useState('today')
  const [timeData, setTimeData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchTimeData()
  }, [period])

  const fetchTimeData = async () => {
    try {
      setLoading(true)
      const data = await driverApi.getTimeSummary(period)
      setTimeData(data)
    } catch (error) {
      console.error('Erro ao buscar dados de tempo:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <p className="text-gray-500 text-center">Carregando...</p>
      </div>
    )
  }

  if (!timeData) {
    return null
  }

  const statusLabels = {
    'available': { label: 'Disponível', color: 'bg-green-500', icon: '🟢' },
    'busy': { label: 'Ocupado', color: 'bg-blue-500', icon: '🔵' },
    'break': { label: 'Pausa', color: 'bg-yellow-500', icon: '🟡' },
    'offline': { label: 'Offline', color: 'bg-gray-500', icon: '⚪' }
  }

  const periodLabels = {
    'today': 'Hoje',
    'week': 'Esta Semana',
    'month': 'Este Mês'
  }

  return (
    <div className="bg-white rounded-lg shadow p-6 mb-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold text-gray-800">⏱️ Meu Tempo Trabalhado</h2>
        
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

      {/* Total */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6 text-center">
        <p className="text-sm text-gray-600 mb-1">Tempo Total Trabalhado</p>
        <p className="text-4xl font-bold text-blue-600">
          {timeData.total_hours}h
        </p>
        <p className="text-sm text-gray-500 mt-1">
          {timeData.total_minutes} minutos
        </p>
      </div>

      {/* Breakdown por Status */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Tempo por Status:</h3>
        
        {Object.entries(timeData.by_status || {}).map(([status, data]) => {
          const statusInfo = statusLabels[status] || { label: status, color: 'bg-gray-500', icon: '⚪' }
          const percentage = (data.minutes / timeData.total_minutes * 100).toFixed(1)
          
          return (
            <div key={status} className="space-y-2">
              {/* Label e Tempo */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-xl">{statusInfo.icon}</span>
                  <span className="font-medium text-gray-700">{statusInfo.label}</span>
                </div>
                <div className="text-right">
                  <span className="font-bold text-gray-800">{data.hours}h</span>
                  <span className="text-sm text-gray-500 ml-2">({percentage}%)</span>
                </div>
              </div>
              
              {/* Barra de Progresso */}
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className={`${statusInfo.color} h-2 rounded-full transition-all`}
                  style={{ width: `${percentage}%` }}
                />
              </div>
              
              {/* Detalhes */}
              <p className="text-xs text-gray-500 text-right">
                {data.minutes} min • {data.count} período(s)
              </p>
            </div>
          )
        })}
        
        {Object.keys(timeData.by_status || {}).length === 0 && (
          <p className="text-gray-500 text-center py-4">
            Nenhum tempo registrado para {periodLabels[period].toLowerCase()}
          </p>
        )}
      </div>
    </div>
  )
}
