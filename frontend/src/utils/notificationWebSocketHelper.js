/**
 * WebSocket Integration Helper
 * 
 * Facilita a integração entre o sistema de WebSocket existente
 * e o sistema de notificações.
 * 
 * Uso em componentes que já usam WebSocket:
 * 
 * @example
 * import { setupNotificationWebSocket } from './utils/notificationWebSocketHelper'
 * 
 * // No seu componente que recebe eventos WebSocket:
 * useEffect(() => {
 *   const handleMessage = (data) => {
 *     // Processar mensagem normalmente
 *     // ...
 *     
 *     // Integrar com notificações
 *     setupNotificationWebSocket.handleMessage(data)
 *   }
 * }, [])
 * 
 * @author Gas Automation
 * @version 1.0.0
 */

/**
 * Helper para integrar WebSocket com sistema de notificações
 */
class NotificationWebSocketHelper {
  /**
   * Processa mensagem WebSocket e dispara eventos de notificação
   * @param {Object} data - Dados da mensagem WebSocket
   */
  handleMessage(data) {
    if (!data || !data.type) return
    
    switch (data.type) {
      case 'order_created':
        this.handleOrderCreated(data)
        break
        
      case 'order_status_updated':
        this.handleOrderStatusUpdated(data)
        break
        
      case 'map_reset':
        this.handleMapReset(data)
        break
        
      case 'delivery_assigned':
        this.handleDeliveryAssigned(data)
        break
        
      default:
        // Ignorar outros tipos de eventos
        break
    }
  }
  
  /**
   * Handler para novo pedido criado
   */
  handleOrderCreated(data) {
    console.log('📦 WebSocket: order_created', data.order_id || data.order_number)
    
    // Disparar evento customizado para useNotifications
    window.dispatchEvent(new CustomEvent('websocket:order_created', {
      detail: { orderData: data }
    }))
  }
  
  /**
   * Handler para atualização de status
   */
  handleOrderStatusUpdated(data) {
    console.log('📝 WebSocket: order_status_updated', data.order_id)
    
    // Disparar evento customizado
    window.dispatchEvent(new CustomEvent('websocket:order_status_updated', {
      detail: {
        orderId: data.order_id,
        oldStatus: data.old_status,
        newStatus: data.new_status,
      }
    }))
  }
  
  /**
   * Handler para reset diário do mapa
   */
  handleMapReset(data) {
    console.log('🔄 WebSocket: map_reset')
    
    // Disparar evento customizado
    window.dispatchEvent(new CustomEvent('websocket:map_reset', {
      detail: data
    }))
  }
  
  /**
   * Handler para entrega atribuída (pode notificar também)
   */
  handleDeliveryAssigned(data) {
    console.log('🚚 WebSocket: delivery_assigned', data.delivery_id)
    
    // Disparar evento customizado
    window.dispatchEvent(new CustomEvent('websocket:delivery_assigned', {
      detail: data
    }))
  }
}

// Exportar instância singleton
export const setupNotificationWebSocket = new NotificationWebSocketHelper()

export default setupNotificationWebSocket
