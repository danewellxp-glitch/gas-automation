import { useState, useEffect, useCallback } from 'react'
import { ShoppingCart, DollarSign, Clock, CheckCircle, Wifi, WifiOff } from 'lucide-react'
import { getOrders } from '../services/api'
import { useSharedWebSocket, useSharedWebSocketEvent } from '../hooks/useSharedWebSocket'
import logger from '../utils/logger'

function MetricCard({ title, value, icon: Icon, color, subtitle }) {
  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500 mb-1">{title}</p>
          <p className="text-3xl font-bold text-gray-900">{value}</p>
          {subtitle && <p className="text-sm text-gray-400 mt-1">{subtitle}</p>}
        </div>
        <div className={`p-3 rounded-full ${color}`}>
          <Icon className="w-6 h-6 text-white" />
        </div>
      </div>
    </div>
  )
}

function RecentOrders({ orders }) {
  const statusColors = {
    pending: 'bg-yellow-100 text-yellow-800',
    paid: 'bg-green-100 text-green-800',
    dispatched: 'bg-blue-100 text-blue-800',
    delivered: 'bg-gray-100 text-gray-800',
    cancelled: 'bg-red-100 text-red-800',
  }

  const statusLabels = {
    pending: 'Pendente',
    paid: 'Pago',
    dispatched: 'Em Entrega',
    delivered: 'Entregue',
    cancelled: 'Cancelado',
  }

  return (
    <div className="bg-white rounded-xl shadow-sm">
      <div className="p-6 border-b border-gray-100">
        <h3 className="text-lg font-semibold text-gray-900">Pedidos Recentes</h3>
      </div>
      <div className="divide-y divide-gray-100">
        {orders.length === 0 ? (
          <div className="p-6 text-center text-gray-500">
            Nenhum pedido encontrado
          </div>
        ) : (
          orders.slice(0, 5).map((order) => (
            <div key={order.id} className="p-4 hover:bg-gray-50">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900">
                    Pedido #{order.order_number}
                  </p>
                  <p className="text-sm text-gray-500">{order.customer_name}</p>
                </div>
                <div className="text-right">
                  <p className="font-medium text-gray-900">
                    R$ {parseFloat(order.total_amount).toFixed(2)}
                  </p>
                  <span className={`inline-block px-2 py-1 text-xs rounded-full ${statusColors[order.status]}`}>
                    {statusLabels[order.status]}
                  </span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

function Dashboard() {
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [metrics, setMetrics] = useState({
    totalOrders: 0,
    totalRevenue: 0,
    pendingOrders: 0,
    deliveredToday: 0,
  })
  const { isConnected } = useSharedWebSocket()

  // Atualizar quando receber novo pedido
  const handleNewOrder = useCallback((data) => {
    logger.log('Novo pedido recebido:', data)
    loadData()
  }, [])

  // Atualizar quando pedido for atualizado
  const handleOrderUpdate = useCallback((data) => {
    logger.log('Pedido atualizado:', data)
    loadData()
  }, [])

  useSharedWebSocketEvent('new_order', handleNewOrder)
  useSharedWebSocketEvent('order_update', handleOrderUpdate)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const ordersData = await getOrders()
      setOrders(ordersData)

      // Calculate metrics
      const today = new Date().toISOString().split('T')[0]
      const totalRevenue = ordersData
        .filter(o => o.status !== 'cancelled')
        .reduce((sum, o) => sum + parseFloat(o.total_amount), 0)

      const pendingOrders = ordersData.filter(o =>
        ['pending', 'paid', 'dispatched'].includes(o.status)
      ).length

      const deliveredToday = ordersData.filter(o =>
        o.status === 'delivered' && o.created_at?.startsWith(today)
      ).length

      setMetrics({
        totalOrders: ordersData.length,
        totalRevenue,
        pendingOrders,
        deliveredToday,
      })
    } catch (error) {
      logger.error('Erro ao carregar dados:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center">
        <div className="text-gray-500">Carregando...</div>
      </div>
    )
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500">Visao geral do sistema</p>
        </div>
        <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-sm ${
          isConnected ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
        }`}>
          {isConnected ? <Wifi className="w-4 h-4" /> : <WifiOff className="w-4 h-4" />}
          {isConnected ? 'Tempo real' : 'Desconectado'}
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <MetricCard
          title="Total de Pedidos"
          value={metrics.totalOrders}
          icon={ShoppingCart}
          color="bg-blue-500"
        />
        <MetricCard
          title="Faturamento"
          value={`R$ ${metrics.totalRevenue.toFixed(2)}`}
          icon={DollarSign}
          color="bg-green-500"
        />
        <MetricCard
          title="Pedidos Pendentes"
          value={metrics.pendingOrders}
          icon={Clock}
          color="bg-yellow-500"
        />
        <MetricCard
          title="Entregas Hoje"
          value={metrics.deliveredToday}
          icon={CheckCircle}
          color="bg-purple-500"
        />
      </div>

      {/* Recent Orders */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RecentOrders orders={orders} />

        {/* Quick Stats */}
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Status do Sistema</h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
              <span className="text-green-700">API Backend</span>
              <span className="px-2 py-1 bg-green-500 text-white text-xs rounded">Online</span>
            </div>
            <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
              <span className="text-green-700">WhatsApp Bot</span>
              <span className="px-2 py-1 bg-green-500 text-white text-xs rounded">Conectado</span>
            </div>
            <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
              <span className="text-green-700">Banco de Dados</span>
              <span className="px-2 py-1 bg-green-500 text-white text-xs rounded">Saudavel</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
