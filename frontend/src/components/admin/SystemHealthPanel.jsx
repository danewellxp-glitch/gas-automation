import { useEffect, useMemo, useState } from 'react'
import { Activity, RefreshCcw, Server, Database, MessageSquare, RotateCw, AlertCircle, CheckCircle2, XCircle } from 'lucide-react'
import { apiRequest } from '../../utils/api'

function Badge({ status }) {
  const s = (status || '').toLowerCase()
  const cls =
    s === 'online' || s === 'healthy'
      ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
      : s === 'not_configured'
      ? 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
      : s === 'degraded'
      ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-400'
      : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
  
  const Icon = s === 'online' || s === 'healthy' 
    ? CheckCircle2 
    : s === 'offline' || s === 'error'
    ? XCircle
    : AlertCircle

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${cls}`}>
      <Icon className="h-3 w-3" />
      {status || '-'}
    </span>
  )
}

function ServiceCard({ service }) {
  const getServiceIcon = (key) => {
    const icons = {
      backend: Server,
      redis: Database,
      postgres: Database,
      waha: MessageSquare,
      firebird_sync: RotateCw,
    }
    return icons[key] || Activity
  }

  const getServiceName = (key) => {
    const names = {
      backend: 'Backend (FastAPI)',
      redis: 'Redis',
      postgres: 'PostgreSQL',
      waha: 'WAHA (WhatsApp)',
      firebird_sync: 'Firebird Sync',
    }
    return names[key] || key
  }

  const Icon = getServiceIcon(service.key)
  const serviceName = getServiceName(service.key)

  const renderServiceDetails = () => {
    switch (service.key) {
      case 'backend':
        return (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <span>API respondendo normalmente</span>
            </div>
          </div>
        )

      case 'redis':
        return (
          <div className="space-y-2">
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-lg bg-gray-50 dark:bg-gray-700 p-3">
                <div className="text-xs text-gray-500 dark:text-gray-400">Latência</div>
                <div className="text-lg font-semibold text-gray-900 dark:text-white">
                  {service.latency_ms ? `${service.latency_ms.toFixed(2)}ms` : '-'}
                </div>
              </div>
              <div className="rounded-lg bg-gray-50 dark:bg-gray-700 p-3">
                <div className="text-xs text-gray-500 dark:text-gray-400">Memória</div>
                <div className="text-lg font-semibold text-gray-900 dark:text-white">
                  {service.used_memory_human || '-'}
                </div>
              </div>
            </div>
            {service.connected_clients !== undefined && (
              <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                <span className="font-medium">Clientes conectados:</span>
                <span className="rounded-full bg-blue-100 dark:bg-blue-900/30 px-2 py-0.5 text-xs font-medium text-blue-700 dark:text-blue-400">
                  {service.connected_clients}
                </span>
              </div>
            )}
          </div>
        )

      case 'postgres':
        return (
          <div className="space-y-2">
            <div className="rounded-lg bg-gray-50 dark:bg-gray-700 p-3">
              <div className="text-xs text-gray-500 dark:text-gray-400">Conexões ativas</div>
              <div className="text-lg font-semibold text-gray-900 dark:text-white">
                {service.active_connections !== undefined ? service.active_connections : '-'}
              </div>
            </div>
            <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <span>Banco de dados operacional</span>
            </div>
          </div>
        )

      case 'waha':
        const sessionStatus = service.session?.status || 'UNKNOWN'
        const isConnected = sessionStatus === 'WORKING' || sessionStatus === 'STARTING'
        return (
          <div className="space-y-2">
            <div className="rounded-lg bg-gray-50 dark:bg-gray-700 p-3">
              <div className="text-xs text-gray-500 dark:text-gray-400">Status da sessão</div>
              <div className="mt-1 flex items-center gap-2">
                <span className={`text-sm font-medium ${
                  isConnected ? 'text-green-700 dark:text-green-400' : 'text-gray-700 dark:text-gray-300'
                }`}>
                  {sessionStatus}
                </span>
                {service.session?.name && (
                  <span className="rounded-full bg-blue-100 dark:bg-blue-900/30 px-2 py-0.5 text-xs text-blue-700 dark:text-blue-400">
                    {service.session.name}
                  </span>
                )}
              </div>
            </div>
            {service.qr_code_base64 && (
              <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-3">
                <div className="text-xs text-gray-500 dark:text-gray-400 mb-2">QR Code para conexão</div>
                <img 
                  src={`data:image/png;base64,${service.qr_code_base64}`} 
                  alt="QR Code WhatsApp"
                  className="mx-auto h-32 w-32"
                />
              </div>
            )}
            {!isConnected && !service.qr_code_base64 && (
              <div className="flex items-center gap-2 text-sm text-amber-600">
                <AlertCircle className="h-4 w-4" />
                <span>Sessão desconectada</span>
              </div>
            )}
          </div>
        )

      case 'firebird_sync':
        return (
          <div className="space-y-2">
            {service.error ? (
              <div className="rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 p-3">
                <div className="flex items-start gap-2">
                  <XCircle className="h-4 w-4 text-red-600 mt-0.5 flex-shrink-0" />
                  <div className="flex-1">
                    <div className="text-xs font-medium text-red-800">Erro de conexão</div>
                    <div className="mt-1 text-xs text-red-600">{service.error}</div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                <CheckCircle2 className="h-4 w-4 text-green-600" />
                <span>Serviço de sincronização operacional</span>
              </div>
            )}
          </div>
        )

      default:
        return null
    }
  }

  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5 shadow-sm hover:shadow-md transition-shadow">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`rounded-lg p-2 ${
            service.status === 'online' || service.status === 'healthy'
              ? 'bg-green-50 dark:bg-green-900/20 text-green-600'
              : service.status === 'offline' || service.status === 'error'
              ? 'bg-red-50 dark:bg-red-900/20 text-red-600'
              : service.status === 'not_configured'
              ? 'bg-gray-50 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
              : 'bg-amber-50 dark:bg-amber-900/20 text-amber-600'
          }`}>
            <Icon className="h-5 w-5" />
          </div>
          <div>
            <div className="font-semibold text-gray-900 dark:text-white">{serviceName}</div>
            <div className="text-xs text-gray-500 dark:text-gray-400 capitalize">{service.key}</div>
          </div>
        </div>
        <Badge status={service.status} />
      </div>
      {renderServiceDetails()}
    </div>
  )
}

export default function SystemHealthPanel() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [data, setData] = useState(null)

  const fetchHealth = async () => {
    try {
      setLoading(true)
      setError('')
      const res = await apiRequest('admin/system-health')
      setData(res)
    } catch (e) {
      setError(e.message || 'Erro ao carregar system health')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchHealth()
    const t = setInterval(fetchHealth, 15000)
    return () => clearInterval(t)
  }, [])

  const services = useMemo(() => {
    const s = data?.services || {}
    return Object.entries(s).map(([key, value]) => ({ key, ...value }))
  }, [data])

  const overallStatus = data?.status || 'unknown'
  const onlineCount = services.filter(s => s.status === 'online' || s.status === 'healthy').length
  const totalCount = services.length

  return (
    <div>
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">System Health</h2>
          <p className="text-gray-600 dark:text-gray-400">Status em tempo real dos serviços críticos</p>
        </div>
        <button
          onClick={fetchHealth}
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 dark:text-white dark:placeholder-gray-400 px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <RefreshCcw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Atualizar
        </button>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 p-4 text-sm text-red-700 dark:text-red-400">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5" />
            <span>{error}</span>
          </div>
        </div>
      )}

      {loading && !data ? (
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-8 text-center shadow-sm">
          <div className="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-gray-200 dark:border-gray-700 border-t-primary-600" />
          <p className="mt-3 text-sm text-gray-600 dark:text-gray-400">Carregando status...</p>
        </div>
      ) : (
        <>
          {/* Status geral */}
          <div className="mb-6 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 shadow-sm">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className={`rounded-lg p-3 ${
                  overallStatus === 'healthy' || overallStatus === 'online'
                    ? 'bg-green-50 dark:bg-green-900/20 text-green-600'
                    : overallStatus === 'degraded'
                    ? 'bg-amber-50 dark:bg-amber-900/20 text-amber-600'
                    : 'bg-red-50 dark:bg-red-900/20 text-red-600'
                }`}>
                  <Activity className="h-6 w-6" />
                </div>
                <div>
                  <div className="text-lg font-semibold text-gray-900 dark:text-white">Status geral do sistema</div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    {onlineCount} de {totalCount} serviços operacionais
                    {data?.timestamp && (
                      <span className="ml-2">
                        • Última atualização: {new Date(data.timestamp).toLocaleTimeString()}
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <Badge status={overallStatus} />
            </div>
          </div>

          {/* Cards dos serviços */}
          <div className="grid gap-4 lg:grid-cols-2">
            {services.map((service) => (
              <ServiceCard key={service.key} service={service} />
            ))}
          </div>
        </>
      )}
    </div>
  )
}

