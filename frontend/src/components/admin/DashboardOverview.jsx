/**
 * Overview Dashboard para Admin
 * Métricas gerais e visão executiva do sistema
 */

import { useState, useEffect } from 'react'

export default function DashboardOverview() {
  const [metrics, setMetrics] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchMetrics()
    // Atualizar a cada 30 segundos
    const interval = setInterval(fetchMetrics, 30000)
    return () => clearInterval(interval)
  }, [])

  const fetchMetrics = async () => {
    try {
      setLoading(true)
      
      // Buscar múltiplas métricas em paralelo usando variável de ambiente
      const apiUrl = import.meta.env.VITE_API_URL || 'http://192.168.10.156:8000/api'
      const token = localStorage.getItem('token')
      
      const [usersRes, driversRes, metricsRes] = await Promise.all([
        fetch(`${apiUrl}/users`, {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
        fetch(`${apiUrl}/drivers`, {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
        fetch(`${apiUrl}/drivers/metrics/dashboard?period=today`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
      ])

      const users = await usersRes.json()
      const drivers = await driversRes.json()
      const driverMetrics = await metricsRes.json()

      // Calcular estatísticas
      const activeUsers = users.filter(u => u.is_active).length
      // Contar drivers pela role de usuário (fonte única da verdade)
      const driversUsers = users.filter(u => u.role === 'driver')
      const totalDrivers = driversUsers.length
      const activeDrivers = driversUsers.filter(u => u.is_active).length
      
      // Para status dos drivers, usar a tabela drivers (se disponível)
      const activeDriversFromTable = drivers.filter(d => d.is_active && d.status !== 'offline').length

      setMetrics({
        users: {
          total: users.length,
          active: activeUsers,
          byRole: {
            admin: users.filter(u => u.role === 'admin').length,
            operator: users.filter(u => u.role === 'operator').length,
            owner: users.filter(u => u.role === 'owner').length,
            driver: users.filter(u => u.role === 'driver').length,
            user: users.filter(u => u.role === 'user').length
          }
        },
        drivers: {
          total: totalDrivers, // Usa contagem de usuários com role 'driver'
          active: activeDriversFromTable, // Usa status da tabela drivers
          offline: drivers.filter(d => d.status === 'offline').length,
          available: drivers.filter(d => d.status === 'available').length,
          busy: drivers.filter(d => d.status === 'busy').length,
          break: drivers.filter(d => d.status === 'break').length
        },
        deliveries: {
          today: driverMetrics.summary?.total_deliveries || 0,
          hoursWorked: driverMetrics.summary?.total_hours_worked || 0
        }
      })
    } catch (error) {
      console.error('Erro ao buscar métricas:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="text-gray-600 mt-4">Carregando métricas...</p>
        </div>
      </div>
    )
  }

  if (!metrics) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-700">Erro ao carregar métricas</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-800">📊 Dashboard Executivo</h2>
        <p className="text-gray-600">Visão geral do sistema em tempo real</p>
      </div>

      {/* Cards de Métricas Principais */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total de Usuários */}
        <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg p-6 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-blue-100 text-sm mb-1">Total de Usuários</p>
              <p className="text-4xl font-bold">{metrics.users.total}</p>
              <p className="text-blue-100 text-xs mt-2">
                {metrics.users.active} ativos
              </p>
            </div>
            <div className="text-5xl opacity-20">👥</div>
          </div>
        </div>

        {/* Entregadores */}
        <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-lg p-6 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-green-100 text-sm mb-1">Entregadores</p>
              <p className="text-4xl font-bold">{metrics.drivers.total}</p>
              <p className="text-green-100 text-xs mt-2">
                {metrics.drivers.active} online
              </p>
            </div>
            <div className="text-5xl opacity-20">🚚</div>
          </div>
        </div>

        {/* Entregas Hoje */}
        <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-lg p-6 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-purple-100 text-sm mb-1">Entregas Hoje</p>
              <p className="text-4xl font-bold">{metrics.deliveries.today}</p>
              <p className="text-purple-100 text-xs mt-2">
                {metrics.deliveries.hoursWorked}h trabalhadas
              </p>
            </div>
            <div className="text-5xl opacity-20">📦</div>
          </div>
        </div>

        {/* Sistema */}
        <div className="bg-gradient-to-br from-orange-500 to-orange-600 rounded-lg p-6 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-orange-100 text-sm mb-1">Status do Sistema</p>
              <p className="text-2xl font-bold">Operacional</p>
              <p className="text-orange-100 text-xs mt-2">
                Todos os serviços online
              </p>
            </div>
            <div className="text-5xl opacity-20">✅</div>
          </div>
        </div>
      </div>

      {/* Seção: Usuários por Role */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-bold text-gray-800 mb-4">👥 Usuários por Role</h3>
        <div className="grid grid-cols-5 gap-4">
          <div className="text-center p-4 bg-red-50 rounded-lg">
            <p className="text-3xl font-bold text-red-600">{metrics.users.byRole.admin}</p>
            <p className="text-sm text-gray-600 mt-1">👑 Admins</p>
          </div>
          <div className="text-center p-4 bg-blue-50 rounded-lg">
            <p className="text-3xl font-bold text-blue-600">{metrics.users.byRole.operator}</p>
            <p className="text-sm text-gray-600 mt-1">👤 Operadores</p>
          </div>
          <div className="text-center p-4 bg-purple-50 rounded-lg">
            <p className="text-3xl font-bold text-purple-600">{metrics.users.byRole.owner}</p>
            <p className="text-sm text-gray-600 mt-1">💼 Owners</p>
          </div>
          <div className="text-center p-4 bg-green-50 rounded-lg">
            <p className="text-3xl font-bold text-green-600">{metrics.users.byRole.driver}</p>
            <p className="text-sm text-gray-600 mt-1">🚚 Drivers</p>
          </div>
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <p className="text-3xl font-bold text-gray-600">{metrics.users.byRole.user}</p>
            <p className="text-sm text-gray-600 mt-1">📦 Users</p>
          </div>
        </div>
      </div>

      {/* Seção: Status dos Entregadores */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-bold text-gray-800 mb-4">🚚 Status dos Entregadores</h3>
        <div className="space-y-3">
          {/* Available */}
          <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
              <span className="font-medium text-gray-800">Disponível</span>
            </div>
            <span className="text-2xl font-bold text-green-600">{metrics.drivers.available}</span>
          </div>

          {/* Busy */}
          <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
              <span className="font-medium text-gray-800">Ocupado (em entrega)</span>
            </div>
            <span className="text-2xl font-bold text-blue-600">{metrics.drivers.busy}</span>
          </div>

          {/* Break */}
          <div className="flex items-center justify-between p-3 bg-yellow-50 rounded-lg">
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
              <span className="font-medium text-gray-800">Em pausa</span>
            </div>
            <span className="text-2xl font-bold text-yellow-600">{metrics.drivers.break}</span>
          </div>

          {/* Offline */}
          <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 bg-gray-500 rounded-full"></div>
              <span className="font-medium text-gray-800">Offline</span>
            </div>
            <span className="text-2xl font-bold text-gray-600">{metrics.drivers.offline}</span>
          </div>
        </div>
      </div>

      {/* Botão de Atualização */}
      <div className="text-center">
        <button
          onClick={fetchMetrics}
          className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition"
        >
          🔄 Atualizar Métricas
        </button>
        <p className="text-xs text-gray-500 mt-2">
          Atualização automática a cada 30 segundos
        </p>
      </div>
    </div>
  )
}
