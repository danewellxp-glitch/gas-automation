/**
 * Operação › Conversas — Visão observacional de conversas WhatsApp
 * Mostra total de conversas, com filtros, e quantas tiveram intervenção humana
 */

import { useState, useEffect } from 'react'
import { MessageCircle, RefreshCw, User, Bot, Filter, AlertCircle, TrendingUp } from 'lucide-react'
import { apiRequest } from '../../utils/api'

const PERIODS = [
  { key: 'day',   label: 'Hoje' },
  { key: 'week',  label: '7 dias' },
  { key: 'month', label: '30 dias' },
]

function StatCard({ label, value, sub, Icon, bg, color }) {
  return (
    <div className={`${bg} border border-gray-200 dark:border-gray-700 rounded-xl p-5`}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">{label}</p>
          <p className={`mt-1.5 text-2xl font-bold ${color}`}>{value}</p>
          {sub && <p className="mt-0.5 text-xs text-gray-400 dark:text-gray-500">{sub}</p>}
        </div>
        <Icon className={`w-5 h-5 shrink-0 mt-0.5 ${color}`} />
      </div>
    </div>
  )
}

export default function OpConversas() {
  const [loading, setLoading] = useState(true)
  const [data, setData]       = useState(null)
  const [sessions, setSessions] = useState([])
  const [period, setPeriod]   = useState('day')
  const [error, setError]     = useState('')
  const [humanFilter, setHumanFilter] = useState('all')

  useEffect(() => { fetchData() }, [period])

  const fetchData = async () => {
    try {
      setLoading(true); setError('')
      // Tenta endpoint específico de conversas
      const res = await apiRequest(`conversations/stats?period=${period}`)
      setData(res)
      setSessions(res?.sessions || res?.conversations || [])
    } catch {
      // Fallback: usa dashboard para estimar
      try {
        const dash = await apiRequest(`owner/dashboard?period=${period}`)
        const orders = dash?.cards?.operational?.orders_today || 0
        // Estimativa: cada pedido = ~1.5 mensagens de conversa
        setData({
          total: Math.round(orders * 1.5) || 0,
          bot_only: Math.round(orders * 0.7) || 0,
          human_intervened: Math.round(orders * 0.3) || 0,
          avg_messages: 8,
          resolution_rate: 85,
        })
        setSessions([])
        setError('Dados estimados com base nos pedidos. Configure o endpoint /conversations/stats para dados exatos.')
      } catch {
        setData({ total: 0, bot_only: 0, human_intervened: 0, avg_messages: 0, resolution_rate: 0 })
        setSessions([])
        setError('Sem dados de conversas disponíveis.')
      }
    } finally { setLoading(false) }
  }

  const filtered = sessions.filter(s => {
    if (humanFilter === 'bot') return !s.human_intervened
    if (humanFilter === 'human') return s.human_intervened
    return true
  })

  const humanRate = data && data.total > 0 ? ((data.human_intervened / data.total) * 100).toFixed(1) : 0

  return (
    <div className="space-y-5">

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Conversas</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Visão observacional do volume de atendimentos WhatsApp</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex bg-gray-100 dark:bg-gray-800 rounded-lg p-0.5 border border-gray-200 dark:border-gray-700">
            {PERIODS.map(({ key, label }) => (
              <button key={key} onClick={() => setPeriod(key)}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${period === key ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}`}>
                {label}
              </button>
            ))}
          </div>
          <button onClick={fetchData} disabled={loading} className="p-1.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-500 hover:bg-gray-50 disabled:opacity-50">
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-start gap-2 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl text-sm text-amber-700 dark:text-amber-400">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" /> {error}
        </div>
      )}

      {/* KPI cards */}
      {loading && !data ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => <div key={i} className="h-28 bg-gray-100 dark:bg-gray-700 rounded-xl animate-pulse" />)}
        </div>
      ) : data && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="Total Conversas" value={data.total} sub={`no período`} Icon={MessageCircle}
            bg="bg-blue-50 dark:bg-blue-900/20" color="text-blue-600 dark:text-blue-400" />
          <StatCard label="Só Bot (IA)" value={data.bot_only} sub={`${data.total > 0 ? ((data.bot_only/data.total)*100).toFixed(0) : 0}% automáticas`}
            Icon={Bot} bg="bg-emerald-50 dark:bg-emerald-900/20" color="text-emerald-600 dark:text-emerald-400" />
          <StatCard label="Com Humano" value={data.human_intervened} sub={`${humanRate}% do total`}
            Icon={User} bg="bg-violet-50 dark:bg-violet-900/20" color="text-violet-600 dark:text-violet-400" />
          <StatCard label="Méd. Mensagens" value={data.avg_messages ?? '—'} sub="por conversa"
            Icon={TrendingUp} bg="bg-white dark:bg-gray-800" color="text-gray-900 dark:text-white" />
        </div>
      )}

      {/* Gauge automação */}
      {data && data.total > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Taxa de Automação</h3>
            <span className="text-sm font-bold text-emerald-600 dark:text-emerald-400">
              {data.total > 0 ? ((data.bot_only / data.total) * 100).toFixed(1) : 0}%
            </span>
          </div>
          <div className="h-3 w-full rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden flex">
            <div
              className="h-full bg-emerald-500 rounded-l-full transition-all duration-700"
              style={{ width: `${data.total > 0 ? (data.bot_only / data.total) * 100 : 0}%` }}
            />
            <div
              className="h-full bg-violet-400"
              style={{ width: `${data.total > 0 ? (data.human_intervened / data.total) * 100 : 0}%` }}
            />
          </div>
          <div className="mt-2 flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" /> Bot apenas ({data.bot_only})</span>
            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-violet-400 inline-block" /> Intervenção humana ({data.human_intervened})</span>
          </div>
        </div>
      )}

      {/* Tabela de sessões se disponível */}
      {sessions.length > 0 && (
        <>
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400 flex items-center gap-1">
              <Filter className="w-3.5 h-3.5" />
            </span>
            {[{ v: 'all', l: 'Todas' }, { v: 'bot', l: 'Só Bot' }, { v: 'human', l: 'Com Humano' }].map(({ v, l }) => (
              <button key={v} onClick={() => setHumanFilter(v)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${humanFilter === v ? 'bg-primary-600 text-white border-primary-600' : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700'}`}>
                {l}
              </button>
            ))}
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50">
                    {['Data', 'Cliente', 'Mensagens', 'Duração', 'Tipo', 'Status'].map(h => (
                      <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                  {filtered.map((s, idx) => (
                    <tr key={s.id || idx} className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                      <td className="px-4 py-3 text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">
                        {s.started_at ? new Date(s.started_at).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—'}
                      </td>
                      <td className="px-4 py-3 text-gray-800 dark:text-gray-200">{s.customer_phone || s.customer_name || '—'}</td>
                      <td className="px-4 py-3 text-gray-600 dark:text-gray-400">{s.message_count ?? '—'}</td>
                      <td className="px-4 py-3 text-gray-600 dark:text-gray-400">{s.duration_minutes ? `${s.duration_minutes}min` : '—'}</td>
                      <td className="px-4 py-3">
                        {s.human_intervened
                          ? <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-violet-50 text-violet-700 dark:bg-violet-900/20 dark:text-violet-400"><User className="w-3 h-3" /> Humano</span>
                          : <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-400"><Bot className="w-3 h-3" /> Bot</span>}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${s.resolved ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-400' : 'bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400'}`}>
                          {s.resolved ? 'Resolvido' : 'Em aberto'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

    </div>
  )
}
