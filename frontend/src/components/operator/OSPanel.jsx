/**
 * OSPanel - Consulta de Ordens de Serviço
 * Permite buscar, filtrar e gerenciar OS (pedidos) com número de 8 dígitos.
 */

import { useState, useEffect, useCallback } from 'react'
import { Search, FileText, MapPin, Clock, CheckCircle2, XCircle, Truck, AlertCircle } from 'lucide-react'
import { toast } from 'react-hot-toast'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

const STATUS_CONFIG = {
    pending: { label: 'Pendente', color: 'amber', icon: Clock },
    paid: { label: 'Aprovado', color: 'blue', icon: CheckCircle2 },
    preparing: { label: 'Preparando', color: 'indigo', icon: AlertCircle },
    dispatched: { label: 'Em Rota', color: 'purple', icon: Truck },
    delivered: { label: 'Entregue', color: 'emerald', icon: CheckCircle2 },
    cancelled: { label: 'Cancelado', color: 'red', icon: XCircle },
}

function formatOSNumber(orderNumber) {
    return String(orderNumber).padStart(8, '0')
}

function formatDate(dateStr) {
    if (!dateStr) return '—'
    const d = new Date(dateStr)
    return d.toLocaleDateString('pt-BR') + ' ' + d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}

function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value || 0)
}

export default function OSPanel() {
    const [orders, setOrders] = useState([])
    const [loading, setLoading] = useState(false)
    const [searchTerm, setSearchTerm] = useState('')
    const [statusFilter, setStatusFilter] = useState('')
    const [selectedOrder, setSelectedOrder] = useState(null)
    const [editingAddress, setEditingAddress] = useState(false)
    const [newAddress, setNewAddress] = useState('')

    const token = localStorage.getItem('token')

    const fetchOrders = useCallback(async () => {
        setLoading(true)
        try {
            let url = `${API_BASE}/orders?page_size=50`
            if (statusFilter) url += `&status=${statusFilter}`

            const res = await fetch(url, {
                headers: { Authorization: `Bearer ${token}` },
            })
            if (!res.ok) throw new Error('Erro ao buscar OS')
            const data = await res.json()
            setOrders(data.items || data || [])
        } catch (err) {
            toast.error('Erro ao carregar ordens de serviço')
            console.error(err)
        } finally {
            setLoading(false)
        }
    }, [statusFilter, token])

    useEffect(() => {
        fetchOrders()
    }, [fetchOrders])

    const searchByOS = async () => {
        if (!searchTerm.trim()) {
            fetchOrders()
            return
        }
        setLoading(true)
        try {
            // Remove zeros à esquerda para buscar pelo número
            const osNum = parseInt(searchTerm.replace(/\D/g, ''), 10)
            if (isNaN(osNum)) {
                toast.error('Número de OS inválido')
                setLoading(false)
                return
            }
            const res = await fetch(`${API_BASE}/orders/number/${osNum}`, {
                headers: { Authorization: `Bearer ${token}` },
            })
            if (!res.ok) {
                toast.error('OS não encontrada')
                setOrders([])
                setLoading(false)
                return
            }
            const order = await res.json()
            setOrders([order])
            setSelectedOrder(order)
        } catch (err) {
            toast.error('Erro ao buscar OS')
        } finally {
            setLoading(false)
        }
    }

    const updateAddress = async (orderId) => {
        if (!newAddress.trim()) return
        try {
            const res = await fetch(`${API_BASE}/orders/${orderId}`, {
                method: 'PATCH',
                headers: {
                    Authorization: `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    delivery_address: { full_address: newAddress },
                }),
            })
            if (!res.ok) throw new Error('Erro ao atualizar')
            toast.success('Endereço atualizado!')
            setEditingAddress(false)
            setNewAddress('')
            fetchOrders()
        } catch (err) {
            toast.error('Erro ao atualizar endereço')
        }
    }

    const StatusBadge = ({ status }) => {
        const config = STATUS_CONFIG[status] || { label: status, color: 'gray', icon: AlertCircle }
        const Icon = config.icon
        return (
            <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium bg-${config.color}-100 text-${config.color}-700`}>
                <Icon className="h-3 w-3" />
                {config.label}
            </span>
        )
    }

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <h2 className="text-2xl font-semibold text-gray-900 flex items-center gap-2">
                    <FileText className="h-6 w-6 text-primary-600" />
                    Consulta de OS
                </h2>
            </div>

            {/* Search and Filters */}
            <div className="flex flex-col sm:flex-row gap-3">
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                    <input
                        type="text"
                        placeholder="Buscar por nº da OS (ex: 00000004)"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && searchByOS()}
                        className="w-full rounded-lg border border-gray-300 pl-10 pr-4 py-2.5 text-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
                    />
                </div>
                <button
                    onClick={searchByOS}
                    className="rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700"
                >
                    Buscar
                </button>
                <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className="rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
                >
                    <option value="">Todos os status</option>
                    <option value="pending">Pendente</option>
                    <option value="paid">Aprovado</option>
                    <option value="dispatched">Em Rota</option>
                    <option value="delivered">Concluído</option>
                    <option value="cancelled">Cancelado</option>
                </select>
                <button
                    onClick={() => { setSearchTerm(''); setStatusFilter(''); fetchOrders() }}
                    className="rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                    Limpar
                </button>
            </div>

            {/* Orders Table */}
            <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
                {loading ? (
                    <div className="flex items-center justify-center py-12">
                        <div className="h-8 w-8 animate-spin rounded-full border-2 border-gray-200 border-t-primary-600" />
                    </div>
                ) : orders.length === 0 ? (
                    <div className="py-12 text-center text-gray-500">
                        <FileText className="mx-auto h-10 w-10 text-gray-300 mb-2" />
                        <p>Nenhuma OS encontrada</p>
                    </div>
                ) : (
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Nº OS</th>
                                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Cliente</th>
                                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Produto</th>
                                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Endereço</th>
                                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Total</th>
                                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Status</th>
                                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Data</th>
                                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Ações</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200">
                            {orders.map((order) => {
                                const osNum = formatOSNumber(order.order_number)
                                const addr = order.delivery_address
                                const addrText = addr
                                    ? (typeof addr === 'string' ? addr : addr.full_address || addr.street || '—')
                                    : 'Retira na loja'
                                const items = order.items || []
                                const itemsText = items.length > 0
                                    ? items.map(i => `${i.quantity}x ${i.product_code}`).join(', ')
                                    : order.items_summary || '—'

                                return (
                                    <tr
                                        key={order.id}
                                        className={`hover:bg-gray-50 cursor-pointer ${selectedOrder?.id === order.id ? 'bg-primary-50' : ''}`}
                                        onClick={() => setSelectedOrder(selectedOrder?.id === order.id ? null : order)}
                                    >
                                        <td className="px-4 py-3 text-sm font-mono font-semibold text-primary-700">
                                            #{osNum}
                                        </td>
                                        <td className="px-4 py-3 text-sm text-gray-900">
                                            {order.customer_name || order.customer?.name || '—'}
                                        </td>
                                        <td className="px-4 py-3 text-sm text-gray-700">{itemsText}</td>
                                        <td className="px-4 py-3 text-sm text-gray-600 max-w-[200px] truncate" title={addrText}>
                                            {addrText}
                                        </td>
                                        <td className="px-4 py-3 text-sm font-medium text-gray-900">
                                            {formatCurrency(order.total_amount)}
                                        </td>
                                        <td className="px-4 py-3">
                                            <StatusBadge status={order.status} />
                                        </td>
                                        <td className="px-4 py-3 text-sm text-gray-500">
                                            {formatDate(order.created_at)}
                                        </td>
                                        <td className="px-4 py-3">
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation()
                                                    setSelectedOrder(order)
                                                }}
                                                className="text-sm text-primary-600 hover:underline"
                                            >
                                                Detalhes
                                            </button>
                                        </td>
                                    </tr>
                                )
                            })}
                        </tbody>
                    </table>
                )}
            </div>

            {/* Selected Order Details */}
            {selectedOrder && (
                <div className="rounded-lg border border-primary-200 bg-primary-50 p-4 shadow-sm">
                    <div className="flex items-center justify-between mb-3">
                        <h3 className="text-lg font-semibold text-gray-900">
                            OS #{formatOSNumber(selectedOrder.order_number)}
                        </h3>
                        <button
                            onClick={() => { setSelectedOrder(null); setEditingAddress(false) }}
                            className="text-gray-400 hover:text-gray-600"
                        >
                            ✕
                        </button>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                        <div>
                            <span className="font-medium text-gray-600">Cliente:</span>{' '}
                            {selectedOrder.customer_name || selectedOrder.customer?.name || '—'}
                        </div>
                        <div>
                            <span className="font-medium text-gray-600">Status:</span>{' '}
                            <StatusBadge status={selectedOrder.status} />
                        </div>
                        <div>
                            <span className="font-medium text-gray-600">Total:</span>{' '}
                            {formatCurrency(selectedOrder.total_amount)}
                        </div>
                        <div>
                            <span className="font-medium text-gray-600">Pagamento:</span>{' '}
                            {selectedOrder.payment_method || '—'}
                        </div>
                        <div className="sm:col-span-2">
                            <span className="font-medium text-gray-600">Endereço:</span>{' '}
                            {editingAddress ? (
                                <div className="mt-1 flex gap-2">
                                    <input
                                        type="text"
                                        value={newAddress}
                                        onChange={(e) => setNewAddress(e.target.value)}
                                        placeholder="Novo endereço completo + CEP"
                                        className="flex-1 rounded border border-gray-300 px-3 py-1 text-sm"
                                    />
                                    <button
                                        onClick={() => updateAddress(selectedOrder.id)}
                                        className="rounded bg-primary-600 px-3 py-1 text-sm text-white hover:bg-primary-700"
                                    >
                                        Salvar
                                    </button>
                                    <button
                                        onClick={() => setEditingAddress(false)}
                                        className="rounded border border-gray-300 px-3 py-1 text-sm hover:bg-gray-50"
                                    >
                                        Cancelar
                                    </button>
                                </div>
                            ) : (
                                <>
                                    {(() => {
                                        const a = selectedOrder.delivery_address
                                        return a ? (typeof a === 'string' ? a : a.full_address || a.street || '—') : 'Retira na loja'
                                    })()}
                                    {selectedOrder.status === 'pending' && (
                                        <button
                                            onClick={() => { setEditingAddress(true); setNewAddress('') }}
                                            className="ml-2 text-primary-600 hover:underline text-xs"
                                        >
                                            <MapPin className="inline h-3 w-3" /> Alterar
                                        </button>
                                    )}
                                </>
                            )}
                        </div>
                        <div>
                            <span className="font-medium text-gray-600">Criado em:</span>{' '}
                            {formatDate(selectedOrder.created_at)}
                        </div>
                        {selectedOrder.delivered_at && (
                            <div>
                                <span className="font-medium text-gray-600">Entregue em:</span>{' '}
                                {formatDate(selectedOrder.delivered_at)}
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    )
}
