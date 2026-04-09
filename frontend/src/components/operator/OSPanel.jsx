/**
 * OSPanel - Todos os Pedidos
 * Listagem rica com modal de detalhes completo.
 */

import { useState, useEffect, useCallback } from 'react'
import {
    Search, FileText, MapPin, Clock, CheckCircle2, XCircle,
    Truck, AlertCircle, User, Phone, CreditCard, Package,
    Building2, Home, Factory, X, RefreshCw, Users, Star,
} from 'lucide-react'
import { toast } from 'react-hot-toast'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

const STATUS_CONFIG = {
    pending:    { label: 'Pendente',    color: 'amber',   icon: Clock },
    paid:       { label: 'Aprovado',    color: 'blue',    icon: CheckCircle2 },
    preparing:  { label: 'Preparando', color: 'indigo',  icon: AlertCircle },
    dispatched: { label: 'Em Rota',    color: 'purple',  icon: Truck },
    delivered:  { label: 'Entregue',   color: 'emerald', icon: CheckCircle2 },
    cancelled:  { label: 'Cancelado',  color: 'red',     icon: XCircle },
}

const TIPO_OPERACAO_CONFIG = {
    troca:   { label: 'Troca (cheio/vazio)',  icon: RefreshCw },
    venda:   { label: 'Venda (vasilhame novo)', icon: Package },
    retira:  { label: 'Retira na loja',       icon: MapPin },
}

const LOCATION_TYPE_CONFIG = {
    residencial: { label: 'Residencial', icon: Home },
    comercial:   { label: 'Comercial',   icon: Building2 },
    industrial:  { label: 'Industrial',  icon: Factory },
}

const PAYMENT_LABELS = {
    pix:         'PIX',
    credit_card: 'Cartão de Crédito',
    debit_card:  'Cartão de Débito',
    cash:        'Dinheiro',
    boleto:      'Boleto',
}

function formatOSNumber(n) {
    return String(n).padStart(8, '0')
}

function formatDate(dateStr) {
    if (!dateStr) return '—'
    const d = new Date(dateStr)
    return d.toLocaleDateString('pt-BR') + ' ' + d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}

function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value || 0)
}

function StatusBadge({ status }) {
    const config = STATUS_CONFIG[status] || { label: status, color: 'gray', icon: AlertCircle }
    const Icon = config.icon
    return (
        <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium bg-${config.color}-100 text-${config.color}-700`}>
            <Icon className="h-3 w-3" />
            {config.label}
        </span>
    )
}

function DetailRow({ label, value, span = false }) {
    if (!value && value !== 0) return null
    return (
        <div className={span ? 'col-span-2' : ''}>
            <dt className="text-xs text-gray-500 mb-0.5">{label}</dt>
            <dd className="text-sm text-gray-900 font-medium">{value}</dd>
        </div>
    )
}

function SectionHeader({ title }) {
    return (
        <div className="col-span-2 border-t border-gray-100 pt-3 mt-1">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">{title}</p>
        </div>
    )
}

function OrderDetailModal({ order, onClose, onAddressEdit }) {
    const [editingAddress, setEditingAddress] = useState(false)
    const [newAddress, setNewAddress] = useState('')
    // T07 — Troca de motorista
    const [showReassign, setShowReassign] = useState(false)
    const [availableDrivers, setAvailableDrivers] = useState([])
    const [loadingDrivers, setLoadingDrivers] = useState(false)
    const [selectedNewDriver, setSelectedNewDriver] = useState(null)
    const [reassignMotivo, setReassignMotivo] = useState('')
    const [reassigning, setReassigning] = useState(false)
    const token = localStorage.getItem('token')

    const canReassign = ['paid', 'preparing', 'dispatched'].includes(order.status)

    const loadDrivers = async () => {
        setLoadingDrivers(true)
        try {
            const res = await fetch(`${API_BASE}/drivers/`, { headers: { Authorization: `Bearer ${token}` } })
            if (res.ok) {
                const data = await res.json()
                setAvailableDrivers((data || []).filter(d => d.is_active))
            }
        } catch { /* silencioso */ }
        finally { setLoadingDrivers(false) }
    }

    const handleReassign = async () => {
        if (!selectedNewDriver) { toast.error('Selecione um motorista'); return }
        setReassigning(true)
        try {
            const res = await fetch(`${API_BASE}/orders/${order.id}/reassign-driver`, {
                method: 'PATCH',
                headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ new_driver_id: selectedNewDriver.id, motivo: reassignMotivo || 'Troca manual pelo operador' }),
            })
            if (!res.ok) {
                const err = await res.json().catch(() => ({}))
                throw new Error(err.detail || 'Erro ao trocar motorista')
            }
            toast.success(`Entrega atribuída para ${selectedNewDriver.name}!`)
            setShowReassign(false)
            setSelectedNewDriver(null)
            setReassignMotivo('')
            onAddressEdit?.() // recarrega a lista
        } catch (e) {
            toast.error(e.message || 'Erro ao trocar motorista')
        } finally {
            setReassigning(false)
        }
    }

    const updateAddress = async () => {
        if (!newAddress.trim()) return
        try {
            const res = await fetch(`${API_BASE}/orders/${order.id}`, {
                method: 'PATCH',
                headers: {
                    Authorization: `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ delivery_address: { full_address: newAddress } }),
            })
            if (!res.ok) throw new Error()
            toast.success('Endereço atualizado!')
            setEditingAddress(false)
            onAddressEdit?.()
        } catch {
            toast.error('Erro ao atualizar endereço')
        }
    }

    const tipoOp = TIPO_OPERACAO_CONFIG[order.tipo_operacao] || null
    const locType = LOCATION_TYPE_CONFIG[order.location_type] || null
    const isDelivered = order.status === 'delivered'
    const isCancelled = order.status === 'cancelled'

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/30 backdrop-blur-sm">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
                    <div className="flex items-center gap-3">
                        <span className="font-mono text-lg font-bold text-gray-900">
                            OS #{formatOSNumber(order.order_number)}
                        </span>
                        <StatusBadge status={order.status} />
                    </div>
                    <button
                        onClick={onClose}
                        className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
                    >
                        <X className="h-5 w-5" />
                    </button>
                </div>

                {/* Body */}
                <div className="flex-1 overflow-y-auto px-6 py-4">
                    <dl className="grid grid-cols-2 gap-x-6 gap-y-3">

                        {/* Identificação */}
                        <SectionHeader title="Identificação" />
                        <DetailRow label="Nº OS" value={`#${formatOSNumber(order.order_number)}`} />
                        <DetailRow label="Data / hora da mensagem" value={formatDate(order.created_at)} />
                        {tipoOp && (
                            <DetailRow label="Tipo de operação" value={tipoOp.label} />
                        )}
                        <DetailRow
                            label="Entregue"
                            value={isDelivered ? `Sim — ${formatDate(order.delivered_at)}` : isCancelled ? 'Cancelado' : 'Não'}
                        />
                        {order.delivered_at && (
                            <DetailRow label="Hora da entrega" value={formatDate(order.delivered_at)} />
                        )}

                        {/* Cliente */}
                        <SectionHeader title="Cliente" />
                        <DetailRow label="Nome" value={order.customer_name || '—'} />
                        <DetailRow label="Telefone" value={order.customer_phone || '—'} />
                        {order.customer_cpf_cnpj && (
                            <DetailRow label="CPF / CNPJ" value={order.customer_cpf_cnpj} />
                        )}

                        {/* Entrega */}
                        <SectionHeader title="Entrega" />
                        <div className="col-span-2">
                            <dt className="text-xs text-gray-500 mb-0.5">Endereço</dt>
                            <dd className="text-sm text-gray-900 font-medium">
                                {editingAddress ? (
                                    <div className="flex gap-2 mt-1">
                                        <input
                                            type="text"
                                            value={newAddress}
                                            onChange={e => setNewAddress(e.target.value)}
                                            placeholder="Novo endereço completo + CEP"
                                            className="flex-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
                                        />
                                        <button
                                            onClick={updateAddress}
                                            className="rounded-lg bg-primary-600 px-3 py-1.5 text-sm text-white hover:bg-primary-700"
                                        >Salvar</button>
                                        <button
                                            onClick={() => setEditingAddress(false)}
                                            className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
                                        >Cancelar</button>
                                    </div>
                                ) : (
                                    <span className="flex items-center gap-2">
                                        {order.delivery_address || 'Retira na loja'}
                                        {order.status === 'pending' && (
                                            <button
                                                onClick={() => { setEditingAddress(true); setNewAddress('') }}
                                                className="text-xs text-primary-600 hover:underline flex items-center gap-0.5"
                                            >
                                                <MapPin className="h-3 w-3" /> Alterar
                                            </button>
                                        )}
                                    </span>
                                )}
                            </dd>
                        </div>
                        <DetailRow label="Bairro" value={order.delivery_bairro || '—'} />
                        {locType && (
                            <DetailRow label="Tipo de local" value={locType.label} />
                        )}
                        {!locType && order.location_type && (
                            <DetailRow label="Tipo de local" value={order.location_type} />
                        )}

                        {/* Pedido */}
                        <SectionHeader title="Pedido" />
                        <DetailRow label="Total" value={formatCurrency(order.total_amount)} />
                        <DetailRow label="Pagamento" value={PAYMENT_LABELS[order.payment_method] || order.payment_method || '—'} />
                        {order.items?.length > 0 && (
                            <div className="col-span-2">
                                <dt className="text-xs text-gray-500 mb-1">Itens</dt>
                                <dd>
                                    <div className="rounded-lg border border-gray-100 overflow-hidden">
                                        <table className="min-w-full text-xs">
                                            <thead className="bg-gray-50">
                                                <tr>
                                                    <th className="px-3 py-2 text-left font-medium text-gray-500">Produto</th>
                                                    <th className="px-3 py-2 text-center font-medium text-gray-500">Qtd</th>
                                                    <th className="px-3 py-2 text-right font-medium text-gray-500">Unit.</th>
                                                    <th className="px-3 py-2 text-right font-medium text-gray-500">Subtotal</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-gray-50">
                                                {order.items.map((it, i) => (
                                                    <tr key={i} className="bg-white">
                                                        <td className="px-3 py-2 text-gray-800">{it.product_name || it.product_code}</td>
                                                        <td className="px-3 py-2 text-center text-gray-700">{it.quantity}</td>
                                                        <td className="px-3 py-2 text-right text-gray-700">{formatCurrency(it.unit_price)}</td>
                                                        <td className="px-3 py-2 text-right font-medium text-gray-900">{formatCurrency(it.subtotal)}</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </dd>
                            </div>
                        )}

                        {/* Atendimento */}
                        <SectionHeader title="Atendimento" />
                        <DetailRow label="Usuário que atendeu" value={order.approved_by_name || '—'} />
                        {isCancelled && order.cancellation_reason && (
                            <DetailRow label="Motivo do cancelamento" value={order.cancellation_reason} span />
                        )}

                        {/* Observações */}
                        {order.notes && (
                            <>
                                <SectionHeader title="Observações" />
                                <div className="col-span-2">
                                    <dd className="text-sm text-gray-700 bg-amber-50 rounded-lg px-3 py-2 border border-amber-100">
                                        {order.notes}
                                    </dd>
                                </div>
                            </>
                        )}
                        {/* T07 — Trocar Motorista */}
                        {canReassign && (
                            <>
                                <SectionHeader title="Motorista" />
                                <div className="col-span-2">
                                    {!showReassign ? (
                                        <button
                                            onClick={() => { setShowReassign(true); loadDrivers() }}
                                            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-violet-200 bg-violet-50 text-violet-700 hover:bg-violet-100 transition-colors"
                                        >
                                            <Truck className="h-3.5 w-3.5" />
                                            Trocar motorista
                                        </button>
                                    ) : (
                                        <div className="space-y-2">
                                            {loadingDrivers ? (
                                                <div className="flex items-center gap-2 py-2 text-xs text-gray-500">
                                                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-gray-200 border-t-violet-600" />
                                                    Carregando motoristas...
                                                </div>
                                            ) : (
                                                <div className="space-y-1 max-h-40 overflow-y-auto">
                                                    {availableDrivers.map((d, i) => (
                                                        <label key={d.id}
                                                            className={`flex items-center gap-2.5 p-2 rounded-lg border cursor-pointer transition-colors text-sm ${
                                                                selectedNewDriver?.id === d.id
                                                                    ? 'border-violet-400 bg-violet-50'
                                                                    : 'border-gray-200 hover:bg-gray-50'
                                                            }`}>
                                                            <input type="radio" name="new_driver"
                                                                checked={selectedNewDriver?.id === d.id}
                                                                onChange={() => setSelectedNewDriver(d)}
                                                                className="h-3.5 w-3.5 text-violet-600" />
                                                            <span className="font-medium text-gray-900">{d.name}</span>
                                                            {d.bairro && <span className="text-xs text-gray-400 ml-auto">{d.bairro}</span>}
                                                        </label>
                                                    ))}
                                                    {availableDrivers.length === 0 && (
                                                        <p className="text-xs text-gray-400 py-2 text-center">Nenhum motorista ativo</p>
                                                    )}
                                                </div>
                                            )}
                                            <input
                                                type="text"
                                                placeholder="Motivo (opcional)"
                                                value={reassignMotivo}
                                                onChange={e => setReassignMotivo(e.target.value)}
                                                className="w-full rounded-lg border border-gray-200 px-3 py-1.5 text-xs focus:border-violet-500 focus:ring-1 focus:ring-violet-500 focus:outline-none"
                                            />
                                            <div className="flex gap-2">
                                                <button onClick={handleReassign} disabled={reassigning || !selectedNewDriver}
                                                    className="flex-1 rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-violet-700 disabled:opacity-50">
                                                    {reassigning ? 'Atribuindo...' : 'Confirmar troca'}
                                                </button>
                                                <button onClick={() => { setShowReassign(false); setSelectedNewDriver(null); setReassignMotivo('') }}
                                                    className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-50">
                                                    Cancelar
                                                </button>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </>
                        )}
                    </dl>
                </div>
            </div>
        </div>
    )
}

export default function OSPanel() {
    const [orders, setOrders] = useState([])
    const [loading, setLoading] = useState(false)
    const [searchTerm, setSearchTerm] = useState('')
    const [statusFilter, setStatusFilter] = useState('')
    const [selectedOrder, setSelectedOrder] = useState(null)
    const [page, setPage] = useState(1)
    const [totalPages, setTotalPages] = useState(1)
    const [total, setTotal] = useState(0)

    const token = localStorage.getItem('token')

    const fetchOrders = useCallback(async (p = page) => {
        setLoading(true)
        try {
            let url = `${API_BASE}/orders?page=${p}&page_size=30`
            if (statusFilter) url += `&status=${statusFilter}`

            const res = await fetch(url, {
                headers: { Authorization: `Bearer ${token}` },
            })
            if (!res.ok) throw new Error('Erro ao buscar OS')
            const data = await res.json()
            setOrders(data.items || [])
            setTotal(data.total || 0)
            setTotalPages(data.total_pages || 1)
        } catch (err) {
            toast.error('Erro ao carregar ordens de serviço')
        } finally {
            setLoading(false)
        }
    }, [statusFilter, token, page])

    useEffect(() => {
        fetchOrders(page)
    }, [fetchOrders, page])

    // Reset page when filter changes
    useEffect(() => {
        setPage(1)
    }, [statusFilter])

    const searchByOS = async () => {
        if (!searchTerm.trim()) { fetchOrders(1); return }
        setLoading(true)
        try {
            const osNum = parseInt(searchTerm.replace(/\D/g, ''), 10)
            if (isNaN(osNum)) { toast.error('Número de OS inválido'); setLoading(false); return }
            const res = await fetch(`${API_BASE}/orders/number/${osNum}`, {
                headers: { Authorization: `Bearer ${token}` },
            })
            if (!res.ok) { toast.error('OS não encontrada'); setOrders([]); setLoading(false); return }
            const order = await res.json()
            setOrders([order])
            setSelectedOrder(order)
            setTotal(1)
            setTotalPages(1)
        } catch {
            toast.error('Erro ao buscar OS')
        } finally {
            setLoading(false)
        }
    }

    const filteredOrders = searchTerm && orders.length > 0 ? orders : orders.filter(o => {
        if (!searchTerm) return true
        const term = searchTerm.toLowerCase()
        return (
            String(o.order_number).includes(term) ||
            (o.customer_name || '').toLowerCase().includes(term) ||
            (o.customer_phone || '').includes(term)
        )
    })

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                    <FileText className="h-5 w-5 text-primary-600" />
                    Todos os Pedidos
                    {total > 0 && <span className="text-sm font-normal text-gray-500">({total} registros)</span>}
                </h2>
            </div>

            {/* Search and Filters */}
            <div className="flex flex-col sm:flex-row gap-2">
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                    <input
                        type="text"
                        placeholder="Buscar por nº OS, nome ou telefone"
                        value={searchTerm}
                        onChange={e => setSearchTerm(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && searchByOS()}
                        className="w-full rounded-lg border border-gray-200 pl-9 pr-4 py-2 text-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500 focus:outline-none"
                    />
                </div>
                <button
                    onClick={searchByOS}
                    className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
                >
                    Buscar
                </button>
                <select
                    value={statusFilter}
                    onChange={e => setStatusFilter(e.target.value)}
                    className="rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500 focus:outline-none"
                >
                    <option value="">Todos os status</option>
                    <option value="pending">Pendente</option>
                    <option value="paid">Aprovado</option>
                    <option value="preparing">Preparando</option>
                    <option value="dispatched">Em Rota</option>
                    <option value="delivered">Entregue</option>
                    <option value="cancelled">Cancelado</option>
                </select>
                <button
                    onClick={() => { setSearchTerm(''); setStatusFilter(''); setPage(1) }}
                    className="rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50"
                >
                    Limpar
                </button>
            </div>

            {/* Table */}
            <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
                {loading ? (
                    <div className="flex items-center justify-center py-12">
                        <div className="h-7 w-7 animate-spin rounded-full border-2 border-gray-200 border-t-primary-600" />
                    </div>
                ) : filteredOrders.length === 0 ? (
                    <div className="py-12 text-center text-gray-500">
                        <FileText className="mx-auto h-8 w-8 text-gray-300 mb-2" />
                        <p className="text-sm">Nenhum pedido encontrado</p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-100">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-3 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-gray-500">Nº OS</th>
                                    <th className="px-3 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-gray-500">Cliente</th>
                                    <th className="px-3 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-gray-500">Telefone</th>
                                    <th className="px-3 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-gray-500">Produto</th>
                                    <th className="px-3 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-gray-500">Bairro</th>
                                    <th className="px-3 py-2.5 text-right text-xs font-medium uppercase tracking-wide text-gray-500">Total</th>
                                    <th className="px-3 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-gray-500">Status</th>
                                    <th className="px-3 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-gray-500">Data</th>
                                    <th className="px-3 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-gray-500">Entregue</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-50">
                                {filteredOrders.map((order, idx) => {
                                    const items = order.items || []
                                    const itemsText = items.length > 0
                                        ? items.map(i => `${i.quantity}x ${i.product_code}`).join(', ')
                                        : '—'
                                    return (
                                        <tr
                                            key={order.id}
                                            onClick={() => setSelectedOrder(order)}
                                            className={`cursor-pointer text-xs transition-colors ${idx % 2 === 1 ? 'bg-gray-50/50' : 'bg-white'} hover:bg-primary-50`}
                                        >
                                            <td className="px-3 py-2.5 font-mono font-semibold text-primary-700">
                                                #{formatOSNumber(order.order_number)}
                                            </td>
                                            <td className="px-3 py-2.5 text-gray-900 font-medium max-w-[140px] truncate">
                                                {order.customer_name || '—'}
                                            </td>
                                            <td className="px-3 py-2.5 text-gray-600 font-mono">
                                                {order.customer_phone || '—'}
                                            </td>
                                            <td className="px-3 py-2.5 text-gray-600 max-w-[160px] truncate">
                                                {itemsText}
                                            </td>
                                            <td className="px-3 py-2.5 text-gray-500 max-w-[120px] truncate">
                                                {order.delivery_bairro || '—'}
                                            </td>
                                            <td className="px-3 py-2.5 text-right font-medium text-gray-900">
                                                {formatCurrency(order.total_amount)}
                                            </td>
                                            <td className="px-3 py-2.5">
                                                <StatusBadge status={order.status} />
                                            </td>
                                            <td className="px-3 py-2.5 text-gray-500 whitespace-nowrap">
                                                {formatDate(order.created_at)}
                                            </td>
                                            <td className="px-3 py-2.5">
                                                {order.status === 'delivered' ? (
                                                    <span className="inline-flex items-center gap-1 text-emerald-600 font-medium">
                                                        <CheckCircle2 className="h-3.5 w-3.5" /> Sim
                                                    </span>
                                                ) : order.status === 'cancelled' ? (
                                                    <span className="text-red-500">Cancelado</span>
                                                ) : (
                                                    <span className="text-gray-400">Não</span>
                                                )}
                                            </td>
                                        </tr>
                                    )
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
                <div className="flex items-center justify-between text-xs text-gray-500">
                    <span>{total} pedidos no total</span>
                    <div className="flex items-center gap-1">
                        <button
                            onClick={() => setPage(p => Math.max(1, p - 1))}
                            disabled={page === 1}
                            className="px-3 py-1.5 rounded-lg border border-gray-200 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
                        >
                            ← Anterior
                        </button>
                        <span className="px-3 py-1.5">Página {page} de {totalPages}</span>
                        <button
                            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                            disabled={page === totalPages}
                            className="px-3 py-1.5 rounded-lg border border-gray-200 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
                        >
                            Próxima →
                        </button>
                    </div>
                </div>
            )}

            {/* Detail Modal */}
            {selectedOrder && (
                <OrderDetailModal
                    order={selectedOrder}
                    onClose={() => setSelectedOrder(null)}
                    onAddressEdit={() => { fetchOrders(page); setSelectedOrder(null) }}
                />
            )}
        </div>
    )
}
