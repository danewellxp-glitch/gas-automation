/**
 * Painel de Logs de Auditoria para Admin
 */

import { useState, useEffect } from 'react'

export default function AuditLogsPanel() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all') // all, admin, operator, system

  useEffect(() => {
    fetchLogs()
  }, [])

  const fetchLogs = async () => {
    try {
      setLoading(true)
      const response = await fetch('http://192.168.10.156:8000/api/audit-logs', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        setLogs(data)
      } else {
        // Se não houver endpoint, mostrar array vazio
        setLogs([])
      }
    } catch (error) {
      console.error('Erro ao buscar logs:', error)
      // Sem dados de mock - mostrar array vazio
      setLogs([])
    } finally {
      setLoading(false)
    }
  }

  const getActionLabel = (action) => {
    const labels = {
      'LOGIN': 'Login',
      'LOGOUT': 'Logout',
      'ROLE_CHANGE': 'Mudança de Role',
      'USER_CREATE': 'Usuário Criado',
      'USER_UPDATE': 'Usuário Atualizado',
      'USER_DELETE': 'Usuário Removido',
      'DELIVERY_CREATE': 'Entrega Criada',
      'DELIVERY_UPDATE': 'Entrega Atualizada',
      'STATUS_CHANGE': 'Mudança de Status',
      'CONFIG_CHANGE': 'Configuração Alterada'
    }
    return labels[action] || action
  }

  const formatTime = (isoString) => {
    const date = new Date(isoString)
    const now = new Date()
    const diff = Math.floor((now - date) / 1000) // segundos

    if (diff < 60) return 'Agora mesmo'
    if (diff < 3600) return `${Math.floor(diff / 60)} min atrás`
    if (diff < 86400) return `${Math.floor(diff / 3600)}h atrás`
    return date.toLocaleDateString('pt-BR') + ' ' + date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
  }

  const getColorClass = (color) => {
    const colors = {
      blue: 'bg-blue-100 text-blue-800 border-blue-300',
      purple: 'bg-purple-100 text-purple-800 border-purple-300',
      green: 'bg-green-100 text-green-800 border-green-300',
      yellow: 'bg-yellow-100 text-yellow-800 border-yellow-300',
      indigo: 'bg-indigo-100 text-indigo-800 border-indigo-300',
      orange: 'bg-orange-100 text-orange-800 border-orange-300',
      red: 'bg-red-100 text-red-800 border-red-300'
    }
    return colors[color] || colors.blue
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="text-gray-600 mt-4">Carregando logs...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">📋 Logs de Auditoria</h2>
          <p className="text-gray-600">Histórico de ações no sistema</p>
        </div>
        <button
          onClick={fetchLogs}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition"
        >
          🔄 Atualizar
        </button>
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex gap-2">
          <button
            onClick={() => setFilter('all')}
            className={`px-4 py-2 rounded-lg font-medium transition ${
              filter === 'all'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            Todos ({logs.length})
          </button>
          <button
            onClick={() => setFilter('admin')}
            className={`px-4 py-2 rounded-lg font-medium transition ${
              filter === 'admin'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            👑 Admins
          </button>
          <button
            onClick={() => setFilter('operator')}
            className={`px-4 py-2 rounded-lg font-medium transition ${
              filter === 'operator'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            👤 Operadores
          </button>
          <button
            onClick={() => setFilter('system')}
            className={`px-4 py-2 rounded-lg font-medium transition ${
              filter === 'system'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            ⚙️ Sistema
          </button>
        </div>
      </div>

      {/* Timeline de Logs */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-4 border-b">
          <p className="text-sm text-gray-600">
            Exibindo {logs.length} registro(s)
          </p>
        </div>
        
        <div className="divide-y max-h-[600px] overflow-y-auto">
          {logs.length === 0 ? (
            <div className="p-8 text-center">
              <p className="text-gray-500">📋 Nenhum log de auditoria disponível</p>
              <p className="text-sm text-gray-400 mt-2">
                Os logs de auditoria serão exibidos aqui quando houver atividade no sistema
              </p>
            </div>
          ) : logs.map((log) => (
            <div key={log.id} className="p-4 hover:bg-gray-50 transition">
              <div className="flex items-start gap-4">
                {/* Ícone */}
                <div className={`flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center text-xl border-2 ${getColorClass(log.color)}`}>
                  {log.icon}
                </div>

                {/* Conteúdo */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <p className="font-semibold text-gray-800">
                        {getActionLabel(log.action)}
                      </p>
                      <p className="text-sm text-gray-600 mt-1">
                        {log.details}
                      </p>
                      <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                        <span>👤 {log.user}</span>
                        <span>🌐 {log.ip}</span>
                        <span>🕒 {formatTime(log.timestamp)}</span>
                      </div>
                    </div>
                    
                    {/* Badge do tipo */}
                    <span className={`flex-shrink-0 px-3 py-1 rounded-full text-xs font-medium border ${getColorClass(log.color)}`}>
                      {log.action}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Estatísticas Rápidas */}
      {logs.length > 0 && (
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded-lg shadow p-4 text-center">
          <p className="text-3xl font-bold text-blue-600">{logs.filter(l => l.action === 'LOGIN').length}</p>
          <p className="text-sm text-gray-600 mt-1">Logins hoje</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4 text-center">
          <p className="text-3xl font-bold text-purple-600">{logs.filter(l => l.action === 'ROLE_CHANGE').length}</p>
          <p className="text-sm text-gray-600 mt-1">Mudanças de Role</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4 text-center">
          <p className="text-3xl font-bold text-green-600">{logs.filter(l => l.action === 'USER_CREATE').length}</p>
          <p className="text-sm text-gray-600 mt-1">Usuários Criados</p>
        </div>
      </div>
      )}
    </div>
  )
}
