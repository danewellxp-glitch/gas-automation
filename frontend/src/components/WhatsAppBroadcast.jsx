import { useState, useEffect } from 'react'
import { Send, Users, Loader2, CheckCircle2, XCircle, AlertCircle } from 'lucide-react'
import { apiRequest } from '../utils/api'

export default function WhatsAppBroadcast() {
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [stats, setStats] = useState({
    all: 0,
    last_week: 0,
    last_month: 0,
  })
  const [loadingStats, setLoadingStats] = useState(true)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchStats()
  }, [])

  const fetchStats = async () => {
    try {
      setLoadingStats(true)
      const data = await apiRequest('whatsapp/broadcast/stats')
      setStats(data)
    } catch (err) {
      console.error('Erro ao buscar estatísticas:', err)
    } finally {
      setLoadingStats(false)
    }
  }

  const handleBroadcast = async (filterType) => {
    if (!message.trim()) {
      setError('Por favor, digite uma mensagem')
      return
    }

    try {
      setLoading(true)
      setError('')
      setResult(null)

      const response = await apiRequest('whatsapp/broadcast', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: message.trim(),
          filter_type: filterType,
        }),
      })

      setResult(response)
      
      // Atualizar estatísticas após envio
      await fetchStats()
      
    } catch (err) {
      console.error('Erro ao disparar mensagens:', err)
      setError(err.message || 'Erro ao enviar mensagens')
    } finally {
      setLoading(false)
    }
  }

  const getFilterLabel = (filterType) => {
    const labels = {
      all: 'Todos os Clientes',
      last_week: 'Última Semana',
      last_month: 'Último Mês',
    }
    return labels[filterType] || filterType
  }

  const getFilterCount = (filterType) => {
    return stats[filterType] || 0
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2 dark:text-white">
          Disparo de Mensagens WhatsApp
        </h2>
        <p className="text-gray-600 dark:text-gray-400">
          Envie mensagens em massa para seus clientes via WhatsApp
        </p>
      </div>

      {/* Campo de Mensagem */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6 dark:bg-gray-800 dark:border-gray-700">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Mensagem
        </label>
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Digite sua mensagem aqui..."
          rows={6}
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none dark:bg-gray-700 dark:border-gray-600 dark:text-white dark:placeholder-gray-400"
          disabled={loading}
        />
        <div className="mt-2 text-sm text-gray-500 dark:text-gray-400">
          {message.length} caracteres
        </div>
      </div>

      {/* Estatísticas */}
      {loadingStats ? (
        <div className="flex items-center justify-center py-4">
          <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
          <span className="ml-2 text-gray-600">Carregando estatísticas...</span>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 dark:bg-gray-800 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Todos os Clientes</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats.all}</p>
              </div>
              <Users className="w-8 h-8 text-blue-500" />
            </div>
          </div>
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 dark:bg-gray-800 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Última Semana</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats.last_week}</p>
              </div>
              <Users className="w-8 h-8 text-green-500" />
            </div>
          </div>
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 dark:bg-gray-800 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Último Mês</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats.last_month}</p>
              </div>
              <Users className="w-8 h-8 text-purple-500" />
            </div>
          </div>
        </div>
      )}

      {/* Botões de Disparo */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <button
          onClick={() => handleBroadcast('all')}
          disabled={loading || !message.trim()}
          className="flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium"
        >
          {loading ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Send className="w-5 h-5" />
          )}
          <span>Enviar para Todos ({getFilterCount('all')})</span>
        </button>

        <button
          onClick={() => handleBroadcast('last_week')}
          disabled={loading || !message.trim()}
          className="flex items-center justify-center gap-2 px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium"
        >
          {loading ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Send className="w-5 h-5" />
          )}
          <span>Última Semana ({getFilterCount('last_week')})</span>
        </button>

        <button
          onClick={() => handleBroadcast('last_month')}
          disabled={loading || !message.trim()}
          className="flex items-center justify-center gap-2 px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium"
        >
          {loading ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Send className="w-5 h-5" />
          )}
          <span>Último Mês ({getFilterCount('last_month')})</span>
        </button>
      </div>

      {/* Mensagem de Erro */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
          <XCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-red-800">Erro</p>
            <p className="text-sm text-red-600">{error}</p>
          </div>
        </div>
      )}

      {/* Resultado */}
      {result && (
        <div className={`p-4 rounded-lg border ${
          result.success 
            ? 'bg-green-50 border-green-200' 
            : 'bg-yellow-50 border-yellow-200'
        }`}>
          <div className="flex items-start gap-3">
            {result.success ? (
              <CheckCircle2 className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
            ) : (
              <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
            )}
            <div className="flex-1">
              <p className={`font-medium ${
                result.success ? 'text-green-800' : 'text-yellow-800'
              }`}>
                {result.message}
              </p>
              <div className="mt-2 text-sm space-y-1">
                <p className={result.success ? 'text-green-700' : 'text-yellow-700'}>
                  Total de clientes: {result.total_customers}
                </p>
                <p className="text-green-700">
                  ✓ Enviadas: {result.sent}
                </p>
                {result.failed > 0 && (
                  <p className="text-red-700">
                    ✗ Falhas: {result.failed}
                  </p>
                )}
                {result.errors && result.errors.length > 0 && (
                  <details className="mt-2">
                    <summary className="cursor-pointer text-sm font-medium">
                      Ver erros ({result.errors.length})
                    </summary>
                    <ul className="mt-2 space-y-1 text-xs">
                      {result.errors.map((err, idx) => (
                        <li key={idx} className="text-red-600">
                          {err.phone}: {err.error}
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}