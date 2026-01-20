import { useState, useEffect } from 'react'
import { useAuth } from '../../hooks/useAuth'

export default function AdminDashboard() {
  const { user, logout } = useAuth()
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedUser, setSelectedUser] = useState(null)
  const [newRole, setNewRole] = useState('')

  useEffect(() => {
    fetchUsers()
  }, [])

  const fetchUsers = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/users', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })
      if (response.ok) {
        const data = await response.json()
        setUsers(data)
      }
    } catch (error) {
      console.error('Erro ao buscar usuários:', error)
    } finally {
      setLoading(false)
    }
  }

  const updateUserRole = async () => {
    if (!selectedUser || !newRole) return

    try {
      const response = await fetch(`http://localhost:8000/api/users/${selectedUser.id}/role`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ role: newRole })
      })

      if (response.ok) {
        alert('Role atualizada com sucesso!')
        setSelectedUser(null)
        setNewRole('')
        fetchUsers()
      }
    } catch (error) {
      console.error('Erro ao atualizar role:', error)
      alert('Erro ao atualizar role')
    }
  }

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <div className="w-64 bg-white shadow-lg">
        <div className="p-6 border-b">
          <h1 className="text-xl font-bold text-gray-800">Gas Automation</h1>
          <p className="text-sm text-gray-500">Painel do Admin</p>
        </div>
        
        <nav className="p-4">
          <div className="space-y-2">
            <button className="w-full text-left px-4 py-3 bg-blue-500 text-white rounded hover:bg-blue-600">
              📊 Dashboard
            </button>
            <button className="w-full text-left px-4 py-3 hover:bg-gray-100 rounded">
              👥 Usuários
            </button>
            <button className="w-full text-left px-4 py-3 hover:bg-gray-100 rounded">
              📋 Relatórios
            </button>
            <button className="w-full text-left px-4 py-3 hover:bg-gray-100 rounded">
              ⚙️ Configurações
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
        <div className="bg-white rounded-lg shadow">
          <div className="p-6 border-b">
            <h2 className="text-lg font-semibold text-gray-800">Gerenciar Usuários</h2>
            <p className="text-sm text-gray-500">Atribuir roles e permissões aos usuários</p>
          </div>

          {loading ? (
            <div className="p-6">
              <p className="text-gray-500">Carregando usuários...</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Email</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Nome</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Role Atual</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Ações</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {users.map(u => (
                    <tr key={u.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 text-sm text-gray-800">{u.email}</td>
                      <td className="px-6 py-4 text-sm text-gray-800">{u.full_name || u.username}</td>
                      <td className="px-6 py-4 text-sm">
                        <span className={`px-3 py-1 rounded-full text-xs font-semibold
                          ${u.role === 'admin' ? 'bg-red-100 text-red-800' : 
                            u.role === 'operator' ? 'bg-blue-100 text-blue-800' : 
                            'bg-gray-100 text-gray-800'}`}>
                          {u.role}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm">
                        <button 
                          onClick={() => setSelectedUser(u)}
                          className="px-3 py-1 bg-blue-500 text-white rounded text-xs hover:bg-blue-600"
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

        {/* Modal para editar role */}
        {selectedUser && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-lg p-6 w-96">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">
                Alterar Role - {selectedUser.email}
              </h3>

              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Nova Role
                </label>
                <select 
                  value={newRole} 
                  onChange={(e) => setNewRole(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Selecione uma role</option>
                  <option value="admin">Admin</option>
                  <option value="operator">Operador</option>
                  <option value="owner">Proprietário</option>
                  <option value="user">Usuário</option>
                </select>
              </div>

              <div className="flex gap-3">
                <button 
                  onClick={() => setSelectedUser(null)}
                  className="flex-1 px-4 py-2 bg-gray-300 text-gray-800 rounded hover:bg-gray-400"
                >
                  Cancelar
                </button>
                <button 
                  onClick={updateUserRole}
                  className="flex-1 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                >
                  Salvar
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
