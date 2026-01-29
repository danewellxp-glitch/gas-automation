/**
 * Dashboard Principal do Driver - Novo Estilo Uber Driver App
 */

import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { 
  MapPin, Navigation, Phone, Clock, Package, ChevronRight,
  CheckCircle, Circle, TrendingUp, DollarSign, Star, Menu,
  X, LogOut, User, Settings, History, AlertCircle, Loader
} from 'lucide-react'
import { driverApi } from '../../utils/driverApi'
import logger from '../../utils/logger'
import useWebSocketDriver from '../../hooks/useWebSocketDriver'
import '../../styles/driver-dashboard.css'

// Constantes
const DELIVERY_STATUS = {
  pending: { label: 'Pendente', color: 'bg-gray-100 text-gray-700', icon: Circle },
  assigned: { label: 'Atribuída', color: 'bg-blue-100 text-blue-700', icon: Circle },
  picked_up: { label: 'Coletada', color: 'bg-yellow-100 text-yellow-700', icon: Package },
  in_transit: { label: 'A Caminho', color: 'bg-purple-100 text-purple-700', icon: Navigation },
  arrived: { label: 'Chegou', color: 'bg-indigo-100 text-indigo-700', icon: MapPin },
  delivered: { label: 'Entregue', color: 'bg-green-100 text-green-700', icon: CheckCircle }
}

const DRIVER_STATUS = {
  offline: { label: 'Desconectado', color: 'bg-gray-400', textColor: 'text-gray-600' },
  available: { label: 'Disponível', color: 'bg-green-500', textColor: 'text-green-600' },
  busy: { label: 'Ocupado', color: 'bg-red-500', textColor: 'text-red-600' },
  break: { label: 'Pausa', color: 'bg-yellow-500', textColor: 'text-yellow-600' }
}

// Helpers para formatar dados
function formatDeliveryForUI(delivery) {
  // Formatar endereço como string
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

  return {
    ...delivery,
    order: {
      numero_pedido: delivery.order_number,
      cliente_nome: delivery.customer_name || 'Cliente',
      telefone: delivery.customer_phone || null,
      endereco: addressStr
    }
  }
}

function formatStats(statsData) {
  if (!statsData) return { today: 0, rating: 5.0, avgTime: 0, earnings: 0 }
  
  return {
    today: statsData.today_deliveries || 0,
    rating: statsData.rating || 5.0,
    avgTime: Math.round(statsData.average_delivery_time_minutes || 0),
    earnings: 0 // Não existe no backend ainda
  }
}

function formatTimeWorked(hours) {
  if (!hours) return '0h 0m'
  const h = Math.floor(hours)
  const m = Math.round((hours - h) * 60)
  return `${h}h ${m}m`
}

export default function DriverDashboard() {
  const navigate = useNavigate()
  const [driver, setDriver] = useState(null)
  const [activeDeliveries, setActiveDeliveries] = useState([])
  const [availableDeliveries, setAvailableDeliveries] = useState([])
  const [stats, setStats] = useState({ today: 0, rating: 5.0, avgTime: 0, earnings: 0 })
  const [loading, setLoading] = useState(true)
  const [menuOpen, setMenuOpen] = useState(false)
  const [selectedDelivery, setSelectedDelivery] = useState(null)
  const [timeWorked, setTimeWorked] = useState({ today: '0h 0m', week: '0h 0m' })
  const [showProblemModal, setShowProblemModal] = useState(false)

  // Carregar dados do motorista
  const loadDriverData = useCallback(async () => {
    try {
      setLoading(true)

      // Buscar tudo em paralelo
      const [profileData, statsData, activeData, pendingData, timeTodayData, timeWeekData] = await Promise.all([
        driverApi.getProfile(),
        driverApi.getStats(),
        driverApi.getDeliveries('active'),
        driverApi.getDeliveries('pending'),
        driverApi.getTimeSummary('today').catch(() => null),
        driverApi.getTimeSummary('week').catch(() => null)
      ])

      setDriver(profileData)
      setStats(formatStats(statsData))
      setActiveDeliveries(activeData.map(formatDeliveryForUI))
      setAvailableDeliveries(pendingData.map(formatDeliveryForUI))

      // Formatar tempo trabalhado
      if (timeTodayData) {
        setTimeWorked(prev => ({
          ...prev,
          today: formatTimeWorked(timeTodayData.total_hours)
        }))
      }
      if (timeWeekData) {
        setTimeWorked(prev => ({
          ...prev,
          week: formatTimeWorked(timeWeekData.total_hours)
        }))
      }

      setLoading(false)
    } catch (error) {
      logger.error('Erro ao carregar dados:', error)
      setLoading(false)
      
      // Se erro 401, redirecionar para login
      if (error.message.includes('401') || error.message.includes('authenticate')) {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        navigate('/driver/login')
      } else {
        toast.error('Erro ao carregar dados: ' + error.message)
      }
    }
  }, [navigate])

  useEffect(() => {
    loadDriverData()
    const interval = setInterval(loadDriverData, 30000) // Atualiza a cada 30s
    return () => clearInterval(interval)
  }, [loadDriverData])

  // WebSocket handlers
  const handleDeliveryAssigned = useCallback((data) => {
    logger.log('📦 Nova entrega alocada:', data)
    toast.success('Nova entrega disponível!')
    loadDriverData()
  }, [loadDriverData])

  const handleDeliveryUpdated = useCallback((data) => {
    logger.log('🔄 Entrega atualizada:', data)
    loadDriverData()
  }, [loadDriverData])

  const handleOperatorMessage = useCallback((data) => {
    logger.log('💬 Mensagem do operador:', data)
    toast(`Operador ${data.from || 'Sistema'}: ${data.message}`, { icon: '💬' })
  }, [])

  // Conectar WebSocket
  const { connected: wsConnected } = useWebSocketDriver(
    handleDeliveryAssigned,
    handleDeliveryUpdated,
    handleOperatorMessage
  )

  // Atualizar status do motorista
  const updateDriverStatus = async (newStatus) => {
    try {
      await driverApi.updateStatus(newStatus)
      setDriver(prev => ({ ...prev, status: newStatus }))
      toast.success(`Status atualizado para: ${DRIVER_STATUS[newStatus]?.label || newStatus}`)
    } catch (error) {
      logger.error('Erro ao atualizar status:', error)
      toast.error('Erro ao atualizar status: ' + error.message)
    }
  }

  // Aceitar entrega
  const acceptDelivery = async (deliveryId) => {
    try {
      await driverApi.acceptDelivery(deliveryId)
      toast.success('Entrega aceita com sucesso!')
      await loadDriverData()
    } catch (error) {
      logger.error('Erro ao aceitar entrega:', error)
      toast.error('Erro ao aceitar entrega: ' + error.message)
    }
  }

  // Atualizar status da entrega
  const updateDeliveryStatus = async (deliveryId, newStatus, notes = '') => {
    try {
      await driverApi.updateDeliveryStatus(deliveryId, newStatus, notes)
      toast.success('Status da entrega atualizado!')
      await loadDriverData()
      setSelectedDelivery(null)
    } catch (error) {
      logger.error('Erro ao atualizar status:', error)
      toast.error('Erro ao atualizar status: ' + error.message)
    }
  }

  // Reportar problema
  const handleReportProblem = async (problemType, description) => {
    if (!selectedDelivery) return
    
    try {
      await driverApi.reportProblem(selectedDelivery.id, problemType, description)
      toast.success('Problema reportado com sucesso!')
      setShowProblemModal(false)
      setSelectedDelivery(null)
      await loadDriverData()
    } catch (error) {
      logger.error('Erro ao reportar problema:', error)
      toast.error('Erro ao reportar problema: ' + error.message)
    }
  }

  // Logout
  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    window.location.href = '/driver/login'
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

  const statusConfig = DRIVER_STATUS[driver?.status] || DRIVER_STATUS.offline

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <header className="bg-slate-800/80 backdrop-blur-lg border-b border-slate-700/50 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-gradient-to-br from-emerald-400 to-teal-500 rounded-full flex items-center justify-center text-white font-bold text-xl shadow-lg shadow-emerald-500/30">
                {driver?.name?.charAt(0) || 'D'}
              </div>
              <div>
                <h1 className="text-white font-bold text-xl tracking-tight">{driver?.name || 'Motorista'}</h1>
                <div className="flex items-center gap-2 mt-1">
                  <div className={`w-2 h-2 rounded-full ${statusConfig.color} shadow-lg`}></div>
                  <span className={`text-sm font-medium ${statusConfig.textColor}`}>{statusConfig.label}</span>
                  {wsConnected && (
                    <span className="text-xs text-green-400 ml-2" title="WebSocket conectado">
                      🔗
                    </span>
                  )}
                </div>
              </div>
            </div>
            <button 
              onClick={() => setMenuOpen(!menuOpen)}
              className="w-10 h-10 bg-slate-700/50 hover:bg-slate-700 rounded-full flex items-center justify-center transition-all duration-200"
            >
              {menuOpen ? <X className="w-5 h-5 text-slate-300" /> : <Menu className="w-5 h-5 text-slate-300" />}
            </button>
          </div>
        </div>
      </header>

      {/* Menu Lateral */}
      {menuOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40" onClick={() => setMenuOpen(false)}>
          <div 
            className="absolute right-0 top-0 h-full w-80 bg-slate-800 shadow-2xl transform transition-transform duration-300"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6">
              <div className="flex items-center justify-between mb-8">
                <h2 className="text-white font-bold text-xl">Menu</h2>
                <button onClick={() => setMenuOpen(false)} className="text-slate-400 hover:text-white">
                  <X className="w-6 h-6" />
                </button>
              </div>
              
              <div className="space-y-2">
                <button 
                  onClick={() => {
                    setMenuOpen(false)
                    navigate('/driver/profile')
                  }}
                  className="w-full flex items-center gap-3 px-4 py-3 bg-slate-700/50 hover:bg-slate-700 rounded-xl text-white transition-all duration-200"
                >
                  <User className="w-5 h-5" />
                  <span>Meu Perfil</span>
                </button>
                <button 
                  onClick={() => {
                    setMenuOpen(false)
                    navigate('/driver/history')
                  }}
                  className="w-full flex items-center gap-3 px-4 py-3 bg-slate-700/50 hover:bg-slate-700 rounded-xl text-white transition-all duration-200"
                >
                  <History className="w-5 h-5" />
                  <span>Histórico</span>
                </button>
                <button 
                  onClick={() => {
                    setMenuOpen(false)
                    navigate('/driver/carga/acerto')
                  }}
                  className="w-full flex items-center gap-3 px-4 py-3 bg-slate-700/50 hover:bg-slate-700 rounded-xl text-white transition-all duration-200"
                >
                  <Package className="w-5 h-5" />
                  <span>Acerto de Carga</span>
                </button>
                <button 
                  onClick={handleLogout}
                  className="w-full flex items-center gap-3 px-4 py-3 bg-red-500/20 hover:bg-red-500/30 rounded-xl text-red-400 transition-all duration-200 mt-4"
                >
                  <LogOut className="w-5 h-5" />
                  <span>Sair</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto px-4 py-6 space-y-6 pb-24">
        {/* Toggle de Status */}
        <div className="bg-gradient-to-r from-slate-800/90 to-slate-700/90 backdrop-blur-lg rounded-2xl p-6 border border-slate-600/30 shadow-xl">
          <h3 className="text-white font-semibold mb-4">Status da Operação</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {Object.entries(DRIVER_STATUS).map(([key, config]) => (
              <button
                key={key}
                onClick={() => updateDriverStatus(key)}
                className={`px-4 py-3 rounded-xl font-medium transition-all duration-200 ${
                  driver?.status === key 
                    ? `${config.color} text-white shadow-lg scale-105` 
                    : 'bg-slate-700/50 text-slate-400 hover:bg-slate-700'
                }`}
              >
                {config.label}
              </button>
            ))}
          </div>
        </div>

        {/* Cards de Estatísticas */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-gradient-to-br from-emerald-500/20 to-emerald-600/20 backdrop-blur-lg rounded-2xl p-5 border border-emerald-500/30 shadow-xl">
            <div className="flex items-center justify-between mb-2">
              <Package className="w-8 h-8 text-emerald-400" />
              <TrendingUp className="w-5 h-5 text-emerald-300" />
            </div>
            <p className="text-3xl font-bold text-white mb-1">{stats.today}</p>
            <p className="text-emerald-300 text-sm font-medium">Entregas Hoje</p>
          </div>

          <div className="bg-gradient-to-br from-amber-500/20 to-amber-600/20 backdrop-blur-lg rounded-2xl p-5 border border-amber-500/30 shadow-xl">
            <div className="flex items-center justify-between mb-2">
              <Star className="w-8 h-8 text-amber-400" />
            </div>
            <p className="text-3xl font-bold text-white mb-1">{stats.rating.toFixed(1)}</p>
            <p className="text-amber-300 text-sm font-medium">Avaliação</p>
          </div>

          <div className="bg-gradient-to-br from-blue-500/20 to-blue-600/20 backdrop-blur-lg rounded-2xl p-5 border border-blue-500/30 shadow-xl">
            <div className="flex items-center justify-between mb-2">
              <Clock className="w-8 h-8 text-blue-400" />
            </div>
            <p className="text-3xl font-bold text-white mb-1">{stats.avgTime}m</p>
            <p className="text-blue-300 text-sm font-medium">Tempo Médio</p>
          </div>

          <div className="bg-gradient-to-br from-purple-500/20 to-purple-600/20 backdrop-blur-lg rounded-2xl p-5 border border-purple-500/30 shadow-xl">
            <div className="flex items-center justify-between mb-2">
              <DollarSign className="w-8 h-8 text-purple-400" />
            </div>
            <p className="text-3xl font-bold text-white mb-1">R$ {stats.earnings}</p>
            <p className="text-purple-300 text-sm font-medium">Ganhos</p>
          </div>
        </div>

        {/* Tempo Trabalhado */}
        <div className="bg-gradient-to-r from-slate-800/90 to-slate-700/90 backdrop-blur-lg rounded-2xl p-6 border border-slate-600/30 shadow-xl">
          <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
            <Clock className="w-5 h-5 text-emerald-400" />
            Tempo Trabalhado
          </h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-slate-400 text-sm mb-1">Hoje</p>
              <p className="text-white text-2xl font-bold">{timeWorked.today}</p>
            </div>
            <div>
              <p className="text-slate-400 text-sm mb-1">Esta Semana</p>
              <p className="text-white text-2xl font-bold">{timeWorked.week}</p>
            </div>
          </div>
        </div>

        {/* Entregas Ativas */}
        {activeDeliveries.length > 0 && (
          <div className="space-y-4">
            <h2 className="text-white font-bold text-xl flex items-center gap-2">
              <Navigation className="w-6 h-6 text-emerald-400" />
              Entregas Ativas ({activeDeliveries.length})
            </h2>
            {activeDeliveries.map((delivery) => (
              <DeliveryCard 
                key={delivery.id} 
                delivery={delivery} 
                onSelect={() => setSelectedDelivery(delivery)}
                active
              />
            ))}
          </div>
        )}

        {/* Entregas Disponíveis */}
        {availableDeliveries.length > 0 && (
          <div className="space-y-4">
            <h2 className="text-white font-bold text-xl flex items-center gap-2">
              <Package className="w-6 h-6 text-blue-400" />
              Entregas Disponíveis ({availableDeliveries.length})
            </h2>
            {availableDeliveries.map((delivery) => (
              <DeliveryCard 
                key={delivery.id} 
                delivery={delivery} 
                onAccept={() => acceptDelivery(delivery.id)}
                available
              />
            ))}
          </div>
        )}

        {/* Mensagem quando não há entregas */}
        {activeDeliveries.length === 0 && availableDeliveries.length === 0 && (
          <div className="bg-slate-800/50 backdrop-blur-lg rounded-2xl p-12 border border-slate-700/30 text-center">
            <Package className="w-16 h-16 text-slate-600 mx-auto mb-4" />
            <h3 className="text-white font-semibold text-lg mb-2">Nenhuma entrega no momento</h3>
            <p className="text-slate-400">Fique conectado para receber novas entregas</p>
          </div>
        )}
      </div>

      {/* Modal de Detalhes da Entrega */}
      {selectedDelivery && (
        <DeliveryDetailModal 
          delivery={selectedDelivery} 
          onClose={() => setSelectedDelivery(null)}
          onUpdateStatus={updateDeliveryStatus}
          onReportProblem={() => setShowProblemModal(true)}
        />
      )}

      {/* Modal de Problema */}
      {showProblemModal && selectedDelivery && (
        <ProblemModal
          onClose={() => setShowProblemModal(false)}
          onSubmit={handleReportProblem}
        />
      )}
    </div>
  )
}

// Componente de Card de Entrega
const DeliveryCard = ({ delivery, onSelect, onAccept, active, available }) => {
  const statusInfo = DELIVERY_STATUS[delivery.status] || DELIVERY_STATUS.pending
  const StatusIcon = statusInfo.icon

  return (
    <div 
      onClick={active ? onSelect : undefined}
      className={`bg-slate-800/70 backdrop-blur-lg rounded-2xl p-5 border border-slate-700/50 shadow-lg transition-all duration-200 ${
        active ? 'cursor-pointer hover:bg-slate-800 hover:scale-[1.02] hover:shadow-xl' : ''
      }`}
    >
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className={`px-3 py-1 rounded-full text-xs font-semibold ${statusInfo.color}`}>
              {statusInfo.label}
            </span>
            {delivery.estimated_minutes && (
              <span className="text-slate-400 text-sm">
                ~{delivery.estimated_minutes} min
              </span>
            )}
          </div>
          <h3 className="text-white font-semibold text-lg mb-1">
            Pedido #{delivery.order?.numero_pedido || delivery.order_number || delivery.id.slice(0, 8)}
          </h3>
          <p className="text-slate-400 text-sm">{delivery.order?.cliente_nome || 'Cliente'}</p>
        </div>
        <StatusIcon className="w-6 h-6 text-emerald-400" />
      </div>

      <div className="space-y-2 mb-4">
        <div className="flex items-start gap-2">
          <MapPin className="w-4 h-4 text-slate-500 mt-1 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-slate-300 text-sm leading-relaxed">
              {delivery.order?.endereco || 'Endereço não disponível'}
            </p>
            {delivery.bairro && (
              <p className="text-slate-500 text-xs mt-1">{delivery.bairro}</p>
            )}
          </div>
        </div>
        
        {delivery.order?.telefone && (
          <div className="flex items-center gap-2">
            <Phone className="w-4 h-4 text-slate-500" />
            <a 
              href={`tel:${delivery.order.telefone}`}
              className="text-emerald-400 text-sm hover:text-emerald-300 transition-colors"
              onClick={(e) => e.stopPropagation()}
            >
              {delivery.order.telefone}
            </a>
          </div>
        )}
      </div>

      {available && (
        <button
          onClick={(e) => {
            e.stopPropagation()
            onAccept()
          }}
          className="w-full bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white font-semibold py-3 rounded-xl transition-all duration-200 shadow-lg shadow-emerald-500/30 hover:shadow-emerald-500/50"
        >
          Aceitar Entrega
        </button>
      )}

      {active && (
        <div className="flex items-center justify-between pt-3 border-t border-slate-700/50">
          <span className="text-slate-400 text-sm">Toque para ver detalhes</span>
          <ChevronRight className="w-5 h-5 text-slate-500" />
        </div>
      )}
    </div>
  )
}

// Modal de Detalhes da Entrega
const DeliveryDetailModal = ({ delivery, onClose, onUpdateStatus, onReportProblem }) => {
  const statusInfo = DELIVERY_STATUS[delivery.status] || DELIVERY_STATUS.pending
  const nextStatuses = {
    assigned: 'picked_up',
    picked_up: 'in_transit',
    in_transit: 'arrived',
    arrived: 'delivered'
  }

  const nextStatus = nextStatuses[delivery.status]
  const nextStatusInfo = nextStatus ? DELIVERY_STATUS[nextStatus] : null

  const openMaps = () => {
    const address = delivery.order?.endereco || delivery.delivery_address_str || ''
    if (address) {
      window.open(`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}`, '_blank')
    }
  }

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-end md:items-center justify-center p-4">
      <div 
        className="bg-slate-800 rounded-t-3xl md:rounded-3xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 bg-slate-800 border-b border-slate-700/50 p-6 flex items-center justify-between rounded-t-3xl">
          <h2 className="text-white font-bold text-xl">Detalhes da Entrega</h2>
          <button 
            onClick={onClose}
            className="w-10 h-10 bg-slate-700/50 hover:bg-slate-700 rounded-full flex items-center justify-center transition-all duration-200"
          >
            <X className="w-5 h-5 text-slate-300" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Status Atual */}
          <div className="bg-slate-900/50 rounded-xl p-5">
            <p className="text-slate-400 text-sm mb-2">Status</p>
            <span className={`inline-block px-4 py-2 rounded-full font-semibold ${statusInfo.color}`}>
              {statusInfo.label}
            </span>
          </div>

          {/* Informações do Pedido */}
          <div className="space-y-4">
            <div>
              <p className="text-slate-400 text-sm mb-1">Número do Pedido</p>
              <p className="text-white font-semibold text-lg">
                #{delivery.order?.numero_pedido || delivery.order_number || delivery.id.slice(0, 8)}
              </p>
            </div>

            <div>
              <p className="text-slate-400 text-sm mb-1">Cliente</p>
              <p className="text-white font-semibold">{delivery.order?.cliente_nome || 'Não informado'}</p>
            </div>

            <div>
              <p className="text-slate-400 text-sm mb-1">Telefone</p>
              <a 
                href={`tel:${delivery.order?.telefone || ''}`}
                className="text-emerald-400 font-semibold hover:text-emerald-300 transition-colors"
              >
                {delivery.order?.telefone || 'Não informado'}
              </a>
            </div>

            <div>
              <p className="text-slate-400 text-sm mb-1">Endereço</p>
              <p className="text-white">{delivery.order?.endereco || delivery.delivery_address_str || 'Não informado'}</p>
              {delivery.bairro && (
                <p className="text-slate-400 text-sm mt-1">{delivery.bairro}</p>
              )}
            </div>

            {delivery.estimated_minutes && (
              <div>
                <p className="text-slate-400 text-sm mb-1">Tempo Estimado</p>
                <p className="text-white font-semibold">{delivery.estimated_minutes} minutos</p>
              </div>
            )}

            {delivery.order_items && delivery.order_items.length > 0 && (
              <div>
                <p className="text-slate-400 text-sm mb-2">Itens do Pedido</p>
                <div className="space-y-1">
                  {delivery.order_items.map((item, index) => (
                    <p key={index} className="text-white text-sm">
                      • {item.quantity}x {item.product_name} ({item.product_code})
                    </p>
                  ))}
                </div>
              </div>
            )}

            {delivery.order_total && (
              <div>
                <p className="text-slate-400 text-sm mb-1">Valor Total</p>
                <p className="text-white font-semibold text-lg text-emerald-400">
                  R$ {delivery.order_total.toFixed(2)}
                </p>
              </div>
            )}

            {delivery.notes && (
              <div>
                <p className="text-slate-400 text-sm mb-1">Observações</p>
                <p className="text-white">{delivery.notes}</p>
              </div>
            )}
          </div>

          {/* Ações */}
          <div className="space-y-3 pt-4">
            {nextStatusInfo && (
              <button
                onClick={() => onUpdateStatus(delivery.id, nextStatus)}
                className="w-full bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white font-semibold py-4 rounded-xl transition-all duration-200 shadow-lg shadow-emerald-500/30"
              >
                Atualizar para: {nextStatusInfo.label}
              </button>
            )}

            <button
              onClick={openMaps}
              className="w-full bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 font-semibold py-4 rounded-xl transition-all duration-200 border border-blue-500/30"
            >
              <div className="flex items-center justify-center gap-2">
                <Navigation className="w-5 h-5" />
                Abrir no Maps
              </div>
            </button>

            {delivery.order?.telefone && (
              <a
                href={`tel:${delivery.order.telefone}`}
                className="w-full bg-green-500/20 hover:bg-green-500/30 text-green-400 font-semibold py-4 rounded-xl transition-all duration-200 border border-green-500/30 flex items-center justify-center gap-2"
              >
                <Phone className="w-5 h-5" />
                Ligar para Cliente
              </a>
            )}

            <button
              onClick={onReportProblem}
              className="w-full bg-red-500/20 hover:bg-red-500/30 text-red-400 font-semibold py-4 rounded-xl transition-all duration-200 border border-red-500/30"
            >
              <div className="flex items-center justify-center gap-2">
                <AlertCircle className="w-5 h-5" />
                Reportar Problema
              </div>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// Modal para reportar problema
const ProblemModal = ({ onClose, onSubmit }) => {
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
        className="bg-slate-800 rounded-3xl max-w-md w-full p-6 shadow-2xl animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-white font-bold text-xl mb-4">⚠️ Reportar Problema</h2>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Tipo de Problema
            </label>
            <select
              value={problemType}
              onChange={(e) => setProblemType(e.target.value)}
              className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:ring-2 focus:ring-red-500 focus:border-red-500"
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
              className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:ring-2 focus:ring-red-500 focus:border-red-500"
              placeholder="Descreva o problema em detalhes..."
            />
          </div>

          <div className="flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 bg-slate-700 text-white rounded-lg hover:bg-slate-600 transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            >
              Reportar
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
