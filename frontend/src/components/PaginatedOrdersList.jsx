/**
 * Lista de Pedidos com Paginação e Infinite Scroll
 * 
 * Componente reutilizável que pode ser usado em:
 * - OperatorDashboard
 * - OwnerDashboard
 * - AdminDashboard
 * 
 * Features:
 * - Lazy loading (carrega apenas 30 por vez)
 * - Infinite scroll automático
 * - Filtros por status/bairro
 * - Atualização em tempo real via WebSocket
 */

import { useCallback } from 'react'
import { usePagination, useInfiniteScroll } from '../hooks/usePagination'
import { useSharedWebSocketEvent } from '../hooks/useSharedWebSocket'
import { getOrdersPaginated } from '../services/api'

export default function PaginatedOrdersList({ filters = {}, onOrderClick }) {
  // Função que busca pedidos paginados
  const fetchOrders = useCallback(async (page, pageSize) => {
    try {
      return await getOrdersPaginated(page, pageSize, filters)
    } catch (error) {
      console.error('Erro ao carregar pedidos:', error)
      throw error
    }
  }, [filters])

  // Hook de paginação
  const pagination = usePagination(fetchOrders, {
    pageSize: 30,
    enabled: true,
    dependencies: [JSON.stringify(filters)], // Reset quando filtros mudarem
  })

  const {
    data: orders,
    total,
    loading,
    error,
    isEmpty,
    hasNext,
    addItem,
    updateItem,
  } = pagination

  // Infinite scroll
  const { containerRef } = useInfiniteScroll(pagination, {
    threshold: 500, // Carregar quando estiver a 500px do fundo
  })

  // WebSocket: novo pedido
  useSharedWebSocketEvent('new_order', useCallback((data) => {
    const order = data.data
    
    // Verificar se passa nos filtros
    if (filters.status && order.status !== filters.status) {
      return
    }
    if (filters.bairro && order.delivery_bairro !== filters.bairro) {
      return
    }
    
    // Adicionar no topo da lista
    addItem(order)
    
    // Notificação sonora
    try {
      const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdH2JkZiYl5eSjImEf35/goeMkZaZmpmYlZGNiYWBf4CGi5CUl5mZmJaSkY2JhYKAg4iNkpWYmZiWk5CLh4OCgYWKj5OWmJeWk5CKhoGAfoCEioyQk5aWlZOQjIeC')
      audio.volume = 0.3
      audio.play().catch(() => {})
    } catch (e) {
      // Ignorar erros de som
    }
  }, [addItem, filters]))

  // WebSocket: atualização de pedido
  useSharedWebSocketEvent('order_update', useCallback((data) => {
    const { order_id, status, order } = data.data
    
    if (order) {
      updateItem(order_id, order)
    } else {
      updateItem(order_id, (prev) => ({ ...prev, status }))
    }
  }, [updateItem]))

  // Renderizar loading inicial
  if (loading && orders.length === 0) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        <span className="ml-3 text-gray-600">Carregando pedidos...</span>
      </div>
    )
  }

  // Renderizar erro
  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 m-4">
        <p className="text-red-800">❌ Erro ao carregar pedidos: {error}</p>
      </div>
    )
  }

  // Renderizar lista vazia
  if (isEmpty) {
    return (
      <div className="text-center p-8 text-gray-500">
        <p>📦 Nenhum pedido encontrado</p>
        {filters.status && <p className="text-sm mt-2">Filtro: {filters.status}</p>}
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header com contadores */}
      <div className="bg-white border-b px-4 py-3 flex justify-between items-center">
        <div>
          <h3 className="font-semibold text-gray-800">Pedidos</h3>
          <p className="text-sm text-gray-600">
            Mostrando {orders.length} de {total} pedidos
            {filters.status && ` (${filters.status})`}
          </p>
        </div>
        {hasNext && (
          <span className="text-xs text-gray-500">
            ↓ Role para carregar mais
          </span>
        )}
      </div>

      {/* Lista com scroll */}
      <div 
        ref={containerRef}
        className="flex-1 overflow-y-auto p-4 space-y-3"
      >
        {orders.map((order) => (
          <OrderCard 
            key={order.id} 
            order={order} 
            onClick={() => onOrderClick?.(order)}
          />
        ))}

        {/* Loading indicator no final */}
        {loading && orders.length > 0 && (
          <div className="flex justify-center py-4">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            <span className="ml-2 text-gray-600">Carregando mais...</span>
          </div>
        )}

        {/* Fim da lista */}
        {!hasNext && orders.length > 0 && (
          <div className="text-center py-4 text-gray-500 text-sm">
            ✓ Todos os pedidos carregados
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * Card de Pedido Individual
 */
function OrderCard({ order, onClick }) {
  const getStatusColor = (status) => {
    const colors = {
      pending: 'bg-yellow-100 text-yellow-800',
      paid: 'bg-green-100 text-green-800',
      preparing: 'bg-blue-100 text-blue-800',
      dispatched: 'bg-purple-100 text-purple-800',
      delivered: 'bg-gray-100 text-gray-800',
      cancelled: 'bg-red-100 text-red-800',
    }
    return colors[status] || 'bg-gray-100 text-gray-800'
  }

  const getStatusLabel = (status) => {
    const labels = {
      pending: 'Pendente',
      paid: 'Pago',
      preparing: 'Preparando',
      dispatched: 'Em Rota',
      delivered: 'Entregue',
      cancelled: 'Cancelado',
    }
    return labels[status] || status
  }

  return (
    <div 
      className="bg-white border rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
      onClick={onClick}
    >
      <div className="flex justify-between items-start mb-2">
        <div>
          <span className="text-sm text-gray-500">#{order.id.substring(0, 8)}</span>
          <h4 className="font-semibold text-gray-800">{order.customer_name || 'Cliente'}</h4>
        </div>
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(order.status)}`}>
          {getStatusLabel(order.status)}
        </span>
      </div>

      <div className="text-sm text-gray-600 space-y-1">
        {order.delivery_address && (
          <p className="flex items-center gap-1">
            <span>📍</span>
            {order.delivery_address}
          </p>
        )}
        {order.delivery_bairro && (
          <p className="text-gray-500">Bairro: {order.delivery_bairro}</p>
        )}
        <p className="font-semibold text-gray-800">
          Total: R$ {order.total?.toFixed(2) || '0.00'}
        </p>
      </div>

      {order.created_at && (
        <p className="text-xs text-gray-400 mt-2">
          {new Date(order.created_at).toLocaleString('pt-BR')}
        </p>
      )}
    </div>
  )
}
