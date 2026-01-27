/**
 * Utilitário para construir URLs da API
 * Usa variáveis de ambiente do Vite para flexibilidade entre ambientes
 */

export function getApiUrl() {
  return import.meta.env.VITE_API_URL || 'http://192.168.10.156:8000/api'
}

export function buildApiEndpoint(endpoint) {
  const baseUrl = getApiUrl()
  // Remove leading slash se existir
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint.substring(1) : endpoint
  return `${baseUrl}/${cleanEndpoint}`
}

export function getAuthHeaders() {
  const token = localStorage.getItem('token')
  return {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
}

/**
 * Fazer requisição com headers de autenticação
 */
export async function apiRequest(endpoint, options = {}) {
  const url = buildApiEndpoint(endpoint)
  const headers = {
    ...getAuthHeaders(),
    ...options.headers
  }

  const response = await fetch(url, {
    ...options,
    headers
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || `Erro: ${response.status}`)
  }

  return response.json()
}
