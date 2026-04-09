/**
 * Operação › Online — Motoristas e atendentes online agora
 */

import { useState, useEffect } from 'react'
import { Wifi, WifiOff, RefreshCw, User, Truck, Headphones, Clock } from 'lucide-react'
import { apiRequest } from '../../utils/api'

function timeSince(dateStr) {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'agora'
  if (mins < 60) return `há ${mins}min`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `há ${hrs}h`
  return `há ${Math.floor(hrs / 24)}d`
}

function OnlineCard({ person, type }) {
  const isOnline = person.is_online || person.status === 'online' || person.status === 'available'
  const Icon = type === 'driver' ? Truck : Headphones

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-xl border p-4 transition-colors ${isOnline ? 'border-gray-200 dark:border-gray-700' : 'border-gray-100 dark:border-gray-800 opacity-60'}`}>
      <div className="flex items-start gap-3">
        <div className="relative shrink-0">
          <div className={`w-10 h-10 rounded-full flex items-center justify-center ${isOnline ? (type === 'driver' ? 'bg-blue-50 dark:bg-blue-900/20' : 'bg-violet-50 dark:bg-violet-900/20') : 'bg-gray-100 dark:bg-gray-700'}`}>
            <Icon className={`w-5 h-5 ${isOnline ? (type === 'driver' ? 'text-blue-500' : 'text-violet-500') : 'text-gray-400'}`} />
          </div>
          <span className={`absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 rounded-full border-2 border-white dark:border-gray-800 ${isOnline ? 'bg-green-500' : 'bg-gray-300 dark:bg-gray-600'}`} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <p className="text-sm font-semibold text-gray-800 dark:text-gray-200 truncate">
              {person.name || person.full_name || person.username || '—'}
            </p>
            <span className={`shrink-0 text-xs font-medium px-2 py-0.5 rounded-full ${isOnline ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400' : 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400'}`}>
              {isOnline ? 'Online' : 'Offline'}
            </span>
          </div>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
            {type === 'driver' ? 'Motorista' : 'Atendente'}
            {person.phone && ` · ${person.phone}`}
          </p>
          {person.last_seen && (
            <p className="text-xs text-gray-400 dark:text-gray-500 flex items-center gap-1 mt-0.5">
              <Clock className="w-3 h-3" /> {timeSince(person.last_seen)}
            </p>
          )}
          {type === 'driver' && person.active_deliveries > 0 && (
            <p className="text-xs text-blue-600 dark:text-blue-400 mt-1 font-medium">
              {person.active_deliveries} entrega{person.active_deliveries > 1 ? 's' : ''} ativa{person.active_deliveries > 1 ? 's' : ''}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

export default function OpOnline() {
  const [loading, setLoading]     = useState(true)
  const [drivers, setDrivers]     = useState([])
  const [operators, setOperators] = useState([])
  const [error, setError]         = useState('')
  const [tab, setTab]             = useState('all')

  useEffect(() => {
    fetchData()
    const t = setInterval(fetchData, 30000)
    return () => clearInterval(t)
  }, [])

  const fetchData = async () => {
    try {
      setLoading(true)
      const [driversRes, opsRes] = await Promise.allSettled([
        apiRequest('drivers'),
        apiRequest('users?role=operator'),
      ])
      if (driversRes.status === 'fulfilled') {
        const list = Array.isArray(driversRes.value) ? driversRes.value : (driversRes.value?.drivers || driversRes.value?.items || [])
        setDrivers(list)
      }
      if (opsRes.status === 'fulfilled') {
        const list = Array.isArray(opsRes.value) ? opsRes.value : (opsRes.value?.users || opsRes.value?.items || [])
        setOperators(list)
      }
    } catch (err) {
      setError(err.message || 'Erro ao carregar dados')
    } finally { setLoading(false) }
  }

  const onlineDrivers   = drivers.filter(d => d.is_online || d.status === 'online' || d.status === 'available')
  const offlineDrivers  = drivers.filter(d => !d.is_online && d.status !== 'online' && d.status !== 'available')
  const onlineOperators = operators.filter(o => o.is_online || o.status === 'online')
  const offlineOperators= operators.filter(o => !o.is_online && o.status !== 'online')

  const filteredDrivers = tab === 'drivers' || tab === 'all' ? drivers : []
  const filteredOperators = tab === 'operators' || tab === 'all' ? operators : []

  const totalOnline = onlineDrivers.length + onlineOperators.length

  return (
    <div className="space-y-5">

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Online Agora</h1>
            {totalOnline > 0 && (
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-green-500" />
              </span>
            )}
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400">Motoristas e atendentes conectados · atualiza a cada 30s</p>
        </div>
        <button onClick={fetchData} disabled={loading} className="p-1.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-500 hover:bg-gray-50 disabled:opacity-50">
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: 'Motoristas online',   value: onlineDrivers.length,   Icon: Truck,      color: 'text-blue-600 dark:text-blue-400',   bg: 'bg-blue-50 dark:bg-blue-900/20' },
          { label: 'Motoristas offline',  value: offlineDrivers.length,  Icon: WifiOff,    color: 'text-gray-500 dark:text-gray-400',   bg: 'bg-gray-50 dark:bg-gray-700' },
          { label: 'Atendentes online',   value: onlineOperators.length, Icon: Headphones, color: 'text-violet-600 dark:text-violet-400',bg: 'bg-violet-50 dark:bg-violet-900/20' },
          { label: 'Atendentes offline',  value: offlineOperators.length,Icon: WifiOff,    color: 'text-gray-500 dark:text-gray-400',   bg: 'bg-gray-50 dark:bg-gray-700' },
        ].map(({ label, value, Icon, color, bg }) => (
          <div key={label} className={`${bg} border border-gray-200 dark:border-gray-700 rounded-xl p-4`}>
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide leading-tight">{label}</p>
                <p className={`mt-1.5 text-2xl font-bold ${color}`}>{value}</p>
              </div>
              <Icon className={`w-5 h-5 shrink-0 mt-0.5 ${color}`} />
            </div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-2">
        {[
          { v: 'all', l: 'Todos' },
          { v: 'drivers', l: `Motoristas (${drivers.length})` },
          { v: 'operators', l: `Atendentes (${operators.length})` },
        ].map(({ v, l }) => (
          <button key={v} onClick={() => setTab(v)}
            className={`px-4 py-2 rounded-lg text-sm font-medium border transition-colors ${tab === v ? 'bg-primary-600 text-white border-primary-600' : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700'}`}>
            {l}
          </button>
        ))}
      </div>

      {loading && drivers.length === 0 && operators.length === 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
          {[...Array(8)].map((_, i) => <div key={i} className="h-24 bg-gray-100 dark:bg-gray-700 rounded-xl animate-pulse" />)}
        </div>
      ) : (
        <>
          {(tab === 'all' || tab === 'drivers') && filteredDrivers.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
                <Truck className="w-4 h-4 text-blue-500" /> Motoristas
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                {[...onlineDrivers, ...offlineDrivers].map((d, i) => (
                  <OnlineCard key={d.id || i} person={d} type="driver" />
                ))}
              </div>
            </div>
          )}

          {(tab === 'all' || tab === 'operators') && filteredOperators.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
                <Headphones className="w-4 h-4 text-violet-500" /> Atendentes
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                {[...onlineOperators, ...offlineOperators].map((o, i) => (
                  <OnlineCard key={o.id || i} person={o} type="operator" />
                ))}
              </div>
            </div>
          )}

          {filteredDrivers.length === 0 && filteredOperators.length === 0 && !loading && (
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-12 text-center">
              <Wifi className="mx-auto w-10 h-10 text-gray-300 dark:text-gray-600 mb-3" />
              <p className="text-sm text-gray-500 dark:text-gray-400">Nenhum usuário encontrado nesta categoria.</p>
            </div>
          )}
        </>
      )}

    </div>
  )
}
