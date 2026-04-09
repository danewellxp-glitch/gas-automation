/**
 * ComodatoPanel - Controle de equipamentos emprestados a clientes
 */

import { useState, useEffect, useCallback } from 'react'
import {
    Package, RefreshCw, Search, CheckCircle2,
    Clock, AlertTriangle, User, Hash,
} from 'lucide-react'
import { toast } from 'react-hot-toast'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

const STATUS_CONFIG = {
    ativo:     { label: 'Ativo',      color: 'blue',    icon: Clock },
    devolvido: { label: 'Devolvido',  color: 'emerald', icon: CheckCircle2 },
    perdido:   { label: 'Perdido',    color: 'red',     icon: AlertTriangle },
}

function StatusBadge({ status }) {
    const cfg = STATUS_CONFIG[status] || { label: status, color: 'gray', icon: Package }
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
    return new Date(dateStr).toLocaleDateString('pt-BR')
}

function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value || 0)
}

export default function ComodatoPanel() {
    const [items, setItems] = useState([])
    const [summary, setSummary] = useState([])
    const [loading, setLoading] = useState(false)
    const [statusFilter, setStatusFilter] = useState('ativo')
    const [search, setSearch] = useState('')
    const token = localStorage.getItem('token')

    const load = useCallback(async () => {
        setLoading(true)
        try {
            let url = `${API_BASE}/comodatos?`
            if (statusFilter) url += `status=${statusFilter}&`
            const [res, sumRes] = await Promise.all([
                fetch(url, { headers: { Authorization: `Bearer ${token}` } }),
                fetch(`${API_BASE}/comodatos/ativos/count`, { headers: { Authorization: `Bearer ${token}` } }),
            ])
            if (!res.ok) throw new Error()
            const data = await res.json()
            setItems(data.items || data || [])
            if (sumRes.ok) {
                const sumData = await sumRes.json()
                setSummary(sumData.summary || sumData || [])
            }
        } catch {
            toast.error('Erro ao carregar comodatos')
        } finally {
            setLoading(false)
        }
    }, [statusFilter, token])

    useEffect(() => { load() }, [load])

    const handleDevolver = async (id) => {
        if (!confirm('Confirmar devolução deste equipamento?')) return
        try {
            const res = await fetch(`${API_BASE}/comodatos/${id}/devolver`, {
                method: 'POST',
                headers: { Authorization: `Bearer ${token}` },
            })
            if (!res.ok) throw new Error()
            toast.success('Equipamento devolvido!')
            load()
        } catch {
            toast.error('Erro ao registrar devolução')
        }
    }

    const filtered = items.filter(item => {
        if (!search) return true
        const t = search.toLowerCase()
        return (
            (item.customer_name || '').toLowerCase().includes(t) ||
            (item.equipment_type || '').toLowerCase().includes(t) ||
            (item.serial_number || '').toLowerCase().includes(t)
        )
    })

    return (
        <div className="space-y-4">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                        <Package className="h-5 w-5 text-indigo-600" />
                        Comodatos
                    </h2>
                    <p className="text-xs text-gray-500 mt-0.5">Equipamentos emprestados a clientes</p>
                </div>
                <button onClick={load} disabled={loading}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-200 bg-white text-gray-600 hover:bg-gray-50 disabled:opacity-50">
                    <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
                    Atualizar
                </button>
            </div>

            {/* Resumo por tipo */}
            {summary.length > 0 && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {summary.map((s, i) => (
                        <div key={i} className="rounded-xl border border-indigo-100 bg-indigo-50 p-3">
                            <p className="text-xl font-bold text-indigo-700">{s.count || s.quantidade}</p>
                            <p className="text-xs text-indigo-600 truncate">{s.equipment_type || s.tipo}</p>
                        </div>
                    ))}
                </div>
            )}

            {/* Filtros */}
            <div className="flex flex-wrap gap-2">
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-400" />
                    <input type="text" placeholder="Cliente, equipamento ou série"
                        value={search} onChange={e => setSearch(e.target.value)}
                        className="rounded-lg border border-gray-200 pl-8 pr-3 py-2 text-sm w-52 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none" />
                </div>
                <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
                    className="rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none">
                    <option value="">Todos</option>
                    <option value="ativo">Ativos</option>
                    <option value="devolvido">Devolvidos</option>
                    <option value="perdido">Perdidos</option>
                </select>
            </div>

            {/* Lista */}
            {loading ? (
                <div className="flex items-center justify-center py-16">
                    <div className="h-7 w-7 animate-spin rounded-full border-2 border-gray-200 border-t-indigo-600" />
                </div>
            ) : filtered.length === 0 ? (
                <div className="rounded-xl border border-gray-200 bg-white py-16 text-center">
                    <Package className="mx-auto h-10 w-10 text-gray-300 mb-3" />
                    <p className="text-sm font-medium text-gray-500">Nenhum comodato encontrado</p>
                </div>
            ) : (
                <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-100">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-3 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-gray-500">Cliente</th>
                                    <th className="px-3 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-gray-500">Equipamento</th>
                                    <th className="px-3 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-gray-500">Série</th>
                                    <th className="px-3 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-gray-500">Empréstimo</th>
                                    <th className="px-3 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-gray-500">Prev. Devolução</th>
                                    <th className="px-3 py-2.5 text-right text-xs font-medium uppercase tracking-wide text-gray-500">Caução</th>
                                    <th className="px-3 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-gray-500">Status</th>
                                    <th className="px-3 py-2.5"></th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-50">
                                {filtered.map(item => (
                                    <tr key={item.id} className="hover:bg-gray-50 transition-colors">
                                        <td className="px-3 py-2.5">
                                            <div className="flex items-center gap-1.5">
                                                <User className="h-3.5 w-3.5 text-gray-400 shrink-0" />
                                                <span className="text-sm text-gray-900">{item.customer_name || '—'}</span>
                                            </div>
                                        </td>
                                        <td className="px-3 py-2.5 text-sm text-gray-700">{item.equipment_type || '—'}</td>
                                        <td className="px-3 py-2.5">
                                            <span className="flex items-center gap-1 text-xs text-gray-500">
                                                <Hash className="h-3 w-3" />
                                                {item.serial_number || '—'}
                                            </span>
                                        </td>
                                        <td className="px-3 py-2.5 text-xs text-gray-600">{formatDate(item.loan_date || item.created_at)}</td>
                                        <td className="px-3 py-2.5 text-xs text-gray-600">{formatDate(item.expected_return_date)}</td>
                                        <td className="px-3 py-2.5 text-sm font-medium text-gray-900 text-right">
                                            {item.deposit_value ? formatCurrency(item.deposit_value) : '—'}
                                        </td>
                                        <td className="px-3 py-2.5">
                                            <StatusBadge status={item.status} />
                                        </td>
                                        <td className="px-3 py-2.5 text-right">
                                            {item.status === 'ativo' && (
                                                <button
                                                    onClick={() => handleDevolver(item.id)}
                                                    className="rounded-lg border border-emerald-200 px-2.5 py-1 text-xs font-medium text-emerald-700 hover:bg-emerald-50 transition-colors"
                                                >
                                                    Devolver
                                                </button>
                                            )}
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
