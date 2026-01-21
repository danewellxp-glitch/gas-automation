/**
 * Card de Entrega
 */

const STATUS_CONFIG = {
  pending: { label: '🟨 Disponível', color: 'bg-yellow-100 border-yellow-300', textColor: 'text-yellow-800' },
  assigned: { label: '🟦 Alocado', color: 'bg-blue-100 border-blue-300', textColor: 'text-blue-800' },
  picked_up: { label: '🟧 Produtos Retirados', color: 'bg-orange-100 border-orange-300', textColor: 'text-orange-800' },
  in_transit: { label: '🟦 Em Trânsito', color: 'bg-blue-100 border-blue-300', textColor: 'text-blue-800' },
  arrived: { label: '🟪 Chegou no Local', color: 'bg-purple-100 border-purple-300', textColor: 'text-purple-800' },
  delivered: { label: '🟩 Entregue', color: 'bg-green-100 border-green-300', textColor: 'text-green-800' }
}

export default function DeliveryCard({ delivery, onAction, isPending = false }) {
  const statusConfig = STATUS_CONFIG[delivery.status] || STATUS_CONFIG.assigned

  const formatTime = (dateString) => {
    if (!dateString) return '--:--'
    return new Date(dateString).toLocaleTimeString('pt-BR', {
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <div 
      className={`rounded-lg shadow border-2 p-4 cursor-pointer hover:shadow-lg transition-shadow ${statusConfig.color}`}
      onClick={onAction}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-bold text-gray-800 text-lg">
            Pedido #{delivery.order_number}
          </h3>
          <p className={`text-sm font-medium ${statusConfig.textColor}`}>
            {statusConfig.label}
          </p>
        </div>
        {delivery.estimated_minutes && (
          <div className="text-right">
            <span className="text-sm font-semibold text-gray-700">
              ⏱️ {delivery.estimated_minutes} min
            </span>
          </div>
        )}
      </div>

      {/* Endereço */}
      {delivery.delivery_address && (
        <div className="mb-3 text-sm text-gray-700">
          <p className="font-medium">📍 {delivery.bairro || delivery.delivery_address.bairro}</p>
          <p className="text-gray-600">
            {delivery.delivery_address.street}, {delivery.delivery_address.number}
          </p>
        </div>
      )}

      {/* Itens */}
      {delivery.order_items && delivery.order_items.length > 0 && (
        <div className="mb-3 text-sm text-gray-700">
          <p className="font-medium">📦 Itens:</p>
          <div className="ml-4">
            {delivery.order_items.map((item, index) => (
              <p key={index} className="text-gray-600">
                • {item.quantity}x {item.product_name}
              </p>
            ))}
          </div>
        </div>
      )}

      {/* Total */}
      <div className="flex items-center justify-between pt-3 border-t border-gray-300">
        <span className="font-bold text-green-600 text-lg">
          R$ {delivery.order_total?.toFixed(2) || '0.00'}
        </span>
        
        {!isPending && delivery.assigned_at && (
          <span className="text-xs text-gray-500">
            Alocado às {formatTime(delivery.assigned_at)}
          </span>
        )}
        
        {isPending && (
          <span className="text-xs font-semibold text-yellow-700">
            👉 Toque para ver
          </span>
        )}
      </div>
    </div>
  )
}
