/**
 * Página de Detalhes da Entrega
 */

import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { driverApi } from '../../utils/driverApi'

const STATUS_CONFIG = {
  assigned: { label: '🟦 Alocado', color: 'bg-yellow-100 text-yellow-800', nextAction: 'Retirei os Produtos', nextStatus: 'picked_up' },
  picked_up: { label: '🟧 Produtos Retirados', color: 'bg-orange-100 text-orange-800', nextAction: 'Saí para Entrega', nextStatus: 'in_transit' },
  in_transit: { label: '🟦 Em Trânsito', color: 'bg-blue-100 text-blue-800', nextAction: 'Cheguei no Local', nextStatus: 'arrived' },
  arrived: { label: '🟪 Chegou no Local', color: 'bg-purple-100 text-purple-800', nextAction: 'Entregue', nextStatus: 'delivered' },
  delivered: { label: '🟩 Entregue', color: 'bg-green-100 text-green-800', nextAction: null, nextStatus: null }
}

export default function DeliveryDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [delivery, setDelivery] = useState(null)
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState(false)
  const [error, setError] = useState('')
  const [showProblemModal, setShowProblemModal] = useState(false)

  // Buscar detalhes da entrega
  useEffect(() => {
    const fetchDelivery = async () => {
      try {
        setLoading(true)
        // Buscar todas as entregas ativas e encontrar a específica
        const deliveries = await driverApi.getDeliveries('active')
        const found = deliveries.find(d => d.id === id)
        
        if (!found) {
          setError('Entrega não encontrada')
        } else {
          setDelivery(found)
        }
      } catch (err) {
        console.error('Erro ao buscar entrega:', err)
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchDelivery()
  }, [id])

  // Atualizar status da entrega
  const handleUpdateStatus = async () => {
    const config = STATUS_CONFIG[delivery.status]
    if (!config || !config.nextStatus) return

    const confirmed = window.confirm(
      `Confirmar: ${config.nextAction}?\n\nIsso irá atualizar o status da entrega.`
    )

    if (!confirmed) return

    try {
      setUpdating(true)
      await driverApi.updateDeliveryStatus(
        delivery.id,
        config.nextStatus,
        `Status atualizado para ${config.nextStatus}`
      )

      // Atualizar estado local
      setDelivery(prev => ({ ...prev, status: config.nextStatus }))

      // Se entregue, voltar para dashboard
      if (config.nextStatus === 'delivered') {
        setTimeout(() => {
          navigate('/driver/dashboard')
        }, 2000)
      }
    } catch (err) {
      console.error('Erro ao atualizar status:', err)
      toast.error('Erro ao atualizar status: ' + err.message)
    } finally {
      setUpdating(false)
    }
  }

  // Ligar para cliente
  const handleCall = () => {
    if (delivery?.customer_phone) {
      window.location.href = `tel:${delivery.customer_phone}`
    }
  }

  // Abrir no Maps
  const handleOpenMaps = () => {
    if (!delivery?.delivery_address) return

    const addr = delivery.delivery_address
    const address = `${addr.street}, ${addr.number}, ${addr.city}, ${addr.cep}`
    window.open(`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}`, '_blank')
  }

  // Reportar problema
  const handleReportProblem = async (problemType, description) => {
    try {
      await driverApi.reportProblem(delivery.id, problemType, description)
      toast.success('Problema reportado com sucesso! O operador foi notificado.')
      setShowProblemModal(false)
      navigate('/driver/dashboard')
    } catch (err) {
      console.error('Erro ao reportar problema:', err)
      toast.error('Erro ao reportar problema: ' + err.message)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <p className="text-gray-600">Carregando...</p>
      </div>
    )
  }

  if (error || !delivery) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow p-8 max-w-md w-full text-center">
          <div className="text-4xl mb-4">⚠️</div>
          <p className="text-gray-600 mb-4">{error || 'Entrega não encontrada'}</p>
          <button
            onClick={() => navigate('/driver/dashboard')}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700"
          >
            Voltar
          </button>
        </div>
      </div>
    )
  }

  const statusConfig = STATUS_CONFIG[delivery.status] || STATUS_CONFIG.assigned

  return (
    <div className="min-h-screen bg-gray-100 pb-6">
      {/* Header */}
      <div className="bg-white shadow-md p-4 mb-4">
        <button
          onClick={() => navigate('/driver/dashboard')}
          className="text-blue-600 hover:text-blue-700 mb-2"
        >
          ← Voltar
        </button>
        <h1 className="text-2xl font-bold text-gray-800">Pedido #{delivery.order_number}</h1>
      </div>

      <div className="max-w-2xl mx-auto px-4 space-y-4">
        {/* Status Atual */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-3">Status Atual</h2>
          <span className={`inline-block px-4 py-2 rounded-full font-semibold ${statusConfig.color}`}>
            {statusConfig.label}
          </span>
        </div>

        {/* Itens do Pedido */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-3">📦 Itens</h2>
          <ul className="space-y-2">
            {delivery.order_items?.map((item, index) => (
              <li key={index} className="flex justify-between text-gray-700">
                <span>• {item.quantity}x {item.product_name}</span>
                <span className="font-medium">{item.product_code}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Endereço de Entrega */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-3">📍 Endereço de Entrega</h2>
          {delivery.delivery_address ? (
            <div className="text-gray-700 space-y-1">
              <p>{delivery.delivery_address.street}, {delivery.delivery_address.number}</p>
              {delivery.delivery_address.complement && <p>{delivery.delivery_address.complement}</p>}
              <p>{delivery.delivery_address.bairro} - {delivery.delivery_address.city}</p>
              <p>CEP: {delivery.delivery_address.cep}</p>
            </div>
          ) : (
            <p className="text-gray-500">Endereço não disponível</p>
          )}
        </div>

        {/* Informações Adicionais */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-3">💰 Pagamento</h2>
          <p className="text-gray-700">Total: <span className="font-bold text-green-600">R$ {delivery.order_total?.toFixed(2)}</span></p>
          <p className="text-sm text-gray-500 mt-2">Status: Já pago ✅</p>
        </div>

        {delivery.notes && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-2">📝 Observações</h2>
            <p className="text-gray-700">{delivery.notes}</p>
          </div>
        )}

        {/* Ações */}
        <div className="space-y-3">
          <button
            onClick={handleCall}
            className="w-full bg-green-600 text-white py-4 rounded-lg font-semibold hover:bg-green-700 active:bg-green-800 text-lg"
          >
            📞 LIGAR PARA CLIENTE
          </button>

          <button
            onClick={handleOpenMaps}
            className="w-full bg-blue-600 text-white py-4 rounded-lg font-semibold hover:bg-blue-700 active:bg-blue-800 text-lg"
          >
            🗺️ ABRIR NO MAPS
          </button>

          {statusConfig.nextAction && (
            <button
              onClick={handleUpdateStatus}
              disabled={updating}
              className={`w-full py-4 rounded-lg font-semibold text-white text-lg ${
                updating
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700 active:bg-blue-800'
              }`}
            >
              {updating ? '⏳ Atualizando...' : `✅ ${statusConfig.nextAction.toUpperCase()}`}
            </button>
          )}

          <button
            onClick={() => setShowProblemModal(true)}
            className="w-full bg-red-600 text-white py-4 rounded-lg font-semibold hover:bg-red-700 active:bg-red-800 text-lg"
          >
            ⚠️ REPORTAR PROBLEMA
          </button>
        </div>
      </div>

      {/* Modal de Problema */}
      {showProblemModal && (
        <ProblemModal
          onClose={() => setShowProblemModal(false)}
          onSubmit={handleReportProblem}
        />
      )}
    </div>
  )
}

// Modal para reportar problema
function ProblemModal({ onClose, onSubmit }) {
  const [problemType, setProblemType] = useState('customer_absent')
  const [description, setDescription] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!description.trim()) {
      toast.error('Por favor, descreva o problema')
      return
    }
    onSubmit(problemType, description)
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
        <h2 className="text-xl font-bold text-gray-800 mb-4">⚠️ Reportar Problema</h2>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Tipo de Problema
            </label>
            <select
              value={problemType}
              onChange={(e) => setProblemType(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500"
            >
              <option value="customer_absent">Cliente Ausente</option>
              <option value="wrong_address">Endereço Errado</option>
              <option value="product_issue">Problema com Produto</option>
              <option value="payment_issue">Problema com Pagamento</option>
              <option value="other">Outro</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Descrição
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={4}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500"
              placeholder="Descreva o problema em detalhes..."
            />
          </div>

          <div className="flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400"
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
            >
              Reportar
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
