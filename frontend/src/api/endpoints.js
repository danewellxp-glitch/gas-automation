/**
 * URLs centralizadas para todos os endpoints da API
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://192.168.10.167:8000';

export const ENDPOINTS = {
  // Autenticação
  AUTH: {
    LOGIN: `${API_BASE_URL}/api/auth/login`,
    REGISTER: `${API_BASE_URL}/api/auth/register`,
    LOGOUT: `${API_BASE_URL}/api/auth/logout`,
    ME: `${API_BASE_URL}/api/auth/me`,
    REFRESH: `${API_BASE_URL}/api/auth/refresh-token`,
  },

  // Clientes
  CUSTOMERS: {
    LIST: `${API_BASE_URL}/api/customers`,
    CREATE: `${API_BASE_URL}/api/customers`,
    DETAIL: (id) => `${API_BASE_URL}/api/customers/${id}`,
    UPDATE: (id) => `${API_BASE_URL}/api/customers/${id}`,
    DELETE: (id) => `${API_BASE_URL}/api/customers/${id}`,
    ORDERS: (id) => `${API_BASE_URL}/api/customers/${id}/orders`,
  },

  // Pedidos
  ORDERS: {
    LIST: `${API_BASE_URL}/api/orders`,
    CREATE: `${API_BASE_URL}/api/orders`,
    DETAIL: (id) => `${API_BASE_URL}/api/orders/${id}`,
    UPDATE: (id) => `${API_BASE_URL}/api/orders/${id}`,
    DELETE: (id) => `${API_BASE_URL}/api/orders/${id}`,
    STATUS: (id) => `${API_BASE_URL}/api/orders/${id}/status`,
    TIMELINE: (id) => `${API_BASE_URL}/api/orders/${id}/timeline`,
  },

  // Entregadores
  DRIVERS: {
    LIST: `${API_BASE_URL}/api/drivers`,
    CREATE: `${API_BASE_URL}/api/drivers`,
    DETAIL: (id) => `${API_BASE_URL}/api/drivers/${id}`,
    UPDATE: (id) => `${API_BASE_URL}/api/drivers/${id}`,
    DELETE: (id) => `${API_BASE_URL}/api/drivers/${id}`,
    LOCATION: (id) => `${API_BASE_URL}/api/drivers/${id}/location`,
    ONLINE: (id) => `${API_BASE_URL}/api/drivers/${id}/online`,
    OFFLINE: (id) => `${API_BASE_URL}/api/drivers/${id}/offline`,
  },

  // Produtos
  PRODUCTS: {
    LIST: `${API_BASE_URL}/api/products`,
    CREATE: `${API_BASE_URL}/api/products`,
    DETAIL: (id) => `${API_BASE_URL}/api/products/${id}`,
    UPDATE: (id) => `${API_BASE_URL}/api/products/${id}`,
    DELETE: (id) => `${API_BASE_URL}/api/products/${id}`,
  },

  // Pagamentos
  PAYMENTS: {
    LIST: `${API_BASE_URL}/api/payments`,
    CREATE: `${API_BASE_URL}/api/payments`,
    DETAIL: (id) => `${API_BASE_URL}/api/payments/${id}`,
  },

  // Dashboard
  DASHBOARD: {
    STATS: `${API_BASE_URL}/api/dashboard/stats`,
    CHARTS: `${API_BASE_URL}/api/dashboard/charts`,
    ALERTS: `${API_BASE_URL}/api/dashboard/alerts`,
  },

  // Chat
  CHAT: {
    SEND: `${API_BASE_URL}/api/chatbot/message`,
    HISTORY: `${API_BASE_URL}/api/chatbot/history`,
    CLEAR: `${API_BASE_URL}/api/chatbot/clear`,
  },

  // Webhooks
  WEBHOOKS: {
    WAHA: `${API_BASE_URL}/api/webhooks/waha`,
  },

  // Integrações
  INTEGRATIONS: {
    STATUS: `${API_BASE_URL}/api/integrations/status`,
  },
};

export const FINANCEIRO = {
  DASHBOARD: `${API_BASE_URL}/api/financeiro/dashboard`,
  ACCOUNTS: `${API_BASE_URL}/api/financeiro/accounts`,
  TRANSACTIONS: `${API_BASE_URL}/api/financeiro/transactions`,
  TRANSACTION: (id) => `${API_BASE_URL}/api/financeiro/transactions/${id}`,
  TRANSACTION_PAY: (id) => `${API_BASE_URL}/api/financeiro/transactions/${id}/pay`,
  RECEIVABLES: `${API_BASE_URL}/api/financeiro/receivables`,
  RECEIVABLE_RECEIVE: (id) => `${API_BASE_URL}/api/financeiro/receivables/${id}/receive`,
  PAYABLES: `${API_BASE_URL}/api/financeiro/payables`,
  PAYABLE_PAY: (id) => `${API_BASE_URL}/api/financeiro/payables/${id}/pay`,
  CASH_FLOW: `${API_BASE_URL}/api/financeiro/cash-flow`,
  DRE: `${API_BASE_URL}/api/financeiro/dre`,
  COST_CENTERS: `${API_BASE_URL}/api/financeiro/cost-centers`,
  REPORTS_MONTHLY: `${API_BASE_URL}/api/financeiro/reports/monthly`,
  REPORTS_BY_CATEGORY: `${API_BASE_URL}/api/financeiro/reports/by-category`,
  // Novos — lucratividade e fiado
  ORDERS_PROFIT: `${API_BASE_URL}/api/financeiro/orders/profit`,
  ORDER_RECALC_PROFIT: (id) => `${API_BASE_URL}/api/financeiro/orders/${id}/recalculate-profit`,
  CUSTOMERS_DEBT: `${API_BASE_URL}/api/financeiro/customers/debt`,
  CUSTOMER_FINANCIAL: (id) => `${API_BASE_URL}/api/financeiro/customers/${id}/financial`,
  CUSTOMER_CREDIT_LIMIT: (id) => `${API_BASE_URL}/api/financeiro/customers/${id}/credit-limit`,
  INSIGHTS_BAIRROS: `${API_BASE_URL}/api/financeiro/insights/bairros`,
  INSIGHTS_EXPENSIVE: `${API_BASE_URL}/api/financeiro/insights/expensive-deliveries`,
  // Conciliação PIX
  CONCILIACAO_PIX: `${API_BASE_URL}/api/financeiro/conciliacao-pix`,
  CONCILIACAO_PIX_RUN: `${API_BASE_URL}/api/financeiro/conciliacao-pix/run`,
  CONCILIACAO_PIX_APROVAR: (id) => `${API_BASE_URL}/api/financeiro/conciliacao-pix/${id}/aprovar`,
  CONCILIACAO_PIX_RESOLVER: (itemId) => `${API_BASE_URL}/api/financeiro/conciliacao-pix/items/${itemId}/resolver`,
  CONCILIACAO_PIX_HISTORICO: `${API_BASE_URL}/api/financeiro/conciliacao-pix/historico`,
  // Vasilhames
  VASILHAMES_POSICAO: `${API_BASE_URL}/api/financeiro/vasilhames/posicao`,
  VASILHAMES_MOVIMENTACOES: `${API_BASE_URL}/api/financeiro/vasilhames/movimentacoes`,
  VASILHAMES_ENTRADA: `${API_BASE_URL}/api/financeiro/vasilhames/entrada`,
  VASILHAMES_RETORNO: `${API_BASE_URL}/api/financeiro/vasilhames/retorno`,
  VASILHAMES_PERDA: `${API_BASE_URL}/api/financeiro/vasilhames/perda`,
  VASILHAMES_AJUSTE: `${API_BASE_URL}/api/financeiro/vasilhames/ajuste`,
  VASILHAMES_ALERTAS: `${API_BASE_URL}/api/financeiro/vasilhames/alertas`,
  // Fiado
  FIADO_AGING: `${API_BASE_URL}/api/financeiro/fiado/aging`,
  FIADO_ENTRIES: `${API_BASE_URL}/api/financeiro/fiado/entries`,
  FIADO_ENTRY: (id) => `${API_BASE_URL}/api/financeiro/fiado/entries/${id}`,
  FIADO_PAGAR: (id) => `${API_BASE_URL}/api/financeiro/fiado/entries/${id}/pagar`,
  FIADO_COBRAR_WA: (id) => `${API_BASE_URL}/api/financeiro/fiado/entries/${id}/cobrar-whatsapp`,
  FIADO_COBRANCA_LOTE: `${API_BASE_URL}/api/financeiro/fiado/cobranca-lote`,
  // Notas Fiscais
  NFE_LIST: `${API_BASE_URL}/api/financeiro/nfe`,
  NFE_DETAIL: (id) => `${API_BASE_URL}/api/financeiro/nfe/${id}`,
  NFE_EMITIR: `${API_BASE_URL}/api/financeiro/nfe/emitir`,
  NFE_CANCELAR: (id) => `${API_BASE_URL}/api/financeiro/nfe/${id}/cancelar`,
  NFE_REENVIAR_WA: (id) => `${API_BASE_URL}/api/financeiro/nfe/${id}/reenviar-whatsapp`,
  NFE_RESUMO: `${API_BASE_URL}/api/financeiro/nfe/resumo`,
};

export const ESTOQUE = {
  DASHBOARD: `${API_BASE_URL}/api/estoque/dashboard`,
  PRODUCTS: `${API_BASE_URL}/api/estoque/products`,
  PRODUCT: (id) => `${API_BASE_URL}/api/estoque/products/${id}`,
  BALANCE: `${API_BASE_URL}/api/estoque/balance`,
  BALANCE_PRODUCT: (id) => `${API_BASE_URL}/api/estoque/balance/${id}`,
  MOVEMENTS: `${API_BASE_URL}/api/estoque/movements`,
  MOVEMENTS_ADJUSTMENT: `${API_BASE_URL}/api/estoque/movements/adjustment`,
  VEHICLE_LOADS: `${API_BASE_URL}/api/estoque/vehicle-loads`,
  VEHICLE_LOADS_OPEN: `${API_BASE_URL}/api/estoque/vehicle-loads/open`,
  VEHICLE_LOAD: (id) => `${API_BASE_URL}/api/estoque/vehicle-loads/${id}`,
  VEHICLE_LOAD_CLOSE: (id) => `${API_BASE_URL}/api/estoque/vehicle-loads/${id}/close`,
  SUPPLIERS: `${API_BASE_URL}/api/estoque/suppliers`,
  SUPPLIER: (id) => `${API_BASE_URL}/api/estoque/suppliers/${id}`,
  PURCHASE_ORDERS: `${API_BASE_URL}/api/estoque/purchase-orders`,
  PURCHASE_ORDER: (id) => `${API_BASE_URL}/api/estoque/purchase-orders/${id}`,
  PURCHASE_ORDER_RECEIVE: (id) => `${API_BASE_URL}/api/estoque/purchase-orders/${id}/receive`,
  REPORTS_DAILY: `${API_BASE_URL}/api/estoque/reports/daily`,
  REPORTS_LOW_STOCK: `${API_BASE_URL}/api/estoque/reports/low-stock`,
  REPORTS_BY_DRIVER: `${API_BASE_URL}/api/estoque/reports/by-driver`,
  VASILHAMES_POSICAO: `${API_BASE_URL}/api/estoque/vasilhames/posicao`,
  VASILHAMES_AJUSTE_DIRETO: `${API_BASE_URL}/api/estoque/vasilhames/ajuste`,
};

// URLs para WebSocket
export const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://192.168.10.167:8000';

export const WS_ENDPOINTS = {
  CHAT: `${WS_BASE_URL}/ws/chat`,
  DRIVER_LOCATION: (driverId) => `${WS_BASE_URL}/ws/drivers/${driverId}/location`,
  NOTIFICATIONS: `${WS_BASE_URL}/ws/notifications`,
};
