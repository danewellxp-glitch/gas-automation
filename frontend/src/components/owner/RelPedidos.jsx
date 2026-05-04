/**
 * Relatórios › Pedidos — Análise completa de pedidos por produto, bairro e status
 */

import { useState, useEffect } from 'react'
import { Download, FileText, Calendar, Package, RefreshCw, AlertCircle } from 'lucide-react'
import { apiRequest } from '../../utils/api'

const fmt = (v) =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 2 }).format(v || 0)
const fmtN = (v) => new Intl.NumberFormat('pt-BR').format(v || 0)

const STATUS_LABELS = {
  pending: 'Pendente', approved: 'Aprovado', in_delivery: 'Em Entrega',
  delivered: 'Entregue', cancelled: 'Cancelado', paid: 'Pago',
}

export default function RelPedidos() {
  const [loading, setLoading]   = useState(false)
  const [exporting, setExporting] = useState(false)
  const [data, setData]         = useState(null)
  const [error, setError]       = useState('')
  const [startDate, setStart]   = useState(() => { const d = new Date(); d.setDate(1); return d.toISOString().split('T')[0] })
  const [endDate, setEnd]       = useState(() => new Date().toISOString().split('T')[0])
  const [activeTab, setTab]     = useState('products')

  useEffect(() => { fetchPreview() }, [startDate, endDate])

  const fetchPreview = async () => {
    try {
      setLoading(true); setError('')
      const res = await apiRequest('owner/dashboard?period=month')
      const ops = res?.cards?.operational || {}
      const topProducts = res?.top_products || []
      const byBairro    = res?.orders_by_bairro || []
      const byType      = res?.orders_by_type || {}
      setData({ ops, topProducts, byBairro, byType })
    } catch (err) {
      setError(err.message || 'Erro ao carregar dados.')
    } finally { setLoading(false) }
  }

  const handleExport = async (format) => {
    try {
      setExporting(true)
      const token = localStorage.getItem('token')
      const base = import.meta.env.VITE_API_URL || 'http://192.168.10.167:5688/api'
      const url = `${base}/owner/reports/orders?start_date=${startDate}&end_date=${endDate}&format=${format}`
      const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      if (!res.ok) { exportLocalCSV(); return }
      const blob = await res.blob()
      const blobUrl = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = blobUrl
      a.download = `pedidos_${startDate}_${endDate}.${format}`; a.click(); URL.revokeObjectURL(blobUrl)
    } catch { exportLocalCSV() }
    finally { setExporting(false) }
  }

  const exportLocalCSV = () => {
    if (!data) return
    const lines = [
      '=== RELATÓRIO DE PEDIDOS ===',
      `Período: ${new Date(startDate).toLocaleDateString('pt-BR')} a ${new Date(endDate).toLocaleDateString('pt-BR')}`,
      `Gerado em: ${new Date().toLocaleString('pt-BR')}`,
      '',
      '--- RESUMO ---',
      `Total de Pedidos,${data.ops.orders_today || 0}`,
      `Entregues,${data.ops.orders_completed || 0}`,
      `Cancelados,${data.ops.orders_cancelled_today || 0}`,
      '',
      '--- PRODUTOS MAIS VENDIDOS ---',
      'Produto,Quantidade,Receita',
      ...data.topProducts.map(p => `"${p.name||p.code}",${p.quantity||0},${(p.revenue||0).toFixed(2)}`),
      '',
      '--- POR BAIRRO ---',
      'Bairro,Pedidos',
      ...data.byBairro.map(b => `"${b.bairro||b.neighborhood||b.name}",${b.count||b.orders||0}`),
    ].join('\n')
    const blob = new Blob(['\uFEFF' + lines], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url
    a.download = `pedidos_${startDate}_${endDate}.csv`; a.click(); URL.revokeObjectURL(url)
  }

  const TABS = [
    { key: 'products', label: 'Por Produto' },
    { key: 'bairro',   label: 'Por Bairro' },
    { key: 'type',     label: 'Por Tipo' },
  ]

  return (
    <div className="space-y-5">

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Relatório de Pedidos</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Análise por produto, bairro e tipo de entrega</p>
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

      {/* KPIs */}
      {data && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            { label: 'Total Pedidos', value: fmtN(data.ops.orders_today || 0),       color: 'text-gray-900 dark:text-white', bg: 'bg-white dark:bg-gray-800' },
            { label: 'Entregues',     value: fmtN(data.ops.orders_completed || 0),   color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-50 dark:bg-emerald-900/20' },
            { label: 'Cancelados',    value: fmtN(data.ops.orders_cancelled_today||0),color: 'text-red-600 dark:text-red-400', bg: 'bg-red-50 dark:bg-red-900/20' },
            { label: 'Produtos únicos',value: fmtN(data.topProducts.length),         color: 'text-blue-600 dark:text-blue-400', bg: 'bg-blue-50 dark:bg-blue-900/20' },
          ].map(({ label, value, color, bg }) => (
            <div key={label} className={`${bg} border border-gray-200 dark:border-gray-700 rounded-xl p-4`}>
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">{label}</p>
              <p className={`mt-1.5 text-2xl font-bold ${color}`}>{value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="flex border-b border-gray-100 dark:border-gray-700">
          {TABS.map(({ key, label }) => (
            <button key={key} onClick={() => setTab(key)}
              className={`px-5 py-3.5 text-sm font-medium border-b-2 transition-colors ${activeTab === key ? 'border-primary-500 text-primary-600 dark:text-primary-400 bg-primary-50/50 dark:bg-primary-900/10' : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}`}>
              {label}
            </button>
          ))}
        </div>

        <div className="overflow-x-auto">
          {activeTab === 'products' && data && (
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 dark:bg-gray-700/50">
                  {['#', 'Produto', 'Código', 'Qtd. Vendida', 'Receita', '% do Total'].map((h, i) => (
                    <th key={h} className={`px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide ${i > 2 ? 'text-right' : 'text-left'}`}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {loading ? [...Array(5)].map((_, i) => (
                  <tr key={i}>{[...Array(6)].map((_, j) => <td key={j} className="px-4 py-3"><div className="h-4 bg-gray-100 dark:bg-gray-700 rounded animate-pulse" /></td>)}</tr>
                )) : data.topProducts.length === 0 ? (
                  <tr><td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-400 dark:text-gray-500">Sem dados de produtos no período.</td></tr>
                ) : (() => {
                  const totalQty = data.topProducts.reduce((s, p) => s + (p.quantity || 0), 0)
                  const totalRev = data.topProducts.reduce((s, p) => s + (p.revenue || 0), 0)
                  return data.topProducts.map((p, idx) => (
                    <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                      <td className="px-4 py-3 text-gray-400 text-sm">{idx + 1}</td>
                      <td className="px-4 py-3 font-medium text-gray-800 dark:text-gray-200">{p.name || p.product_name || '—'}</td>
                      <td className="px-4 py-3 text-xs text-gray-400 font-mono">{p.code || '—'}</td>
                      <td className="px-4 py-3 text-right font-semibold text-gray-800 dark:text-gray-200">{fmtN(p.quantity || 0)}</td>
                      <td className="px-4 py-3 text-right text-emerald-600 dark:text-emerald-400 font-semibold">{fmt(p.revenue || 0)}</td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <div className="w-16 h-1.5 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
                            <div className="h-full bg-primary-500 rounded-full" style={{ width: `${totalQty > 0 ? (p.quantity / totalQty) * 100 : 0}%` }} />
                          </div>
                          <span className="text-xs text-gray-500 dark:text-gray-400 w-10 text-right">
                            {totalQty > 0 ? `${((p.quantity / totalQty) * 100).toFixed(1)}%` : '—'}
                          </span>
                        </div>
                      </td>
                    </tr>
                  ))
                })()}
              </tbody>
              {data.topProducts.length > 0 && (
                <tfoot>
                  <tr className="border-t-2 border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700/50 font-semibold">
                    <td colSpan={3} className="px-4 py-3 text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">TOTAL</td>
                    <td className="px-4 py-3 text-right text-gray-800 dark:text-gray-200">{fmtN(data.topProducts.reduce((s,p)=>s+(p.quantity||0),0))}</td>
                    <td className="px-4 py-3 text-right text-emerald-700 dark:text-emerald-400">{fmt(data.topProducts.reduce((s,p)=>s+(p.revenue||0),0))}</td>
                    <td className="px-4 py-3 text-right text-gray-500 dark:text-gray-400">100%</td>
                  </tr>
                </tfoot>
              )}
            </table>
          )}

          {activeTab === 'bairro' && data && (
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 dark:bg-gray-700/50">
                  {['#', 'Bairro', 'Pedidos', '% do Total'].map((h, i) => (
                    <th key={h} className={`px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide ${i > 1 ? 'text-right' : 'text-left'}`}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {data.byBairro.length === 0 ? (
                  <tr><td colSpan={4} className="px-4 py-8 text-center text-sm text-gray-400 dark:text-gray-500">Sem dados por bairro.</td></tr>
                ) : (() => {
                  const totalOrders = data.byBairro.reduce((s, b) => s + (b.count || b.orders || 0), 0)
                  return data.byBairro.sort((a, b) => (b.count || b.orders || 0) - (a.count || a.orders || 0)).map((b, idx) => {
                    const cnt = b.count || b.orders || 0
                    return (
                      <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                        <td className="px-4 py-3 text-gray-400 text-sm">{idx + 1}</td>
                        <td className="px-4 py-3 font-medium text-gray-800 dark:text-gray-200">{b.bairro || b.neighborhood || b.name || '—'}</td>
                        <td className="px-4 py-3 text-right font-semibold text-gray-800 dark:text-gray-200">{fmtN(cnt)}</td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <div className="w-16 h-1.5 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
                              <div className="h-full bg-blue-500 rounded-full" style={{ width: `${totalOrders > 0 ? (cnt / totalOrders) * 100 : 0}%` }} />
                            </div>
                            <span className="text-xs text-gray-500 dark:text-gray-400 w-10 text-right">
                              {totalOrders > 0 ? `${((cnt / totalOrders) * 100).toFixed(1)}%` : '—'}
                            </span>
                          </div>
                        </td>
                      </tr>
                    )
                  })
                })()}
              </tbody>
            </table>
          )}

          {activeTab === 'type' && data && (
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 dark:bg-gray-700/50">
                  {['Tipo', 'Quantidade', '% do Total'].map((h, i) => (
                    <th key={h} className={`px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide ${i > 0 ? 'text-right' : 'text-left'}`}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {Object.keys(data.byType).length === 0 ? (
                  <tr><td colSpan={3} className="px-4 py-8 text-center text-sm text-gray-400 dark:text-gray-500">Sem dados por tipo.</td></tr>
                ) : (() => {
                  const total = Object.values(data.byType).reduce((s, v) => s + v, 0)
                  return Object.entries(data.byType).sort(([,a],[,b]) => b-a).map(([type, count]) => (
                    <tr key={type} className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                      <td className="px-4 py-3 font-medium text-gray-800 dark:text-gray-200 capitalize">{STATUS_LABELS[type] || type}</td>
                      <td className="px-4 py-3 text-right font-semibold text-gray-800 dark:text-gray-200">{fmtN(count)}</td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <div className="w-20 h-1.5 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
                            <div className="h-full bg-violet-500 rounded-full" style={{ width: `${total > 0 ? (count / total) * 100 : 0}%` }} />
                          </div>
                          <span className="text-xs text-gray-500 dark:text-gray-400 w-10 text-right">
                            {total > 0 ? `${((count / total) * 100).toFixed(1)}%` : '—'}
                          </span>
                        </div>
                      </td>
                    </tr>
                  ))
                })()}
              </tbody>
            </table>
          )}
        </div>
      </div>

    </div>
  )
}

