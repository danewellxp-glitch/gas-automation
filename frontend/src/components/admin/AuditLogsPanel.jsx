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

  const getBadge = (color) => {
    const map = {
      blue: 'bg-blue-100 text-blue-800',
      purple: 'bg-purple-100 text-purple-800',
      green: 'bg-green-100 text-green-800',
      yellow: 'bg-amber-100 text-amber-800',
      indigo: 'bg-indigo-100 text-indigo-800',
      orange: 'bg-orange-100 text-orange-800',
      red: 'bg-red-100 text-red-800',
    }
    return map[color] || 'bg-gray-100 text-gray-800'
  }

  if (loading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-8 text-center shadow-sm">
        <div className="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-gray-200 border-t-primary-600" />
        <p className="mt-3 text-sm text-gray-600">Carregando logs...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-gray-900">Logs de auditoria</h2>
          <p className="text-sm text-gray-600">Histórico de ações no sistema</p>
        </div>
        <button
          onClick={fetchLogs}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
        >
          Atualizar
        </button>
      </div>

      {/* Filtros */}
      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setFilter('all')}
            className={`rounded-lg px-3 py-2 text-sm font-medium ${
              filter === 'all' ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Todos ({logs.length})
          </button>
          <button
            onClick={() => setFilter('admin')}
            className={`rounded-lg px-3 py-2 text-sm font-medium ${
              filter === 'admin' ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Admin
          </button>
          <button
            onClick={() => setFilter('operator')}
            className={`rounded-lg px-3 py-2 text-sm font-medium ${
              filter === 'operator' ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Operador
          </button>
          <button
            onClick={() => setFilter('system')}
            className={`rounded-lg px-3 py-2 text-sm font-medium ${
              filter === 'system' ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Sistema
          </button>
        </div>
      </div>

      {/* Timeline de Logs */}
      <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
        <div className="border-b border-gray-200 p-4">
          <p className="text-sm text-gray-600">
            Exibindo {logs.length} registro(s)
          </p>
        </div>
        
        <div className="divide-y max-h-[600px] overflow-y-auto">
          {logs.length === 0 ? (
            <div className="p-10 text-center">
              <p className="text-base font-medium text-gray-900">Nenhum log disponível</p>
              <p className="mt-1 text-sm text-gray-600">
                Os logs de auditoria serão exibidos aqui quando houver atividade no sistema
              </p>
            </div>
          ) : logs.map((log) => (
            <div key={log.id} className="p-4 hover:bg-gray-50 transition">
              <div className="flex items-start gap-4">
                {/* Ícone */}
                <div className="flex-shrink-0 grid h-10 w-10 place-items-center rounded-lg bg-gray-100 text-gray-700">
                  {log.icon || ''}
                </div>

                {/* Conteúdo */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <p className="font-semibold text-gray-900">
                        {getActionLabel(log.action)}
                      </p>
                      <p className="text-sm text-gray-600 mt-1">
                        {log.details}
                      </p>
                      <div className="flex flex-wrap items-center gap-4 mt-2 text-xs text-gray-500">
                        <span>{log.user}</span>
                        <span>{log.ip}</span>
                        <span>{formatTime(log.timestamp)}</span>
                      </div>
                    </div>
                    
                    {/* Badge do tipo */}
                    <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${getBadge(log.color)}`}>
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
        <div className="rounded-lg border border-gray-200 bg-white p-4 text-center shadow-sm">
          <p className="text-3xl font-semibold text-gray-900">{logs.filter(l => l.action === 'LOGIN').length}</p>
          <p className="text-sm text-gray-600 mt-1">Logins</p>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4 text-center shadow-sm">
          <p className="text-3xl font-semibold text-gray-900">{logs.filter(l => l.action === 'ROLE_CHANGE').length}</p>
          <p className="text-sm text-gray-600 mt-1">Mudanças de role</p>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4 text-center shadow-sm">
          <p className="text-3xl font-semibold text-gray-900">{logs.filter(l => l.action === 'USER_CREATE').length}</p>
          <p className="text-sm text-gray-600 mt-1">Usuários criados</p>
        </div>
      </div>
      )}
    </div>
  )
}
