/**
 * Painel de Historico de Pedidos — Linear.app style
 * Ultra-dense data table, compact filters, minimal spacing
 */

import { useState, useEffect } from 'react'
import { RefreshCcw, ChevronLeft, ChevronRight, Filter, X, Eye } from 'lucide-react'
import { getOrdersPaginated } from '../../services/api'

const STATUS_OPTIONS = [
  { value: '', label: 'Todos os status' },
  { value: 'pending', label: 'Pendente' },
  { value: 'paid', label: 'Pago' },
  { value: 'preparing', label: 'Em preparo' },
  { value: 'dispatched', label: 'Em rota' },
  { value: 'delivered', label: 'Entregue' },
  { value: 'cancelled', label: 'Cancelado' },
]

const STATUS_COLORS = {
  pending:    'bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-400',
  paid:       'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300',
  preparing:  'bg-purple-100 dark:bg-purple-900/30 text-purple-800 dark:text-purple-300',
  dispatched: 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-800 dark:text-indigo-300',
  delivered:  'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300',
  cancelled:  'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400',
}

const STATUS_LABELS = {
  pending:    'Pendente',
  paid:       'Pago',
  preparing:  'Em preparo',
  dispatched: 'Em rota',
  delivered:  'Entregue',
  cancelled:  'Cancelado',
}

export default function OrderHistoryPanel() {
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [selectedOrder, setSelectedOrder] = useState(null)

  const [filters, setFilters] = useState({ status: '', bairro: '', date_from: '', date_to: '' })
  const [showFilters, setShowFilters] = useState(false)

  useEffect(() => {
    fetchOrders()
  }, [page])

  const fetchOrders = async (resetPage = false) => {
    try {
      setLoading(true)
      const currentPage = resetPage ? 1 : page
      const apiFilters = {}
      if (filters.status) apiFilters.status = filters.status
      if (filters.bairro) apiFilters.bairro = filters.bairro
      if (filters.date_from) apiFilters.date_from = new Date(filters.date_from).toISOString()
      if (filters.date_to) apiFilters.date_to = new Date(filters.date_to + 'T23:59:59').toISOString()

      const data = await getOrdersPaginated(currentPage, 15, apiFilters)
      setOrders(data.items || [])
      setTotalPages(data.total_pages || 1)
      setTotal(data.total || 0)
      if (resetPage) setPage(1)
    } catch (error) {
      console.error('Erro ao buscar pedidos:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleFilterChange = (field, value) => setFilters(prev => ({ ...prev, [field]: value }))

  const applyFilters = () => { fetchOrders(true); setShowFilters(false) }

  const clearFilters = () => {
    setFilters({ status: '', bairro: '', date_from: '', date_to: '' })
    fetchOrders(true)
    setShowFilters(false)
  }

  const formatCurrency = (value) =>
    new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value || 0)

  const formatDateTime = (isoString) => {
    if (!isoString) return '-'
    const date = new Date(isoString)
    return date.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
  }

  const activeFiltersCount = Object.values(filters).filter(v => v).length

  if (loading && orders.length === 0) {
    return (
      <div className="flex items-center justify-center h-40">
        <div className="w-6 h-6 animate-spin rounded-full border-2 border-gray-200 border-t-primary-600" />
      </div>
    )
  }

  return (
    <div className="space-y-3">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Histórico de Pedidos</h2>
          <span className="text-xs text-gray-400 dark:text-gray-500">{total} pedidos</span>
        </div>
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-md border transition-colors ${
              activeFiltersCount > 0
                ? 'border-primary-300 dark:border-primary-700 bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-400'
                : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`}
          >
            <Filter className="h-3 w-3" />
            Filtros
            {activeFiltersCount > 0 && (
              <span className="rounded-full bg-primary-600 px-1.5 text-xs text-white leading-4">{activeFiltersCount}</span>
            )}
          </button>
          <button
            onClick={() => fetchOrders()}
            disabled={loading}
            className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 transition-colors"
          >
            <RefreshCcw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />
            Atualizar
          </button>
        </div>
      </div>

      {/* Filter panel */}
      {showFilters && (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-3">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Status</label>
              <select
                value={filters.status}
                onChange={(e) => handleFilterChange('status', e.target.value)}
                className="block w-full rounded-md border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 dark:text-white px-2.5 py-1.5 text-xs focus:border-primary-500 focus:ring-primary-500"
              >
                {STATUS_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Bairro</label>
              <input
                type="text"
                value={filters.bairro}
                onChange={(e) => handleFilterChange('bairro', e.target.value)}
                placeholder="Digite o bairro"
                className="block w-full rounded-md border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 dark:text-white dark:placeholder-gray-400 px-2.5 py-1.5 text-xs focus:border-primary-500 focus:ring-primary-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Data inicial</label>
              <input
                type="date"
                value={filters.date_from}
                onChange={(e) => handleFilterChange('date_from', e.target.value)}
                className="block w-full rounded-md border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 dark:text-white px-2.5 py-1.5 text-xs focus:border-primary-500 focus:ring-primary-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Data final</label>
              <input
                type="date"
                value={filters.date_to}
                onChange={(e) => handleFilterChange('date_to', e.target.value)}
                className="block w-full rounded-md border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 dark:text-white px-2.5 py-1.5 text-xs focus:border-primary-500 focus:ring-primary-500"
              />
            </div>
          </div>
          <div className="mt-3 flex justify-end gap-2">
            <button
              onClick={clearFilters}
              className="px-3 py-1.5 text-xs font-medium rounded-md border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50"
            >
              Limpar
            </button>
            <button
              onClick={applyFilters}
              className="px-3 py-1.5 text-xs font-medium rounded-md bg-primary-600 text-white hover:bg-primary-700"
            >
              Aplicar
            </button>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="overflow-hidden rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/80">
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wide">Pedido</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wide">Cliente</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wide">Bairro</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wide">Status</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wide">Total</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wide">Data</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wide">Ação</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {orders.length === 0 ? (
                <tr>
                  <td colSpan="7" className="px-3 py-8 text-center text-xs text-gray-400 dark:text-gray-500">
                    Nenhum pedido encontrado
                  </td>
                </tr>
              ) : (
                orders.map((order, idx) => (
                  <tr
                    key={order.id}
                    className={`hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors ${idx % 2 === 1 ? 'bg-gray-50/40 dark:bg-gray-800/40' : ''}`}
                  >
                    <td className="whitespace-nowrap px-3 py-2">
                      <span className="text-xs font-mono font-medium text-gray-700 dark:text-gray-300">#{order.order_number}</span>
                    </td>
                    <td className="px-3 py-2">
                      <p className="text-xs font-medium text-gray-900 dark:text-white truncate max-w-[120px]">{order.customer_name || 'N/A'}</p>
                      <p className="text-xs text-gray-400 dark:text-gray-500">{order.customer_phone}</p>
                    </td>
                    <td className="whitespace-nowrap px-3 py-2 text-xs text-gray-500 dark:text-gray-400">
                      {order.delivery_bairro || '-'}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2">
                      <span className={`inline-flex rounded px-1.5 py-0.5 text-xs font-medium ${STATUS_COLORS[order.status] || 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'}`}>
                        {STATUS_LABELS[order.status] || order.status}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-3 py-2 text-xs font-medium text-gray-900 dark:text-white">
                      {formatCurrency(order.total_amount)}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2 text-xs text-gray-400 dark:text-gray-500">
                      {formatDateTime(order.created_at)}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2 text-right">
                      <button
                        onClick={() => setSelectedOrder(order)}
                        className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                      >
                        <Eye className="h-3 w-3" />
                        Ver
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 px-3 py-2">
            <p className="text-xs text-gray-400 dark:text-gray-500">
              Página {page} de {totalPages}
            </p>
            <div className="flex gap-1">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1 || loading}
                className="inline-flex items-center gap-1 rounded-md border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 px-2.5 py-1 text-xs font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-40 transition-colors"
              >
                <ChevronLeft className="h-3 w-3" />
                Anterior
              </button>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages || loading}
                className="inline-flex items-center gap-1 rounded-md border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 px-2.5 py-1 text-xs font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-40 transition-colors"
              >
                Próximo
                <ChevronRight className="h-3 w-3" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Detail modal */}
      {selectedOrder && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/50 p-4">
          <div className="w-full max-w-lg overflow-hidden rounded-xl bg-white dark:bg-gray-800 shadow-xl border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 px-5 py-4">
              <div>
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
                  Pedido #{selectedOrder.order_number}
                </h3>
                <p className="text-xs text-gray-400 dark:text-gray-500">{formatDateTime(selectedOrder.created_at)}</p>
              </div>
              <button
                onClick={() => setSelectedOrder(null)}
                className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-600 transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="max-h-[60vh] overflow-y-auto p-5 space-y-4">
              <span className={`inline-flex rounded px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[selectedOrder.status] || ''}`}>
                {STATUS_LABELS[selectedOrder.status] || selectedOrder.status}
              </span>
              <div className="rounded-lg bg-gray-50 dark:bg-gray-700 p-3">
                <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">Cliente</p>
                <p className="text-sm text-gray-900 dark:text-white">{selectedOrder.customer_name || 'N/A'}</p>
                <p className="text-xs text-gray-400 dark:text-gray-500">{selectedOrder.customer_phone}</p>
              </div>
              {selectedOrder.delivery_bairro && (
                <div className="rounded-lg bg-gray-50 dark:bg-gray-700 p-3">
                  <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">Endereço</p>
                  <p className="text-sm text-gray-700 dark:text-gray-300">{selectedOrder.delivery_bairro}</p>
                </div>
              )}
              <div className="flex items-center justify-between rounded-lg bg-primary-50 dark:bg-primary-900/20 p-3">
                <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">Total</span>
                <span className="text-lg font-bold text-primary-700 dark:text-primary-400">
                  {formatCurrency(selectedOrder.total_amount)}
                </span>
              </div>
            </div>
            <div className="border-t border-gray-200 dark:border-gray-700 px-5 py-3">
              <button
                onClick={() => setSelectedOrder(null)}
                className="w-full rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
