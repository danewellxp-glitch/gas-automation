/**
 * Utilitários Admin exportados do painel_admin.html
 * Funções para formatação, badges, toasts e validações
 */

// ===== FORMATTING =====

/**
 * Formata a role para exibição amigável
 * @param {string} role - Role do usuário (admin, owner, operator, user)
 * @returns {string} Role formatada em português
 */
export function formatRole(role) {
  const roles = {
    'admin': 'Admin',
    'owner': 'Proprietário',
    'operator': 'Operador',
    'operador': 'Operador',
    'user': 'Usuário',
  }
  return roles[role] || role
}

/**
 * Retorna a classe CSS para badge de role
 * @param {string} role - Role do usuário
 * @returns {string} Classe CSS (danger, blue, purple, gray)
 */
export function getRoleBadge(role) {
  const badges = {
    'admin': 'danger',
    'owner': 'purple',
    'operator': 'blue',
    'operador': 'blue',
    'user': 'gray',
  }
  return badges[role] || 'gray'
}

/**
 * Formata timestamp para formato legível
 * @param {string|Date} timestamp - Data/hora para formatar
 * @returns {string} Data/hora formatada em pt-BR
 */
export function formatDateTime(timestamp) {
  if (!timestamp) return ''
  try {
    const date = new Date(timestamp)
    return date.toLocaleString('pt-BR')
  } catch {
    return timestamp
  }
}

/**
 * Formata timestamp apenas para hora
 * @param {string|Date} timestamp - Data/hora para formatar
 * @returns {string} Hora formatada em pt-BR (HH:mm)
 */
export function formatTime(timestamp) {
  if (!timestamp) return ''
  try {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
  } catch {
    return timestamp
  }
}

/**
 * Formata ação do audit log para exibição
 * @param {string} action - Código da ação
 * @returns {string} Ação formatada em português
 */
export function formatAction(action) {
  const actions = {
    'user_created': 'Usuário criado',
    'user_updated': 'Usuário atualizado',
    'user_deactivated': 'Usuário desativado',
    'user_activated': 'Usuário ativado',
    'role_changed': 'Role alterada',
    'password_reset': 'Senha resetada',
    'login': 'Login realizado',
    'logout': 'Logout realizado',
    'product_created': 'Produto criado',
    'product_updated': 'Produto atualizado',
    'product_deleted': 'Produto deletado',
  }
  return actions[action] || action
}

/**
 * Retorna classe CSS para badge de status
 * @param {string} status - Status (active, pending, closed, etc)
 * @returns {string} Classe CSS
 */
export function getStatusBadge(status) {
  const badges = {
    'active': 'success',
    'pending': 'warning',
    'closed': 'secondary',
    'paused': 'info',
  }
  return badges[status] || 'secondary'
}

// ===== VALIDATION =====

/**
 * Valida email
 * @param {string} email - Email para validar
 * @returns {boolean} True se email é válido
 */
export function isValidEmail(email) {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email)
}

/**
 * Valida senha (mínimo 6 caracteres)
 * @param {string} password - Senha para validar
 * @returns {boolean} True se senha é válida
 */
export function isValidPassword(password) {
  return password && password.length >= 6
}

/**
 * Valida se um nome tem comprimento adequado
 * @param {string} name - Nome para validar
 * @returns {boolean} True se nome é válido (3+ caracteres)
 */
export function isValidName(name) {
  return name && name.trim().length >= 3
}

// ===== TOAST NOTIFICATIONS =====

/**
 * Exibe notificação toast (alerta temporário)
 * @param {string} message - Mensagem a exibir
 * @param {string} type - Tipo (success, error, warning, info)
 * @param {number} duration - Duração em ms (padrão 3000)
 */
export function showToast(message, type = 'info', duration = 3000) {
  // Se usando React, retornar a mensagem e deixar o componente renderizar
  // Se estiver em HTML puro, criar elemento DOM
  const toast = document.createElement('div')
  toast.className = `toast toast-${type}`
  toast.textContent = message
  toast.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 15px 20px;
    border-radius: 8px;
    z-index: 9999;
    font-size: 14px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.2);
    background: ${getToastBackground(type)};
    color: white;
  `
  document.body.appendChild(toast)
  setTimeout(() => toast.remove(), duration)
}

/**
 * Retorna cor de fundo para toast
 * @param {string} type - Tipo do toast
 * @returns {string} Cor hex ou rgb
 */
function getToastBackground(type) {
  const backgrounds = {
    'success': '#28a745',
    'error': '#dc3545',
    'warning': '#ffc107',
    'info': '#17a2b8',
  }
  return backgrounds[type] || backgrounds['info']
}

// ===== USER OPERATIONS =====

/**
 * Filtra array de usuários por termo de busca
 * @param {Array} users - Array de usuários
 * @param {string} searchTerm - Termo de busca
 * @returns {Array} Usuários filtrados
 */
export function filterUsers(users, searchTerm) {
  if (!searchTerm) return users
  const term = searchTerm.toLowerCase()
  return users.filter(user =>
    (user.name && user.name.toLowerCase().includes(term)) ||
    (user.email && user.email.toLowerCase().includes(term)) ||
    (user.username && user.username.toLowerCase().includes(term))
  )
}

/**
 * Ordena usuários por critério
 * @param {Array} users - Array de usuários
 * @param {string} field - Campo para ordenar (name, email, role, created_at)
 * @param {string} direction - Direção (asc, desc)
 * @returns {Array} Usuários ordenados
 */
export function sortUsers(users, field = 'created_at', direction = 'desc') {
  const sorted = [...users]
  sorted.sort((a, b) => {
    let valueA = a[field] || ''
    let valueB = b[field] || ''

    // Se for data
    if (field.includes('date') || field.includes('time')) {
      valueA = new Date(valueA).getTime()
      valueB = new Date(valueB).getTime()
    }
    // Se for role, ordenar customizado
    else if (field === 'role') {
      const roleOrder = { 'admin': 0, 'owner': 1, 'operator': 2, 'user': 3 }
      valueA = roleOrder[valueA] || 999
      valueB = roleOrder[valueB] || 999
    }
    // Se for string
    else if (typeof valueA === 'string') {
      valueA = valueA.toLowerCase()
      valueB = valueB.toLowerCase()
    }

    if (direction === 'asc') {
      return valueA > valueB ? 1 : -1
    } else {
      return valueA < valueB ? 1 : -1
    }
  })
  return sorted
}

// ===== MODAL HELPERS =====

/**
 * Abre modal com animação
 * @param {string} modalId - ID do elemento modal
 */
export function openModal(modalId) {
  const modal = document.getElementById(modalId)
  if (modal) {
    modal.classList.add('active')
    modal.style.display = 'block'
  }
}

/**
 * Fecha modal com animação
 * @param {string} modalId - ID do elemento modal
 */
export function closeModal(modalId) {
  const modal = document.getElementById(modalId)
  if (modal) {
    modal.classList.remove('active')
    setTimeout(() => {
      modal.style.display = 'none'
    }, 300)
  }
}

// ===== CONFIRMATION DIALOG =====

/**
 * Exibe diálogo de confirmação customizado
 * @param {string} title - Título do diálogo
 * @param {string} message - Mensagem
 * @param {Function} onConfirm - Callback ao confirmar
 * @param {Function} onCancel - Callback ao cancelar
 */
export function showConfirmDialog(title, message, onConfirm, onCancel) {
  return new Promise((resolve) => {
    const confirmed = window.confirm(`${title}\n\n${message}`)
    if (confirmed) {
      onConfirm?.()
      resolve(true)
    } else {
      onCancel?.()
      resolve(false)
    }
  })
}

// ===== STORAGE HELPERS =====

/**
 * Salva dados no localStorage
 * @param {string} key - Chave
 * @param {any} value - Valor (será convertido para JSON)
 */
export function saveToStorage(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch (e) {
    console.error('Erro ao salvar no localStorage:', e)
  }
}

/**
 * Recupera dados do localStorage
 * @param {string} key - Chave
 * @param {any} defaultValue - Valor padrão se não encontrar
 * @returns {any} Valor recuperado ou padrão
 */
export function getFromStorage(key, defaultValue = null) {
  try {
    const value = localStorage.getItem(key)
    return value ? JSON.parse(value) : defaultValue
  } catch (e) {
    console.error('Erro ao ler do localStorage:', e)
    return defaultValue
  }
}

// ===== DEBOUNCE =====

/**
 * Cria função debounced
 * @param {Function} func - Função a executar
 * @param {number} delay - Delay em ms
 * @returns {Function} Função debounced
 */
export function debounce(func, delay = 300) {
  let timeoutId
  return function debounced(...args) {
    clearTimeout(timeoutId)
    timeoutId = setTimeout(() => func(...args), delay)
  }
}

// ===== EXPORT ALL =====
export default {
  formatRole,
  getRoleBadge,
  formatDateTime,
  formatTime,
  formatAction,
  getStatusBadge,
  isValidEmail,
  isValidPassword,
  isValidName,
  showToast,
  filterUsers,
  sortUsers,
  openModal,
  closeModal,
  showConfirmDialog,
  saveToStorage,
  getFromStorage,
  debounce,
}
