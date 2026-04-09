/**
 * AgendadosPanel - Pedidos Agendados
 * Lista pedidos com entrega programada futura.
 */

import { useState, useEffect, useCallback } from 'react'
import {
    Calendar, Clock, MapPin, User, Phone,
    Package, RefreshCw, Search,
} from 'lucide-react'
import { toast } from 'react-hot-toast'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

function formatDate(dateStr) {
    if (!dateStr) return '—'
    const d = new Date(dateStr)
    return d.toLocaleDateString('pt-BR') + ' ' + d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}

function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value || 0)
}

function formatOSNumber(n) {
    return String(n).padStart(8, '0')
}

const PAYMENT_LABELS = {
    pix: 'PIX', cash: 'Dinheiro', credit_card: 'Cartão Crédito',
    debit_card: 'Cartão Débito', boleto: 'Boleto',
}

function ScheduledBadge({ date }) {
    const d = new Date(date)
    const diffH = (d - Date.now()) / 36e5
    const color = diffH < 2 ? 'red' : diffH < 6 ? 'amber' : 'blue'
    return (
        <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium bg-${color}-100 text-${color}-700`}>
            <Clock className="h-3 w-3" />
            {formatDate(date)}
        </span>
    )
}

export default function AgendadosPanel() {
    const [orders, setOrders] = useState([])
    const [loading, setLoading] = useState(false)
    const [dateFrom, setDateFrom] = useState('')
    const [dateTo, setDateTo] = useState('')
    const [search, setSearch] = useState('')
    const token = localStorage.getItem('token')

    const load = useCallback(async () => {
        setLoading(true)
        try {
            let url = `${API_BASE}/orders/agendados?`
            if (dateFrom) url += `date_from=${dateFrom}&`
            if (dateTo)   url += `date_to=${dateTo}&`
            const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } })
            if (!res.ok) throw new Error()
            const data = await res.json()
            setOrders(data.items || data || [])
        } catch {
            toast.error('Erro ao carregar pedidos agendados')
        } finally {
            setLoading(false)
        }
    }, [dateFrom, dateTo, token])

    useEffect(() => { load() }, [load])

    const filtered = orders.filter(o => {
        if (!search) return true
        const t = search.toLowerCase()
        return (
            String(o.order_number).includes(t) ||
            (o.customer_name || '').toLowerCase().includes(t) ||
            (o.customer_phone || '').includes(t) ||
            (o.delivery_bairro || '').toLowerCase().includes(t)
        )
    })

    return (
        <div className="space-y-4">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                        <Calendar className="h-5 w-5 text-blue-600" />
                        Pedidos Agendados
                    </h2>
                    <p className="text-xs text-gray-500 mt-0.5">Entregas programadas para datas futuras</p>
                </div>
                <button
                    onClick={load}
                    disabled={loading}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-200 bg-white text-gray-600 hover:bg-gray-50 disabled:opacity-50"
                >
                    <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
                    Atualizar
                </button>
            </div>

            {/* Filtros */}
            <div className="flex flex-wrap gap-2">
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-400" />
                    <input
                        type="text"
                        placeholder="Cliente, OS ou bairro"
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                        className="rounded-lg border border-gray-200 pl-8 pr-3 py-2 text-sm w-52 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
                    />
                </div>
                <div className="flex items-center gap-1.5">
                    <label className="text-xs text-gray-500 whitespace-nowrap">De:</label>
                    <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)}
                        className="rounded-lg border border-gray-200 px-2 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none" />
                </div>
                <div className="flex items-center gap-1.5">
                    <label className="text-xs text-gray-500 whitespace-nowrap">Até:</label>
                    <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)}
                        className="rounded-lg border border-gray-200 px-2 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none" />
                </div>
                {(dateFrom || dateTo || search) && (
                    <button onClick={() => { setDateFrom(''); setDateTo(''); setSearch('') }}
                        className="rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50">
                        Limpar
                    </button>
                )}
            </div>

            {/* Lista */}
            {loading ? (
                <div className="flex items-center justify-center py-16">
                    <div className="h-7 w-7 animate-spin rounded-full border-2 border-gray-200 border-t-blue-600" />
                </div>
            ) : filtered.length === 0 ? (
                <div className="rounded-xl border border-gray-200 bg-white py-16 text-center">
                    <Calendar className="mx-auto h-10 w-10 text-gray-300 mb-3" />
                    <p className="text-sm font-medium text-gray-500">Nenhum pedido agendado</p>
                    <p className="text-xs text-gray-400 mt-1">Ajuste os filtros de data ou aguarde novos agendamentos</p>
                </div>
            ) : (
                <div className="space-y-2">
                    {filtered.map(order => (
                        <div key={order.id}
                            className="rounded-xl border border-gray-200 bg-white p-4 hover:border-blue-300 hover:shadow-sm transition-all">
                            <div className="flex items-start justify-between gap-4">
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                                        <span className="font-mono text-sm font-bold text-gray-900">
                                            OS #{formatOSNumber(order.order_number)}
                                        </span>
                                        {order.scheduled_for && <ScheduledBadge date={order.scheduled_for} />}
                                    </div>
                                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-1 text-xs text-gray-600">
                                        <span className="flex items-center gap-1">
                                            <User className="h-3 w-3 text-gray-400" />
                                            {order.customer_name || '—'}
                                        </span>
                                        <span className="flex items-center gap-1">
                                            <Phone className="h-3 w-3 text-gray-400" />
                                            {order.customer_phone || '—'}
                                        </span>
                                        <span className="flex items-center gap-1">
                                            <MapPin className="h-3 w-3 text-gray-400" />
                                            {order.delivery_bairro || '—'}
                                        </span>
                                        {order.items?.length > 0 && (
                                            <span className="flex items-center gap-1 col-span-2">
                                                <Package className="h-3 w-3 text-gray-400" />
                                                {order.items.map(i => `${i.product_name || i.product_code} x${i.quantity}`).join(', ')}
                                            </span>
                                        )}
                                    </div>
                                </div>
                                <div className="text-right shrink-0">
                                    <p className="text-sm font-bold text-gray-900">{formatCurrency(order.total_amount)}</p>
                                    <p className="text-xs text-gray-500 mt-0.5">{PAYMENT_LABELS[order.payment_method] || order.payment_method || '—'}</p>
                                </div>
                            </div>
                            {order.notes && (
                                <div className="mt-2 rounded-lg bg-amber-50 border border-amber-100 px-3 py-2 text-xs text-amber-700">
                                    {order.notes}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}
