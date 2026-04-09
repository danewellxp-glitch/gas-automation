/**
 * Operação › Mapa — Mapa dos pedidos do dia com filtros de período
 */

import { useState, useEffect } from 'react'
import { Map, RefreshCw, AlertCircle, Filter } from 'lucide-react'
import { apiRequest } from '../../utils/api'
import DeliveryMap from '../map/DeliveryMap'

const PERIOD_OPTIONS = [
  { key: 'today', label: 'Hoje' },
  { key: 'week',  label: 'Semana' },
  { key: 'month', label: 'Mês' },
]

export default function OpMapa() {
  const [loading, setLoading]   = useState(true)
  const [orders, setOrders]     = useState([])
  const [drivers, setDrivers]   = useState([])
  const [error, setError]       = useState('')
  const [period, setPeriod]     = useState('today')
  const [statusFilter, setStatus] = useState('all')

  useEffect(() => { fetchData() }, [period])

  const fetchData = async () => {
    try {
      setLoading(true); setError('')
      const [ordersRes, driversRes] = await Promise.allSettled([
        apiRequest(period === 'today' ? 'orders/today' : `orders?days=${period === 'week' ? 7 : 30}`),
        apiRequest('drivers'),
      ])
      if (ordersRes.status === 'fulfilled') {
        const list = Array.isArray(ordersRes.value) ? ordersRes.value : (ordersRes.value?.items || ordersRes.value?.orders || [])
        setOrders(list)
      }
      if (driversRes.status === 'fulfilled') {
        const list = Array.isArray(driversRes.value) ? driversRes.value : (driversRes.value?.drivers || driversRes.value?.items || [])
        setDrivers(list)
      }
    } catch (err) {
      setError(err.message || 'Erro ao carregar dados do mapa')
    } finally { setLoading(false) }
  }

  const mapOrders = orders.filter(o => {
    const hasCoords = o.latitude && o.longitude
    const matchStatus = statusFilter === 'all' || o.status === statusFilter
    return hasCoords && matchStatus
  })

  const mapDrivers = drivers.filter(d => d.location?.latitude && d.location?.longitude)

  const stats = {
    total: orders.length,
    withCoords: orders.filter(o => o.latitude && o.longitude).length,
    delivered: orders.filter(o => o.status === 'delivered').length,
    inRoute: orders.filter(o => o.status === 'in_delivery').length,
    pending: orders.filter(o => o.status === 'pending').length,
    onlineDrivers: drivers.filter(d => d.is_online || d.status === 'online' || d.status === 'available').length,
  }

  return (
    <div className="space-y-5">

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Mapa de Pedidos</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Localização geográfica dos pedidos e motoristas</p>
        </div>
        <div className="flex items-center gap-2">
          {/* Período */}
          <div className="flex bg-gray-100 dark:bg-gray-800 rounded-lg p-0.5 border border-gray-200 dark:border-gray-700">
            {PERIOD_OPTIONS.map(({ key, label }) => (
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

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {[
          { label: 'Total pedidos', value: stats.total, color: 'text-gray-900 dark:text-white' },
          { label: 'No mapa', value: stats.withCoords, color: 'text-blue-600 dark:text-blue-400' },
          { label: 'Entregues', value: stats.delivered, color: 'text-emerald-600 dark:text-emerald-400' },
          { label: 'Em rota', value: stats.inRoute, color: 'text-violet-600 dark:text-violet-400' },
          { label: 'Pendentes', value: stats.pending, color: 'text-amber-600 dark:text-amber-400' },
          { label: 'Motoristas online', value: stats.onlineDrivers, color: 'text-blue-600 dark:text-blue-400' },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-3">
            <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{label}</p>
            <p className={`mt-1 text-xl font-bold ${color}`}>{value}</p>
          </div>
        ))}
      </div>

      {/* Filtro de status */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs font-medium text-gray-500 dark:text-gray-400 flex items-center gap-1">
          <Filter className="w-3.5 h-3.5" /> Filtrar:
        </span>
        {[
          { v: 'all',         l: 'Todos' },
          { v: 'pending',     l: 'Pendentes' },
          { v: 'in_delivery', l: 'Em entrega' },
          { v: 'delivered',   l: 'Entregues' },
          { v: 'cancelled',   l: 'Cancelados' },
        ].map(({ v, l }) => (
          <button key={v} onClick={() => setStatus(v)}
            className={`px-3 py-1 rounded-lg text-xs font-medium border transition-colors ${statusFilter === v ? 'bg-primary-600 text-white border-primary-600' : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700'}`}>
            {l}
          </button>
        ))}
      </div>

      {error && (
        <div className="flex items-center gap-2 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl text-sm text-amber-700 dark:text-amber-400">
          <AlertCircle className="w-4 h-4 shrink-0" /> {error}
        </div>
      )}

      {/* Mapa */}
      {loading && orders.length === 0 ? (
        <div className="h-[520px] bg-gray-100 dark:bg-gray-700 rounded-xl animate-pulse flex items-center justify-center">
          <div className="text-center">
            <div className="w-8 h-8 border-2 border-gray-300 border-t-primary-500 rounded-full animate-spin mx-auto" />
            <p className="mt-3 text-sm text-gray-500 dark:text-gray-400">Carregando mapa...</p>
          </div>
        </div>
      ) : (
        <div className="rounded-xl overflow-hidden border border-gray-200 dark:border-gray-700">
          <DeliveryMap
            orders={mapOrders}
            drivers={mapDrivers}
            height="520px"
            autoRefresh
          />
        </div>
      )}

      {stats.withCoords === 0 && !loading && (
        <div className="flex items-start gap-3 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl">
          <Map className="w-4 h-4 text-blue-600 dark:text-blue-400 shrink-0 mt-0.5" />
          <p className="text-sm text-blue-700 dark:text-blue-300">
            Nenhum pedido com coordenadas no período. O mapa exibe pedidos apenas quando o cliente compartilha localização via WhatsApp ou quando o endereço é geocodificado.
          </p>
        </div>
      )}

    </div>
  )
}
