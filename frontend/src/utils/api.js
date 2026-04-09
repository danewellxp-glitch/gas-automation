/**
 * Utilitário para construir URLs da API
 * Usa variáveis de ambiente do Vite para flexibilidade entre ambientes
 */

export function getApiUrl() {
  return import.meta.env.VITE_API_URL || 'http://192.168.10.167:5688/api'
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
  const token = localStorage.getItem('token')
  
  // Verificar se tem token antes de fazer requisição
  if (!token && !options.skipAuth) {
    console.warn('Nenhum token encontrado, redirecionando para login')
    localStorage.removeItem('token')
    window.location.href = '/login'
    throw new Error('Sessão expirada. Por favor, faça login novamente.')
  }
  
  const headers = {
    ...getAuthHeaders(),
    ...options.headers
  }

  const response = await fetch(url, {
    ...options,
    headers
  })

  if (!response.ok) {
    // Se for 401, pode ser token expirado ou inválido
    if (response.status === 401) {
      // Tentar limpar token e redirecionar para login
      localStorage.removeItem('token')
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
      const error = await response.json().catch(() => ({}))
      throw new Error(error.detail || 'Sessão expirada. Por favor, faça login novamente.')
    }
    
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || error.message || `Erro: ${response.status}`)
  }

  return response.json()
}
