/**
 * Financeiro › Lucratividade — DRE simplificado: Receita − Despesas = Lucro
 */

import { useState, useEffect } from 'react'
import { TrendingUp, TrendingDown, RefreshCw, Download, AlertCircle } from 'lucide-react'
import { apiRequest } from '../../utils/api'

const fmt = (v) =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 2 }).format(v || 0)

const fmtPct = (v) => {
  const n = parseFloat(v) || 0
  return `${n >= 0 ? '+' : ''}${n.toFixed(1)}%`
}

const MONTHS = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

export default function FinLucratividade() {
  const [loading, setLoading] = useState(true)
  const [data, setData]       = useState(null)
  const [period, setPeriod]   = useState('month')
  const [error, setError]     = useState('')

  useEffect(() => { fetchData() }, [period])

  const fetchData = async () => {
    try {
      setLoading(true); setError('')
      const raw = await apiRequest(`owner/dashboard?period=${period}`)
      const fin = raw?.financial_breakdown || {}
      const expenses = raw?.expenses_total || 0
      const gross = fin.gross_revenue || 0
      const net = fin.net_revenue || gross
      const cancelled = fin.cancelled_revenue || 0
      const profit = net - expenses
      const margin = net > 0 ? (profit / net) * 100 : 0

      // histórico mensal se disponível
      const history = raw?.monthly_history || raw?.revenue_chart || []

      setData({ gross, net, expenses, cancelled, profit, margin, history, period })
    } catch (err) {
      setError(err.message || 'Erro ao carregar dados de lucratividade.')
    } finally { setLoading(false) }
  }

  const handleExport = () => {
    if (!data) return
    const csv = [
      'Indicador,Valor',
      `Receita Bruta,${data.gross.toFixed(2)}`,
      `Receita Líquida,${data.net.toFixed(2)}`,
      `Cancelamentos,${data.cancelled.toFixed(2)}`,
      `Despesas,${data.expenses.toFixed(2)}`,
      `Lucro Operacional,${data.profit.toFixed(2)}`,
      `Margem Líquida,${data.margin.toFixed(2)}%`,
    ].join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url
    a.download = `lucratividade_${period}.csv`; a.click(); URL.revokeObjectURL(url)
  }

  const DRE_ROWS = data ? [
    { label: '(+) Receita Bruta',        value: data.gross,       style: 'font-medium text-gray-800 dark:text-gray-200' },
    { label: '(−) Cancelamentos',         value: -data.cancelled,  style: 'text-red-600 dark:text-red-400' },
    { label: '(=) Receita Líquida',       value: data.net,         style: 'font-semibold text-blue-600 dark:text-blue-400 border-t border-gray-200 dark:border-gray-700 pt-2 mt-1' },
    { label: '(−) Despesas Operacionais', value: -data.expenses,   style: 'text-red-600 dark:text-red-400' },
    { label: '(=) LUCRO OPERACIONAL',     value: data.profit,      style: `font-bold border-t-2 border-gray-300 dark:border-gray-600 pt-2 mt-1 text-lg ${data.profit >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}` },
  ] : []

  return (
    <div className="space-y-5">

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Lucratividade</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">DRE simplificado — Receita, Despesas e Margem</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex bg-gray-100 dark:bg-gray-800 rounded-lg p-0.5 border border-gray-200 dark:border-gray-700">
            {[{ k: 'day', l: 'Hoje' }, { k: 'week', l: 'Semana' }, { k: 'month', l: 'Mês' }].map(({ k, l }) => (
              <button key={k} onClick={() => setPeriod(k)}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${period === k ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}`}>
                {l}
              </button>
            ))}
          </div>
          <button onClick={handleExport} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 transition-colors">
            <Download className="w-3.5 h-3.5" /> CSV
          </button>
          <button onClick={fetchData} disabled={loading} className="p-1.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-500 hover:bg-gray-50 disabled:opacity-50">
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl text-sm text-red-600 dark:text-red-400">
          <AlertCircle className="w-4 h-4 shrink-0" /> {error}
        </div>
      )}

      {loading && !data ? (
        <div className="grid grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => <div key={i} className="h-28 bg-gray-100 dark:bg-gray-700 rounded-xl animate-pulse" />)}
        </div>
      ) : data && (
        <>
          {/* KPI cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: 'Receita Bruta',    value: fmt(data.gross),     color: 'text-blue-600 dark:text-blue-400',    bg: 'bg-blue-50 dark:bg-blue-900/20' },
              { label: 'Despesas',          value: fmt(data.expenses),  color: 'text-red-600 dark:text-red-400',      bg: 'bg-red-50 dark:bg-red-900/20' },
              { label: 'Lucro Operacional', value: fmt(data.profit),    color: data.profit >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400', bg: data.profit >= 0 ? 'bg-emerald-50 dark:bg-emerald-900/20' : 'bg-red-50 dark:bg-red-900/20' },
              { label: 'Margem Líquida',    value: `${data.margin.toFixed(1)}%`, color: data.margin >= 0 ? 'text-violet-600 dark:text-violet-400' : 'text-red-600 dark:text-red-400', bg: 'bg-violet-50 dark:bg-violet-900/20' },
            ].map(({ label, value, color, bg }) => (
              <div key={label} className={`${bg} border border-gray-200 dark:border-gray-700 rounded-xl p-5`}>
                <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">{label}</p>
                <p className={`mt-2 text-2xl font-bold ${color}`}>{value}</p>
              </div>
            ))}
          </div>

          {/* DRE */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">DRE — Demonstração do Resultado</h3>
              <div className="space-y-2">
                {DRE_ROWS.map(({ label, value, style }, i) => (
                  <div key={i} className={`flex items-center justify-between py-1 ${style}`}>
                    <span className="text-sm">{label}</span>
                    <span className="text-sm font-mono tabular-nums">
                      {value >= 0 ? fmt(value) : `(${fmt(Math.abs(value))})`}
                    </span>
                  </div>
                ))}
              </div>

              {/* Margem gauge */}
              <div className="mt-5 pt-4 border-t border-gray-100 dark:border-gray-700">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-gray-500 dark:text-gray-400">Margem líquida</span>
                  <span className={`text-xs font-semibold ${data.margin >= 10 ? 'text-emerald-600 dark:text-emerald-400' : data.margin >= 0 ? 'text-amber-600 dark:text-amber-400' : 'text-red-600 dark:text-red-400'}`}>
                    {data.margin.toFixed(1)}%
                  </span>
                </div>
                <div className="h-2 w-full rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-700 ${data.margin >= 10 ? 'bg-emerald-500' : data.margin >= 0 ? 'bg-amber-500' : 'bg-red-500'}`}
                    style={{ width: `${Math.max(0, Math.min(data.margin, 100))}%` }}
                  />
                </div>
                <div className="mt-1 flex justify-between text-xs text-gray-400">
                  <span>0%</span><span>Bom ≥ 10%</span><span>100%</span>
                </div>
              </div>
            </div>

            {/* Breakdown visual */}
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">Composição da Receita Bruta</h3>
              {[
                { label: 'Receita entregue', value: data.net, total: data.gross, color: 'bg-emerald-500' },
                { label: 'Cancelamentos',    value: data.cancelled, total: data.gross, color: 'bg-red-400' },
              ].map(({ label, value, total, color }) => {
                const pct = total > 0 ? (value / total) * 100 : 0
                return (
                  <div key={label} className="mb-4">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-sm text-gray-600 dark:text-gray-400">{label}</span>
                      <span className="text-sm font-semibold text-gray-800 dark:text-gray-200">{fmt(value)} <span className="text-xs text-gray-400">({pct.toFixed(1)}%)</span></span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
                      <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                )
              })}

              <div className="mt-4 pt-4 border-t border-gray-100 dark:border-gray-700">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Despesas / Receita líquida</span>
                  <span className="text-sm font-semibold text-gray-800 dark:text-gray-200">
                    {data.net > 0 ? `${((data.expenses / data.net) * 100).toFixed(1)}%` : '—'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </>
      )}

    </div>
  )
}
