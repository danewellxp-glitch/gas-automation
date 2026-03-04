import { useState, useEffect, useMemo } from 'react'
import { LayoutDashboard, Users, FileText, Settings, Plus, RefreshCcw, KeyRound, Activity, Bug, Wrench, MessageSquare } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import { apiRequest } from '../../utils/api'
import FlowbiteLayout from '../../components/flowbite/FlowbiteLayout'
import {
  formatDateTime,
  filterUsers,
  sortUsers,
} from '../../utils/adminHelpers'

// Importar componentes das views
import DashboardOverview from '../../components/admin/DashboardOverview'
import AuditLogsPanel from '../../components/admin/AuditLogsPanel'
import SystemSettings from '../../components/admin/SystemSettings'
import SystemHealthPanel from '../../components/admin/SystemHealthPanel'
import ErrorCenterPanel from '../../components/admin/ErrorCenterPanel'
import DebugToolsPanel from '../../components/admin/DebugToolsPanel'
import WhatsAppBroadcast from '../../components/WhatsAppBroadcast'

const VALID_ROLES = [
  { value: 'admin', label: 'Admin', description: 'Acesso total ao sistema' },
  { value: 'operator', label: 'Operador', description: 'Gerencia conversas e pedidos' },
  { value: 'owner', label: 'Proprietário', description: 'Visão executiva' },
  { value: 'driver', label: 'Entregador', description: 'Acesso ao app do driver' },
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
  const [updating, setUpdating] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [sortField, setSortField] = useState('created_at')
  const [sortDirection, setSortDirection] = useState('desc')

  // Create/Edit modals
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [createForm, setCreateForm] = useState({
    email: '',
    full_name: '',
    role: 'operator',
    is_active: true,
  })
  const [createTempPassword, setCreateTempPassword] = useState('')

  const [showEditModal, setShowEditModal] = useState(false)
  const [editForm, setEditForm] = useState({
    id: null,
    username: '',
    email: '',
    full_name: '',
    role: '',
    is_active: true,
    created_at: null,
  })
  const [resetTempPassword, setResetTempPassword] = useState('')

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

  const openCreateModal = () => {
    setCreateTempPassword('')
    setCreateForm({
      email: '',
      full_name: '',
      role: 'operator',
      is_active: true,
    })
    setShowCreateModal(true)
  }

  const openEditModal = (userData) => {
    setResetTempPassword('')
    setEditForm({
      id: userData.id,
      username: userData.username || '',
      email: userData.email || '',
      full_name: userData.full_name || '',
      role: userData.role || 'user',
      is_active: !!userData.is_active,
      created_at: userData.created_at || null,
    })
    setShowEditModal(true)
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

  const createUser = async () => {
    try {
      setUpdating(true)
      setError('')
      setCreateTempPassword('')

      const username = createForm.email.split('@')[0].replace(/[^a-zA-Z0-9._-]/g, '')
      const res = await apiRequest(`admin/users`, {
        method: 'POST',
        body: JSON.stringify({ ...createForm, username }),
      })

      setCreateTempPassword(res?.temporary_password || '')
      await fetchUsers()
    } catch (err) {
      console.error('Erro ao criar usuário:', err)
      setError(err.message || 'Erro ao criar usuário')
    } finally {
      setUpdating(false)
    }
  }

  const updateUser = async () => {
    if (!editForm?.id) return
    try {
      setUpdating(true)
      setError('')

      const payload = {
        username: editForm.username,
        email: editForm.email,
        full_name: editForm.full_name,
        role: editForm.role,
        is_active: editForm.is_active,
      }

      await apiRequest(`admin/users/${editForm.id}`, {
        method: 'PUT',
        body: JSON.stringify(payload),
      })

      await fetchUsers()
      setShowEditModal(false)
    } catch (err) {
      console.error('Erro ao atualizar usuário:', err)
      setError(err.message || 'Erro ao atualizar usuário')
    } finally {
      setUpdating(false)
    }
  }

  const resetPassword = async () => {
    if (!editForm?.id) return
    try {
      setUpdating(true)
      setError('')
      setResetTempPassword('')

      const res = await apiRequest(`admin/users/${editForm.id}/reset-password`, {
        method: 'POST',
      })

      setResetTempPassword(res?.temporary_password || '')
      await fetchUsers()
    } catch (err) {
      console.error('Erro ao resetar senha:', err)
      setError(err.message || 'Erro ao resetar senha')
    } finally {
      setUpdating(false)
    }
  }

  // Aplicar filtros e ordenação
  const displayedUsers = useMemo(() => {
    const filtered = filterUsers(users, searchTerm)
    return sortUsers(filtered, sortField, sortDirection)
  }, [users, searchTerm, sortField, sortDirection])

  const SortIcon = ({ field }) => {
    if (sortField !== field) return <span className="text-gray-400">⇅</span>
    return sortDirection === 'asc' ? <span>↑</span> : <span>↓</span>
  }

  const copyToClipboard = async (text) => {
    try {
      await navigator.clipboard.writeText(text)
    } catch {
      // ignore (sem permissão)
    }
  }

  return (
    <FlowbiteLayout
      appName="Gas Automation"
      pageTitle="Admin"
      userEmail={user?.email || ''}
      onLogout={logout}
      activeNavKey={activeView}
      navItems={[
        { key: 'dashboard', type: 'button', label: 'Dashboard', icon: LayoutDashboard, onClick: () => setActiveView('dashboard') },
        { key: 'users', type: 'button', label: 'Usuários', icon: Users, onClick: () => setActiveView('users') },
        { key: 'system-health', type: 'button', label: 'System Health', icon: Activity, onClick: () => setActiveView('system-health') },
        { key: 'errors', type: 'button', label: 'Logs & Erros', icon: Bug, onClick: () => setActiveView('errors') },
        { key: 'debug', type: 'button', label: 'Debug Tools', icon: Wrench, onClick: () => setActiveView('debug') },
        { key: 'reports', type: 'button', label: 'Relatórios', icon: FileText, onClick: () => setActiveView('reports') },
        { key: 'whatsapp-broadcast', type: 'button', label: 'Disparo WhatsApp', icon: MessageSquare, onClick: () => setActiveView('whatsapp-broadcast') },
        { key: 'settings', type: 'button', label: 'Configurações', icon: Settings, onClick: () => setActiveView('settings') },
      ]}
    >
      {/* Renderizar view baseada no estado */}
      {activeView === 'dashboard' && <DashboardOverview />}
      {activeView === 'whatsapp-broadcast' && <WhatsAppBroadcast />}

      {activeView === 'system-health' && <SystemHealthPanel />}

      {activeView === 'errors' && <ErrorCenterPanel />}

      {activeView === 'debug' && <DebugToolsPanel />}

      {activeView === 'reports' && <AuditLogsPanel />}

      {activeView === 'settings' && <SystemSettings />}

      {activeView === 'whatsapp-broadcast' && <WhatsAppBroadcast />}

      {activeView === 'users' && (
        <>
          {/* Header */}
          <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-2xl font-semibold text-gray-900">Gerenciamento de Usuários</h2>
              <p className="text-gray-600">Crie usuários reais, edite dados e redefina senhas</p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={fetchUsers}
                className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                <RefreshCcw className="h-4 w-4" />
                Atualizar
              </button>
              <button
                onClick={openCreateModal}
                className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-3 py-2 text-sm font-medium text-white hover:bg-primary-700"
              >
                <Plus className="h-4 w-4" />
                Adicionar usuário
              </button>
            </div>
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
                        onClick={() => handleSort('username')}
                        className="cursor-pointer hover:bg-opacity-50 transition"
                        style={{ background: 'rgba(0, 0, 0, 0.02)' }}
                      >
                        <div className="flex items-center gap-2">
                          Usuário
                          <SortIcon field="username" />
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
                        <td className="px-4 py-3 text-gray-600">{userData.username || '-'}</td>
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
                            onClick={() => openEditModal(userData)}
                            className="rounded-lg bg-primary-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-700"
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

      {/* Modal: Criar usuário */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/50 p-4">
          <div className="w-full max-w-lg overflow-hidden rounded-xl bg-white shadow-xl">
            <div className="border-b border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900">Adicionar usuário</h3>
              <p className="mt-1 text-sm text-gray-500">A senha temporária será exibida uma única vez.</p>
            </div>

            <div className="space-y-4 p-6">
              <div>
                <label className="block text-sm font-medium text-gray-700">Email</label>
                <input
                  value={createForm.email}
                  onChange={(e) => setCreateForm((p) => ({ ...p, email: e.target.value }))}
                  className="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-primary-500 focus:ring-primary-500"
                  placeholder="ex: joao@empresa.com"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Nome</label>
                <input
                  value={createForm.full_name}
                  onChange={(e) => setCreateForm((p) => ({ ...p, full_name: e.target.value }))}
                  className="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-primary-500 focus:ring-primary-500"
                  placeholder="Nome completo"
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Role</label>
                  <select
                    value={createForm.role}
                    onChange={(e) => setCreateForm((p) => ({ ...p, role: e.target.value }))}
                    className="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-primary-500 focus:ring-primary-500"
                  >
                    {VALID_ROLES.map((r) => (
                      <option key={r.value} value={r.value}>
                        {r.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex items-end">
                  <label className="inline-flex items-center gap-2 text-sm text-gray-700">
                    <input
                      type="checkbox"
                      checked={createForm.is_active}
                      onChange={(e) => setCreateForm((p) => ({ ...p, is_active: e.target.checked }))}
                      className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                    Usuário ativo
                  </label>
                </div>
              </div>

              {createTempPassword && (
                <div className="rounded-lg border border-green-200 bg-green-50 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-green-800">Senha temporária</p>
                      <p className="mt-1 font-mono text-sm text-green-900">{createTempPassword}</p>
                      <p className="mt-1 text-xs text-green-800">
                        No primeiro login, o usuário será obrigado a trocar a senha.
                      </p>
                    </div>
                    <button
                      onClick={() => copyToClipboard(createTempPassword)}
                      className="rounded-lg bg-green-600 px-3 py-2 text-xs font-medium text-white hover:bg-green-700"
                    >
                      Copiar
                    </button>
                  </div>
                </div>
              )}
            </div>

            <div className="flex gap-3 border-t border-gray-200 bg-gray-50 p-6">
              <button
                onClick={() => setShowCreateModal(false)}
                className="flex-1 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Fechar
              </button>
              <button
                onClick={createUser}
                disabled={updating || !createForm.email}
                className="flex-1 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
              >
                {updating ? 'Criando...' : 'Criar usuário'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Editar usuário */}
      {showEditModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/50 p-4">
          <div className="w-full max-w-lg overflow-hidden rounded-xl bg-white shadow-xl">
            <div className="border-b border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900">Editar usuário</h3>
              <p className="mt-1 text-sm text-gray-500">
                {editForm.email} {editForm.created_at ? `• Criado em ${formatDateTime(editForm.created_at)}` : ''}
              </p>
            </div>

            <div className="space-y-4 p-6">
              <div>
                <label className="block text-sm font-medium text-gray-700">Email</label>
                <input
                  value={editForm.email}
                  onChange={(e) => setEditForm((p) => ({ ...p, email: e.target.value }))}
                  className="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-primary-500 focus:ring-primary-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Nome</label>
                <input
                  value={editForm.full_name}
                  onChange={(e) => setEditForm((p) => ({ ...p, full_name: e.target.value }))}
                  className="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-primary-500 focus:ring-primary-500"
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Role</label>
                  <select
                    value={editForm.role}
                    onChange={(e) => setEditForm((p) => ({ ...p, role: e.target.value }))}
                    disabled={editForm.id === user?.id}
                    className="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-primary-500 focus:ring-primary-500 disabled:cursor-not-allowed disabled:bg-gray-100"
                  >
                    {VALID_ROLES.map((r) => (
                      <option key={r.value} value={r.value}>
                        {r.label}
                      </option>
                    ))}
                  </select>
                  {editForm.id === user?.id && (
                    <p className="mt-1 text-xs text-gray-500">Você não pode alterar sua própria role.</p>
                  )}
                </div>
                <div className="flex items-end">
                  <label className="inline-flex items-center gap-2 text-sm text-gray-700">
                    <input
                      type="checkbox"
                      checked={editForm.is_active}
                      onChange={(e) => setEditForm((p) => ({ ...p, is_active: e.target.checked }))}
                      className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                    Usuário ativo
                  </label>
                </div>
              </div>

              {resetTempPassword && (
                <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-amber-900">Nova senha temporária</p>
                      <p className="mt-1 font-mono text-sm text-amber-900">{resetTempPassword}</p>
                      <p className="mt-1 text-xs text-amber-800">O usuário deverá trocar no próximo login.</p>
                    </div>
                    <button
                      onClick={() => copyToClipboard(resetTempPassword)}
                      className="rounded-lg bg-amber-600 px-3 py-2 text-xs font-medium text-white hover:bg-amber-700"
                    >
                      Copiar
                    </button>
                  </div>
                </div>
              )}
            </div>

            <div className="flex flex-col gap-3 border-t border-gray-200 bg-gray-50 p-6 sm:flex-row">
              <button
                onClick={() => setShowEditModal(false)}
                className="flex-1 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                onClick={resetPassword}
                disabled={updating}
                className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg bg-amber-600 px-4 py-2 text-sm font-medium text-white hover:bg-amber-700 disabled:opacity-50"
              >
                <KeyRound className="h-4 w-4" />
                {updating ? 'Aguarde...' : 'Resetar senha'}
              </button>
              <button
                onClick={updateUser}
                disabled={updating}
                className="flex-1 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
              >
                {updating ? 'Salvando...' : 'Salvar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </FlowbiteLayout>
  )
}
