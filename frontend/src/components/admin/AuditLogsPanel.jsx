/**
 * Painel de Logs de Auditoria para Admin
 */

import { useMemo, useState, useEffect } from 'react'
import { apiRequest } from '../../utils/api'

export default function AuditLogsPanel() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all') // all, admin, operator, system
  const [counts, setCounts] = useState({ all: 0, admin: 0, operator: 0, system: 0 })
  const [total, setTotal] = useState(0)
  const [selectedLogId, setSelectedLogId] = useState(null)
  const [selectedLog, setSelectedLog] = useState(null)
  const [detailsLoading, setDetailsLoading] = useState(false)
  const [detailsError, setDetailsError] = useState('')

  useEffect(() => {
    fetchLogs()
  }, [])

  const fetchLogs = async () => {
    try {
      setLoading(true)
      // Preferir endpoint com contagens
      try {
        const data = await apiRequest('audit-logs/summary')
        const items = Array.isArray(data?.items) ? data.items : []
        setLogs(items)
        setCounts(data?.counts || { all: items.length, admin: 0, operator: 0, system: 0 })
        setTotal(typeof data?.total === 'number' ? data.total : items.length)
      } catch (e) {
        // Fallback: endpoint legado
        const items = await apiRequest('audit-logs')
        setLogs(Array.isArray(items) ? items : [])
        const safeItems = Array.isArray(items) ? items : []
        setCounts({ all: safeItems.length, admin: 0, operator: 0, system: 0 })
        setTotal(safeItems.length)
      }
    } catch (error) {
      console.error('Erro ao buscar logs:', error)
      // Sem dados de mock - mostrar array vazio
      setLogs([])
      setCounts({ all: 0, admin: 0, operator: 0, system: 0 })
      setTotal(0)
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
      'PASSWORD_RESET': 'Senha Resetada',
      'DELIVERY_CREATE': 'Entrega Criada',
      'DELIVERY_UPDATE': 'Entrega Atualizada',
      'STATUS_CHANGE': 'Mudança de Status',
      'CONFIG_CHANGE': 'Configuração Alterada',
      'DEBUG_SIMULATE_MESSAGE': 'Simulação de Mensagem (Debug)',
      'DEBUG_RESET_CONTEXT': 'Reset de Contexto (Debug)',
      'DEBUG_CREATE_FAKE_ORDER': 'Criar Pedido Fake (Debug)',
      'DEBUG_REEXECUTE_STATE_MACHINE': 'Reexecutar State Machine (Debug)',
      'DEBUG_RAISE_ERROR': 'Forçar Erro (Debug)',
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
      blue: 'bg-blue-100 dark:bg-blue-900/30 text-blue-800',
      purple: 'bg-purple-100 text-purple-800',
      green: 'bg-green-100 dark:bg-green-900/30 text-green-800',
      yellow: 'bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-400',
      indigo: 'bg-indigo-100 text-indigo-800',
      orange: 'bg-orange-100 text-orange-800',
      red: 'bg-red-100 dark:bg-red-900/30 text-red-800',
    }
    return map[color] || 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-100'
  }

  const displayedLogs = useMemo(() => {
    const items = Array.isArray(logs) ? logs : []
    if (filter === 'all') return items
    const getCategory = (l) => {
      if (l?.category) return l.category
      if (!l?.user_id) return 'system'
      return l?.user_role === 'admin' || l?.user_role === 'owner' ? 'admin' : 'operator'
    }
    return items.filter((l) => getCategory(l) === filter)
  }, [logs, filter])

  const openLog = async (log) => {
    try {
      setSelectedLogId(log.id)
      setSelectedLog(null)
      setDetailsError('')
      setDetailsLoading(true)
      const data = await apiRequest(`audit-logs/${log.id}`)
      setSelectedLog(data)
    } catch (e) {
      setDetailsError(e.message || 'Erro ao carregar detalhes')
    } finally {
      setDetailsLoading(false)
    }
  }

  const closeModal = () => {
    setSelectedLogId(null)
    setSelectedLog(null)
    setDetailsError('')
    setDetailsLoading(false)
  }

  if (loading) {
    return (
      <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-8 text-center shadow-sm">
        <div className="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-gray-200 dark:border-gray-700 border-t-primary-600" />
        <p className="mt-3 text-sm text-gray-600 dark:text-gray-400">Carregando logs...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">Logs de auditoria</h2>
          <p className="text-sm text-gray-600 dark:text-gray-400">Histórico de ações no sistema</p>
        </div>
        <button
          onClick={fetchLogs}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
        >
          Atualizar
        </button>
      </div>

      {/* Filtros */}
      <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 shadow-sm">
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setFilter('all')}
            className={`rounded-lg px-3 py-2 text-sm font-medium ${
              filter === 'all' ? 'bg-primary-600 text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200'
            }`}
          >
            Todos ({counts.all ?? total ?? logs.length})
          </button>
          <button
            onClick={() => setFilter('admin')}
            className={`rounded-lg px-3 py-2 text-sm font-medium ${
              filter === 'admin' ? 'bg-primary-600 text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200'
            }`}
          >
            Admin ({counts.admin ?? 0})
          </button>
          <button
            onClick={() => setFilter('operator')}
            className={`rounded-lg px-3 py-2 text-sm font-medium ${
              filter === 'operator' ? 'bg-primary-600 text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200'
            }`}
          >
            Operador ({counts.operator ?? 0})
          </button>
          <button
            onClick={() => setFilter('system')}
            className={`rounded-lg px-3 py-2 text-sm font-medium ${
              filter === 'system' ? 'bg-primary-600 text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200'
            }`}
          >
            Sistema ({counts.system ?? 0})
          </button>
        </div>
      </div>

      {/* Timeline de Logs */}
      <div className="overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm">
        <div className="border-b border-gray-200 dark:border-gray-700 p-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Exibindo {displayedLogs.length} registro(s){total ? ` (de ${total})` : ''}
          </p>
        </div>
        
        <div className="divide-y max-h-[600px] overflow-y-auto">
          {displayedLogs.length === 0 ? (
            <div className="p-10 text-center">
              <p className="text-base font-medium text-gray-900 dark:text-white">Nenhum log disponível</p>
              <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                Os logs de auditoria serão exibidos aqui quando houver atividade no sistema
              </p>
            </div>
          ) : displayedLogs.map((log) => (
            <button
              type="button"
              key={log.id}
              onClick={() => openLog(log)}
              className="w-full text-left p-4 hover:bg-gray-50 dark:hover:bg-gray-700 transition"
            >
              <div className="flex items-start gap-4">
                {/* Ícone */}
                <div className="flex-shrink-0 grid h-10 w-10 place-items-center rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
                  {/* Ícone simples */}
                  <span className="text-xs font-semibold">{(log.action || '').slice(0, 2)}</span>
                </div>

                {/* Conteúdo */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <p className="font-semibold text-gray-900 dark:text-white">
                        {getActionLabel(log.action)}
                      </p>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                        {log.details}
                      </p>
                      <div className="flex flex-wrap items-center gap-4 mt-2 text-xs text-gray-500 dark:text-gray-400">
                        <span>{log.user_email || (log.user_id ? `user_id=${log.user_id}` : 'Sistema')}</span>
                        <span>{log.ip_address || '-'}</span>
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
            </button>
          ))}
        </div>
      </div>

      {/* Estatísticas Rápidas */}
      {logs.length > 0 && (
      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 text-center shadow-sm">
          <p className="text-3xl font-semibold text-gray-900 dark:text-white">{logs.filter(l => l.action === 'LOGIN').length}</p>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">Logins</p>
        </div>
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 text-center shadow-sm">
          <p className="text-3xl font-semibold text-gray-900 dark:text-white">{logs.filter(l => l.action === 'ROLE_CHANGE').length}</p>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">Mudanças de role</p>
        </div>
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 text-center shadow-sm">
          <p className="text-3xl font-semibold text-gray-900 dark:text-white">{logs.filter(l => l.action === 'USER_CREATE').length}</p>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">Usuários criados</p>
        </div>
      </div>
      )}

      {/* Modal de detalhes */}
      {selectedLogId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onMouseDown={closeModal}>
          <div
            className="w-full max-w-2xl rounded-lg bg-white dark:bg-gray-800 shadow-lg"
            onMouseDown={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 p-4">
              <div>
                <div className="text-sm text-gray-500 dark:text-gray-400">Detalhes do log</div>
                <div className="text-lg font-semibold text-gray-900 dark:text-white">
                  {selectedLog ? getActionLabel(selectedLog.action) : 'Carregando...'}
                </div>
              </div>
              <button
                type="button"
                onClick={closeModal}
                className="rounded-lg px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
              >
                Fechar
              </button>
            </div>

            <div className="p-4">
              {detailsLoading && (
                <div className="text-sm text-gray-600 dark:text-gray-400">Carregando detalhes...</div>
              )}
              {detailsError && (
                <div className="rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 p-3 text-sm text-red-700 dark:text-red-400">
                  {detailsError}
                </div>
              )}

              {selectedLog && (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700 p-3">
                      <div className="text-xs text-gray-500 dark:text-gray-400">Ação</div>
                      <div className="mt-1 font-medium text-gray-900 dark:text-white">{selectedLog.action}</div>
                    </div>
                    <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700 p-3">
                      <div className="text-xs text-gray-500 dark:text-gray-400">Quando</div>
                      <div className="mt-1 font-medium text-gray-900 dark:text-white">
                        {new Date(selectedLog.timestamp).toLocaleString('pt-BR')}
                      </div>
                    </div>
                    <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700 p-3">
                      <div className="text-xs text-gray-500 dark:text-gray-400">Quem</div>
                      <div className="mt-1 font-medium text-gray-900 dark:text-white">
                        {selectedLog.user_email || 'Sistema'}
                      </div>
                      <div className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                        {selectedLog.user_role ? `role=${selectedLog.user_role}` : ''}{selectedLog.user_id ? ` user_id=${selectedLog.user_id}` : ''}
                      </div>
                    </div>
                    <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700 p-3">
                      <div className="text-xs text-gray-500 dark:text-gray-400">IP / Navegador</div>
                      <div className="mt-1 text-sm text-gray-900 dark:text-white break-words">
                        <div><span className="font-medium">IP:</span> {selectedLog.ip_address || '-'}</div>
                        <div className="mt-1"><span className="font-medium">UA:</span> {selectedLog.user_agent || '-'}</div>
                      </div>
                    </div>
                  </div>

                  <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-3">
                    <div className="text-xs text-gray-500 dark:text-gray-400">Detalhes</div>
                    <div className="mt-1 text-sm text-gray-900 dark:text-white whitespace-pre-wrap break-words">
                      {selectedLog.details || '-'}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
