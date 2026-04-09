/**
 * Relatórios › PIX — Conciliação e análise de transações PIX
 */

import { useState, useEffect } from 'react'
import { Download, FileText, QrCode, RefreshCw, AlertCircle, CheckCircle, Clock, XCircle } from 'lucide-react'
import { apiRequest } from '../../utils/api'

const fmt = (v) =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 2 }).format(v || 0)
const fmtN = (v) => new Intl.NumberFormat('pt-BR').format(v || 0)

const STATUS = {
  paid:     { label: 'Pago',     color: 'text-emerald-600 dark:text-emerald-400', icon: CheckCircle },
  received: { label: 'Recebido', color: 'text-emerald-600 dark:text-emerald-400', icon: CheckCircle },
  pending:  { label: 'Pendente', color: 'text-amber-600 dark:text-amber-400',     icon: Clock },
  failed:   { label: 'Falhou',   color: 'text-red-600 dark:text-red-400',          icon: XCircle },
}

export default function RelPIX() {
  const [loading, setLoading]   = useState(false)
  const [exporting, setExporting] = useState(false)
  const [transactions, setTransactions] = useState([])
  const [summary, setSummary]   = useState(null)
  const [error, setError]       = useState('')
  const [startDate, setStart]   = useState(() => { const d = new Date(); d.setDate(1); return d.toISOString().split('T')[0] })
  const [endDate, setEnd]       = useState(() => new Date().toISOString().split('T')[0])

  useEffect(() => { fetchPreview() }, [startDate, endDate])

  const fetchPreview = async () => {
    try {
      setLoading(true); setError('')
      // Tenta endpoint de relatório PIX
      const res = await apiRequest(`financial/pix?start=${startDate}&end=${endDate}`)
      const list = Array.isArray(res) ? res : (res?.items || res?.transactions || [])
      setTransactions(list)
      const paid = list.filter(t => t.status === 'paid' || t.status === 'received')
      setSummary({
        total: paid.reduce((s, t) => s + (t.amount || t.value || 0), 0),
        count: list.length,
        paid: paid.length,
        pending: list.filter(t => t.status === 'pending').length,
        failed: list.filter(t => t.status === 'failed').length,
        avgValue: paid.length > 0 ? paid.reduce((s, t) => s + (t.amount || t.value || 0), 0) / paid.length : 0,
      })
    } catch {
      // fallback: orders com pagamento PIX
      try {
        const orders = await apiRequest(`orders?payment_method=pix&start_date=${startDate}&end_date=${endDate}`)
        const list = Array.isArray(orders) ? orders : (orders?.items || [])
        const mapped = list.map(o => ({
          id: o.id, created_at: o.created_at,
          description: `Pedido #${o.order_number || o.id}`,
          payer: o.customer_name || o.customer_phone || '—',
          amount: o.total_price || o.total || 0,
          status: o.status === 'delivered' ? 'paid' : 'pending',
        }))
        setTransactions(mapped)
        const total = mapped.filter(t => t.status === 'paid').reduce((s, t) => s + t.amount, 0)
        setSummary({ total, count: mapped.length, paid: mapped.filter(t => t.status === 'paid').length, pending: mapped.filter(t => t.status === 'pending').length, failed: 0, avgValue: mapped.length ? total / mapped.length : 0 })
        setError('Dados estimados de pedidos PIX. Configure /financial/pix para dados exatos.')
      } catch {
        setSummary({ total: 0, count: 0, paid: 0, pending: 0, failed: 0, avgValue: 0 })
        setTransactions([])
        setError('Sem dados PIX disponíveis no período.')
      }
    } finally { setLoading(false) }
  }

  const handleExport = async (format) => {
    try {
      setExporting(true)
      const token = localStorage.getItem('token')
      const base  = import.meta.env.VITE_API_URL || 'http://192.168.10.167:8000/api'
      const res   = await fetch(`${base}/owner/reports/pix?start_date=${startDate}&end_date=${endDate}&format=${format}`, { headers: { Authorization: `Bearer ${token}` } })
      if (!res.ok) { exportLocalCSV(); return }
      const blob = await res.blob(); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url
      a.download = `pix_${startDate}_${endDate}.${format}`; a.click(); URL.revokeObjectURL(url)
    } catch { exportLocalCSV() }
    finally { setExporting(false) }
  }

  const exportLocalCSV = () => {
    const header = [
      '=== RELATÓRIO PIX ===',
      `Período: ${new Date(startDate).toLocaleDateString('pt-BR')} a ${new Date(endDate).toLocaleDateString('pt-BR')}`,
      `Gerado em: ${new Date().toLocaleString('pt-BR')}`,
      '',
      '--- RESUMO ---',
      `Total Recebido,${fmt(summary?.total)}`,
      `Transações,${summary?.count}`,
      `Pagas,${summary?.paid}`,
      `Pendentes,${summary?.pending}`,
      `Falhas,${summary?.failed}`,
      `Valor Médio,${fmt(summary?.avgValue)}`,
      '',
      '--- DETALHE ---',
      'Data,Descrição,Pagador,Valor,Status',
      ...transactions.map(t =>
        `${t.created_at ? new Date(t.created_at).toLocaleString('pt-BR') : '—'},"${t.description||''}","${t.payer||''}",${(t.amount||t.value||0).toFixed(2)},${t.status||''}`
      ),
    ].join('\n')
    const blob = new Blob(['\uFEFF' + header], { type: 'text/csv;charset=utf-8;' })
    const url  = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url
    a.download = `pix_${startDate}_${endDate}.csv`; a.click(); URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-5">

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Relatório PIX</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Conciliação e análise de recebimentos via PIX</p>
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
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {[
            { label: 'Total Recebido', value: fmt(summary.total), color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-50 dark:bg-emerald-900/20' },
            { label: 'Transações',     value: fmtN(summary.count),     color: 'text-gray-900 dark:text-white',          bg: 'bg-white dark:bg-gray-800' },
            { label: 'Pagas',          value: fmtN(summary.paid),      color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-white dark:bg-gray-800' },
            { label: 'Pendentes',      value: fmtN(summary.pending),   color: 'text-amber-600 dark:text-amber-400',     bg: 'bg-white dark:bg-gray-800' },
            { label: 'Falhas',         value: fmtN(summary.failed),    color: 'text-red-600 dark:text-red-400',          bg: 'bg-white dark:bg-gray-800' },
            { label: 'Valor Médio',    value: fmt(summary.avgValue),   color: 'text-blue-600 dark:text-blue-400',        bg: 'bg-blue-50 dark:bg-blue-900/20' },
          ].map(({ label, value, color, bg }) => (
            <div key={label} className={`${bg} border border-gray-200 dark:border-gray-700 rounded-xl p-3`}>
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400 leading-tight">{label}</p>
              <p className={`mt-1 text-lg font-bold ${color}`}>{value}</p>
            </div>
          ))}
        </div>
      )}

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-700 flex items-center gap-2">
          <QrCode className="w-4 h-4 text-emerald-500" />
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Transações do Período</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 dark:bg-gray-700/50">
                {['Data/Hora', 'Descrição', 'Pagador', 'Status', 'Valor'].map((h, i) => (
                  <th key={h} className={`px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide ${i === 4 ? 'text-right' : 'text-left'}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {loading ? (
                [...Array(5)].map((_, i) => <tr key={i}>{[...Array(5)].map((_, j) => <td key={j} className="px-4 py-3"><div className="h-4 bg-gray-100 dark:bg-gray-700 rounded animate-pulse" /></td>)}</tr>)
              ) : transactions.length === 0 ? (
                <tr><td colSpan={5} className="px-4 py-10 text-center text-sm text-gray-400 dark:text-gray-500">Nenhuma transação PIX no período.</td></tr>
              ) : (
                transactions.map((t, idx) => {
                  const st = STATUS[t.status] || STATUS.pending
                  const StIcon = st.icon
                  return (
                    <tr key={t.id || idx} className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                      <td className="px-4 py-3 text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">
                        {t.created_at ? new Date(t.created_at).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—'}
                      </td>
                      <td className="px-4 py-3 text-gray-800 dark:text-gray-200">{t.description || '—'}</td>
                      <td className="px-4 py-3 text-gray-600 dark:text-gray-400">{t.payer || '—'}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1 text-xs font-medium ${st.color}`}>
                          <StIcon className="w-3 h-3" />{st.label}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right font-semibold text-emerald-600 dark:text-emerald-400">
                        {fmt(t.amount || t.value || 0)}
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
            {transactions.length > 0 && (
              <tfoot>
                <tr className="border-t-2 border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700/50 font-semibold">
                  <td colSpan={4} className="px-4 py-3 text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">{transactions.length} transações</td>
                  <td className="px-4 py-3 text-right text-emerald-700 dark:text-emerald-400">{fmt(summary?.total)}</td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      </div>

    </div>
  )
}
