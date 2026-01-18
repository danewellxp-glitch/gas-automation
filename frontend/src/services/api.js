import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

// Orders
export const getOrders = async (params = {}) => {
  const response = await api.get('/orders', { params })
  return response.data
}

export const getOrder = async (id) => {
  const response = await api.get(`/orders/${id}`)
  return response.data
}

export const updateOrderStatus = async (id, status) => {
  const response = await api.patch(`/orders/${id}/status`, { status })
  return response.data
}

// Customers
export const getCustomers = async () => {
  const response = await api.get('/customers')
  return response.data
}

// Products
export const getProducts = async () => {
  const response = await api.get('/products')
  return response.data
}

// Analytics
export const getAnalyticsSummary = async () => {
  const response = await api.get('/analytics/summary')
  return response.data
}

// Health
export const getHealth = async () => {
  const response = await api.get('/health')
  return response.data
}

// Chats
export const getChats = async () => {
  const response = await api.get('/chats')
  return response.data
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

export default api
