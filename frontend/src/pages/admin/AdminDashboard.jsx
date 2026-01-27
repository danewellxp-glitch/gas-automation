import { useState, useEffect } from 'react'
import { useAuth } from '../../hooks/useAuth'
import { apiRequest, getApiUrl } from '../../utils/api'
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
  { value: 'admin', label: 'Admin', icon: '👑', description: 'Acesso total ao sistema' },
  { value: 'operator', label: 'Operador', icon: '👤', description: 'Gerencia conversas e pedidos' },
  { value: 'owner', label: 'Proprietário', icon: '💼', description: 'Visão executiva' },
  { value: 'user', label: 'Usuário', icon: '📦', description: 'Acesso básico' }
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
    const roleObj = VALID_ROLES.find(r => r.value === role)
    return roleObj?.icon || '📦'
  }

  const SortIcon = ({ field }) => {
    if (sortField !== field) return <span className="text-gray-400">⇅</span>
    return sortDirection === 'asc' ? <span>↑</span> : <span>↓</span>
  }

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <div className="w-64 bg-white shadow-lg flex flex-col">
        <div className="p-6 border-b">
          <h1 className="text-xl font-bold text-gray-800">Gas Automation</h1>
          <p className="text-sm text-gray-500">Painel do Admin</p>
        </div>
        
        <nav className="p-4 flex-1">
          <div className="space-y-2">
            <button 
              onClick={() => setActiveView('dashboard')}
              className={`w-full text-left px-4 py-3 rounded transition ${
                activeView === 'dashboard' 
                  ? 'bg-blue-500 text-white' 
                  : 'hover:bg-gray-100'
              }`}
            >
              📊 Dashboard
            </button>
            <button 
              onClick={() => setActiveView('users')}
              className={`w-full text-left px-4 py-3 rounded transition ${
                activeView === 'users' 
                  ? 'bg-blue-500 text-white' 
                  : 'hover:bg-gray-100'
              }`}
            >
              👥 Usuários
            </button>
            <button 
              onClick={() => setActiveView('reports')}
              className={`w-full text-left px-4 py-3 rounded transition ${
                activeView === 'reports' 
                  ? 'bg-blue-500 text-white' 
                  : 'hover:bg-gray-100'
              }`}
            >
              📋 Relatórios
            </button>
            <button 
              onClick={() => setActiveView('settings')}
              className={`w-full text-left px-4 py-3 rounded transition ${
                activeView === 'settings' 
                  ? 'bg-blue-500 text-white' 
                  : 'hover:bg-gray-100'
              }`}
            >
              ⚙️ Configurações
            </button>
          </div>
        </nav>

        <div className="border-t p-4">
          <div className="flex items-center justify-between gap-2">
            <div className="text-sm min-w-0">
              <p className="font-semibold text-gray-800 truncate">{user?.email}</p>
              <p className="text-gray-500 text-xs uppercase font-bold">{getRoleIcon(user?.role)} {user?.role}</p>
            </div>
            <button 
              onClick={logout}
              className="px-3 py-1 bg-red-500 text-white rounded text-xs hover:bg-red-600 transition whitespace-nowrap"
            >
              Sair
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto">
        <div className="p-8">
          {/* Renderizar view baseada no estado */}
          {activeView === 'dashboard' && <DashboardOverview />}
          
          {activeView === 'reports' && <AuditLogsPanel />}
          
          {activeView === 'settings' && <SystemSettings />}
          
          {activeView === 'users' && (
            <>
              {/* Header */}
              <div className="mb-6">
                <h2 className="text-2xl font-bold text-gray-800">Gerenciamento de Usuários</h2>
                <p className="text-gray-600">Gerencie roles e permissões do sistema</p>
              </div>

              {/* Error Message */}
              {error && (
                <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
                  {error}
                </div>
              )}

              {/* Users Table */}
          <div className="bg-white rounded-lg shadow">
            {/* Search Bar */}
            <div className="p-4 border-b">
              <input
                type="text"
                placeholder="Buscar por email, nome ou usuário..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:border-blue-500"
              />
              <p className="text-xs text-gray-500 mt-2">
                {displayedUsers.length} de {users.length} usuários
              </p>
            </div>

            {loading ? (
              <div className="p-8 text-center">
                <div className="inline-block">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                </div>
                <p className="text-gray-600 mt-4">Carregando usuários...</p>
              </div>
            ) : displayedUsers.length === 0 ? (
              <div className="p-8 text-center">
                <p className="text-gray-500">
                  {searchTerm ? 'Nenhum usuário encontrado com esse critério' : 'Nenhum usuário encontrado'}
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th 
                        onClick={() => handleSort('email')}
                        className="px-6 py-4 text-left text-sm font-semibold text-gray-700 cursor-pointer hover:bg-gray-100 transition"
                      >
                        <div className="flex items-center gap-2">
                          Email
                          <SortIcon field="email" />
                        </div>
                      </th>
                      <th 
                        onClick={() => handleSort('full_name')}
                        className="px-6 py-4 text-left text-sm font-semibold text-gray-700 cursor-pointer hover:bg-gray-100 transition"
                      >
                        <div className="flex items-center gap-2">
                          Nome
                          <SortIcon field="full_name" />
                        </div>
                      </th>
                      <th 
                        onClick={() => handleSort('role')}
                        className="px-6 py-4 text-left text-sm font-semibold text-gray-700 cursor-pointer hover:bg-gray-100 transition"
                      >
                        <div className="flex items-center gap-2">
                          Role
                          <SortIcon field="role" />
                        </div>
                      </th>
                      <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700">Status</th>
                      <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700">Criado em</th>
                      <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700">Ações</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {displayedUsers.map(userData => (
                      <tr key={userData.id} className="hover:bg-gray-50 transition">
                        <td className="px-6 py-4 text-sm text-gray-800">{userData.email}</td>
                        <td className="px-6 py-4 text-sm text-gray-800">{userData.full_name || userData.username || '-'}</td>
                        <td className="px-6 py-4 text-sm">
                          <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold border ${getRoleColor(userData.role)}`}>
                            {getRoleIcon(userData.role)} {userData.role}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-sm">
                          <span className={`px-2 py-1 rounded text-xs font-medium ${userData.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                            {userData.is_active ? '✓ Ativo' : '✗ Inativo'}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-600">
                          {userData.created_at ? formatDateTime(userData.created_at) : '-'}
                        </td>
                        <td className="px-6 py-4 text-sm">
                          <button 
                            onClick={() => handleEditClick(userData)}
                            disabled={userData.id === user?.id}
                            className={`px-3 py-1 rounded text-xs font-medium transition ${
                              userData.id === user?.id 
                                ? 'bg-gray-100 text-gray-400 cursor-not-allowed' 
                                : 'bg-blue-500 text-white hover:bg-blue-600'
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
        </div>
      </div>

      {/* Modal para editar role (só aparece na view de users) */}
      {selectedUser && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-2xl w-full max-w-md">
            {/* Header */}
            <div className="p-6 border-b">
              <h3 className="text-lg font-bold text-gray-800">
                Alterar Role
              </h3>
              <p className="text-sm text-gray-600 mt-1">
                {selectedUser.email}
              </p>
            </div>

            {/* Content */}
            <div className="p-6">
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Role Atual
                </label>
                <div className={`px-4 py-3 rounded-lg border-2 ${getRoleColor(selectedUser.role)}`}>
                  <span className="font-medium">{getRoleIcon(selectedUser.role)} {selectedUser.role}</span>
                </div>
              </div>

              {!showConfirmation ? (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-3">
                    Nova Role
                  </label>
                  <div className="space-y-2">
                    {VALID_ROLES.map(role => (
                      <button
                        key={role.value}
                        onClick={() => handleRoleChange(role.value)}
                        className={`w-full p-3 text-left rounded-lg border-2 transition ${
                          newRole === role.value
                            ? 'border-blue-500 bg-blue-50'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <div className="font-medium text-gray-800">
                          {role.icon} {role.label}
                        </div>
                        <div className="text-xs text-gray-600 mt-1">
                          {role.description}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                  <p className="font-medium text-gray-800 mb-2">Confirmar alteração?</p>
                  <p className="text-sm text-gray-700">
                    Você está alterando a role de <strong>{selectedUser.email}</strong> para <strong>{newRole}</strong>
                  </p>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="p-6 border-t bg-gray-50 rounded-b-lg flex gap-3">
              {!showConfirmation ? (
                <>
                  <button 
                    onClick={() => {
                      setSelectedUser(null)
                      setNewRole('')
                    }}
                    className="flex-1 px-4 py-2 bg-gray-300 text-gray-800 rounded hover:bg-gray-400 transition font-medium"
                  >
                    Cancelar
                  </button>
                  <button 
                    onClick={() => setShowConfirmation(true)}
                    disabled={newRole === selectedUser.role || !newRole}
                    className="flex-1 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Próximo
                  </button>
                </>
              ) : (
                <>
                  <button 
                    onClick={() => setShowConfirmation(false)}
                    className="flex-1 px-4 py-2 bg-gray-300 text-gray-800 rounded hover:bg-gray-400 transition font-medium"
                  >
                    Voltar
                  </button>
                  <button 
                    onClick={updateUserRole}
                    disabled={updating}
                    className="flex-1 px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 transition font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {updating ? 'Salvando...' : 'Confirmar'}
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
