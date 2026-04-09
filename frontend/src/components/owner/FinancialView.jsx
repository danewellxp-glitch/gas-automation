/**
 * Financial View — Breakdown financeiro do dono
 * Design Preline-inspired: cards brancos, sem glassmorphism.
 */

import { useState, useEffect } from 'react'
import { DollarSign, TrendingDown, AlertCircle, RefreshCw, Users, TrendingUp, XCircle } from 'lucide-react'
import { apiRequest } from '../../utils/api'
import RevenueChart from './RevenueChart'

const PERIODS = [{ key: 'day', label: 'Dia' }, { key: 'week', label: 'Semana' }, { key: 'month', label: 'Mês' }]

export default function FinancialView() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [period, setPeriod] = useState('day')
  const [dashboardData, setDashboardData] = useState(null)

  useEffect(() => { fetchDashboard() }, [period])

  const fetchDashboard = async () => {
    try {
      setLoading(true)
      setError('')
      const data = await apiRequest(`owner/dashboard?period=${period}`)
      setDashboardData(data)
    } catch (err) {
      setError(err.message || 'Erro ao carregar dados')
    } finally {
      setLoading(false)
    }
  }

  const fmtCurrency = (v) =>
    new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 2 }).format(v || 0)

  if (loading && !dashboardData) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 animate-spin rounded-full border-2 border-gray-200 border-t-primary-500" />
      </div>
    )
  }

  if (error && !dashboardData) {
    return (
      <div className="rounded-xl border border-red-200 dark:border-red-700/40 bg-red-50 dark:bg-red-900/10 p-5">
        <div className="flex items-center gap-2 mb-2">
          <AlertCircle className="w-4 h-4 text-red-500" />
          <span className="text-sm font-semibold text-red-700 dark:text-red-400">Erro ao carregar dados</span>
        </div>
        <p className="text-sm text-red-600 dark:text-red-400 mb-3">{error}</p>
        <button onClick={fetchDashboard} className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm font-medium hover:bg-red-500 transition-colors">
          Tentar novamente
        </button>
      </div>
    )
  }

  if (!dashboardData) return null

  const financial = dashboardData?.financial_breakdown
  const revenueChart = dashboardData?.revenue_chart

  return (
    <div className="space-y-4">

      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Financeiro</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Breakdown de receita, cancelamentos e inadimplência</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 p-1 gap-1">
            {PERIODS.map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setPeriod(key)}
                className={`rounded-md px-3 py-1 text-xs font-medium transition-all ${
                  period === key
                    ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                    : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                }`}
              >{label}</button>
            ))}
          </div>
          <button
            onClick={fetchDashboard}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Atualizar
          </button>
        </div>
      </div>

      {/* 4 Metric Cards */}
      {financial && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { label: 'Receita Bruta',     value: fmtCurrency(financial.gross_revenue),     sub: 'Total não cancelado',         icon: DollarSign, iconBg: 'bg-blue-50 dark:bg-blue-900/20',     iconColor: 'text-blue-500' },
            { label: 'Receita Líquida',   value: fmtCurrency(financial.net_revenue),       sub: 'Apenas entregues',            icon: DollarSign, iconBg: 'bg-emerald-50 dark:bg-emerald-900/20', iconColor: 'text-emerald-500' },
            { label: 'Cancelamentos',     value: fmtCurrency(financial.cancelled_revenue), sub: `${financial.cancelled_count} pedidos`, icon: TrendingDown, iconBg: 'bg-red-50 dark:bg-red-900/20', iconColor: 'text-red-500' },
            { label: 'Taxa de Repetição', value: `${(financial.repeat_rate || 0).toFixed(1)}%`, sub: `${financial.repeat_customers_count} recorrentes`, icon: Users, iconBg: 'bg-violet-50 dark:bg-violet-900/20', iconColor: 'text-violet-500' },
          ].map(({ label, value, sub, icon: Icon, iconBg, iconColor }) => (
            <div key={label} className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">{label}</p>
                  <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
                  <p className="mt-0.5 text-xs text-gray-400 dark:text-gray-500">{sub}</p>
                </div>
                <div className={`shrink-0 w-9 h-9 rounded-lg flex items-center justify-center ${iconBg}`}>
                  <Icon className={`w-4 h-4 ${iconColor}`} />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Revenue Chart */}
      {revenueChart && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="w-4 h-4 text-primary-500" />
            <span className="text-sm font-semibold text-gray-900 dark:text-white">Receita ao Longo do Tempo</span>
          </div>
          <div className="h-64">
            <RevenueChart data={revenueChart} />
          </div>
        </div>
      )}

      {/* Motivos de Cancelamento + Inadimplência */}
      {financial && (
        <div className="grid gap-4 lg:grid-cols-2">

          {financial.cancelled_reasons && Object.keys(financial.cancelled_reasons).length > 0 && (
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
              <div className="flex items-center gap-2 mb-4">
                <XCircle className="w-4 h-4 text-red-500" />
                <span className="text-sm font-semibold text-gray-900 dark:text-white">Motivos de Cancelamento</span>
              </div>
              <div className="space-y-2">
                {Object.entries(financial.cancelled_reasons).map(([reason, count]) => (
                  <div key={reason} className="flex items-center justify-between py-2.5 px-3 rounded-lg bg-gray-50 dark:bg-gray-700/50 border border-gray-100 dark:border-gray-700">
                    <span className="text-sm text-gray-700 dark:text-gray-300">{reason}</span>
                    <span className="text-sm font-semibold text-red-600 dark:text-red-400">{count} pedidos</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
            <div className="flex items-center gap-2 mb-4">
              <AlertCircle className="w-4 h-4 text-amber-500" />
              <span className="text-sm font-semibold text-gray-900 dark:text-white">Clientes & Pagamentos</span>
            </div>
            <div className="space-y-2">
              {[
                { label: 'Pedidos Pendentes', sub: fmtCurrency(financial.pending_payments_value), value: financial.pending_payments_count, valueColor: 'text-gray-900 dark:text-white' },
                { label: 'Clientes Novos', sub: 'Este período', value: financial.new_customers_count, valueColor: 'text-blue-600 dark:text-blue-400' },
                { label: 'Clientes Recorrentes', sub: `Taxa: ${(financial.repeat_rate || 0).toFixed(1)}%`, value: financial.repeat_customers_count, valueColor: 'text-emerald-600 dark:text-emerald-400' },
              ].map(({ label, sub, value, valueColor }) => (
                <div key={label} className="flex items-center justify-between py-2.5 px-3 rounded-lg bg-gray-50 dark:bg-gray-700/50 border border-gray-100 dark:border-gray-700">
                  <div>
                    <p className="text-sm font-medium text-gray-700 dark:text-gray-300">{label}</p>
                    <p className="text-xs text-gray-400 dark:text-gray-500">{sub}</p>
                  </div>
                  <p className={`text-2xl font-bold ${valueColor}`}>{value}</p>
                </div>
              ))}
            </div>
          </div>

        </div>
      )}

    </div>
  )
}
