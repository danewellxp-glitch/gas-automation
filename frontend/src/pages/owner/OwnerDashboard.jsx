import { useState, useEffect } from 'react'
import { useAuth } from '../../hooks/useAuth'

export default function OwnerDashboard() {
  const { user, logout } = useAuth()
  const [stats, setStats] = useState({
    totalConversations: 0,
    totalOrders: 0,
    revenue: 0,
    activeOperators: 0
  })

  useEffect(() => {
    fetchStats()
  }, [])

  const fetchStats = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/stats', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })
      if (response.ok) {
        const data = await response.json()
        setStats(data)
      }
    } catch (error) {
      console.error('Erro ao buscar estatísticas:', error)
    }
  }

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <div className="w-64 bg-white shadow-lg">
        <div className="p-6 border-b">
          <h1 className="text-xl font-bold text-gray-800">Gas Automation</h1>
          <p className="text-sm text-gray-500">Painel do Proprietário</p>
        </div>
        
        <nav className="p-4">
          <div className="space-y-2">
            <button className="w-full text-left px-4 py-3 bg-blue-500 text-white rounded hover:bg-blue-600">
              📊 Dashboard
            </button>
            <button className="w-full text-left px-4 py-3 hover:bg-gray-100 rounded">
              📈 Relatórios
            </button>
            <button className="w-full text-left px-4 py-3 hover:bg-gray-100 rounded">
              💰 Financeiro
            </button>
            <button className="w-full text-left px-4 py-3 hover:bg-gray-100 rounded">
              👥 Equipe
            </button>
          </div>
        </nav>

        <div className="border-t p-4 absolute bottom-0 w-64">
          <div className="flex items-center justify-between">
            <div className="text-sm">
              <p className="font-semibold text-gray-800">{user?.email}</p>
              <p className="text-gray-500 text-xs uppercase">{user?.role}</p>
            </div>
            <button 
              onClick={logout}
              className="px-3 py-1 bg-red-500 text-white rounded text-sm hover:bg-red-600"
            >
              Sair
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 p-8">
        <h2 className="text-2xl font-bold text-gray-800 mb-8">Visão Geral do Negócio</h2>

        <div className="grid grid-cols-4 gap-6 mb-8">
          {/* Card 1 */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-gray-500 text-sm font-semibold mb-2">Conversas Total</h3>
            <p className="text-3xl font-bold text-gray-800">{stats.totalConversations}</p>
            <p className="text-xs text-gray-400 mt-2">↑ 12% vs. mês passado</p>
          </div>

          {/* Card 2 */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-gray-500 text-sm font-semibold mb-2">Pedidos</h3>
            <p className="text-3xl font-bold text-green-600">{stats.totalOrders}</p>
            <p className="text-xs text-gray-400 mt-2">↑ 8% vs. mês passado</p>
          </div>

          {/* Card 3 */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-gray-500 text-sm font-semibold mb-2">Receita</h3>
            <p className="text-3xl font-bold text-blue-600">R$ {stats.revenue.toLocaleString('pt-BR')}</p>
            <p className="text-xs text-gray-400 mt-2">↑ 15% vs. mês passado</p>
          </div>

          {/* Card 4 */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-gray-500 text-sm font-semibold mb-2">Operadores Ativos</h3>
            <p className="text-3xl font-bold text-purple-600">{stats.activeOperators}</p>
            <p className="text-xs text-gray-400 mt-2">Todos online</p>
          </div>
        </div>

        {/* Gráfico Placeholder */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Desempenho Mensal</h3>
          <div className="h-64 bg-gray-100 rounded flex items-center justify-center">
            <p className="text-gray-500">Gráfico de desempenho (em desenvolvimento)</p>
          </div>
        </div>
      </div>
    </div>
  )
}
