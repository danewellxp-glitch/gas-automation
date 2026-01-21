/**
 * Página de Histórico de Entregas
 */

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { driverApi } from '../../utils/driverApi'

export default function DeliveryHistory() {
  const navigate = useNavigate()
  const [deliveries, setDeliveries] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        setLoading(true)
        const data = await driverApi.getDeliveries('completed')
        setDeliveries(data)
      } catch (err) {
        console.error('Erro ao buscar histórico:', err)
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchHistory()
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <p className="text-gray-600">Carregando histórico...</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-100 pb-24">
      {/* Header */}
      <div className="bg-white shadow-md p-4 mb-4">
        <button
          onClick={() => navigate('/driver/dashboard')}
          className="text-blue-600 hover:text-blue-700 mb-2"
        >
          ← Voltar
        </button>
        <h1 className="text-2xl font-bold text-gray-800">Histórico de Entregas</h1>
      </div>

      <div className="max-w-2xl mx-auto px-4">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
            {error}
          </div>
        )}

        {deliveries.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-8 text-center">
            <div className="text-6xl mb-4">📭</div>
            <h3 className="text-xl font-semibold text-gray-800 mb-2">
              Nenhuma entrega finalizada ainda
            </h3>
            <p className="text-gray-500">
              Suas entregas concluídas aparecerão aqui
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {deliveries.map((delivery) => (
              <HistoryCard key={delivery.id} delivery={delivery} />
            ))}
          </div>
        )}
      </div>

      {/* Bottom Navigation */}
      <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 shadow-lg">
        <div className="flex justify-around items-center h-16">
          <button
            onClick={() => navigate('/driver/dashboard')}
            className="flex flex-col items-center justify-center flex-1 py-2 text-gray-600 hover:text-blue-600"
          >
            <span className="text-2xl">🏠</span>
            <span className="text-xs font-medium">Início</span>
          </button>
          <button
            onClick={() => navigate('/driver/history')}
            className="flex flex-col items-center justify-center flex-1 py-2 text-blue-600"
          >
            <span className="text-2xl">📦</span>
            <span className="text-xs font-medium">Histórico</span>
          </button>
          <button
            onClick={() => navigate('/driver/profile')}
            className="flex flex-col items-center justify-center flex-1 py-2 text-gray-600 hover:text-blue-600"
          >
            <span className="text-2xl">👤</span>
            <span className="text-xs font-medium">Perfil</span>
          </button>
        </div>
      </nav>
    </div>
  )
}

// Card de histórico
function HistoryCard({ delivery }) {
  const isDelivered = delivery.status === 'delivered'
  const statusIcon = isDelivered ? '✅' : '❌'
  const statusColor = isDelivered ? 'text-green-600' : 'text-red-600'

  const deliveryTime = delivery.delivered_at 
    ? new Date(delivery.delivered_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
    : '--:--'

  const deliveryDate = delivery.delivered_at
    ? new Date(delivery.delivered_at).toLocaleDateString('pt-BR')
    : new Date(delivery.created_at).toLocaleDateString('pt-BR')

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold text-gray-800">
            {statusIcon} Pedido #{delivery.order_number}
          </h3>
          <p className="text-sm text-gray-500">{deliveryDate} às {deliveryTime}</p>
        </div>
        <span className={`font-bold ${statusColor}`}>
          {isDelivered ? 'Entregue' : 'Falhou'}
        </span>
      </div>

      <div className="border-t pt-3 space-y-2">
        <p className="text-sm text-gray-700">
          📍 {delivery.bairro || 'Endereço não disponível'}
        </p>
        <p className="text-sm text-gray-700">
          📦 {delivery.order_items?.length || 0} item(ns)
        </p>
        <p className="text-sm font-semibold text-gray-800">
          💰 R$ {delivery.order_total?.toFixed(2) || '0.00'}
        </p>
        {delivery.actual_delivery_minutes && (
          <p className="text-sm text-gray-600">
            ⏱️ Tempo: {delivery.actual_delivery_minutes} min
          </p>
        )}
      </div>

      {delivery.failure_reason && (
        <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
          ⚠️ {delivery.failure_reason}
        </div>
      )}
    </div>
  )
}
