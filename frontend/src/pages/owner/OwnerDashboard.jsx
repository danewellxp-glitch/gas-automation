import { useState, useEffect, lazy, Suspense } from 'react'
import { LayoutDashboard, FileText, DollarSign, Users, Truck } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import { apiRequest } from '../../utils/api'
import DriversMetricsPanel from '../../components/owner/DriversMetricsPanel'
import FlowbiteLayout from '../../components/flowbite/FlowbiteLayout'

// Lazy load do componente de gráfico para não quebrar outras páginas
const FinancialChart = lazy(() => import('../../components/owner/FinancialChart'))

export default function OwnerDashboard() {
  const { user, logout } = useAuth()
  const [stats, setStats] = useState({
    totalConversations: 0,
    totalOrders: 0,
    revenue: 0,
    activeOperators: 0,
    totalUsers: 0,
    activeUsers: 0,
    todayOrders: 0
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [activeView, setActiveView] = useState('dashboard') // dashboard, reports, financial, team
  const [financialReport, setFinancialReport] = useState(null)
  const [ordersReport, setOrdersReport] = useState(null)
  const [financialPeriod, setFinancialPeriod] = useState('30') // 7, 14, 30, 365
  const [usersList, setUsersList] = useState([])
  const [showAddUser, setShowAddUser] = useState(false)

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
      const days = parseInt(financialPeriod)
      const endDate = new Date().toISOString().split('T')[0]
      const startDate = new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
      const data = await apiRequest(`reports/financial?start_date=${startDate}&end_date=${endDate}`)
      setFinancialReport(data)
    } catch (err) {
      console.error('Erro ao buscar relatório financeiro:', err)
      setError(err.message || 'Erro ao carregar relatório financeiro')
    } finally {
      setLoading(false)
    }
  }

  const fetchUsers = async () => {
    try {
      setLoading(true)
      setError('')
      const data = await apiRequest('users')
      setUsersList(data)
    } catch (err) {
      console.error('Erro ao buscar usuários:', err)
      setError(err.message || 'Erro ao carregar usuários')
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
    if (view === 'financial') {
      fetchFinancialReport()
    } else if (view === 'reports' && !ordersReport) {
      fetchOrdersReport()
    } else if (view === 'team') {
      fetchUsers()
    }
  }

  useEffect(() => {
    if (activeView === 'financial' && financialPeriod) {
      fetchFinancialReport()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [financialPeriod])

  return (
    <FlowbiteLayout
      appName="Gas Automation"
      pageTitle="Owner"
      userEmail={user?.email || ''}
      onLogout={logout}
      navItems={[
        { key: 'dashboard', type: 'button', label: 'Dashboard', icon: LayoutDashboard, onClick: () => handleViewChange('dashboard') },
        { key: 'reports', type: 'button', label: 'Relatórios', icon: FileText, onClick: () => handleViewChange('reports') },
        { key: 'financial', type: 'button', label: 'Financeiro', icon: DollarSign, onClick: () => handleViewChange('financial') },
        { key: 'team', type: 'button', label: 'Equipe', icon: Users, onClick: () => handleViewChange('team') },
        { key: 'drivers', type: 'button', label: 'Drivers', icon: Truck, onClick: () => handleViewChange('drivers') },
      ]}
    >
      {activeView === 'dashboard' && (
          <>
            <h2 className="text-2xl font-semibold text-gray-900 mb-6">Visão Geral do Negócio</h2>

        <div className="grid grid-cols-4 gap-6 mb-8">
          {/* Card 1 - Conversas */}
          <div className="corona-metric-card">
            <h3 className="corona-metric-label">💬 Conversas Total</h3>
            <p className="corona-metric-value">{stats.totalConversations}</p>
            <p className="corona-metric-subvalue">Total de conversas no sistema</p>
          </div>

          {/* Card 2 - Pedidos */}
          <div className="corona-metric-card">
            <h3 className="corona-metric-label">📦 Pedidos</h3>
            <p className="corona-metric-value corona-text-success">{stats.totalOrders}</p>
            <p className="corona-metric-subvalue">
              {stats.todayOrders > 0 ? `${stats.todayOrders} hoje` : 'Nenhum pedido hoje'}
            </p>
          </div>

          {/* Card 3 - Receita */}
          <div className="corona-metric-card">
            <h3 className="corona-metric-label">💰 Receita Total</h3>
            <p className="corona-metric-value corona-text-primary">
              R$ {stats.revenue.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </p>
            <p className="corona-metric-subvalue">Receita acumulada</p>
          </div>

          {/* Card 4 - Operadores */}
          <div className="corona-metric-card">
            <h3 className="corona-metric-label">👥 Operadores Ativos</h3>
            <p className="corona-metric-value corona-text-info">{stats.activeOperators}</p>
            <p className="corona-metric-subvalue">
              {stats.totalUsers > 0 ? `${stats.totalUsers} usuários total` : 'Sem usuários'}
            </p>
          </div>
        </div>

            {/* Informações Adicionais */}
            <div className="grid grid-cols-2 gap-6">
              <div className="corona-card">
                <div className="corona-card-header">
                  <h3 className="corona-card-title">📊 Resumo do Sistema</h3>
                </div>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="corona-text-muted">Usuários Total:</span>
                    <span className="font-bold">{stats.totalUsers}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="corona-text-muted">Usuários Ativos:</span>
                    <span className="font-bold corona-text-success">{stats.activeUsers}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="corona-text-muted">Pedidos Hoje:</span>
                    <span className="font-bold corona-text-primary">{stats.todayOrders}</span>
                  </div>
                </div>
              </div>
              
              <div className="corona-card">
                <div className="corona-card-header">
                  <h3 className="corona-card-title">⚡ Ações Rápidas</h3>
                </div>
                <div className="space-y-2">
                  <button
                    onClick={() => handleViewChange('reports')}
                    className="w-full text-left px-4 py-2 corona-bg-dark hover:bg-opacity-80 rounded transition"
                  >
                    📈 Ver Relatórios
                  </button>
                  <button
                    onClick={() => handleViewChange('financial')}
                    className="w-full text-left px-4 py-2 corona-bg-dark hover:bg-opacity-80 rounded transition"
                  >
                    💰 Ver Financeiro
                  </button>
                  <button
                    onClick={fetchStats}
                    className="w-full text-left px-4 py-2 corona-bg-dark hover:bg-opacity-80 rounded transition"
                  >
                    🔄 Atualizar Dados
                  </button>
                </div>
              </div>
            </div>
            
            {error && (
              <div className="mt-6 corona-card" style={{ borderColor: 'var(--corona-danger)' }}>
                <p className="corona-text-danger">⚠️ {error}</p>
              </div>
            )}
            
            {loading && (
              <div className="mt-6 corona-loading">
                <div className="corona-spinner"></div>
                <p className="mt-4">⏳ Carregando dados...</p>
              </div>
            )}
          </>
        )}

        {activeView === 'reports' && (
          <div>
            <h2 className="text-2xl font-bold mb-8" style={{ color: 'var(--corona-text)' }}>Relatórios de Pedidos</h2>
            {ordersReport && (
              <div className="grid grid-cols-2 gap-6 mb-6">
                <div className="corona-card">
                  <div className="corona-card-header">
                    <h3 className="corona-card-title">Resumo do Período</h3>
                  </div>
                  <div className="space-y-2">
                    <p className="text-sm">Total de Pedidos: <span className="font-bold">{ordersReport.summary?.total_orders || 0}</span></p>
                    <p className="text-sm">Taxa de Conclusão: <span className="font-bold">{ordersReport.summary?.completed_rate?.toFixed(1) || 0}%</span></p>
                    <p className="text-sm corona-text-muted">Período: {ordersReport.period?.start_date} - {ordersReport.period?.end_date}</p>
                  </div>
                </div>
                <div className="corona-card">
                  <div className="corona-card-header">
                    <h3 className="corona-card-title">Status dos Pedidos</h3>
                  </div>
                  <div className="space-y-2">
                    <p className="text-sm corona-text-success">✅ Concluídos: {ordersReport.summary?.by_status?.completed || 0}</p>
                    <p className="text-sm corona-text-primary">🔄 Em Processamento: {ordersReport.summary?.by_status?.in_process || 0}</p>
                    <p className="text-sm corona-text-warning">⏳ Pendentes: {ordersReport.summary?.by_status?.pending || 0}</p>
                    <p className="text-sm corona-text-danger">❌ Cancelados: {ordersReport.summary?.by_status?.cancelled || 0}</p>
                  </div>
                </div>
              </div>
            )}
            <div className="corona-card">
              <div className="corona-card-header">
                <div className="flex justify-between items-center">
                  <h3 className="corona-card-title">Últimos Pedidos</h3>
                  <button
                    onClick={() => window.open('/api/reports/export/orders', '_blank')}
                    className="corona-btn corona-btn-success"
                  >
                    📊 Exportar CSV
                  </button>
                </div>
              </div>
              {ordersReport?.orders && ordersReport.orders.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="corona-table">
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>Cliente</th>
                        <th>Status</th>
                        <th>Total</th>
                        <th>Data</th>
                      </tr>
                    </thead>
                    <tbody>
                      {ordersReport.orders.map((order, index) => (
                        <tr key={index}>
                          <td>{order.id}</td>
                          <td>{order.customer}</td>
                          <td>
                            <span className={`corona-badge ${
                              order.status === 'completed' ? 'corona-badge-success' :
                              order.status === 'pending' ? 'corona-badge-warning' :
                              'corona-badge-danger'
                            }`}>
                              {order.status}
                            </span>
                          </td>
                          <td>R$ {order.total}</td>
                          <td className="corona-text-muted">{order.created_at}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="corona-empty-state">
                  <p>Carregando dados dos pedidos...</p>
                </div>
              )}
            </div>
          </div>
        )}

        {activeView === 'financial' && (
          <div>
            <h2 className="text-2xl font-bold mb-8" style={{ color: 'var(--corona-text)' }}>Relatórios Financeiros</h2>
            {financialReport && (
              <div className="grid grid-cols-2 gap-6 mb-6">
                <div className="corona-card">
                  <div className="corona-card-header">
                    <h3 className="corona-card-title">Resumo Financeiro</h3>
                  </div>
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="corona-text-muted">Receita Total:</span>
                      <span className="font-bold corona-text-success">R$ {financialReport.summary?.total_revenue?.toLocaleString('pt-BR') || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="corona-text-muted">Despesas:</span>
                      <span className="font-bold corona-text-danger">R$ {financialReport.summary?.total_expenses?.toLocaleString('pt-BR') || 0}</span>
                    </div>
                    <div className="flex justify-between border-t pt-2" style={{ borderColor: 'var(--corona-border)' }}>
                      <span className="font-semibold">Lucro Líquido:</span>
                      <span className="font-bold corona-text-primary">R$ {financialReport.summary?.net_profit?.toLocaleString('pt-BR') || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="corona-text-muted">Margem de Lucro:</span>
                      <span className="font-bold">{financialReport.summary?.profit_margin?.toFixed(1) || 0}%</span>
                    </div>
                  </div>
                </div>
                <div className="corona-card">
                  <div className="corona-card-header">
                    <h3 className="corona-card-title">Métricas do Período</h3>
                  </div>
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="corona-text-muted">Total de Pedidos:</span>
                      <span className="font-bold">{financialReport.summary?.total_orders || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="corona-text-muted">Ticket Médio:</span>
                      <span className="font-bold">R$ {financialReport.summary?.average_ticket?.toFixed(2) || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="corona-text-muted">Período:</span>
                      <span className="font-bold text-sm">{financialReport.period?.start_date} - {financialReport.period?.end_date}</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
            <div className="corona-card">
              <div className="corona-card-header">
                <div className="flex justify-between items-center">
                  <h3 className="corona-card-title">Receita Diária</h3>
                  <div className="flex gap-2">
                    {/* Filtros de Período */}
                    <div className="flex gap-2 mr-4">
                      {[
                        { label: '7 dias', value: '7' },
                        { label: '14 dias', value: '14' },
                        { label: '30 dias', value: '30' },
                        { label: '1 ano', value: '365' }
                      ].map((period) => (
                        <button
                          key={period.value}
                          onClick={() => setFinancialPeriod(period.value)}
                          className={`corona-btn ${financialPeriod === period.value ? 'corona-btn-primary' : 'corona-btn-secondary'}`}
                        >
                          {period.label}
                        </button>
                      ))}
                    </div>
                    <button
                      onClick={fetchFinancialReport}
                      className="corona-btn corona-btn-primary"
                    >
                      🔄 Atualizar
                    </button>
                    <button
                      onClick={() => {
                        const days = parseInt(financialPeriod)
                        const endDate = new Date().toISOString().split('T')[0]
                        const startDate = new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
                        window.open(`/api/reports/export/financial?start_date=${startDate}&end_date=${endDate}`, '_blank')
                      }}
                      className="corona-btn corona-btn-success"
                    >
                      📊 Exportar CSV
                    </button>
                  </div>
                </div>
              </div>
              {financialReport?.charts && financialReport.charts.revenue_trend.length > 0 ? (
                <div className="h-96">
                  <Suspense fallback={<div className="corona-loading">Carregando gráfico...</div>}>
                    <FinancialChart data={financialReport.charts} />
                  </Suspense>
                </div>
              ) : (
                <div className="h-64 corona-bg-dark rounded flex items-center justify-center">
                  <p className="corona-text-muted">Carregando dados financeiros...</p>
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
            <h2 className="text-2xl font-bold mb-8" style={{ color: 'var(--corona-text)' }}>Gestão de Equipe</h2>
            <div className="grid grid-cols-2 gap-6 mb-6">
              <div className="corona-card">
                <div className="corona-card-header">
                  <h3 className="corona-card-title">Operadores Ativos</h3>
                </div>
                <p className="corona-metric-value corona-text-primary">{stats.activeOperators}</p>
                <p className="corona-text-muted mt-2">Operadores online</p>
              </div>
              <div className="corona-card">
                <div className="corona-card-header">
                  <h3 className="corona-card-title">Total de Usuários</h3>
                </div>
                <p className="corona-metric-value corona-text-success">{stats.totalUsers}</p>
                <p className="corona-text-muted mt-2">Usuários cadastrados</p>
              </div>
            </div>
            
            <div className="corona-card mb-6">
              <div className="corona-card-header">
                <div className="flex justify-between items-center">
                  <h3 className="corona-card-title">Gerenciar Equipe</h3>
                  <button
                    onClick={() => {
                      setShowAddUser(!showAddUser)
                      if (!showAddUser) fetchUsers()
                    }}
                    className="corona-btn corona-btn-success"
                  >
                    {showAddUser ? '❌ Cancelar' : '➕ Adicionar Usuário'}
                  </button>
                </div>
              </div>
              
              {showAddUser && (
                <div className="corona-bg-dark p-4 rounded mb-4">
                  <p className="text-sm mb-2">Funcionalidade em desenvolvimento</p>
                  <p className="text-xs corona-text-muted">Use o endpoint /api/users para criar novos usuários</p>
                </div>
              )}
            </div>

            <div className="corona-table-wrapper">
              <div className="corona-card-header">
                <div className="flex justify-between items-center">
                  <h3 className="corona-card-title">👥 Lista de Usuários</h3>
                  <button
                    onClick={fetchUsers}
                    className="corona-btn corona-btn-primary"
                  >
                    🔄 Atualizar
                  </button>
                </div>
              </div>
              
              {usersList.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="corona-table">
                    <thead>
                      <tr>
                        <th>Nome</th>
                        <th>Email</th>
                        <th>Role</th>
                        <th>Status</th>
                        <th>Criado em</th>
                      </tr>
                    </thead>
                    <tbody>
                      {usersList.map((user) => (
                        <tr key={user.id}>
                          <td>{user.username || user.email}</td>
                          <td>{user.email}</td>
                          <td>
                            <span className={`corona-badge ${
                              user.role === 'admin' ? 'corona-badge-danger' :
                              user.role === 'owner' ? 'corona-badge-info' :
                              user.role === 'operator' ? 'corona-badge-primary' :
                              'corona-badge-secondary'
                            }`}>
                              {user.role}
                            </span>
                          </td>
                          <td>
                            <span className={`corona-badge ${user.is_active ? 'corona-badge-success' : 'corona-badge-danger'}`}>
                              {user.is_active ? 'Ativo' : 'Inativo'}
                            </span>
                          </td>
                          <td className="corona-text-muted text-sm">
                            {user.created_at ? new Date(user.created_at).toLocaleDateString('pt-BR') : '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="corona-empty-state">
                  <p>
                    {loading ? 'Carregando usuários...' : 'Nenhum usuário encontrado'}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
    </FlowbiteLayout>
  )
}
