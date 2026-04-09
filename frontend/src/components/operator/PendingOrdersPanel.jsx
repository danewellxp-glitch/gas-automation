/**
 * Painel de Pedidos Pendentes — Linear.app style
 * Rows compactas ~44px, approve/reject inline
 * + Sugestão de motorista ao aprovar (T05/T06)
 */

import { useState, useEffect } from 'react'
import { RefreshCcw, ChevronRight, ChevronDown, Check, X, Truck, MapPin, Star } from 'lucide-react'
import toast from 'react-hot-toast'
import api, { getOrdersPending } from '../../services/api'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

const formatCurrency = (value) =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value || 0)

const formatTime = (isoString) => {
  const date = new Date(isoString)
  return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}

export default function PendingOrdersPanel() {
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedOrder, setSelectedOrder] = useState(null)
  const [actionType, setActionType] = useState(null)
  const [rejectReason, setRejectReason] = useState('')
  const [processing, setProcessing] = useState(false)
  const [expanded, setExpanded] = useState(new Set())

  // Sugestão de motorista
  const [suggestedDrivers, setSuggestedDrivers] = useState([])
  const [loadingDrivers, setLoadingDrivers] = useState(false)
  const [selectedDriverId, setSelectedDriverId] = useState(null)

  useEffect(() => {
    fetchOrders()
  }, [])

  const fetchOrders = async () => {
    try {
      setLoading(true)
      const data = await getOrdersPending()
      setOrders(data)
    } catch (error) {
      console.error('Erro ao buscar pedidos:', error)
    } finally {
      setLoading(false)
    }
  }

  // Ao clicar Aprovar: busca sugestões antes de abrir o modal
  const handleClickApprove = async (order) => {
    setSelectedOrder(order)
    setActionType('approve')
    setSelectedDriverId(null)
    setSuggestedDrivers([])
    setLoadingDrivers(true)
    try {
      const token = localStorage.getItem('token')
      const res = await fetch(`${API_BASE}/drivers/orders/${order.id}/suggested-driver`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        setSuggestedDrivers(data.sugestoes || [])
      }
    } catch {
      // Sugestões são opcionais — não bloqueia o fluxo
    } finally {
      setLoadingDrivers(false)
    }
  }

  const handleApprove = async (orderId) => {
    try {
      setProcessing(true)
      await api.post(`/orders/${orderId}/approve`)

      // Se operador selecionou um motorista, atribui imediatamente após aprovação
      if (selectedDriverId) {
        try {
          const token = localStorage.getItem('token')
          await fetch(`${API_BASE}/orders/${orderId}/reassign-driver`, {
            method: 'PATCH',
            headers: {
              Authorization: `Bearer ${token}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              new_driver_id: selectedDriverId,
              motivo: 'Atribuição no momento da aprovação',
            }),
          })
          const driver = suggestedDrivers.find(d => d.driver_id === selectedDriverId)
          toast.success(`Pedido aprovado e atribuído para ${driver?.nome || 'motorista'}!`)
        } catch {
          toast.success('Pedido aprovado!')
          toast.error('Não foi possível atribuir o motorista — tente pela tela de entregadores')
        }
      } else {
        toast.success('Pedido aprovado com sucesso!')
      }

      await fetchOrders()
      setSelectedOrder(null)
      setActionType(null)
      setSelectedDriverId(null)
      setSuggestedDrivers([])
    } catch (error) {
      console.error('Erro ao aprovar:', error)
      toast.error('Erro ao aprovar pedido')
    } finally {
      setProcessing(false)
    }
  }

  const handleReject = async (orderId) => {
    if (!rejectReason.trim()) {
      toast.error('Por favor, informe o motivo da rejeição')
      return
    }
    try {
      setProcessing(true)
      await api.post(`/orders/${orderId}/reject`, { reason: rejectReason })
      await fetchOrders()
      setSelectedOrder(null)
      setActionType(null)
      setRejectReason('')
      toast.success('Pedido rejeitado')
    } catch (error) {
      console.error('Erro ao rejeitar:', error)
      toast.error('Erro ao rejeitar pedido')
    } finally {
      setProcessing(false)
    }
  }

  const toggleExpand = (orderId) => {
    setExpanded(prev => {
      const next = new Set(prev)
      if (next.has(orderId)) next.delete(orderId)
      else next.add(orderId)
      return next
    })
  }

  const closeModal = () => {
    setSelectedOrder(null)
    setActionType(null)
    setRejectReason('')
    setSelectedDriverId(null)
    setSuggestedDrivers([])
  }

  if (loading) {
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
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Pedidos Pendentes</h2>
          {orders.length > 0 && (
            <span className="inline-flex items-center justify-center w-5 h-5 text-xs font-semibold text-white bg-amber-500 rounded-full">
              {orders.length}
            </span>
          )}
        </div>
        <button
          onClick={fetchOrders}
          disabled={loading}
          className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 transition-colors"
        >
          <RefreshCcw className="h-3 w-3" />
          Atualizar
        </button>
      </div>

      {/* List */}
      {orders.length === 0 ? (
        <div className="flex items-center justify-center h-32 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
          <div className="text-center">
            <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Sem pedidos pendentes</p>
            <p className="mt-0.5 text-xs text-gray-400 dark:text-gray-500">Todos os pedidos foram processados.</p>
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden">

          {/* Column headers */}
          <div className="flex items-center gap-2 px-3 py-1.5 border-b border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/80">
            <span className="w-4" />
            <span className="w-20 text-xs font-medium text-gray-400 uppercase tracking-wide shrink-0">Status</span>
            <span className="w-12 text-xs font-medium text-gray-400 uppercase tracking-wide shrink-0">OS</span>
            <span className="flex-1 text-xs font-medium text-gray-400 uppercase tracking-wide">Cliente</span>
            <span className="w-28 text-xs font-medium text-gray-400 uppercase tracking-wide hidden md:block shrink-0">Endereço</span>
            <span className="w-14 text-xs font-medium text-gray-400 uppercase tracking-wide hidden sm:block shrink-0">Pagto.</span>
            <span className="w-20 text-xs font-medium text-gray-400 uppercase tracking-wide text-right shrink-0">Total</span>
            <span className="w-10 text-xs font-medium text-gray-400 uppercase tracking-wide hidden sm:block shrink-0">Hora</span>
            <span className="w-32 shrink-0" />
          </div>

          {orders.map((order, idx) => {
            const isExpanded = expanded.has(order.id)

            let groupedList = []
            let totalFromItems = 0
            if (order.items?.length) {
              const grouped = {}
              order.items.forEach((item) => {
                const code = item.product_code || item.product_name || 'item'
                const unitPrice = Number(item.unit_price ?? 0)
                const qty = item.quantity || 0
                if (!grouped[code]) {
                  grouped[code] = { product_name: item.product_name || item.name || code, quantity: 0, unit_price: unitPrice }
                }
                grouped[code].quantity += qty
                if (unitPrice && !grouped[code].unit_price) grouped[code].unit_price = unitPrice
              })
              groupedList = Object.entries(grouped).map(([code, row]) => {
                const unit = row.unit_price || 0
                return [code, { ...row, unit_price: unit, subtotal: row.quantity * unit }]
              })
              totalFromItems = groupedList.reduce((acc, [, row]) => acc + row.subtotal, 0)
            }

            const displayTotal = groupedList.length > 0 ? totalFromItems : (order.total_amount || order.total || 0)

            return (
              <div key={order.id} className={idx > 0 ? 'border-t border-gray-100 dark:border-gray-700' : ''}>
                {/* Main row */}
                <div className="flex items-center gap-2 px-3 h-11 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors group">

                  <button
                    onClick={() => toggleExpand(order.id)}
                    className="w-4 flex items-center justify-center text-gray-300 dark:text-gray-600 hover:text-gray-500 dark:hover:text-gray-400 shrink-0"
                  >
                    {isExpanded
                      ? <ChevronDown className="w-3.5 h-3.5" />
                      : <ChevronRight className="w-3.5 h-3.5" />
                    }
                  </button>

                  <span className="w-20 shrink-0">
                    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-400">
                      Pendente
                    </span>
                  </span>

                  <span className="w-12 text-xs font-mono text-gray-400 dark:text-gray-500 shrink-0">
                    #{order.order_number || order.id}
                  </span>

                  <span className="flex-1 min-w-0">
                    <span className="block text-sm text-gray-900 dark:text-white truncate">
                      {order.customer_name || 'N/A'}
                    </span>
                    <span className="block text-xs text-gray-400 dark:text-gray-500 truncate md:hidden">
                      {(order.customer_phone || '').replace(/@c\.us$/i, '')}
                    </span>
                  </span>

                  <span className="w-28 text-xs text-gray-400 dark:text-gray-500 truncate hidden md:block shrink-0">
                    {order.delivery_address || '—'}
                  </span>

                  <span className="w-14 text-xs text-gray-500 dark:text-gray-400 truncate hidden sm:block shrink-0">
                    {order.payment_method || '—'}
                  </span>

                  <span className="w-20 text-sm font-medium text-gray-900 dark:text-white text-right shrink-0">
                    {formatCurrency(displayTotal)}
                  </span>

                  <span className="w-10 text-xs text-gray-400 dark:text-gray-500 hidden sm:block shrink-0">
                    {formatTime(order.created_at)}
                  </span>

                  <div className="flex items-center gap-1 w-32 shrink-0 justify-end">
                    <button
                      onClick={() => handleClickApprove(order)}
                      className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded hover:bg-emerald-100 dark:hover:bg-emerald-900/30 transition-colors"
                    >
                      <Check className="w-3 h-3" />
                      Aprovar
                    </button>
                    <button
                      onClick={() => { setSelectedOrder(order); setActionType('reject') }}
                      className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
                    >
                      <X className="w-3 h-3" />
                      Rejeitar
                    </button>
                  </div>
                </div>

                {/* Expanded items */}
                {isExpanded && (
                  <div className="px-9 pb-2 border-t border-gray-100 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-800/50">
                    <div className="py-2 space-y-0.5">
                      {groupedList.length === 0 ? (
                        <p className="text-xs text-gray-400 dark:text-gray-500 py-1">Nenhum item especificado</p>
                      ) : (
                        groupedList.map(([code, row]) => (
                          <div key={code} className="flex items-center gap-2 text-xs py-0.5">
                            <span className="text-gray-300 dark:text-gray-600">↳</span>
                            <span className="text-gray-700 dark:text-gray-300">{row.product_name}</span>
                            <span className="text-gray-400 dark:text-gray-500">× {row.quantity}</span>
                            {row.unit_price > 0 && (
                              <span className="text-gray-400 dark:text-gray-500">
                                (R$ {Number(row.unit_price).toFixed(2).replace('.', ',')}/un)
                              </span>
                            )}
                            <span className="ml-auto font-medium text-gray-700 dark:text-gray-300">
                              {formatCurrency(row.subtotal)}
                            </span>
                          </div>
                        ))
                      )}
                      {order.payment_method && (
                        <p className="text-xs text-gray-400 dark:text-gray-500 pt-1">
                          Pagamento: <span className="font-medium text-gray-600 dark:text-gray-400">{order.payment_method}</span>
                        </p>
                      )}
                      {order.notes && (
                        <p className="text-xs text-gray-400 dark:text-gray-500">
                          Obs: <span className="text-gray-600 dark:text-gray-400">{order.notes}</span>
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Modal de confirmação */}
      {selectedOrder && actionType && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/50 p-4">
          <div className="w-full max-w-md overflow-hidden rounded-xl bg-white dark:bg-gray-800 shadow-xl">

            {/* Header do modal */}
            <div className={`border-b border-gray-200 dark:border-gray-700 p-6 ${actionType === 'approve' ? 'bg-green-50 dark:bg-green-900/20' : 'bg-red-50 dark:bg-red-900/20'}`}>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                {actionType === 'approve' ? 'Aprovar pedido' : 'Rejeitar pedido'}
              </h3>
              <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                Pedido #{selectedOrder.order_number || selectedOrder.id}
                {selectedOrder.delivery_bairro && (
                  <span className="ml-2 inline-flex items-center gap-1 text-xs text-gray-500">
                    <MapPin className="h-3 w-3" />{selectedOrder.delivery_bairro}
                  </span>
                )}
              </p>
            </div>

            <div className="p-6">
              {actionType === 'approve' ? (
                <div className="space-y-4">
                  {/* Resumo do pedido */}
                  <div className="rounded-lg bg-gray-50 dark:bg-gray-700 p-3 text-sm">
                    Total: <span className="font-semibold text-gray-900 dark:text-white">{formatCurrency(selectedOrder.total_amount || 0)}</span>
                  </div>

                  {/* Seção de motoristas sugeridos */}
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <Truck className="h-4 w-4 text-gray-500" />
                      <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        Motorista sugerido
                        <span className="ml-1 text-xs font-normal text-gray-400">(opcional)</span>
                      </p>
                    </div>

                    {loadingDrivers ? (
                      <div className="flex items-center justify-center py-4">
                        <div className="h-5 w-5 animate-spin rounded-full border-2 border-gray-200 border-t-emerald-600" />
                      </div>
                    ) : suggestedDrivers.length === 0 ? (
                      <p className="text-xs text-gray-400 py-2 text-center border border-dashed border-gray-200 rounded-lg">
                        Nenhum motorista disponível no momento
                      </p>
                    ) : (
                      <div className="space-y-1.5 max-h-52 overflow-y-auto">
                        {/* Opção: sem motorista */}
                        <label className="flex items-center gap-3 p-2 rounded-lg border cursor-pointer transition-colors border-gray-200 hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-700">
                          <input
                            type="radio"
                            name="driver"
                            value=""
                            checked={selectedDriverId === null}
                            onChange={() => setSelectedDriverId(null)}
                            className="h-3.5 w-3.5 text-emerald-600"
                          />
                          <span className="text-xs text-gray-500 dark:text-gray-400">Aprovar sem atribuir motorista</span>
                        </label>

                        {/* Motoristas sugeridos */}
                        {suggestedDrivers.map((driver, i) => (
                          <label
                            key={driver.driver_id}
                            className={`flex items-center gap-3 p-2 rounded-lg border cursor-pointer transition-colors ${
                              selectedDriverId === driver.driver_id
                                ? 'border-emerald-400 bg-emerald-50 dark:bg-emerald-900/20'
                                : 'border-gray-200 hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-700'
                            }`}
                          >
                            <input
                              type="radio"
                              name="driver"
                              value={driver.driver_id}
                              checked={selectedDriverId === driver.driver_id}
                              onChange={() => setSelectedDriverId(driver.driver_id)}
                              className="h-3.5 w-3.5 text-emerald-600"
                            />
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-1.5">
                                {i === 0 && <Star className="h-3 w-3 text-amber-400 fill-amber-400 shrink-0" />}
                                <span className="text-sm font-medium text-gray-900 dark:text-white truncate">{driver.nome}</span>
                              </div>
                              <div className="flex items-center gap-2 mt-0.5 text-xs text-gray-500">
                                {driver.bairro && (
                                  <span className="flex items-center gap-0.5">
                                    <MapPin className="h-3 w-3" />{driver.bairro}
                                  </span>
                                )}
                                <span>{driver.entregas_ativas} entrega{driver.entregas_ativas !== 1 ? 's' : ''} ativa{driver.entregas_ativas !== 1 ? 's' : ''}</span>
                                {driver.vehicle_type && <span>· {driver.vehicle_type}</span>}
                              </div>
                            </div>
                          </label>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div>
                  <label className="block text-sm font-medium text-gray-900 dark:text-white mb-2">
                    Motivo da Rejeição:
                  </label>
                  <textarea
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    className="block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 dark:text-white dark:placeholder-gray-400 px-3 py-2 text-sm text-gray-900 focus:border-red-500 focus:ring-red-500"
                    rows="4"
                    placeholder="Ex: Produto indisponível, endereço fora da área de entrega, etc."
                  />
                </div>
              )}
            </div>

            <div className="flex gap-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700 p-6">
              <button
                onClick={closeModal}
                disabled={processing}
                className="flex-1 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50"
              >
                Cancelar
              </button>
              <button
                onClick={() => actionType === 'approve' ? handleApprove(selectedOrder.id) : handleReject(selectedOrder.id)}
                disabled={processing}
                className={`flex-1 rounded-lg px-4 py-2 text-sm font-medium text-white disabled:opacity-50 ${
                  actionType === 'approve' ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'
                }`}
              >
                {processing
                  ? 'Processando...'
                  : actionType === 'approve'
                    ? selectedDriverId ? 'Aprovar e atribuir' : 'Aprovar'
                    : 'Confirmar rejeição'
                }
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
