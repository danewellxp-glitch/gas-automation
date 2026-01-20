import { useState, useEffect } from 'react'
import { useAuth } from '../../hooks/useAuth'

export default function OperatorDashboard() {
  const { user, logout } = useAuth()
  const [conversations, setConversations] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchConversations()
  }, [])

  const fetchConversations = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/conversations', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })
      if (response.ok) {
        const data = await response.json()
        setConversations(data)
      }
    } catch (error) {
      console.error('Erro ao buscar conversas:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <div className="w-64 bg-white shadow-lg">
        <div className="p-6 border-b">
          <h1 className="text-xl font-bold text-gray-800">Gas Automation</h1>
          <p className="text-sm text-gray-500">Painel do Operador</p>
        </div>
        
        <nav className="p-4">
          <div className="space-y-2">
            <button className="w-full text-left px-4 py-3 bg-blue-500 text-white rounded hover:bg-blue-600">
              📊 Dashboard
            </button>
            <button className="w-full text-left px-4 py-3 hover:bg-gray-100 rounded">
              💬 Conversas
            </button>
            <button className="w-full text-left px-4 py-3 hover:bg-gray-100 rounded">
              📦 Pedidos
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
        <div className="grid grid-cols-3 gap-6 mb-8">
          {/* Card 1 */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-gray-500 text-sm font-semibold mb-2">Conversas Ativas</h3>
            <p className="text-3xl font-bold text-gray-800">{conversations.length}</p>
          </div>

          {/* Card 2 */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-gray-500 text-sm font-semibold mb-2">Pedidos Hoje</h3>
            <p className="text-3xl font-bold text-blue-600">0</p>
          </div>

          {/* Card 3 */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-gray-500 text-sm font-semibold mb-2">Taxa de Resolução</h3>
            <p className="text-3xl font-bold text-green-600">0%</p>
          </div>
        </div>

        {/* Conversas */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-6 border-b">
            <h2 className="text-lg font-semibold text-gray-800">Conversas Recentes</h2>
          </div>
          <div className="p-6">
            {loading ? (
              <p className="text-gray-500">Carregando...</p>
            ) : conversations.length === 0 ? (
              <p className="text-gray-500 text-center py-8">Nenhuma conversa ativa</p>
            ) : (
              <div className="space-y-4">
                {conversations.map(conv => (
                  <div key={conv.id} className="border-l-4 border-blue-500 pl-4 py-2">
                    <p className="font-semibold text-gray-800">{conv.name || conv.customer_number}</p>
                    <p className="text-sm text-gray-500">{conv.status}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
