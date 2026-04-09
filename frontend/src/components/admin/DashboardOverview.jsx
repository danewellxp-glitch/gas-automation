/**
 * Overview Dashboard para Admin
 * Métricas gerais e visão executiva do sistema
 */

import { useState, useEffect, useCallback } from 'react'
import { Activity, Truck, Users, Package, RefreshCw } from 'lucide-react'
import { getApiUrl, getAuthHeaders } from '../../utils/api'

export default function DashboardOverview() {
  const [metrics, setMetrics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [errorMsg, setErrorMsg] = useState(null)

  const fetchMetrics = useCallback(async () => {
    try {
      setLoading(true)
      setErrorMsg(null)
      const apiUrl = getApiUrl()
      const headers = getAuthHeaders()

      const [usersRes, driversRes, metricsRes] = await Promise.all([
        fetch(`${apiUrl}/users`, { headers }),
        fetch(`${apiUrl}/drivers`, { headers }),
        fetch(`${apiUrl}/drivers/metrics/dashboard?period=today`, { headers })
      ])

      const [usersData, driversData, metricsData] = await Promise.all([
        usersRes.ok ? usersRes.json().catch(() => []) : [],
        driversRes.ok ? driversRes.json().catch(() => []) : [],
        metricsRes.ok ? metricsRes.json().catch(() => ({})) : {}
      ])

      const users = Array.isArray(usersData) ? usersData : []
      const driversList = Array.isArray(driversData) ? driversData : []
      const driverMetrics = metricsData && typeof metricsData === 'object' ? metricsData : {}

      const activeUsers = users.filter(u => u.is_active).length
      const totalDrivers = users.filter(u => u.role === 'driver').length
      const activeDriversFromTable = driversList.filter(d => d.is_active && d.status !== 'offline').length

      setMetrics({
        users: {
          total: users.length,
          active: activeUsers,
          byRole: {
            admin: users.filter(u => u.role === 'admin').length,
            operator: users.filter(u => u.role === 'operator').length,
            owner: users.filter(u => u.role === 'owner').length,
            driver: users.filter(u => u.role === 'driver').length,
            user: users.filter(u => u.role === 'user').length
          }
        },
        drivers: {
          total: totalDrivers,
          active: activeDriversFromTable,
          offline: driversList.filter(d => d.status === 'offline').length,
          available: driversList.filter(d => d.status === 'available').length,
          busy: driversList.filter(d => d.status === 'busy').length,
          break: driversList.filter(d => d.status === 'break').length
        },
        deliveries: {
          today: driverMetrics.summary?.total_deliveries ?? 0,
          hoursWorked: driverMetrics.summary?.total_hours_worked ?? 0
        }
      })
    } catch (error) {
      console.error('Erro ao buscar métricas:', error)
      setErrorMsg(error.message || 'Falha ao conectar. Verifique a rede e tente novamente.')
      setMetrics(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchMetrics()
    const interval = setInterval(fetchMetrics, 30000)
    return () => clearInterval(interval)
  }, [fetchMetrics])

  if (loading) {
    return (
      <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-8 text-center shadow-sm">
        <div className="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-gray-200 dark:border-gray-700 border-t-primary-600" />
        <p className="mt-3 text-sm text-gray-600 dark:text-gray-400">Carregando métricas...</p>
      </div>
    )
  }

  if (!metrics) {
    return (
      <div className="rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 p-6 text-sm text-red-700 dark:text-red-400">
        <p className="font-medium">Erro ao carregar métricas</p>
        {errorMsg && <p className="mt-1 text-red-600">{errorMsg}</p>}
        <button
          type="button"
          onClick={() => fetchMetrics()}
          className="mt-4 inline-flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
        >
          <RefreshCw className="h-4 w-4" />
          Tentar novamente
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">Visão geral</h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">Métricas do sistema em tempo real</p>
      </div>

      {/* Cards principais */}
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Total de usuários</p>
              <p className="mt-1 text-3xl font-semibold text-gray-900 dark:text-white">{metrics.users.total}</p>
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{metrics.users.active} ativos</p>
            </div>
            <div className="rounded-lg bg-primary-50 dark:bg-primary-900/30 p-3 text-primary-700">
              <Users className="h-5 w-5" />
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Entregadores</p>
              <p className="mt-1 text-3xl font-semibold text-gray-900 dark:text-white">{metrics.drivers.total}</p>
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{metrics.drivers.active} online</p>
            </div>
            <div className="rounded-lg bg-green-50 dark:bg-green-900/20 p-3 text-green-700 dark:text-green-400">
              <Truck className="h-5 w-5" />
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Entregas hoje</p>
              <p className="mt-1 text-3xl font-semibold text-gray-900 dark:text-white">{metrics.deliveries.today}</p>
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{metrics.deliveries.hoursWorked}h trabalhadas</p>
            </div>
            <div className="rounded-lg bg-indigo-50 dark:bg-indigo-900/20 p-3 text-indigo-700">
              <Package className="h-5 w-5" />
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Status do sistema</p>
              <p className="mt-1 text-2xl font-semibold text-gray-900 dark:text-white">Operacional</p>
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Serviços online</p>
            </div>
            <div className="rounded-lg bg-amber-50 dark:bg-amber-900/20 p-3 text-amber-700">
              <Activity className="h-5 w-5" />
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-4 grid-cols-1 lg:grid-cols-2">
        {/* Usuários por role */}
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 shadow-sm">
          <div className="mb-4">
            <h3 className="text-base font-semibold text-gray-900 dark:text-white">Usuários por role</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">Distribuição de perfis</p>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {[
              { label: 'Admins', value: metrics.users.byRole.admin },
              { label: 'Operadores', value: metrics.users.byRole.operator },
              { label: 'Owners', value: metrics.users.byRole.owner },
              { label: 'Drivers', value: metrics.users.byRole.driver },
              { label: 'Users', value: metrics.users.byRole.user },
            ].map((r) => (
              <div key={r.label} className="rounded-lg bg-gray-50 dark:bg-gray-700 p-4">
                <div className="text-2xl font-semibold text-gray-900 dark:text-white">{r.value}</div>
                <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">{r.label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Status drivers */}
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 shadow-sm">
          <div className="mb-4">
            <h3 className="text-base font-semibold text-gray-900 dark:text-white">Status dos entregadores</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">Situação atual</p>
          </div>
          <div className="space-y-2">
            {[
              { label: 'Disponível', value: metrics.drivers.available, dot: 'bg-green-500' },
              { label: 'Ocupado', value: metrics.drivers.busy, dot: 'bg-blue-500' },
              { label: 'Em pausa', value: metrics.drivers.break, dot: 'bg-amber-500' },
              { label: 'Offline', value: metrics.drivers.offline, dot: 'bg-gray-400' },
            ].map((s) => (
              <div key={s.label} className="flex items-center justify-between rounded-lg bg-gray-50 dark:bg-gray-700 p-3">
                <div className="flex items-center gap-3">
                  <span className={`h-2.5 w-2.5 rounded-full ${s.dot}`} />
                  <span className="text-sm font-medium text-gray-900 dark:text-white">{s.label}</span>
                </div>
                <span className="text-sm font-semibold text-gray-900 dark:text-white">{s.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="flex items-center justify-end">
        <button
          onClick={fetchMetrics}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
        >
          Atualizar métricas
        </button>
      </div>
    </div>
  )
}
