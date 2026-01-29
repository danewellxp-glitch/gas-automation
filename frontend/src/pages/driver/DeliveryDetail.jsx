/**
 * Página de Detalhes da Entrega - Novo Estilo
 */

import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { ArrowLeft, Loader, MapPin, Phone, Package, DollarSign, Navigation, AlertCircle, CheckCircle } from 'lucide-react'
import { driverApi } from '../../utils/driverApi'
import '../../styles/driver-dashboard.css'

const STATUS_CONFIG = {
  assigned: { label: 'Atribuída', color: 'bg-blue-500/20 text-blue-300 border-blue-500/30', nextAction: 'Retirei os Produtos', nextStatus: 'picked_up' },
  picked_up: { label: 'Coletada', color: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30', nextAction: 'Saí para Entrega', nextStatus: 'in_transit' },
  in_transit: { label: 'Em Trânsito', color: 'bg-purple-500/20 text-purple-300 border-purple-500/30', nextAction: 'Cheguei no Local', nextStatus: 'arrived' },
  arrived: { label: 'Chegou', color: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30', nextAction: 'Entregue', nextStatus: 'delivered' },
  delivered: { label: 'Entregue', color: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30', nextAction: null, nextStatus: null }
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
        setError('')
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
        setError(err.message || 'Erro ao carregar entrega')
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

      toast.success('Status atualizado com sucesso!')

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
    const phone = delivery?.customer_phone || delivery?.order?.telefone
    if (phone) {
      window.location.href = `tel:${phone}`
    }
  }

  // Abrir no Maps
  const handleOpenMaps = () => {
    if (!delivery?.delivery_address) return

    const addr = delivery.delivery_address
    const address = `${addr.street || ''}, ${addr.number || ''}, ${addr.city || ''}, ${addr.cep || ''}`.trim()
    if (address) {
      window.open(`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}`, '_blank')
    }
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
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <Loader className="w-12 h-12 text-emerald-400 animate-spin mx-auto mb-4" />
          <p className="text-slate-300 text-lg font-medium">Carregando...</p>
        </div>
      </div>
    )
  }

  if (error || !delivery) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
        <div className="bg-slate-800 rounded-2xl shadow-2xl p-8 max-w-md w-full text-center border border-slate-700/50">
          <AlertCircle className="w-16 h-16 text-slate-400 mx-auto mb-4" />
          <p className="text-slate-300 mb-4">{error || 'Entrega não encontrada'}</p>
          <button
            onClick={() => navigate('/driver/dashboard')}
            className="bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white px-6 py-3 rounded-xl font-semibold transition-all duration-200"
          >
            Voltar
          </button>
        </div>
      </div>
    )
  }

  const statusConfig = STATUS_CONFIG[delivery.status] || STATUS_CONFIG.assigned

  // Formatar endereço
  let addressStr = 'Endereço não disponível'
  if (delivery.delivery_address) {
    const addr = delivery.delivery_address
    const parts = []
    if (addr.street) parts.push(addr.street)
    if (addr.number) parts.push(addr.number)
    if (addr.complement) parts.push(addr.complement)
    if (parts.length > 0) {
      addressStr = parts.join(', ')
    }
  } else if (delivery.delivery_address_str) {
    addressStr = delivery.delivery_address_str
  }

  const customerPhone = delivery.customer_phone || delivery.order?.telefone

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 pb-6">
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
              <h1 className="text-white font-bold text-xl">Pedido #{delivery.order_number || delivery.id.slice(0, 8)}</h1>
              <span className={`inline-block px-3 py-1 rounded-full text-xs font-semibold ${statusConfig.color} border mt-1`}>
                {statusConfig.label}
              </span>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-2xl mx-auto px-4 py-6 space-y-6">
        {/* Status Atual */}
        <div className="bg-slate-800/70 backdrop-blur-lg rounded-2xl p-6 border border-slate-700/50 shadow-lg">
          <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-emerald-400" />
            Status Atual
          </h2>
          <span className={`inline-block px-4 py-2 rounded-full font-semibold ${statusConfig.color} border`}>
            {statusConfig.label}
          </span>
        </div>

        {/* Itens do Pedido */}
        {delivery.order_items && delivery.order_items.length > 0 && (
          <div className="bg-slate-800/70 backdrop-blur-lg rounded-2xl p-6 border border-slate-700/50 shadow-lg">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Package className="w-5 h-5 text-emerald-400" />
              Itens
            </h2>
            <ul className="space-y-2">
              {delivery.order_items.map((item, index) => (
                <li key={index} className="flex justify-between items-center text-slate-300 py-2 border-b border-slate-700/50 last:border-0">
                  <span>{item.quantity}x {item.product_name}</span>
                  <span className="text-slate-400 text-sm">{item.product_code}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Endereço de Entrega */}
        <div className="bg-slate-800/70 backdrop-blur-lg rounded-2xl p-6 border border-slate-700/50 shadow-lg">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <MapPin className="w-5 h-5 text-emerald-400" />
            Endereço de Entrega
          </h2>
          <div className="text-slate-300 space-y-1">
            <p className="font-medium">{addressStr}</p>
            {delivery.delivery_address && (
              <>
                {delivery.delivery_address.bairro && (
                  <p className="text-slate-400">{delivery.delivery_address.bairro}</p>
                )}
                {delivery.delivery_address.city && (
                  <p className="text-slate-400">{delivery.delivery_address.city}</p>
                )}
                {delivery.delivery_address.cep && (
                  <p className="text-slate-400">CEP: {delivery.delivery_address.cep}</p>
                )}
              </>
            )}
            {delivery.bairro && !delivery.delivery_address?.bairro && (
              <p className="text-slate-400">{delivery.bairro}</p>
            )}
          </div>
        </div>

        {/* Informações Adicionais */}
        <div className="bg-slate-800/70 backdrop-blur-lg rounded-2xl p-6 border border-slate-700/50 shadow-lg">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <DollarSign className="w-5 h-5 text-emerald-400" />
            Pagamento
          </h2>
          <p className="text-slate-300">
            Total: <span className="font-bold text-emerald-400 text-xl">R$ {delivery.order_total?.toFixed(2) || '0.00'}</span>
          </p>
          <p className="text-sm text-emerald-400 mt-2 flex items-center gap-1">
            <CheckCircle className="w-4 h-4" />
            Status: Já pago
          </p>
        </div>

        {delivery.notes && (
          <div className="bg-amber-500/20 border border-amber-500/30 rounded-2xl p-6 backdrop-blur-lg">
            <h2 className="text-lg font-semibold text-amber-300 mb-2 flex items-center gap-2">
              <AlertCircle className="w-5 h-5" />
              Observações
            </h2>
            <p className="text-amber-200">{delivery.notes}</p>
          </div>
        )}

        {/* Ações */}
        <div className="space-y-3">
          {customerPhone && (
            <button
              onClick={handleCall}
              className="w-full bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 text-white py-4 rounded-xl font-semibold transition-all duration-200 shadow-lg shadow-green-500/30 hover:shadow-green-500/50 flex items-center justify-center gap-2 text-lg"
            >
              <Phone className="w-5 h-5" />
              LIGAR PARA CLIENTE
            </button>
          )}

          <button
            onClick={handleOpenMaps}
            className="w-full bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 font-semibold py-4 rounded-xl transition-all duration-200 border border-blue-500/30 flex items-center justify-center gap-2 text-lg"
          >
            <Navigation className="w-5 h-5" />
            ABRIR NO MAPS
          </button>

          {statusConfig.nextAction && (
            <button
              onClick={handleUpdateStatus}
              disabled={updating}
              className={`w-full py-4 rounded-xl font-semibold text-white text-lg transition-all duration-200 ${
                updating
                  ? 'bg-slate-600 cursor-not-allowed'
                  : 'bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 shadow-lg shadow-emerald-500/30'
              }`}
            >
              {updating ? (
                <span className="flex items-center justify-center gap-2">
                  <Loader className="w-5 h-5 animate-spin" />
                  Atualizando...
                </span>
              ) : (
                `✅ ${statusConfig.nextAction.toUpperCase()}`
              )}
            </button>
          )}

          <button
            onClick={() => setShowProblemModal(true)}
            className="w-full bg-red-500/20 hover:bg-red-500/30 text-red-400 font-semibold py-4 rounded-xl transition-all duration-200 border border-red-500/30 flex items-center justify-center gap-2 text-lg"
          >
            <AlertCircle className="w-5 h-5" />
            REPORTAR PROBLEMA
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
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div 
        className="bg-slate-800 rounded-3xl max-w-md w-full p-6 shadow-2xl animate-slide-up border border-slate-700/50"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
          <AlertCircle className="w-6 h-6 text-red-400" />
          Reportar Problema
        </h2>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Tipo de Problema
            </label>
            <select
              value={problemType}
              onChange={(e) => setProblemType(e.target.value)}
              className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-xl text-white focus:ring-2 focus:ring-red-500 focus:border-red-500"
            >
              <option value="customer_absent">Cliente Ausente</option>
              <option value="wrong_address">Endereço Errado</option>
              <option value="product_issue">Problema com Produto</option>
              <option value="payment_issue">Problema com Pagamento</option>
              <option value="other">Outro</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Descrição
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={4}
              className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-xl text-white placeholder-slate-500 focus:ring-2 focus:ring-red-500 focus:border-red-500"
              placeholder="Descreva o problema em detalhes..."
            />
          </div>

          <div className="flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-3 bg-slate-700 text-white rounded-xl hover:bg-slate-600 transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="flex-1 px-4 py-3 bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white rounded-xl transition-all duration-200 shadow-lg shadow-red-500/30"
            >
              Reportar
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
