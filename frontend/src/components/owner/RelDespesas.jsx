/**
 * Relatórios › Despesas — Análise de gastos por categoria com exportação
 */

import { useState, useEffect } from 'react'
import { Download, FileText, Receipt, RefreshCw, AlertCircle, TrendingDown } from 'lucide-react'
import { apiRequest } from '../../utils/api'

const fmt = (v) =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 2 }).format(v || 0)
const fmtN = (v) => new Intl.NumberFormat('pt-BR').format(v || 0)

const CAT_COLORS = {
  'Fornecedor':  'bg-blue-500',
  'Aluguel':     'bg-violet-500',
  'Salário':     'bg-emerald-500',
  'Comissão':    'bg-amber-500',
  'Utilitários': 'bg-cyan-500',
  'Marketing':   'bg-pink-500',
  'Manutenção':  'bg-orange-500',
  'Outros':      'bg-gray-400',
}

export default function RelDespesas() {
  const [loading, setLoading]   = useState(false)
  const [exporting, setExporting] = useState(false)
  const [expenses, setExpenses] = useState([])
  const [summary, setSummary]   = useState(null)
  const [error, setError]       = useState('')
  const [startDate, setStart]   = useState(() => { const d = new Date(); d.setDate(1); return d.toISOString().split('T')[0] })
  const [endDate, setEnd]       = useState(() => new Date().toISOString().split('T')[0])
  const [activeTab, setTab]     = useState('detail')

  useEffect(() => { fetchPreview() }, [startDate, endDate])

  const fetchPreview = async () => {
    try {
      setLoading(true); setError('')
      const res = await apiRequest(`expenses?start_date=${startDate}&end_date=${endDate}`)
      const list = Array.isArray(res) ? res : (res?.items || res?.expenses || [])
      setExpenses(list)
      buildSummary(list)
    } catch {
      try {
        const res = await apiRequest(`financial/expenses?start=${startDate}&end=${endDate}`)
        const list = Array.isArray(res) ? res : (res?.items || [])
        setExpenses(list)
        buildSummary(list)
      } catch {
        setError('Sem dados de despesas. Configure o módulo de despesas para ver os relatórios.')
        setExpenses([])
        setSummary({ total: 0, count: 0, byCategory: {}, topCategory: '—' })
      }
    } finally { setLoading(false) }
  }

  const buildSummary = (list) => {
    const total = list.reduce((s, e) => s + (e.amount || e.value || 0), 0)
    const byCategory = {}
    list.forEach(e => {
      const cat = e.category || 'Outros'
      byCategory[cat] = (byCategory[cat] || 0) + (e.amount || e.value || 0)
    })
    const topCategory = Object.entries(byCategory).sort(([, a], [, b]) => b - a)[0]?.[0] || '—'
    setSummary({ total, count: list.length, byCategory, topCategory })
  }

  const handleExport = async (format) => {
    try {
      setExporting(true)
      const token = localStorage.getItem('token')
      const base  = import.meta.env.VITE_API_URL || 'http://192.168.10.167:8000/api'
      const res   = await fetch(`${base}/owner/reports/expenses?start_date=${startDate}&end_date=${endDate}&format=${format}`, { headers: { Authorization: `Bearer ${token}` } })
      if (!res.ok) { exportLocalCSV(); return }
      const blob = await res.blob(); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url
      a.download = `despesas_${startDate}_${endDate}.${format}`; a.click(); URL.revokeObjectURL(url)
    } catch { exportLocalCSV() }
    finally { setExporting(false) }
  }

  const exportLocalCSV = () => {
    if (!summary) return
    const catRows = Object.entries(summary.byCategory).sort(([,a],[,b]) => b-a)
    const lines = [
      '=== RELATÓRIO DE DESPESAS ===',
      `Período: ${new Date(startDate).toLocaleDateString('pt-BR')} a ${new Date(endDate).toLocaleDateString('pt-BR')}`,
      `Gerado em: ${new Date().toLocaleString('pt-BR')}`,
      '',
      '--- RESUMO POR CATEGORIA ---',
      'Categoria,Total,% do Total',
      ...catRows.map(([cat, val]) => `"${cat}",${val.toFixed(2)},${summary.total > 0 ? ((val/summary.total)*100).toFixed(1) : 0}%`),
      `TOTAL,${summary.total.toFixed(2)},100%`,
      '',
      '--- LANÇAMENTOS DETALHADOS ---',
      'Data,Descrição,Categoria,Valor,Status',
      ...expenses.map(e =>
        `${e.date || e.created_at ? new Date(e.date || e.created_at).toLocaleDateString('pt-BR') : '—'},"${e.description||''}","${e.category||'Outros'}",${(e.amount||e.value||0).toFixed(2)},${e.status||''}`
      ),
    ].join('\n')
    const blob = new Blob(['\uFEFF' + lines], { type: 'text/csv;charset=utf-8;' })
    const url  = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url
    a.download = `despesas_${startDate}_${endDate}.csv`; a.click(); URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-5">

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Relatório de Despesas</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Análise de gastos por categoria com totais e percentuais</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => handleExport('csv')} disabled={exporting}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors disabled:opacity-40">
            <Download className="w-4 h-4" /> CSV
          </button>
          <button onClick={() => handleExport('pdf')} disabled={exporting}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 transition-colors disabled:opacity-40">
            <FileText className="w-4 h-4" /> PDF
          </button>
          <button onClick={fetchPreview} disabled={loading} className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-500 hover:bg-gray-50 disabled:opacity-50">
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <div className="grid grid-cols-2 gap-3 max-w-sm">
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">De</label>
            <input type="date" value={startDate} onChange={e => setStart(e.target.value)}
              className="w-full rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-primary-500" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Até</label>
            <input type="date" value={endDate} onChange={e => setEnd(e.target.value)}
              className="w-full rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-primary-500" />
          </div>
        </div>
      </div>

      {error && <div className="flex items-center gap-2 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl text-sm text-amber-700 dark:text-amber-400"><AlertCircle className="w-4 h-4 shrink-0" />{error}</div>}

      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            { label: 'Total Despesas', value: fmt(summary.total),   color: 'text-red-600 dark:text-red-400',    bg: 'bg-red-50 dark:bg-red-900/20' },
            { label: 'Lançamentos',    value: fmtN(summary.count),  color: 'text-gray-900 dark:text-white',     bg: 'bg-white dark:bg-gray-800' },
            { label: 'Categorias',     value: Object.keys(summary.byCategory).length, color: 'text-blue-600 dark:text-blue-400', bg: 'bg-white dark:bg-gray-800' },
            { label: 'Maior categoria',value: summary.topCategory,  color: 'text-violet-600 dark:text-violet-400', bg: 'bg-violet-50 dark:bg-violet-900/20' },
          ].map(({ label, value, color, bg }) => (
            <div key={label} className={`${bg} border border-gray-200 dark:border-gray-700 rounded-xl p-4`}>
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">{label}</p>
              <p className={`mt-1 text-xl font-bold ${color} truncate`}>{value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Por Categoria - visual bars */}
      {summary && Object.keys(summary.byCategory).length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
          <div className="flex items-center gap-2 mb-4">
            <TrendingDown className="w-4 h-4 text-red-500" />
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Despesas por Categoria</h3>
          </div>
          <div className="space-y-3">
            {Object.entries(summary.byCategory).sort(([,a],[,b]) => b-a).map(([cat, val]) => {
              const pct = summary.total > 0 ? (val / summary.total) * 100 : 0
              const barColor = CAT_COLORS[cat] || 'bg-gray-400'
              return (
                <div key={cat}>
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className={`w-2.5 h-2.5 rounded-full ${barColor} shrink-0`} />
                      <span className="text-sm text-gray-700 dark:text-gray-300">{cat}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-gray-400 dark:text-gray-500">{pct.toFixed(1)}%</span>
                      <span className="text-sm font-semibold text-gray-800 dark:text-gray-200 w-28 text-right">{fmt(val)}</span>
                    </div>
                  </div>
                  <div className="h-1.5 w-full rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
                    <div className={`h-full rounded-full ${barColor}`} style={{ width: `${pct}%` }} />
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Tabs: detalhe / resumo */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="flex border-b border-gray-100 dark:border-gray-700">
          {[{ k: 'detail', l: 'Lançamentos' }, { k: 'summary', l: 'Resumo por Categoria' }].map(({ k, l }) => (
            <button key={k} onClick={() => setTab(k)}
              className={`px-5 py-3.5 text-sm font-medium border-b-2 transition-colors ${activeTab === k ? 'border-primary-500 text-primary-600 dark:text-primary-400' : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}`}>
              {l}
            </button>
          ))}
        </div>

        <div className="overflow-x-auto">
          {activeTab === 'detail' ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 dark:bg-gray-700/50">
                  {['Data', 'Descrição', 'Categoria', 'Valor'].map((h, i) => (
                    <th key={h} className={`px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide ${i === 3 ? 'text-right' : 'text-left'}`}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {loading ? (
                  [...Array(5)].map((_, i) => <tr key={i}>{[...Array(4)].map((_, j) => <td key={j} className="px-4 py-3"><div className="h-4 bg-gray-100 dark:bg-gray-700 rounded animate-pulse" /></td>)}</tr>)
                ) : expenses.length === 0 ? (
                  <tr><td colSpan={4} className="px-4 py-10 text-center text-sm text-gray-400 dark:text-gray-500">
                    {error ? 'Configure o módulo de despesas.' : 'Nenhuma despesa no período.'}
                  </td></tr>
                ) : (
                  expenses.map((e, idx) => (
                    <tr key={e.id || idx} className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                      <td className="px-4 py-3 text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">
                        {(e.date || e.created_at) ? new Date(e.date || e.created_at).toLocaleDateString('pt-BR') : '—'}
                      </td>
                      <td className="px-4 py-3 text-gray-800 dark:text-gray-200">{e.description || '—'}</td>
                      <td className="px-4 py-3">
                        <span className="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400">
                          {e.category || 'Outros'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right font-semibold text-red-600 dark:text-red-400">
                        {fmt(e.amount || e.value || 0)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
              {expenses.length > 0 && (
                <tfoot>
                  <tr className="border-t-2 border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700/50 font-semibold">
                    <td colSpan={3} className="px-4 py-3 text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">{expenses.length} lançamentos</td>
                    <td className="px-4 py-3 text-right text-red-700 dark:text-red-400">{fmt(summary?.total)}</td>
                  </tr>
                </tfoot>
              )}
            </table>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 dark:bg-gray-700/50">
                  {['Categoria', 'Lançamentos', 'Total', '% do Total'].map((h, i) => (
                    <th key={h} className={`px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide ${i > 1 ? 'text-right' : 'text-left'}`}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {!summary || Object.keys(summary.byCategory).length === 0 ? (
                  <tr><td colSpan={4} className="px-4 py-8 text-center text-sm text-gray-400 dark:text-gray-500">Sem dados por categoria.</td></tr>
                ) : Object.entries(summary.byCategory).sort(([,a],[,b]) => b-a).map(([cat, val]) => {
                  const count = expenses.filter(e => (e.category || 'Outros') === cat).length
                  const pct   = summary.total > 0 ? (val / summary.total) * 100 : 0
                  const bar   = CAT_COLORS[cat] || 'bg-gray-400'
                  return (
                    <tr key={cat} className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <span className={`w-2.5 h-2.5 rounded-full ${bar} shrink-0`} />
                          <span className="font-medium text-gray-800 dark:text-gray-200">{cat}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right text-gray-600 dark:text-gray-400">{fmtN(count)}</td>
                      <td className="px-4 py-3 text-right font-semibold text-red-600 dark:text-red-400">{fmt(val)}</td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <div className="w-16 h-1.5 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
                            <div className={`h-full ${bar} rounded-full`} style={{ width: `${pct}%` }} />
                          </div>
                          <span className="text-xs text-gray-500 dark:text-gray-400 w-10 text-right">{pct.toFixed(1)}%</span>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
              {summary && Object.keys(summary.byCategory).length > 0 && (
                <tfoot>
                  <tr className="border-t-2 border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700/50 font-semibold">
                    <td className="px-4 py-3 text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">TOTAL</td>
                    <td className="px-4 py-3 text-right text-gray-800 dark:text-gray-200">{fmtN(summary.count)}</td>
                    <td className="px-4 py-3 text-right text-red-700 dark:text-red-400">{fmt(summary.total)}</td>
                    <td className="px-4 py-3 text-right text-gray-500 dark:text-gray-400">100%</td>
                  </tr>
                </tfoot>
              )}
            </table>
          )}
        </div>
      </div>

    </div>
  )
}
