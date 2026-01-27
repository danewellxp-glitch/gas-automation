import axios from 'axios'
import logger from '../utils/logger'

// Pega a URL base da API das variáveis de ambiente
// Em produção, VITE_API_URL deve ser configurado no .env
const apiBaseURL = import.meta.env.VITE_API_URL || 'http://192.168.10.156:8000/api'

const api = axios.create({
  baseURL: apiBaseURL,
  timeout: 10000,
})

// Interceptor para adicionar token de autenticacao
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token') || localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Interceptor para tratar erros de autenticacao
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Limpa tokens invalidos
      localStorage.removeItem('access_token')
      localStorage.removeItem('token')
      // TODO: Redirecionar para login quando implementado
      // Por enquanto, apenas loga o erro para não quebrar navegação
      logger.warn('API 401: Não autenticado')
    }
    return Promise.reject(error)
  }
)

// ==================== Orders ====================
export const getOrders = async (params = {}) => {
  // Suporta paginação: { page, page_size, status, bairro, etc }
  const response = await api.get('/orders', { params })
  return response.data
}

export const getOrdersPaginated = async (page = 1, pageSize = 30, filters = {}) => {
  const params = { page, page_size: pageSize, ...filters }
  const response = await api.get('/orders', { params })
  return response.data
}

export const getOrdersToday = async () => {
  const response = await api.get('/orders/today')
  return response.data
}

export const getOrdersPending = async () => {
  const response = await api.get('/orders/pending')
  return response.data
}

export const getOrder = async (id) => {
  const response = await api.get(`/orders/${id}`)
  return response.data
}

export const createOrder = async (orderData) => {
  const response = await api.post('/orders', orderData)
  return response.data
}

export const updateOrderStatus = async (id, status) => {
  const response = await api.patch(`/orders/${id}/status`, { status })
  return response.data
}

export const cancelOrder = async (id, reason) => {
  const response = await api.delete(`/orders/${id}`, { data: { reason } })
  return response.data
}

export const getOrdersStats = async () => {
  const response = await api.get('/orders/stats/summary')
  return response.data
}

// ==================== Customers ====================
export const getCustomers = async (params = {}) => {
  const response = await api.get('/customers', { params })
  return response.data
}

export const getCustomer = async (id) => {
  const response = await api.get(`/customers/${id}`)
  return response.data
}

export const getCustomerByPhone = async (phone) => {
  const response = await api.get(`/customers/phone/${phone}`)
  return response.data
}

export const createCustomer = async (customerData) => {
  const response = await api.post('/customers', customerData)
  return response.data
}

export const updateCustomer = async (id, customerData) => {
  const response = await api.patch(`/customers/${id}`, customerData)
  return response.data
}

// ==================== Products ====================
export const getProducts = async (activeOnly = true) => {
  const response = await api.get('/products', { params: { active_only: activeOnly } })
  return response.data
}

export const getProductsActive = async () => {
  const response = await api.get('/products/active')
  return response.data
}

export const getProduct = async (id) => {
  const response = await api.get(`/products/${id}`)
  return response.data
}

export const getProductByCode = async (code) => {
  const response = await api.get(`/products/code/${code}`)
  return response.data
}

export const createProduct = async (productData) => {
  const response = await api.post('/products', productData)
  return response.data
}

export const updateProduct = async (id, productData) => {
  const response = await api.patch(`/products/${id}`, productData)
  return response.data
}

// ==================== Chats ====================
export const getChats = async () => {
  try {
    const token = localStorage.getItem('access_token') || localStorage.getItem('token')
    logger.debug('[API] getChats: Token presente?', !!token)
    const response = await api.get('/chats')
    logger.debug('[API] getChats: Resposta recebida')
    return response.data
  } catch (error) {
    logger.error('[API] getChats: Erro', {
      message: error.message,
      status: error.response?.status
    })
    throw error
  }
}

export const getChatMessages = async (phone, limit = 50) => {
  const response = await api.get(`/chats/${phone}/messages`, { params: { limit } })
  return response.data
}

export const sendChatMessage = async (phone, message) => {
  const response = await api.post(`/chats/${phone}/send`, { phone, message })
  return response.data
}

export const getChatContext = async (phone) => {
  const response = await api.get(`/chats/${phone}/context`)
  return response.data
}

export const resetChatContext = async (phone) => {
  const response = await api.delete(`/chats/${phone}/context`)
  return response.data
}

// ==================== Conversations (Operador) ====================
export const getConversations = async (filterType = null) => {
  const params = filterType ? { filter_type: filterType } : {}
  const response = await api.get('/conversations', { params })
  return response.data
}

export const getMyConversations = async () => {
  const response = await api.get('/my-conversations')
  return response.data
}

export const getConversationMessages = async (id) => {
  const response = await api.get(`/conversations/${id}/messages`)
  return response.data
}

export const assignConversation = async (id) => {
  const response = await api.post(`/conversations/${id}/assign`)
  return response.data
}

export const replyConversation = async (id, message) => {
  const response = await api.post(`/conversations/${id}/reply`, { message })
  return response.data
}

export const endConversation = async (id) => {
  const response = await api.post(`/conversations/${id}/end`)
  return response.data
}

// REMOVIDO: createTestConversation - Não usar em produção
// Conversas devem ser criadas apenas através do fluxo real do WhatsApp

// ==================== Bot Interactions ====================
export const getBotInteractions = async () => {
  const response = await api.get('/bot-interactions')
  return response.data
}

// ==================== Chatbot ====================
export const getChatbotStatus = async () => {
  const response = await api.get('/chatbot/status')
  return response.data
}

export const testChatbot = async (message, phone) => {
  const response = await api.post('/chatbot/test', { message, phone_number: phone })
  return response.data
}

export const clearChatbotContext = async (phone) => {
  const response = await api.delete(`/chatbot/context/${phone}`)
  return response.data
}

// ==================== Dashboard Owner ====================
export const getOwnerDashboard = async () => {
  const response = await api.get('/dashboard/owner')
  return response.data
}

// ==================== Settings ====================
export const getSettings = async () => {
  const response = await api.get('/settings')
  return response.data
}

export const updateSettings = async (settings) => {
  const response = await api.put('/settings', settings)
  return response.data
}

// ==================== Analytics ====================
export const getAnalyticsSummary = async () => {
  const response = await api.get('/analytics/summary')
  return response.data
}

// ==================== Auth ====================
export const login = async (username, password) => {
  const formData = new URLSearchParams()
  formData.append('username', username)
  formData.append('password', password)

  const response = await api.post('/auth/token', formData, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
  })
  return response.data
}

export const register = async (userData) => {
  const response = await api.post('/auth/register', userData)
  return response.data
}

export const getCurrentUser = async () => {
  const response = await api.get('/auth/users/me')
  return response.data
}

export const updateCurrentUser = async (userData) => {
  const response = await api.put('/auth/users/me', userData)
  return response.data
}

// ==================== Health ====================
export const getHealth = async () => {
  const response = await api.get('/health')
  return response.data
}

export default api
