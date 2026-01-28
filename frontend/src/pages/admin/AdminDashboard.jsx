import { useState, useEffect } from 'react'
import { LayoutDashboard, Users, FileText, Settings } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import { apiRequest, getApiUrl } from '../../utils/api'
import FlowbiteLayout from '../../components/flowbite/FlowbiteLayout'
import {
  getRoleBadge,
  formatDateTime,
  showToast,
  filterUsers,
  sortUsers,
  debounce
} from '../../utils/adminHelpers'

// Importar componentes das views
import DashboardOverview from '../../components/admin/DashboardOverview'
import AuditLogsPanel from '../../components/admin/AuditLogsPanel'
import SystemSettings from '../../components/admin/SystemSettings'

const VALID_ROLES = [
  { value: 'admin', label: 'Admin', description: 'Acesso total ao sistema' },
  { value: 'operator', label: 'Operador', description: 'Gerencia conversas e pedidos' },
  { value: 'owner', label: 'Proprietário', description: 'Visão executiva' },
  { value: 'user', label: 'Usuário', description: 'Acesso básico' }
]

export default function AdminDashboard() {
  const { user, logout } = useAuth()
  
  // Estado de navegação
  const [activeView, setActiveView] = useState('dashboard')
  
  // Estados para gerenciamento de usuários
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedUser, setSelectedUser] = useState(null)
  const [newRole, setNewRole] = useState('')
  const [showConfirmation, setShowConfirmation] = useState(false)
  const [updating, setUpdating] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [sortField, setSortField] = useState('created_at')
  const [sortDirection, setSortDirection] = useState('desc')

  useEffect(() => {
    fetchUsers()
  }, [])

  const fetchUsers = async () => {
    try {
      setLoading(true)
      setError('')
      const data = await apiRequest('users')
      setUsers(data)
    } catch (err) {
      console.error('Erro ao buscar usuários:', err)
      setError(err.message || 'Erro ao carregar usuários')
    } finally {
      setLoading(false)
    }
  }

  const handleEditClick = (userData) => {
    setSelectedUser(userData)
    setNewRole(userData.role)
    setShowConfirmation(false)
  }

  const handleRoleChange = (role) => {
    setNewRole(role)
    setShowConfirmation(true)
  }

  const handleSort = (field) => {
    if (sortField === field) {
      // Toggle direction
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('asc')
    }
  }

  const updateUserRole = async () => {
    if (!selectedUser || !newRole || newRole === selectedUser.role) return

    // Validação: admin não pode editar sua própria role
    if (selectedUser.id === user?.id) {
      setError('Você não pode alterar sua própria role')
      return
    }

    try {
      setUpdating(true)
      setError('')
      
      const response = await apiRequest(`users/${selectedUser.id}/role`, {
        method: 'PUT',
        body: JSON.stringify({ role: newRole })
      })

      // Atualizar lista de usuários
      await fetchUsers()
      setSelectedUser(null)
      setNewRole('')
      setShowConfirmation(false)
    } catch (err) {
      console.error('Erro ao atualizar role:', err)
      setError(err.message || 'Erro ao atualizar role')
    } finally {
      setUpdating(false)
    }
  }

  // Aplicar filtros e ordenação
  const getDisplayedUsers = () => {
    let filtered = filterUsers(users, searchTerm)
    let sorted = sortUsers(filtered, sortField, sortDirection)
    return sorted
  }

  const displayedUsers = getDisplayedUsers()

  const getRoleColor = (role) => {
    switch (role) {
      case 'admin':
        return 'bg-red-100 text-red-800 border-red-300'
      case 'operator':
        return 'bg-blue-100 text-blue-800 border-blue-300'
      case 'owner':
        return 'bg-purple-100 text-purple-800 border-purple-300'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300'
    }
  }

  const getRoleIcon = (role) => {
    // Removido: emojis nos dashboards (visual mais profissional)
    return ''
  }

  const SortIcon = ({ field }) => {
    if (sortField !== field) return <span className="text-gray-400">⇅</span>
    return sortDirection === 'asc' ? <span>↑</span> : <span>↓</span>
  }

  return (
    <FlowbiteLayout
      appName="Gas Automation"
      pageTitle="Admin"
      userEmail={user?.email || ''}
      onLogout={logout}
      navItems={[
        { key: 'dashboard', type: 'button', label: 'Dashboard', icon: LayoutDashboard, onClick: () => setActiveView('dashboard') },
        { key: 'users', type: 'button', label: 'Usuários', icon: Users, onClick: () => setActiveView('users') },
        { key: 'reports', type: 'button', label: 'Relatórios', icon: FileText, onClick: () => setActiveView('reports') },
        { key: 'settings', type: 'button', label: 'Configurações', icon: Settings, onClick: () => setActiveView('settings') },
      ]}
    >
      {/* Renderizar view baseada no estado */}
      {activeView === 'dashboard' && <DashboardOverview />}

      {activeView === 'reports' && <AuditLogsPanel />}

      {activeView === 'settings' && <SystemSettings />}

      {activeView === 'users' && (
        <>
          {/* Header */}
          <div className="mb-6">
            <h2 className="text-2xl font-semibold text-gray-900">Gerenciamento de Usuários</h2>
            <p className="text-gray-600">Gerencie roles e permissões do sistema</p>
          </div>

              {/* Error Message */}
              {error && (
                <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                  {error}
                </div>
              )}

              {/* Users Table */}
          <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
            {/* Search Bar */}
            <div className="border-b border-gray-200 p-4">
              <input
                type="text"
                placeholder="Buscar por email, nome ou usuário..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-primary-500 focus:ring-primary-500"
              />
              <p className="mt-2 text-xs text-gray-500">
                {displayedUsers.length} de {users.length} usuários
              </p>
            </div>

            {loading ? (
              <div className="p-8 text-center">
                <div className="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-gray-200 border-t-primary-600" />
                <p className="mt-3 text-sm text-gray-600">Carregando usuários...</p>
              </div>
            ) : displayedUsers.length === 0 ? (
              <div className="p-8 text-center text-sm text-gray-600">
                {searchTerm ? 'Nenhum usuário encontrado com esse critério' : 'Nenhum usuário encontrado'}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-gray-700">
                  <thead>
                    <tr>
                      <th 
                        onClick={() => handleSort('email')}
                        className="cursor-pointer hover:bg-opacity-50 transition"
                        style={{ background: 'rgba(0, 0, 0, 0.02)' }}
                      >
                        <div className="flex items-center gap-2">
                          Email
                          <SortIcon field="email" />
                        </div>
                      </th>
                      <th 
                        onClick={() => handleSort('full_name')}
                        className="cursor-pointer hover:bg-opacity-50 transition"
                        style={{ background: 'rgba(0, 0, 0, 0.02)' }}
                      >
                        <div className="flex items-center gap-2">
                          Nome
                          <SortIcon field="full_name" />
                        </div>
                      </th>
                      <th 
                        onClick={() => handleSort('role')}
                        className="cursor-pointer hover:bg-opacity-50 transition"
                        style={{ background: 'rgba(0, 0, 0, 0.02)' }}
                      >
                        <div className="flex items-center gap-2">
                          Role
                          <SortIcon field="role" />
                        </div>
                      </th>
                      <th style={{ background: 'rgba(0, 0, 0, 0.02)' }}>Status</th>
                      <th style={{ background: 'rgba(0, 0, 0, 0.02)' }}>Criado em</th>
                      <th style={{ background: 'rgba(0, 0, 0, 0.02)' }}>Ações</th>
                    </tr>
                  </thead>
                  <tbody>
                    {displayedUsers.map(userData => (
                      <tr key={userData.id} className="border-t border-gray-100 hover:bg-gray-50">
                        <td className="px-4 py-3">{userData.email}</td>
                        <td className="px-4 py-3">{userData.full_name || userData.username || '-'}</td>
                        <td>
                          <span className="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-700">
                            {userData.role}
                          </span>
                        </td>
                        <td>
                          <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${
                            userData.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'
                          }`}>
                            {userData.is_active ? 'Ativo' : 'Inativo'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-gray-500">
                          {userData.created_at ? formatDateTime(userData.created_at) : '-'}
                        </td>
                        <td>
                          <button 
                            onClick={() => handleEditClick(userData)}
                            disabled={userData.id === user?.id}
                            className={`rounded-lg px-3 py-1.5 text-xs font-medium ${
                              userData.id === user?.id
                                ? 'cursor-not-allowed bg-gray-100 text-gray-400'
                                : 'bg-primary-600 text-white hover:bg-primary-700'
                            }`}
                            title={userData.id === user?.id ? 'Você não pode editar sua própria role' : 'Editar role'}
                          >
                            Editar
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
            </>
          )}

      {/* Modal para editar role (só aparece na view de users) */}
      {selectedUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/50 p-4">
          <div className="w-full max-w-md overflow-hidden rounded-xl bg-white shadow-xl">
            {/* Header */}
            <div className="border-b border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900">
                Alterar Role
              </h3>
              <p className="mt-1 text-sm text-gray-500">
                {selectedUser.email}
              </p>
            </div>

            {/* Content */}
            <div className="p-6">
              <div className="mb-4">
                <label className="block text-sm font-medium mb-3">
                  Role Atual
                </label>
                <div className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3">
                  <span className="font-medium text-gray-900">{selectedUser.role}</span>
                </div>
              </div>

              {!showConfirmation ? (
                <div>
                  <label className="block text-sm font-medium mb-3">
                    Nova Role
                  </label>
                  <div className="space-y-2">
                    {VALID_ROLES.map(role => (
                      <button
                        key={role.value}
                        onClick={() => handleRoleChange(role.value)}
                        className={`w-full rounded-lg border p-3 text-left transition ${
                          newRole === role.value
                            ? 'border-primary-600 bg-primary-50'
                            : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                        }`}
                      >
                        <div className="font-medium text-gray-900">{role.label}</div>
                        <div className="mt-1 text-xs text-gray-500">
                          {role.description}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
                  <p className="mb-2 font-medium text-gray-900">Confirmar alteração?</p>
                  <p className="text-sm text-gray-700">
                    Você está alterando a role de <strong>{selectedUser.email}</strong> para <strong>{newRole}</strong>
                  </p>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="flex gap-3 border-t border-gray-200 bg-gray-50 p-6">
              {!showConfirmation ? (
                <>
                  <button 
                    onClick={() => {
                      setSelectedUser(null)
                      setNewRole('')
                    }}
                    className="flex-1 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                  >
                    Cancelar
                  </button>
                  <button 
                    onClick={() => setShowConfirmation(true)}
                    disabled={newRole === selectedUser.role || !newRole}
                    className="flex-1 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
                  >
                    Próximo
                  </button>
                </>
              ) : (
                <>
                  <button 
                    onClick={() => setShowConfirmation(false)}
                    className="flex-1 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                  >
                    Voltar
                  </button>
                  <button 
                    onClick={updateUserRole}
                    disabled={updating}
                    className="flex-1 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
                  >
                    {updating ? 'Salvando...' : 'Confirmar'}
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </FlowbiteLayout>
  )
}
