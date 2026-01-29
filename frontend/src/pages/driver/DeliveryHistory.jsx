/**
 * Página de Histórico de Entregas - Novo Estilo
 */

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Package, ArrowLeft, Loader, CheckCircle, XCircle, MapPin, Clock, DollarSign } from 'lucide-react'
import { driverApi } from '../../utils/driverApi'
import '../../styles/driver-dashboard.css'

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
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <Loader className="w-12 h-12 text-emerald-400 animate-spin mx-auto mb-4" />
          <p className="text-slate-300 text-lg font-medium">Carregando histórico...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 pb-24">
      {/* Header */}
      <header className="bg-slate-800/80 backdrop-blur-lg border-b border-slate-700/50 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/driver/dashboard')}
              className="w-10 h-10 bg-slate-700/50 hover:bg-slate-700 rounded-full flex items-center justify-center transition-all duration-200"
            >
              <ArrowLeft className="w-5 h-5 text-slate-300" />
            </button>
            <div>
              <h1 className="text-white font-bold text-xl">Histórico de Entregas</h1>
              <p className="text-slate-400 text-sm">{deliveries.length} entrega(s) finalizada(s)</p>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-2xl mx-auto px-4 py-6">
        {error && (
          <div className="bg-red-500/20 border border-red-500/30 text-red-300 px-4 py-3 rounded-xl mb-4 backdrop-blur-lg">
            {error}
          </div>
        )}

        {deliveries.length === 0 ? (
          <div className="bg-slate-800/50 backdrop-blur-lg rounded-2xl p-12 border border-slate-700/30 text-center">
            <Package className="w-16 h-16 text-slate-600 mx-auto mb-4" />
            <h3 className="text-white font-semibold text-lg mb-2">
              Nenhuma entrega finalizada ainda
            </h3>
            <p className="text-slate-400">
              Suas entregas concluídas aparecerão aqui
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {deliveries.map((delivery) => (
              <HistoryCard key={delivery.id} delivery={delivery} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// Card de histórico
function HistoryCard({ delivery }) {
  const isDelivered = delivery.status === 'delivered'
  const StatusIcon = isDelivered ? CheckCircle : XCircle
  const statusColor = isDelivered ? 'text-emerald-400' : 'text-red-400'
  const bgColor = isDelivered ? 'bg-emerald-500/20 border-emerald-500/30' : 'bg-red-500/20 border-red-500/30'

  const deliveryTime = delivery.delivered_at 
    ? new Date(delivery.delivered_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
    : '--:--'

  const deliveryDate = delivery.delivered_at
    ? new Date(delivery.delivered_at).toLocaleDateString('pt-BR')
    : new Date(delivery.created_at).toLocaleDateString('pt-BR')

  // Formatar endereço
  let addressStr = 'Endereço não disponível'
  if (delivery.delivery_address) {
    const addr = delivery.delivery_address
    const parts = []
    if (addr.street) parts.push(addr.street)
    if (addr.number) parts.push(addr.number)
    if (parts.length > 0) {
      addressStr = parts.join(', ')
    }
  } else if (delivery.delivery_address_str) {
    addressStr = delivery.delivery_address_str
  }

  return (
    <div className="bg-slate-800/70 backdrop-blur-lg rounded-2xl p-5 border border-slate-700/50 shadow-lg">
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <StatusIcon className={`w-5 h-5 ${statusColor}`} />
            <h3 className="font-semibold text-white text-lg">
              Pedido #{delivery.order_number || delivery.id.slice(0, 8)}
            </h3>
          </div>
          <p className="text-sm text-slate-400">{deliveryDate} às {deliveryTime}</p>
        </div>
        <span className={`px-3 py-1 rounded-full text-xs font-semibold ${bgColor} ${statusColor} border`}>
          {isDelivered ? 'Entregue' : 'Falhou'}
        </span>
      </div>

      <div className="space-y-2 pt-3 border-t border-slate-700/50">
        <div className="flex items-start gap-2">
          <MapPin className="w-4 h-4 text-slate-500 mt-1 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-sm text-slate-300">{addressStr}</p>
            {delivery.bairro && (
              <p className="text-xs text-slate-500 mt-1">{delivery.bairro}</p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Package className="w-4 h-4 text-slate-500" />
          <p className="text-sm text-slate-300">
            {delivery.order_items?.length || 0} item(ns)
          </p>
        </div>

        {delivery.order_total && (
          <div className="flex items-center gap-2">
            <DollarSign className="w-4 h-4 text-emerald-400" />
            <p className="text-sm font-semibold text-emerald-400">
              R$ {delivery.order_total.toFixed(2)}
            </p>
          </div>
        )}

        {delivery.actual_delivery_minutes && (
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-slate-500" />
            <p className="text-sm text-slate-400">
              Tempo: {delivery.actual_delivery_minutes} min
            </p>
          </div>
        )}
      </div>

      {delivery.failure_reason && (
        <div className="mt-4 p-3 bg-red-500/20 border border-red-500/30 rounded-xl text-sm text-red-300">
          <div className="flex items-start gap-2">
            <XCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
            <p>{delivery.failure_reason}</p>
          </div>
        </div>
      )}
    </div>
  )
}
