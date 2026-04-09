/**
 * API específica para Drivers (Entregadores)
 * Conecta com backend em http://192.168.10.167:5688
 */

import { buildApiEndpoint, getAuthHeaders } from './api'

const API_BASE = import.meta.env.VITE_API_URL || 'http://192.168.10.167:5688/api'

/**
 * Login específico para drivers
 * @param {string} username - Username (apenas para salvar no localStorage)
 * @param {string} email - Email do driver
 * @param {string} password - Senha
 */
export async function driverLogin(username, email, password) {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ email, password })
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || 'Erro ao fazer login')
  }

  const data = await response.json()

  // Verificar se é driver
  if (data.role !== 'driver') {
    throw new Error('Usuário não é um entregador. Acesso negado.')
  }

  return data
}

/**
 * Buscar perfil do driver logado
 */
export async function getDriverProfile() {
  const response = await fetch(buildApiEndpoint('drivers/me'), {
    headers: getAuthHeaders()
  })

  if (!response.ok) {
    throw new Error('Erro ao buscar perfil')
  }

  return response.json()
}

/**
 * Buscar estatísticas do driver
 */
export async function getDriverStats() {
  const response = await fetch(buildApiEndpoint('drivers/me/stats'), {
    headers: getAuthHeaders()
  })

  if (!response.ok) {
    throw new Error('Erro ao buscar estatísticas')
  }

  return response.json()
}

/**
 * Atualizar status do driver (online/offline/busy/break)
 */
export async function updateDriverStatus(status) {
  const response = await fetch(buildApiEndpoint('drivers/me/status'), {
    method: 'PUT',
    headers: getAuthHeaders(),
    body: JSON.stringify({ status })
  })

  if (!response.ok) {
    throw new Error('Erro ao atualizar status')
  }

  return response.json()
}

/**
 * Atualizar localização GPS do driver
 */
export async function updateDriverLocation(latitude, longitude) {
  const response = await fetch(buildApiEndpoint('drivers/me/location'), {
    method: 'PUT',
    headers: getAuthHeaders(),
    body: JSON.stringify({ latitude, longitude })
  })

  if (!response.ok) {
    throw new Error('Erro ao atualizar localização')
  }

  return response.json()
}

/**
 * Buscar entregas do driver
 * @param {string} status - 'pending', 'active', 'completed' ou null para todas
 */
export async function getDriverDeliveries(status = null) {
  const url = status 
    ? buildApiEndpoint(`drivers/me/deliveries?status=${status}`)
    : buildApiEndpoint('drivers/me/deliveries')

  const response = await fetch(url, {
    headers: getAuthHeaders()
  })

  if (!response.ok) {
    throw new Error('Erro ao buscar entregas')
  }

  return response.json()
}

/**
 * Atualizar status de uma entrega
 */
export async function updateDeliveryStatus(deliveryId, status, notes = '') {
  const response = await fetch(buildApiEndpoint(`drivers/deliveries/${deliveryId}/status`), {
    method: 'PUT',
    headers: getAuthHeaders(),
    body: JSON.stringify({ status, notes })
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || 'Erro ao atualizar status da entrega')
  }

  return response.json()
}

/**
 * Aceitar uma entrega disponível
 */
export async function acceptDelivery(deliveryId) {
  const response = await fetch(buildApiEndpoint(`drivers/deliveries/${deliveryId}/accept`), {
    method: 'POST',
    headers: getAuthHeaders()
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || 'Erro ao aceitar entrega')
  }

  return response.json()
}

/**
 * Reportar problema em uma entrega
 */
export async function reportDeliveryProblem(deliveryId, problemType, description) {
  const response = await fetch(buildApiEndpoint(`drivers/deliveries/${deliveryId}/problem`), {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      problem_type: problemType,
      description
    })
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || 'Erro ao reportar problema')
  }

  return response.json()
}

// ==================== FUNÇÕES DE CARGA DO VEÍCULO ====================

/**
 * Buscar carga atual do motorista (ativa)
 */
export async function getCargaAtual() {
  try {
    // Primeiro buscar o perfil para obter o driver_id
    const profile = await getDriverProfile()

    if (!profile || !profile.id) {
      console.warn('Perfil não encontrado ao buscar carga')
      return { tem_carga: false, carga: null }
    }

    const response = await fetch(buildApiEndpoint(`cargas/driver/${profile.id}/atual`), {
      headers: getAuthHeaders()
    })

    if (!response.ok) {
      // Se 404, não tem carga (não é erro)
      if (response.status === 404) {
        return { tem_carga: false, carga: null }
      }
      // Se 401, pode ser token expirado - deixar propagar
      if (response.status === 401) {
        const error = await response.json().catch(() => ({}))
        throw new Error(error.detail || 'Sessão expirada. Por favor, faça login novamente.')
      }
      // Outros erros - retornar sem carga
      console.warn(`Erro ${response.status} ao buscar carga atual`)
      return { tem_carga: false, carga: null }
    }

    const data = await response.json()
    return data
  } catch (error) {
    // Se erro de rede ou outro, retornar sem carga (exceto 401)
    if (error.message && error.message.includes('Sessão expirada')) {
      throw error // Propagar erro de autenticação
    }
    console.error('Erro ao buscar carga:', error)
    return { tem_carga: false, carga: null }
  }
}

/**
 * Registrar saída com a carga
 */
export async function registrarSaidaCarga(cargaId) {
  const response = await fetch(buildApiEndpoint(`cargas/${cargaId}/saida`), {
    method: 'POST',
    headers: getAuthHeaders()
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || 'Erro ao registrar saída')
  }

  return response.json()
}

/**
 * Realizar acerto da carga
 * @param {string} cargaId - ID da carga
 * @param {Array} itens - Array de { produto_id, qtd_retorno_cheio, qtd_retorno_vazio, qtd_vendida }
 * @param {string} observacoes - Observações do acerto
 */
export async function realizarAcertoCarga(cargaId, itens, observacoes = '') {
  const response = await fetch(buildApiEndpoint(`cargas/${cargaId}/acerto`), {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ itens, observacoes })
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || 'Erro ao realizar acerto')
  }

  return response.json()
}

/**
 * Buscar resumo de tempo trabalhado
 * @param {string} period - 'today', 'week', 'month'
 */
export async function getTimeSummary(period = 'today') {
  const response = await fetch(buildApiEndpoint(`drivers/me/time-summary?period=${period}`), {
    headers: getAuthHeaders()
  })

  if (!response.ok) {
    throw new Error('Erro ao buscar tempo trabalhado')
  }

  return response.json()
}

/**
 * Wrapper completo de todas as APIs do driver
 */
export const driverApi = {
  login: driverLogin,
  getProfile: getDriverProfile,
  getStats: getDriverStats,
  updateStatus: updateDriverStatus,
  updateLocation: updateDriverLocation,
  getDeliveries: getDriverDeliveries,
  acceptDelivery,
  updateDeliveryStatus,
  reportProblem: reportDeliveryProblem,
  getTimeSummary,
  // Carga do veículo
  getCargaAtual,
  registrarSaidaCarga,
  realizarAcertoCarga
}

export default driverApi
