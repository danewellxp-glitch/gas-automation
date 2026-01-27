/**
 * Dashboard Principal do Driver
 */

import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { driverApi } from '../../utils/driverApi'
import logger from '../../utils/logger'
import useWebSocketDriver from '../../hooks/useWebSocketDriver'
import DriverHeader from '../../components/driver/DriverHeader'
import StatsCard from '../../components/driver/StatsCard'
import DeliveryCard from '../../components/driver/DeliveryCard'
import MyTimePanel from '../../components/driver/MyTimePanel'

export default function DriverDashboard() {
  const navigate = useNavigate()
  const [driver, setDriver] = useState(null)
  const [stats, setStats] = useState(null)
  const [activeDeliveries, setActiveDeliveries] = useState([])
  const [pendingDeliveries, setPendingDeliveries] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [refreshing, setRefreshing] = useState(false)

  // Carregar dados
  const fetchData = useCallback(async (showLoading = true) => {
    try {
      if (showLoading) setLoading(true)
      setError('')

      // Buscar tudo em paralelo
      const [profileData, statsData, activeData, pendingData] = await Promise.all([
        driverApi.getProfile(),
        driverApi.getStats(),
        driverApi.getDeliveries('active'),
        driverApi.getDeliveries('pending')
      ])

      setDriver(profileData)
      setStats(statsData)
      setActiveDeliveries(activeData)
      setPendingDeliveries(pendingData)
    } catch (err) {
      logger.error('Erro ao carregar dados:', err)
      setError(err.message)
      
      // Se erro 401, redirecionar para login
      if (err.message.includes('401') || err.message.includes('authenticate')) {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        navigate('/driver/login')
      }
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [navigate])

  // Carregar dados ao montar
  useEffect(() => {
    fetchData()
  }, [fetchData])

  // Auto-refresh a cada 30 segundos
  useEffect(() => {
    const interval = setInterval(() => {
      fetchData(false) // Refresh silencioso
    }, 30000)

    return () => clearInterval(interval)
  }, [fetchData])

  // WebSocket handlers
  const handleDeliveryAssigned = useCallback((data) => {
    logger.log('📦 Nova entrega alocada:', data)
    // Refresh entregas pendentes
    fetchData(false)
  }, [fetchData])

  const handleDeliveryUpdated = useCallback((data) => {
    logger.log('🔄 Entrega atualizada:', data)
    // Refresh entregas
    fetchData(false)
  }, [fetchData])

  const handleOperatorMessage = useCallback((data) => {
    logger.log('💬 Mensagem do operador:', data)
    toast(`Operador ${data.from}: ${data.message}`, { icon: '💬' })
  }, [])

  // Conectar WebSocket
  const { connected: wsConnected } = useWebSocketDriver(
    handleDeliveryAssigned,
    handleDeliveryUpdated,
    handleOperatorMessage
  )

  // Atualizar status do driver
  const handleStatusChange = async (newStatus) => {
    try {
      await driverApi.updateStatus(newStatus)
      setDriver(prev => ({ ...prev, status: newStatus }))
    } catch (err) {
      logger.error('Erro ao atualizar status:', err)
      toast.error('Erro ao atualizar status: ' + err.message)
    }
  }

  // Refresh manual
  const handleRefresh = async () => {
    setRefreshing(true)
    await fetchData(false)
  }

  // Loading inicial
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">🚚</div>
          <p className="text-gray-600">Carregando...</p>
        </div>
      </div>
    )
  }

  // Erro
  if (error && !driver) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full text-center">
          <div className="text-6xl mb-4">⚠️</div>
          <h2 className="text-2xl font-bold text-gray-800 mb-4">Erro</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <button
            onClick={() => fetchData()}
            className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700"
          >
            Tentar Novamente
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <DriverHeader 
        driver={driver}
        onStatusChange={handleStatusChange}
        wsConnected={wsConnected}
      />

      <div className="max-w-7xl mx-auto p-4 pb-24">
        {/* Stats Cards */}
        <div className="mb-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-3">📊 Estatísticas Hoje</h2>
          <StatsCard stats={stats} />
        </div>

        {/* Painel de Tempo Trabalhado */}
        <MyTimePanel />

        {/* Entregas Ativas */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-gray-800">
              🚚 Entregas em Andamento ({activeDeliveries.length})
            </h2>
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="text-blue-600 hover:text-blue-700 disabled:text-gray-400"
            >
              {refreshing ? '🔄 Atualizando...' : '🔄 Atualizar'}
            </button>
          </div>

          {activeDeliveries.length === 0 ? (
            <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
              <div className="text-4xl mb-3">📭</div>
              <p>Nenhuma entrega em andamento</p>
            </div>
          ) : (
            <div className="space-y-3">
              {activeDeliveries.map(delivery => (
                <DeliveryCard
                  key={delivery.id}
                  delivery={delivery}
                  onAction={() => navigate(`/driver/delivery/${delivery.id}`)}
                />
              ))}
            </div>
          )}
        </div>

        {/* Entregas Disponíveis */}
        <div className="mb-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-3">
            📦 Entregas Disponíveis ({pendingDeliveries.length})
          </h2>

          {pendingDeliveries.length === 0 ? (
            <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
              <div className="text-4xl mb-3">✅</div>
              <p>Nenhuma entrega disponível no momento</p>
              <p className="text-sm mt-2">Fique atento! Você será notificado quando houver novas entregas.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {pendingDeliveries.map(delivery => (
                <DeliveryCard
                  key={delivery.id}
                  delivery={delivery}
                  onAction={() => navigate(`/driver/delivery/${delivery.id}`)}
                  isPending
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Bottom Navigation */}
      <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 shadow-lg">
        <div className="flex justify-around items-center h-16">
          <button
            onClick={() => navigate('/driver/dashboard')}
            className="flex flex-col items-center justify-center flex-1 py-2 text-blue-600"
          >
            <span className="text-2xl">🏠</span>
            <span className="text-xs font-medium">Início</span>
          </button>
          <button
            onClick={() => navigate('/driver/carga/acerto')}
            className="flex flex-col items-center justify-center flex-1 py-2 text-gray-600 hover:text-blue-600"
          >
            <span className="text-2xl">📋</span>
            <span className="text-xs font-medium">Acerto</span>
          </button>
          <button
            onClick={() => navigate('/driver/history')}
            className="flex flex-col items-center justify-center flex-1 py-2 text-gray-600 hover:text-blue-600"
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
