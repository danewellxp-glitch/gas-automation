import { useState, useEffect } from 'react'
import { useAuth } from '../../hooks/useAuth'
import { apiRequest } from '../../utils/api'
import DriversMetricsPanel from '../../components/owner/DriversMetricsPanel'

export default function OwnerDashboard() {
  const { user, logout } = useAuth()
  const [stats, setStats] = useState({
    totalConversations: 0,
    totalOrders: 0,
    revenue: 0,
    activeOperators: 0
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [activeView, setActiveView] = useState('dashboard') // dashboard, reports, financial, team
  const [financialReport, setFinancialReport] = useState(null)
  const [ordersReport, setOrdersReport] = useState(null)

  useEffect(() => {
    fetchStats()
  }, [])

  const fetchStats = async () => {
    try {
      setLoading(true)
      setError('')
      const data = await apiRequest('stats')
      setStats(data)
    } catch (err) {
      console.error('Erro ao buscar estatísticas:', err)
      setError(err.message || 'Erro ao carregar estatísticas')
    } finally {
      setLoading(false)
    }
  }

  const fetchFinancialReport = async () => {
    try {
      setLoading(true)
      setError('')
      const data = await apiRequest('reports/financial')
      setFinancialReport(data)
    } catch (err) {
      console.error('Erro ao buscar relatório financeiro:', err)
      setError(err.message || 'Erro ao carregar relatório financeiro')
    } finally {
      setLoading(false)
    }
  }

  const fetchOrdersReport = async () => {
    try {
      setLoading(true)
      setError('')
      const data = await apiRequest('reports/orders')
      setOrdersReport(data)
    } catch (err) {
      console.error('Erro ao buscar relatório de pedidos:', err)
      setError(err.message || 'Erro ao carregar relatório de pedidos')
    } finally {
      setLoading(false)
    }
  }

  const handleViewChange = (view) => {
    setActiveView(view)
    if (view === 'financial' && !financialReport) {
      fetchFinancialReport()
    } else if (view === 'reports' && !ordersReport) {
      fetchOrdersReport()
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
            <button
              onClick={() => handleViewChange('dashboard')}
              className={`w-full text-left px-4 py-3 rounded hover:bg-blue-600 ${
                activeView === 'dashboard'
                  ? 'bg-blue-500 text-white'
                  : 'hover:bg-gray-100'
              }`}
            >
              📊 Dashboard
            </button>
            <button
              onClick={() => handleViewChange('reports')}
              className={`w-full text-left px-4 py-3 rounded hover:bg-blue-600 ${
                activeView === 'reports'
                  ? 'bg-blue-500 text-white'
                  : 'hover:bg-gray-100'
              }`}
            >
              📈 Relatórios
            </button>
            <button
              onClick={() => handleViewChange('financial')}
              className={`w-full text-left px-4 py-3 rounded hover:bg-blue-600 ${
                activeView === 'financial'
                  ? 'bg-blue-500 text-white'
                  : 'hover:bg-gray-100'
              }`}
            >
              💰 Financeiro
            </button>
            <button
              onClick={() => handleViewChange('team')}
              className={`w-full text-left px-4 py-3 rounded hover:bg-blue-600 ${
                activeView === 'team'
                  ? 'bg-blue-500 text-white'
                  : 'hover:bg-gray-100'
              }`}
            >
              👥 Equipe
            </button>
            <button
              onClick={() => handleViewChange('drivers')}
              className={`w-full text-left px-4 py-3 rounded hover:bg-blue-600 ${
                activeView === 'drivers'
                  ? 'bg-blue-500 text-white'
                  : 'hover:bg-gray-100'
              }`}
            >
              🚚 Métricas Drivers
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
        {activeView === 'dashboard' && (
          <>
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
          </>
        )}

        {activeView === 'reports' && (
          <div>
            <h2 className="text-2xl font-bold text-gray-800 mb-8">Relatórios de Pedidos</h2>
            {ordersReport && (
              <div className="grid grid-cols-2 gap-6 mb-6">
                <div className="bg-white p-6 rounded-lg shadow">
                  <h3 className="text-lg font-semibold text-gray-800 mb-4">Resumo do Período</h3>
                  <div className="space-y-2">
                    <p className="text-sm text-gray-600">Total de Pedidos: <span className="font-bold">{ordersReport.summary?.total_orders || 0}</span></p>
                    <p className="text-sm text-gray-600">Taxa de Conclusão: <span className="font-bold">{ordersReport.summary?.completed_rate?.toFixed(1) || 0}%</span></p>
                    <p className="text-sm text-gray-600">Período: {ordersReport.period?.start_date} - {ordersReport.period?.end_date}</p>
                  </div>
                </div>
                <div className="bg-white p-6 rounded-lg shadow">
                  <h3 className="text-lg font-semibold text-gray-800 mb-4">Status dos Pedidos</h3>
                  <div className="space-y-2">
                    <p className="text-sm text-green-600">✅ Concluídos: {ordersReport.summary?.by_status?.completed || 0}</p>
                    <p className="text-sm text-yellow-600">⏳ Pendentes: {ordersReport.summary?.by_status?.pending || 0}</p>
                    <p className="text-sm text-red-600">❌ Cancelados: {ordersReport.summary?.by_status?.cancelled || 0}</p>
                  </div>
                </div>
              </div>
            )}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold text-gray-800">Últimos Pedidos</h3>
                <button
                  onClick={() => window.open('/api/reports/export/orders', '_blank')}
                  className="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600"
                >
                  📊 Exportar CSV
                </button>
              </div>
              {ordersReport?.orders && ordersReport.orders.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="min-w-full table-auto">
                    <thead>
                      <tr className="bg-gray-50">
                        <th className="px-4 py-2 text-left">ID</th>
                        <th className="px-4 py-2 text-left">Cliente</th>
                        <th className="px-4 py-2 text-left">Status</th>
                        <th className="px-4 py-2 text-left">Total</th>
                        <th className="px-4 py-2 text-left">Data</th>
                      </tr>
                    </thead>
                    <tbody>
                      {ordersReport.orders.map((order, index) => (
                        <tr key={index} className="border-t">
                          <td className="px-4 py-2">{order.id}</td>
                          <td className="px-4 py-2">{order.customer}</td>
                          <td className="px-4 py-2">
                            <span className={`px-2 py-1 rounded text-xs ${
                              order.status === 'completed' ? 'bg-green-100 text-green-800' :
                              order.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                              'bg-red-100 text-red-800'
                            }`}>
                              {order.status}
                            </span>
                          </td>
                          <td className="px-4 py-2">R$ {order.total}</td>
                          <td className="px-4 py-2">{order.created_at}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-gray-500 text-center py-8">Carregando dados dos pedidos...</p>
              )}
            </div>
          </div>
        )}

        {activeView === 'financial' && (
          <div>
            <h2 className="text-2xl font-bold text-gray-800 mb-8">Relatórios Financeiros</h2>
            {financialReport && (
              <div className="grid grid-cols-2 gap-6 mb-6">
                <div className="bg-white p-6 rounded-lg shadow">
                  <h3 className="text-lg font-semibold text-gray-800 mb-4">Resumo Financeiro</h3>
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Receita Total:</span>
                      <span className="font-bold text-green-600">R$ {financialReport.summary?.total_revenue?.toLocaleString('pt-BR') || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Despesas:</span>
                      <span className="font-bold text-red-600">R$ {financialReport.summary?.total_expenses?.toLocaleString('pt-BR') || 0}</span>
                    </div>
                    <div className="flex justify-between border-t pt-2">
                      <span className="text-gray-600 font-semibold">Lucro Líquido:</span>
                      <span className="font-bold text-blue-600">R$ {financialReport.summary?.net_profit?.toLocaleString('pt-BR') || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Margem de Lucro:</span>
                      <span className="font-bold">{financialReport.summary?.profit_margin?.toFixed(1) || 0}%</span>
                    </div>
                  </div>
                </div>
                <div className="bg-white p-6 rounded-lg shadow">
                  <h3 className="text-lg font-semibold text-gray-800 mb-4">Métricas do Período</h3>
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Total de Pedidos:</span>
                      <span className="font-bold">{financialReport.summary?.total_orders || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Ticket Médio:</span>
                      <span className="font-bold">R$ {financialReport.summary?.average_ticket?.toFixed(2) || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Período:</span>
                      <span className="font-bold text-sm">{financialReport.period?.start_date} - {financialReport.period?.end_date}</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold text-gray-800">Receita Diária</h3>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleViewChange('financial')}
                    className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
                  >
                    🔄 Atualizar
                  </button>
                  <button
                    onClick={() => window.open('/api/reports/export/financial', '_blank')}
                    className="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600"
                  >
                    📊 Exportar CSV
                  </button>
                </div>
              </div>
              {financialReport?.charts ? (
                <div className="h-64 bg-gray-50 rounded flex items-center justify-center">
                  <div className="text-center">
                    <p className="text-gray-600 mb-2">📈 Receita nos últimos dias</p>
                    <p className="text-sm text-gray-500">
                      Máximo: R$ {Math.max(...financialReport.charts.revenue_trend).toLocaleString('pt-BR')} |
                      Média: R$ {(financialReport.charts.revenue_trend.reduce((a, b) => a + b, 0) / financialReport.charts.revenue_trend.length).toFixed(0)}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="h-64 bg-gray-100 rounded flex items-center justify-center">
                  <p className="text-gray-500">Carregando dados financeiros...</p>
                </div>
              )}
            </div>
          </div>
        )}

        {activeView === 'drivers' && (
          <div>
            <DriversMetricsPanel />
          </div>
        )}

        {activeView === 'team' && (
          <div>
            <h2 className="text-2xl font-bold text-gray-800 mb-8">Gestão de Equipe</h2>
            <div className="grid grid-cols-2 gap-6">
              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">Operadores Ativos</h3>
                <p className="text-3xl font-bold text-blue-600">{stats.activeOperators}</p>
                <p className="text-gray-600 mt-2">Operadores online</p>
              </div>
              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">Total de Usuários</h3>
                <p className="text-3xl font-bold text-green-600">{stats.totalUsers}</p>
                <p className="text-gray-600 mt-2">Usuários cadastrados</p>
              </div>
            </div>
            <div className="bg-white rounded-lg shadow p-6 mt-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">Gerenciar Equipe</h3>
              <button className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 mr-4">
                👥 Ver Todos os Usuários
              </button>
              <button className="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600">
                ➕ Adicionar Usuário
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
