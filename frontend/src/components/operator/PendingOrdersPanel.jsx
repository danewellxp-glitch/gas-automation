/**
 * Painel de Pedidos Pendentes para Operador
 * Aprovar, rejeitar e gerenciar pedidos do WhatsApp Bot
 */

import { useState, useEffect } from 'react'

export default function PendingOrdersPanel() {
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedOrder, setSelectedOrder] = useState(null)
  const [actionType, setActionType] = useState(null) // 'approve' or 'reject'
  const [rejectReason, setRejectReason] = useState('')
  const [processing, setProcessing] = useState(false)

  useEffect(() => {
    fetchOrders()
  }, [])

  const fetchOrders = async () => {
    try {
      setLoading(true)
      const response = await fetch('http://192.168.10.156:8000/api/orders/pending', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        setOrders(data)
      }
    } catch (error) {
      console.error('Erro ao buscar pedidos:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleApprove = async (orderId) => {
    try {
      setProcessing(true)
      const response = await fetch(`http://192.168.10.156:8000/api/orders/${orderId}/approve`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        }
      })

      if (response.ok) {
        await fetchOrders()
        setSelectedOrder(null)
        setActionType(null)
        alert('✅ Pedido aprovado com sucesso!')
      } else {
        alert('❌ Erro ao aprovar pedido')
      }
    } catch (error) {
      console.error('Erro ao aprovar:', error)
      alert('❌ Erro ao aprovar pedido')
    } finally {
      setProcessing(false)
    }
  }

  const handleReject = async (orderId) => {
    if (!rejectReason.trim()) {
      alert('Por favor, informe o motivo da rejeição')
      return
    }

    try {
      setProcessing(true)
      const response = await fetch(`http://192.168.10.156:8000/api/orders/${orderId}/reject`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ reason: rejectReason })
      })

      if (response.ok) {
        await fetchOrders()
        setSelectedOrder(null)
        setActionType(null)
        setRejectReason('')
        alert('✅ Pedido rejeitado')
      } else {
        alert('❌ Erro ao rejeitar pedido')
      }
    } catch (error) {
      console.error('Erro ao rejeitar:', error)
      alert('❌ Erro ao rejeitar pedido')
    } finally {
      setProcessing(false)
    }
  }

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(value)
  }

  const formatDateTime = (isoString) => {
    const date = new Date(isoString)
    return date.toLocaleString('pt-BR')
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="text-gray-600 mt-4">Carregando pedidos...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">📦 Pedidos Pendentes</h2>
          <p className="text-gray-600">Aprovar ou rejeitar pedidos do WhatsApp</p>
        </div>
        <button
          onClick={fetchOrders}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition"
        >
          🔄 Atualizar
        </button>
      </div>

      {/* Lista de Pedidos */}
      {orders.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <div className="text-6xl mb-4">🎉</div>
          <p className="text-xl font-semibold text-gray-800">Nenhum pedido pendente!</p>
          <p className="text-gray-600 mt-2">Todos os pedidos foram processados</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {orders.map((order) => (
            <div key={order.id} className="bg-white rounded-lg shadow hover:shadow-lg transition">
              <div className="p-6">
                {/* Header do Pedido */}
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h3 className="text-lg font-bold text-gray-800">
                      Pedido #{order.order_number || order.id}
                    </h3>
                    <p className="text-sm text-gray-600 mt-1">
                      📅 {formatDateTime(order.created_at)}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => {
                        setSelectedOrder(order)
                        setActionType('approve')
                      }}
                      className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition font-medium"
                    >
                      ✅ Aprovar
                    </button>
                    <button
                      onClick={() => {
                        setSelectedOrder(order)
                        setActionType('reject')
                      }}
                      className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition font-medium"
                    >
                      ❌ Rejeitar
                    </button>
                  </div>
                </div>

                {/* Informações do Cliente */}
                <div className="bg-gray-50 rounded-lg p-4 mb-4">
                  <h4 className="font-semibold text-gray-700 mb-2">👤 Cliente</h4>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <span className="text-gray-600">Nome:</span>
                      <span className="font-medium text-gray-800 ml-2">
                        {order.customer_name || 'N/A'}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-600">Telefone:</span>
                      <span className="font-medium text-gray-800 ml-2">
                        {order.customer_phone || 'N/A'}
                      </span>
                    </div>
                    {order.delivery_address && (
                      <div className="col-span-2">
                        <span className="text-gray-600">Endereço:</span>
                        <span className="font-medium text-gray-800 ml-2">
                          {order.delivery_address}
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Itens do Pedido */}
                <div className="mb-4">
                  <h4 className="font-semibold text-gray-700 mb-2">📦 Itens</h4>
                  <div className="space-y-2">
                    {order.items?.map((item, idx) => (
                      <div key={idx} className="flex justify-between items-center p-2 bg-gray-50 rounded">
                        <div>
                          <span className="font-medium">{item.product_name || item.name}</span>
                          <span className="text-gray-600 text-sm ml-2">x{item.quantity}</span>
                        </div>
                        <span className="font-bold">{formatCurrency(item.total || item.price * item.quantity)}</span>
                      </div>
                    )) || (
                      <p className="text-gray-500 text-sm">Nenhum item especificado</p>
                    )}
                  </div>
                </div>

                {/* Total */}
                <div className="border-t pt-4 flex justify-between items-center">
                  <span className="text-lg font-bold text-gray-700">Total:</span>
                  <span className="text-2xl font-bold text-green-600">
                    {formatCurrency(order.total_amount || order.total || 0)}
                  </span>
                </div>

                {/* Forma de Pagamento */}
                {order.payment_method && (
                  <div className="mt-2 text-sm text-gray-600">
                    💳 Pagamento: <span className="font-medium">{order.payment_method}</span>
                  </div>
                )}

                {/* Observações */}
                {order.notes && (
                  <div className="mt-4 p-3 bg-blue-50 rounded-lg">
                    <p className="text-sm text-gray-700">
                      <strong>📝 Observações:</strong> {order.notes}
                    </p>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal de Confirmação */}
      {selectedOrder && actionType && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-2xl w-full max-w-md">
            {/* Header */}
            <div className={`p-6 border-b ${actionType === 'approve' ? 'bg-green-50' : 'bg-red-50'}`}>
              <h3 className="text-lg font-bold text-gray-800">
                {actionType === 'approve' ? '✅ Aprovar Pedido' : '❌ Rejeitar Pedido'}
              </h3>
              <p className="text-sm text-gray-600 mt-1">
                Pedido #{selectedOrder.order_number || selectedOrder.id}
              </p>
            </div>

            {/* Content */}
            <div className="p-6">
              {actionType === 'approve' ? (
                <div>
                  <p className="text-gray-700 mb-4">
                    Confirmar aprovação deste pedido?
                  </p>
                  <div className="bg-gray-50 p-3 rounded">
                    <p className="text-sm font-medium">
                      Total: <span className="text-green-600">{formatCurrency(selectedOrder.total_amount || 0)}</span>
                    </p>
                  </div>
                </div>
              ) : (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Motivo da Rejeição:
                  </label>
                  <textarea
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:border-red-500"
                    rows="4"
                    placeholder="Ex: Produto indisponível, endereço fora da área de entrega, etc."
                  />
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="p-6 border-t bg-gray-50 rounded-b-lg flex gap-3">
              <button
                onClick={() => {
                  setSelectedOrder(null)
                  setActionType(null)
                  setRejectReason('')
                }}
                disabled={processing}
                className="flex-1 px-4 py-2 bg-gray-300 text-gray-800 rounded hover:bg-gray-400 transition font-medium disabled:opacity-50"
              >
                Cancelar
              </button>
              <button
                onClick={() => {
                  if (actionType === 'approve') {
                    handleApprove(selectedOrder.id)
                  } else {
                    handleReject(selectedOrder.id)
                  }
                }}
                disabled={processing}
                className={`flex-1 px-4 py-2 text-white rounded hover:opacity-90 transition font-medium disabled:opacity-50 ${
                  actionType === 'approve' ? 'bg-green-500' : 'bg-red-500'
                }`}
              >
                {processing ? 'Processando...' : 'Confirmar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
