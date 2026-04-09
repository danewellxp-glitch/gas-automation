/**
 * Relatórios › Desempenho — Ranking de motoristas e atendentes
 */

import { useState, useEffect } from 'react'
import { Download, FileText, TrendingUp, Star, Truck, Headphones, RefreshCw, AlertCircle } from 'lucide-react'
import { apiRequest } from '../../utils/api'

const fmtN = (v) => new Intl.NumberFormat('pt-BR').format(v || 0)
const fmtPct = (v) => `${(v || 0).toFixed(1)}%`
const fmtMin = (v) => v ? `${Math.floor(v)}min` : '—'

export default function RelDesempenho() {
  const [loading, setLoading]   = useState(false)
  const [exporting, setExporting] = useState(false)
  const [data, setData]         = useState(null)
  const [error, setError]       = useState('')
  const [startDate, setStart]   = useState(() => { const d = new Date(); d.setDate(1); return d.toISOString().split('T')[0] })
  const [endDate, setEnd]       = useState(() => new Date().toISOString().split('T')[0])
  const [tab, setTab]           = useState('drivers')

  useEffect(() => { fetchPreview() }, [startDate, endDate])

  const fetchPreview = async () => {
    try {
      setLoading(true); setError('')
      const res = await apiRequest('owner/dashboard?period=month')
      setData({
        drivers:   res?.driver_rankings   || res?.drivers_performance   || [],
        operators: res?.operator_rankings || res?.operators_performance || [],
      })
    } catch (err) {
      setError(err.message || 'Erro ao carregar dados de desempenho.')
    } finally { setLoading(false) }
  }

  const handleExport = async (format) => {
    try {
      setExporting(true)
      const token = localStorage.getItem('token')
      const base  = import.meta.env.VITE_API_URL || 'http://192.168.10.167:8000/api'
      const res   = await fetch(`${base}/owner/reports/performance?start_date=${startDate}&end_date=${endDate}&format=${format}`, { headers: { Authorization: `Bearer ${token}` } })
      if (!res.ok) { exportLocalCSV(); return }
      const blob = await res.blob()
      const url  = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url
      a.download = `desempenho_${startDate}_${endDate}.${format}`; a.click(); URL.revokeObjectURL(url)
    } catch { exportLocalCSV() }
    finally { setExporting(false) }
  }

  const exportLocalCSV = () => {
    if (!data) return
    const lines = [
      '=== RELATÓRIO DE DESEMPENHO ===',
      `Período: ${new Date(startDate).toLocaleDateString('pt-BR')} a ${new Date(endDate).toLocaleDateString('pt-BR')}`,
      `Gerado em: ${new Date().toLocaleString('pt-BR')}`,
      '',
      '--- RANKING MOTORISTAS ---',
      'Pos,Motorista,Entregas,T.Médio Entrega,No Prazo,Atrasadas,Avaliação',
      ...data.drivers.map((d, i) => `${i+1},"${d.name||''}",${d.deliveries_count||0},${fmtMin(d.avg_delivery_time)},${fmtPct(d.on_time_rate)},${d.late_deliveries||0},${(d.rating||0).toFixed(1)}`),
      '',
      '--- RANKING ATENDENTES ---',
      'Pos,Atendente,Pedidos aprovados,Erros,T.Médio Resposta',
      ...data.operators.map((o, i) => `${i+1},"${o.name||''}",${o.orders_approved||0},${o.errors_count||0},${fmtMin(o.avg_response_time)}`),
    ].join('\n')
    const blob = new Blob(['\uFEFF' + lines], { type: 'text/csv;charset=utf-8;' })
    const url  = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url
    a.download = `desempenho_${startDate}_${endDate}.csv`; a.click(); URL.revokeObjectURL(url)
  }

  const starColor = (rating) => rating >= 4.5 ? 'text-amber-400' : rating >= 3.5 ? 'text-amber-300' : 'text-gray-300'

  return (
    <div className="space-y-5">

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Relatório de Desempenho</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Ranking de motoristas e atendentes por performance</p>
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

      {/* Filtros */}
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

      {/* Tabs */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="flex border-b border-gray-100 dark:border-gray-700">
          <button onClick={() => setTab('drivers')}
            className={`flex items-center gap-2 px-5 py-3.5 text-sm font-medium border-b-2 transition-colors ${tab === 'drivers' ? 'border-primary-500 text-primary-600 dark:text-primary-400' : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}`}>
            <Truck className="w-4 h-4" /> Motoristas {data && `(${data.drivers.length})`}
          </button>
          <button onClick={() => setTab('operators')}
            className={`flex items-center gap-2 px-5 py-3.5 text-sm font-medium border-b-2 transition-colors ${tab === 'operators' ? 'border-primary-500 text-primary-600 dark:text-primary-400' : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}`}>
            <Headphones className="w-4 h-4" /> Atendentes {data && `(${data.operators.length})`}
          </button>
        </div>

        <div className="overflow-x-auto">
          {loading ? (
            <div className="p-8">
              {[...Array(4)].map((_, i) => <div key={i} className="h-14 bg-gray-100 dark:bg-gray-700 rounded-lg mb-2 animate-pulse" />)}
            </div>
          ) : tab === 'drivers' ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 dark:bg-gray-700/50">
                  {['#', 'Motorista', 'Entregas', 'T. Médio', 'No Prazo', 'Atrasadas', 'Avaliação', 'Comissão'].map((h, i) => (
                    <th key={h} className={`px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide ${i > 1 ? 'text-right' : 'text-left'}`}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {!data || data.drivers.length === 0 ? (
                  <tr><td colSpan={8} className="px-4 py-10 text-center text-sm text-gray-400 dark:text-gray-500">Sem dados de motoristas no período.</td></tr>
                ) : data.drivers.map((d, idx) => (
                  <tr key={d.id || idx} className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${idx === 0 ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400' : idx === 1 ? 'bg-gray-200 text-gray-600 dark:bg-gray-700 dark:text-gray-400' : idx === 2 ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400' : 'text-gray-400 dark:text-gray-500'}`}>
                        {idx + 1}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-medium text-gray-800 dark:text-gray-200">{d.name || d.full_name || '—'}</td>
                    <td className="px-4 py-3 text-right font-semibold text-gray-800 dark:text-gray-200">{fmtN(d.deliveries_count || 0)}</td>
                    <td className="px-4 py-3 text-right text-gray-600 dark:text-gray-400">{fmtMin(d.avg_delivery_time)}</td>
                    <td className="px-4 py-3 text-right">
                      <span className={`text-sm font-semibold ${(d.on_time_rate || 0) >= 90 ? 'text-emerald-600 dark:text-emerald-400' : (d.on_time_rate || 0) >= 70 ? 'text-amber-600 dark:text-amber-400' : 'text-red-600 dark:text-red-400'}`}>
                        {fmtPct(d.on_time_rate)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-red-600 dark:text-red-400">{fmtN(d.late_deliveries || 0)}</td>
                    <td className="px-4 py-3 text-right">
                      <span className="flex items-center justify-end gap-1">
                        <Star className={`w-3.5 h-3.5 fill-current ${starColor(d.rating)}`} />
                        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{(d.rating || 0).toFixed(1)}</span>
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-violet-600 dark:text-violet-400 font-semibold">
                      {d.commission != null ? `R$ ${(d.commission || 0).toFixed(2)}` : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 dark:bg-gray-700/50">
                  {['#', 'Atendente', 'Pedidos Aprov.', 'Erros', 'T. Resposta', 'Taxa Acerto'].map((h, i) => (
                    <th key={h} className={`px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide ${i > 1 ? 'text-right' : 'text-left'}`}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {!data || data.operators.length === 0 ? (
                  <tr><td colSpan={6} className="px-4 py-10 text-center text-sm text-gray-400 dark:text-gray-500">Sem dados de atendentes no período.</td></tr>
                ) : data.operators.map((o, idx) => {
                  const accuracy = o.orders_approved && o.errors_count != null
                    ? (1 - o.errors_count / Math.max(o.orders_approved, 1)) * 100 : null
                  return (
                    <tr key={o.id || idx} className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${idx === 0 ? 'bg-amber-100 text-amber-700' : idx === 1 ? 'bg-gray-200 text-gray-600' : idx === 2 ? 'bg-orange-100 text-orange-700' : 'text-gray-400'}`}>
                          {idx + 1}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-medium text-gray-800 dark:text-gray-200">{o.name || o.full_name || '—'}</td>
                      <td className="px-4 py-3 text-right font-semibold text-emerald-600 dark:text-emerald-400">{fmtN(o.orders_approved || 0)}</td>
                      <td className="px-4 py-3 text-right text-red-600 dark:text-red-400">{fmtN(o.errors_count || 0)}</td>
                      <td className="px-4 py-3 text-right text-gray-600 dark:text-gray-400">{fmtMin(o.avg_response_time)}</td>
                      <td className="px-4 py-3 text-right">
                        {accuracy != null && (
                          <span className={`text-sm font-semibold ${accuracy >= 95 ? 'text-emerald-600 dark:text-emerald-400' : accuracy >= 80 ? 'text-amber-600 dark:text-amber-400' : 'text-red-600 dark:text-red-400'}`}>
                            {accuracy.toFixed(1)}%
                          </span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

    </div>
  )
}
