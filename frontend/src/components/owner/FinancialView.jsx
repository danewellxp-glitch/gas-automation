/**
 * Financial View — Command Center Dark Premium
 */

import { useState, useEffect } from 'react'
import { DollarSign, TrendingDown, AlertCircle, RefreshCw, Users, TrendingUp, XCircle } from 'lucide-react'
import { apiRequest } from '../../utils/api'
import RevenueChart from './RevenueChart'

export default function FinancialView() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [period, setPeriod] = useState('day')
  const [dashboardData, setDashboardData] = useState(null)

  useEffect(() => {
    fetchDashboard()
  }, [period])

  const fetchDashboard = async () => {
    try {
      setLoading(true)
      setError('')
      const data = await apiRequest(`owner/dashboard?period=${period}`)
      setDashboardData(data)
    } catch (err) {
      console.error('Erro ao buscar dados financeiros:', err)
      setError(err.message || 'Erro ao carregar dados')
    } finally {
      setLoading(false)
    }
  }

  const formatCurrency = (value) =>
    new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 2 }).format(value || 0)

  if (loading && !dashboardData) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-gray-700 border-t-emerald-500" />
          <p className="mt-4 text-xs text-gray-500 tracking-widest uppercase">Carregando financeiro...</p>
        </div>
      </div>
    )
  }

  if (error && !dashboardData) {
    return (
      <div className="rounded-2xl border border-red-500/30 bg-red-950/40 p-6">
        <div className="flex items-center gap-2">
          <AlertCircle className="h-5 w-5 text-red-400" />
          <span className="font-semibold text-red-300">Erro ao carregar dados</span>
        </div>
        <p className="mt-2 text-sm text-red-400">{error}</p>
        <button
          onClick={fetchDashboard}
          className="mt-4 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-500"
        >
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
          <h1 className="text-2xl font-black tracking-tight text-white">Financeiro</h1>
          <p className="mt-1 text-xs text-gray-500">Breakdown completo de receita, cancelamentos e inadimplência</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border border-gray-700 bg-gray-900/80 p-1 gap-1">
            {[{ key: 'day', label: 'Dia' }, { key: 'week', label: 'Semana' }, { key: 'month', label: 'Mês' }].map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setPeriod(key)}
                className={`rounded-md px-4 py-1.5 text-xs font-bold transition-all ${
                  period === key
                    ? 'bg-emerald-600 text-white shadow-sm shadow-emerald-500/30'
                    : 'text-gray-400 hover:text-white'
                }`}
              >{label}</button>
            ))}
          </div>
          <button
            onClick={fetchDashboard}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-700 bg-gray-900/80 px-3 py-2 text-xs font-medium text-gray-400 hover:text-white hover:border-gray-600 disabled:opacity-40 transition-all"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            Atualizar
          </button>
        </div>
      </div>

      {/* 4 Metric Cards */}
      {financial && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">

          <div className="rounded-2xl border border-blue-500/20 bg-gray-900 p-5 shadow-lg shadow-blue-500/10">
            <div className="flex items-center justify-between mb-4">
              <p className="text-xs font-bold uppercase tracking-widest text-blue-400/80">Receita Bruta</p>
              <div className="rounded-lg bg-blue-500/10 p-2 ring-1 ring-blue-500/20">
                <DollarSign className="h-4 w-4 text-blue-400" />
              </div>
            </div>
            <p className="text-3xl font-black text-white">{formatCurrency(financial.gross_revenue)}</p>
            <p className="mt-2 text-xs text-gray-500">Total de pedidos não cancelados</p>
          </div>

          <div className="rounded-2xl border border-emerald-500/20 bg-gray-900 p-5 shadow-lg shadow-emerald-500/10">
            <div className="flex items-center justify-between mb-4">
              <p className="text-xs font-bold uppercase tracking-widest text-emerald-400/80">Receita Líquida</p>
              <div className="rounded-lg bg-emerald-500/10 p-2 ring-1 ring-emerald-500/20">
                <DollarSign className="h-4 w-4 text-emerald-400" />
              </div>
            </div>
            <p className="text-3xl font-black text-emerald-400">{formatCurrency(financial.net_revenue)}</p>
            <p className="mt-2 text-xs text-gray-500">Apenas pedidos entregues</p>
          </div>

          <div className="rounded-2xl border border-red-500/20 bg-gray-900 p-5 shadow-lg shadow-red-500/10">
            <div className="flex items-center justify-between mb-4">
              <p className="text-xs font-bold uppercase tracking-widest text-red-400/80">Cancelamentos</p>
              <div className="rounded-lg bg-red-500/10 p-2 ring-1 ring-red-500/20">
                <TrendingDown className="h-4 w-4 text-red-400" />
              </div>
            </div>
            <p className="text-3xl font-black text-red-400">{formatCurrency(financial.cancelled_revenue)}</p>
            <p className="mt-2 text-xs text-gray-500">{financial.cancelled_count} pedidos cancelados</p>
          </div>

          <div className="rounded-2xl border border-violet-500/20 bg-gray-900 p-5 shadow-lg shadow-violet-500/10">
            <div className="flex items-center justify-between mb-4">
              <p className="text-xs font-bold uppercase tracking-widest text-violet-400/80">Taxa de Repetição</p>
              <div className="rounded-lg bg-violet-500/10 p-2 ring-1 ring-violet-500/20">
                <Users className="h-4 w-4 text-violet-400" />
              </div>
            </div>
            <p className="text-3xl font-black text-white">{(financial.repeat_rate || 0).toFixed(1)}%</p>
            <p className="mt-2 text-xs text-gray-500">{financial.repeat_customers_count} clientes recorrentes</p>
          </div>

        </div>
      )}

      {/* Revenue Chart */}
      {revenueChart && (
        <div className="rounded-2xl border border-gray-700/40 bg-gray-900 p-5">
          <div className="mb-4 flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-blue-400" />
            <span className="text-xs font-bold uppercase tracking-widest text-gray-400">Receita ao Longo do Tempo</span>
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
            <div className="rounded-2xl border border-gray-700/40 bg-gray-900 p-5">
              <div className="mb-4 flex items-center gap-2">
                <XCircle className="h-4 w-4 text-red-400" />
                <span className="text-xs font-bold uppercase tracking-widest text-gray-400">Motivos de Cancelamento</span>
              </div>
              <div className="space-y-2">
                {Object.entries(financial.cancelled_reasons).map(([reason, count]) => (
                  <div key={reason} className="flex items-center justify-between rounded-xl border border-gray-700/50 bg-gray-800/40 px-4 py-3">
                    <span className="text-sm text-gray-300">{reason}</span>
                    <span className="text-sm font-bold text-red-400">{count} pedidos</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="rounded-2xl border border-gray-700/40 bg-gray-900 p-5">
            <div className="mb-4 flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-amber-400" />
              <span className="text-xs font-bold uppercase tracking-widest text-gray-400">Inadimplência</span>
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between rounded-xl border border-gray-700/50 bg-gray-800/40 px-4 py-3">
                <div>
                  <p className="text-xs font-bold uppercase tracking-widest text-gray-400">Pedidos Pendentes</p>
                  <p className="mt-0.5 text-xs text-gray-500">{formatCurrency(financial.pending_payments_value)}</p>
                </div>
                <p className="text-2xl font-black text-white">{financial.pending_payments_count}</p>
              </div>
              <div className="flex items-center justify-between rounded-xl border border-gray-700/50 bg-gray-800/40 px-4 py-3">
                <div>
                  <p className="text-xs font-bold uppercase tracking-widest text-gray-400">Clientes Novos</p>
                  <p className="mt-0.5 text-xs text-gray-500">Este período</p>
                </div>
                <p className="text-2xl font-black text-blue-400">{financial.new_customers_count}</p>
              </div>
              <div className="flex items-center justify-between rounded-xl border border-gray-700/50 bg-gray-800/40 px-4 py-3">
                <div>
                  <p className="text-xs font-bold uppercase tracking-widest text-gray-400">Clientes Recorrentes</p>
                  <p className="mt-0.5 text-xs text-gray-500">Taxa: {(financial.repeat_rate || 0).toFixed(1)}%</p>
                </div>
                <p className="text-2xl font-black text-emerald-400">{financial.repeat_customers_count}</p>
              </div>
            </div>
          </div>

        </div>
      )}

    </div>
  )
}
