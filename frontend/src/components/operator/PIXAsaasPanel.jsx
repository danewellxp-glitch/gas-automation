/**
 * PIXAsaasPanel - Consulta de PIX recebidos via Asaas
 * Permite atendentes cruzarem pagamentos PIX com pedidos.
 */

import { useState, useEffect, useCallback } from 'react'
import { QrCode, RefreshCw, Download, Search, CheckCircle2, Clock, XCircle, AlertCircle } from 'lucide-react'
import { toast } from 'react-hot-toast'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

const STATUS_CONFIG = {
    RECEIVED:          { label: 'Recebido',    color: 'emerald', icon: CheckCircle2 },
    CONFIRMED:         { label: 'Confirmado',  color: 'emerald', icon: CheckCircle2 },
    PENDING:           { label: 'Pendente',    color: 'amber',   icon: Clock },
    OVERDUE:           { label: 'Vencido',     color: 'red',     icon: XCircle },
    REFUNDED:          { label: 'Devolvido',   color: 'purple',  icon: AlertCircle },
    REFUND_REQUESTED:  { label: 'Dev. solicit.',color: 'purple', icon: AlertCircle },
}

function StatusBadge({ status }) {
    const cfg = STATUS_CONFIG[status] || { label: status, color: 'gray', icon: AlertCircle }
    const Icon = cfg.icon
    return (
        <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium bg-${cfg.color}-100 text-${cfg.color}-700`}>
            <Icon className="h-3 w-3" />
            {cfg.label}
        </span>
    )
}

function formatDate(dateStr) {
    if (!dateStr) return '—'
    const d = new Date(dateStr)
    return d.toLocaleDateString('pt-BR') + ' ' + d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}

function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value || 0)
}

export default function PIXAsaasPanel() {
    const [payments, setPayments] = useState([])
    const [loading, setLoading] = useState(false)
    const [exporting, setExporting] = useState(false)
    const [dateFrom, setDateFrom] = useState(() => {
        const d = new Date()
        d.setDate(d.getDate() - 7)
        return d.toISOString().split('T')[0]
    })
    const [dateTo, setDateTo] = useState(() => new Date().toISOString().split('T')[0])
    const [statusFilter, setStatusFilter] = useState('')
    const [search, setSearch] = useState('')
    const token = localStorage.getItem('token')

    const load = useCallback(async () => {
        setLoading(true)
        try {
            let url = `${API_BASE}/financeiro/pix?`
            if (dateFrom)     url += `date_from=${dateFrom}&`
            if (dateTo)       url += `date_to=${dateTo}&`
            if (statusFilter) url += `status=${statusFilter}&`
            const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } })
            if (!res.ok) throw new Error()
            const data = await res.json()
            // API retorna { data: [...], totalCount, hasMore }
            setPayments(data.data || data.payments || (Array.isArray(data) ? data : []))
        } catch {
            toast.error('Erro ao consultar PIX Asaas')
        } finally {
            setLoading(false)
        }
    }, [dateFrom, dateTo, statusFilter, token])

    useEffect(() => { load() }, [load])

    const handleExport = async () => {
        setExporting(true)
        try {
            let url = `${API_BASE}/financeiro/pix/exportar-excel?`
            if (dateFrom)     url += `date_from=${dateFrom}&`
            if (dateTo)       url += `date_to=${dateTo}&`
            if (statusFilter) url += `status=${statusFilter}&`
            const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } })
            if (!res.ok) throw new Error()
            const blob = await res.blob()
            const a = document.createElement('a')
            a.href = URL.createObjectURL(blob)
            a.download = `pix_asaas_${dateFrom}_${dateTo}.xlsx`
            a.click()
            toast.success('Planilha exportada!')
        } catch {
            toast.error('Erro ao exportar')
        } finally {
            setExporting(false)
        }
    }

    const filtered = payments.filter(p => {
        if (!search) return true
        const t = search.toLowerCase()
        return (
            (p.description || '').toLowerCase().includes(t) ||
            (p.externalReference || '').toLowerCase().includes(t) ||
            String(p.value || '').includes(t)
        )
    })

    const total = filtered.reduce((sum, p) => {
        if (['RECEIVED', 'CONFIRMED'].includes(p.status)) return sum + (p.value || 0)
        return sum
    }, 0)

    return (
        <div className="space-y-4">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                        <QrCode className="h-5 w-5 text-emerald-600" />
                        PIX Asaas
                    </h2>
                    <p className="text-xs text-gray-500 mt-0.5">Pagamentos PIX recebidos via gateway Asaas</p>
                </div>
                <div className="flex gap-2">
                    <button onClick={handleExport} disabled={exporting || loading}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 disabled:opacity-50">
                        <Download className="h-3.5 w-3.5" />
                        {exporting ? 'Exportando...' : 'Excel'}
                    </button>
                    <button onClick={load} disabled={loading}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-200 bg-white text-gray-600 hover:bg-gray-50 disabled:opacity-50">
                        <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
                        Atualizar
                    </button>
                </div>
            </div>

            {/* Filtros */}
            <div className="flex flex-wrap gap-2">
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-400" />
                    <input type="text" placeholder="Pagador, descrição ou ref."
                        value={search} onChange={e => setSearch(e.target.value)}
                        className="rounded-lg border border-gray-200 pl-8 pr-3 py-2 text-sm w-52 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 focus:outline-none" />
                </div>
                <div className="flex items-center gap-1.5">
                    <label className="text-xs text-gray-500">De:</label>
                    <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)}
                        className="rounded-lg border border-gray-200 px-2 py-2 text-sm focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 focus:outline-none" />
                </div>
                <div className="flex items-center gap-1.5">
                    <label className="text-xs text-gray-500">Até:</label>
                    <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)}
                        className="rounded-lg border border-gray-200 px-2 py-2 text-sm focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 focus:outline-none" />
                </div>
                <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
                    className="rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 focus:outline-none">
                    <option value="">Todos os status</option>
                    <option value="RECEIVED">Recebido</option>
                    <option value="CONFIRMED">Confirmado</option>
                    <option value="PENDING">Pendente</option>
                    <option value="OVERDUE">Vencido</option>
                </select>
            </div>

            {/* Total recebido */}
            {filtered.length > 0 && (
                <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 flex items-center justify-between">
                    <span className="text-sm text-emerald-700 font-medium">Total recebido no período</span>
                    <span className="text-lg font-bold text-emerald-800">{formatCurrency(total)}</span>
                </div>
            )}

            {/* Tabela */}
            {loading ? (
                <div className="flex items-center justify-center py-16">
                    <div className="h-7 w-7 animate-spin rounded-full border-2 border-gray-200 border-t-emerald-600" />
                </div>
            ) : filtered.length === 0 ? (
                <div className="rounded-xl border border-gray-200 bg-white py-16 text-center">
                    <QrCode className="mx-auto h-10 w-10 text-gray-300 mb-3" />
                    <p className="text-sm font-medium text-gray-500">Nenhum PIX encontrado</p>
                    <p className="text-xs text-gray-400 mt-1">Ajuste os filtros de data ou status</p>
                </div>
            ) : (
                <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-100">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-3 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-gray-500">Data</th>
                                    <th className="px-3 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-gray-500">Pagador</th>
                                    <th className="px-3 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-gray-500">Descrição / Ref.</th>
                                    <th className="px-3 py-2.5 text-right text-xs font-medium uppercase tracking-wide text-gray-500">Valor</th>
                                    <th className="px-3 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-gray-500">Status</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-50">
                                {filtered.map((p, i) => (
                                    <tr key={p.id || i} className="hover:bg-gray-50 transition-colors">
                                        <td className="px-3 py-2.5 text-xs text-gray-600 whitespace-nowrap">
                                            {formatDate(p.paymentDate || p.confirmedDate || p.dueDate)}
                                        </td>
                                        <td className="px-3 py-2.5 text-sm text-gray-900">
                                            {p.externalReference || '—'}
                                        </td>
                                        <td className="px-3 py-2.5 text-xs text-gray-500 max-w-xs truncate">
                                            {p.description || p.externalReference || '—'}
                                        </td>
                                        <td className="px-3 py-2.5 text-sm font-semibold text-gray-900 text-right whitespace-nowrap">
                                            {formatCurrency(p.value)}
                                        </td>
                                        <td className="px-3 py-2.5">
                                            <StatusBadge status={p.status} />
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    )
}
