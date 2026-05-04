/**
 * Relatórios › Faturamento
 * Preview da tabela + exportação CSV (super planilha) e PDF (relatório gráfico)
 */

import { useState, useEffect } from 'react'
import { Download, FileText, Calendar, TrendingUp, TrendingDown, DollarSign, RefreshCw, AlertCircle } from 'lucide-react'
import { apiRequest } from '../../utils/api'

const fmt = (v) =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 2 }).format(v || 0)

const fmtN = (v) => new Intl.NumberFormat('pt-BR').format(v || 0)

function KpiCard({ label, value, sub, trend, color, bg }) {
  return (
    <div className={`${bg} border border-gray-200 dark:border-gray-700 rounded-xl p-5`}>
      <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">{label}</p>
      <p className={`mt-1.5 text-2xl font-bold ${color}`}>{value}</p>
      {sub && <p className="mt-0.5 text-xs text-gray-400 dark:text-gray-500">{sub}</p>}
      {trend != null && (
        <div className={`mt-2 inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${trend >= 0 ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-400' : 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400'}`}>
          {trend >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
          {trend >= 0 ? '+' : ''}{trend?.toFixed(1)}% vs período anterior
        </div>
      )}
    </div>
  )
}

export default function RelFaturamento() {
  const [loading, setLoading]   = useState(false)
  const [exporting, setExporting] = useState(false)
  const [data, setData]         = useState(null)
  const [rows, setRows]         = useState([])
  const [error, setError]       = useState('')
  const [startDate, setStart]   = useState(() => { const d = new Date(); d.setDate(1); return d.toISOString().split('T')[0] })
  const [endDate, setEnd]       = useState(() => new Date().toISOString().split('T')[0])
  const [groupBy, setGroupBy]   = useState('day')

  useEffect(() => { fetchPreview() }, [startDate, endDate, groupBy])

  const fetchPreview = async () => {
    try {
      setLoading(true); setError('')
      const res = await apiRequest(`owner/dashboard?period=month`)
      const fin = res?.financial_breakdown || {}
      const ops = res?.cards?.operational || {}
      const chart = res?.revenue_chart || []

      setData({
        gross: fin.gross_revenue || 0,
        net: fin.net_revenue || 0,
        cancelled: fin.cancelled_revenue || 0,
        orders: ops.orders_completed || 0,
        ticket: fin.average_ticket || 0,
        growth: fin.growth_vs_last_month || null,
      })

      // Monta preview da tabela a partir do revenue_chart
      const preview = chart.map(item => ({
        date: item.date || item.label || item.day,
        orders: item.orders || item.count || 0,
        gross: item.revenue || item.gross || item.value || 0,
        cancelled: item.cancelled || 0,
        net: (item.revenue || item.value || 0) - (item.cancelled || 0),
        ticket: item.orders ? (item.revenue / item.orders) : 0,
      }))
      setRows(preview)
    } catch (err) {
      setError(err.message || 'Erro ao carregar dados de faturamento.')
    } finally { setLoading(false) }
  }

  const handleExport = async (format) => {
    try {
      setExporting(true)
      const token = localStorage.getItem('token')
      const base = import.meta.env.VITE_API_URL || 'http://192.168.10.167:5688/api'
      const url = `${base}/owner/reports/revenue?start_date=${startDate}&end_date=${endDate}&format=${format}&group_by=${groupBy}`
      const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } })

      if (!res.ok) {
        // fallback: gera CSV local
        if (format === 'csv') exportLocalCSV()
        else alert('PDF não disponível. Exporte como CSV e importe no Excel.')
        return
      }

      const blob = await res.blob()
      const blobUrl = URL.createObjectURL(blob)
      const a = document.createElement('a'); a.href = blobUrl
      a.download = `faturamento_${startDate}_${endDate}.${format}`
      a.click(); URL.revokeObjectURL(blobUrl)
    } catch {
      if (format === 'csv') exportLocalCSV()
    } finally { setExporting(false) }
  }

  const exportLocalCSV = () => {
    const header = [
      '=== RELATÓRIO DE FATURAMENTO ===',
      `Período: ${new Date(startDate).toLocaleDateString('pt-BR')} a ${new Date(endDate).toLocaleDateString('pt-BR')}`,
      `Gerado em: ${new Date().toLocaleString('pt-BR')}`,
      '',
      '--- RESUMO EXECUTIVO ---',
      `Receita Bruta,${fmt(data?.gross)}`,
      `Receita Líquida,${fmt(data?.net)}`,
      `Cancelamentos,${fmt(data?.cancelled)}`,
      `Pedidos Entregues,${fmtN(data?.orders)}`,
      `Ticket Médio,${fmt(data?.ticket)}`,
      '',
      '--- DETALHE DIÁRIO ---',
      'Data,Pedidos,Receita Bruta,Cancelamentos,Receita Líquida,Ticket Médio',
      ...rows.map(r =>
        `${r.date ? new Date(r.date).toLocaleDateString('pt-BR') : r.date},${r.orders},${r.gross.toFixed(2)},${r.cancelled.toFixed(2)},${r.net.toFixed(2)},${r.ticket.toFixed(2)}`
      ),
    ].join('\n')
    const blob = new Blob(['\uFEFF' + header], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url
    a.download = `faturamento_${startDate}_${endDate}.csv`; a.click(); URL.revokeObjectURL(url)
  }

  const totalRows = {
    orders: rows.reduce((s, r) => s + r.orders, 0),
    gross:  rows.reduce((s, r) => s + r.gross, 0),
    cancelled: rows.reduce((s, r) => s + r.cancelled, 0),
    net:    rows.reduce((s, r) => s + r.net, 0),
  }

  return (
    <div className="space-y-5">

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Relatório de Faturamento</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Receita bruta, líquida, cancelamentos e ticket médio por período</p>
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
        <div className="flex items-center gap-2 mb-3">
          <Calendar className="w-4 h-4 text-gray-400" />
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Período e Agrupamento</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Data inicial</label>
            <input type="date" value={startDate} onChange={e => setStart(e.target.value)}
              className="w-full rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-primary-500" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Data final</label>
            <input type="date" value={endDate} onChange={e => setEnd(e.target.value)}
              className="w-full rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-primary-500" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Agrupar por</label>
            <select value={groupBy} onChange={e => setGroupBy(e.target.value)}
              className="w-full rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-primary-500">
              <option value="day">Dia</option>
              <option value="week">Semana</option>
              <option value="month">Mês</option>
            </select>
          </div>
          <div className="flex items-end">
            <div className="w-full p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
              <p className="text-xs text-blue-600 dark:text-blue-400">
                CSV: super planilha com cabeçalho e totais.<br />
                PDF: relatório formatado para impressão.
              </p>
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl text-sm text-amber-700 dark:text-amber-400">
          <AlertCircle className="w-4 h-4 shrink-0" /> {error}
        </div>
      )}

      {/* KPIs */}
      {data && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard label="Receita Bruta"     value={fmt(data.gross)}     sub="total do período"         color="text-blue-600 dark:text-blue-400"    bg="bg-blue-50 dark:bg-blue-900/20"    trend={data.growth} />
          <KpiCard label="Receita Líquida"   value={fmt(data.net)}       sub="descontando cancelamentos" color="text-emerald-600 dark:text-emerald-400" bg="bg-emerald-50 dark:bg-emerald-900/20" />
          <KpiCard label="Cancelamentos"     value={fmt(data.cancelled)} sub={`${data.gross > 0 ? ((data.cancelled/data.gross)*100).toFixed(1) : 0}% da bruta`} color="text-red-600 dark:text-red-400" bg="bg-red-50 dark:bg-red-900/20" />
          <KpiCard label="Ticket Médio"      value={fmt(data.ticket)}    sub={`${fmtN(data.orders)} pedidos`} color="text-violet-600 dark:text-violet-400" bg="bg-violet-50 dark:bg-violet-900/20" />
        </div>
      )}

      {/* Preview tabela */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-700 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Preview do Relatório</h3>
            <p className="text-xs text-gray-400 mt-0.5">Prévia dos dados · exporte para análise completa</p>
          </div>
          <DollarSign className="w-4 h-4 text-gray-300 dark:text-gray-600" />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50">
                {['Período', 'Pedidos', 'Receita Bruta', 'Cancelamentos', 'Receita Líquida', 'Ticket Médio', '% Cancelamento'].map((h, i) => (
                  <th key={h} className={`px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide ${i > 0 ? 'text-right' : 'text-left'}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {loading ? (
                [...Array(5)].map((_, i) => (
                  <tr key={i}>{[...Array(7)].map((_, j) => (
                    <td key={j} className="px-4 py-3"><div className="h-4 bg-gray-100 dark:bg-gray-700 rounded animate-pulse" /></td>
                  ))}</tr>
                ))
              ) : rows.length === 0 ? (
                <tr><td colSpan={7} className="px-4 py-10 text-center text-sm text-gray-400 dark:text-gray-500">
                  Sem dados no período. Ajuste as datas ou exporte diretamente.
                </td></tr>
              ) : (
                rows.map((row, idx) => {
                  const cancelPct = row.gross > 0 ? (row.cancelled / row.gross) * 100 : 0
                  return (
                    <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                      <td className="px-4 py-3 font-medium text-gray-700 dark:text-gray-300 whitespace-nowrap">
                        {row.date ? (isNaN(new Date(row.date)) ? row.date : new Date(row.date).toLocaleDateString('pt-BR')) : '—'}
                      </td>
                      <td className="px-4 py-3 text-right text-gray-700 dark:text-gray-300">{fmtN(row.orders)}</td>
                      <td className="px-4 py-3 text-right font-medium text-blue-600 dark:text-blue-400">{fmt(row.gross)}</td>
                      <td className="px-4 py-3 text-right text-red-600 dark:text-red-400">{fmt(row.cancelled)}</td>
                      <td className="px-4 py-3 text-right font-semibold text-emerald-600 dark:text-emerald-400">{fmt(row.net)}</td>
                      <td className="px-4 py-3 text-right text-gray-600 dark:text-gray-400">{fmt(row.ticket)}</td>
                      <td className="px-4 py-3 text-right">
                        <span className={`text-xs font-medium ${cancelPct > 10 ? 'text-red-600 dark:text-red-400' : cancelPct > 5 ? 'text-amber-600 dark:text-amber-400' : 'text-gray-500 dark:text-gray-400'}`}>
                          {cancelPct.toFixed(1)}%
                        </span>
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
            {rows.length > 0 && (
              <tfoot>
                <tr className="border-t-2 border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700/50 font-semibold">
                  <td className="px-4 py-3 text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">TOTAL</td>
                  <td className="px-4 py-3 text-right text-gray-800 dark:text-gray-200">{fmtN(totalRows.orders)}</td>
                  <td className="px-4 py-3 text-right text-blue-700 dark:text-blue-400">{fmt(totalRows.gross)}</td>
                  <td className="px-4 py-3 text-right text-red-700 dark:text-red-400">{fmt(totalRows.cancelled)}</td>
                  <td className="px-4 py-3 text-right text-emerald-700 dark:text-emerald-400">{fmt(totalRows.net)}</td>
                  <td className="px-4 py-3 text-right text-gray-700 dark:text-gray-300">{fmt(totalRows.orders ? totalRows.gross / totalRows.orders : 0)}</td>
                  <td className="px-4 py-3 text-right text-gray-700 dark:text-gray-300">
                    {totalRows.gross > 0 ? `${((totalRows.cancelled / totalRows.gross) * 100).toFixed(1)}%` : '—'}
                  </td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      </div>

    </div>
  )
}
