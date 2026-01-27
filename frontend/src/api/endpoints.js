/**
 * URLs centralizadas para todos os endpoints da API
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://192.168.10.156:8000';

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
    ASAAS: `${API_BASE_URL}/api/webhooks/asaas`,
    WAHA: `${API_BASE_URL}/api/webhooks/waha`,
  },

  // Integrações
  INTEGRATIONS: {
    STATUS: `${API_BASE_URL}/api/integrations/status`,
  },
};

// URLs para WebSocket
export const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://192.168.10.156:8000';

export const WS_ENDPOINTS = {
  CHAT: `${WS_BASE_URL}/ws/chat`,
  DRIVER_LOCATION: (driverId) => `${WS_BASE_URL}/ws/drivers/${driverId}/location`,
  NOTIFICATIONS: `${WS_BASE_URL}/ws/notifications`,
};
