/**
 * Exemplos de Uso dos Admin Helpers
 * Estes exemplos mostram padrões comuns e boas práticas
 */

// ============================================
// EXEMPLO 1: Tabela de Usuários com Busca e Ordenação
// ============================================

import { useState, useEffect } from 'react'
import {
  formatRole,
  formatDateTime,
  filterUsers,
  sortUsers,
  debounce,
  getRoleBadge,
} from '../../utils/adminHelpers'

export function UsersTableExample() {
  const [users, setUsers] = useState([])
  const [searchTerm, setSearchTerm] = useState('')
  const [sortField, setSortField] = useState('created_at')
  const [sortDirection, setSortDirection] = useState('desc')

  // Debounce para busca (evita chamadas excessivas)
  const debouncedSearch = debounce((term) => {
    // Se precisar fazer busca na API, fazer aqui
    console.log('Buscando por:', term)
  }, 300)

  const handleSearch = (term) => {
    setSearchTerm(term)
    debouncedSearch(term)
  }

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('asc')
    }
  }

  // Aplicar filtros e ordenação
  const displayedUsers = sortUsers(
    filterUsers(users, searchTerm),
    sortField,
    sortDirection
  )

  return (
    <div className="p-4">
      {/* Search Input */}
      <input
        type="text"
        placeholder="Buscar por email, nome ou username..."
        value={searchTerm}
        onChange={(e) => handleSearch(e.target.value)}
        className="w-full px-4 py-2 border rounded mb-4"
      />

      {/* Info Text */}
      <p className="text-sm text-gray-600 mb-4">
        Mostrando {displayedUsers.length} de {users.length} usuários
      </p>

      {/* Table */}
      <table className="w-full">
        <thead>
          <tr className="border-b">
            <th 
              onClick={() => handleSort('email')}
              className="cursor-pointer px-4 py-2 text-left hover:bg-gray-100"
            >
              Email {sortField === 'email' && (sortDirection === 'asc' ? '↑' : '↓')}
            </th>
            <th 
              onClick={() => handleSort('full_name')}
              className="cursor-pointer px-4 py-2 text-left hover:bg-gray-100"
            >
              Nome {sortField === 'full_name' && (sortDirection === 'asc' ? '↑' : '↓')}
            </th>
            <th 
              onClick={() => handleSort('role')}
              className="cursor-pointer px-4 py-2 text-left hover:bg-gray-100"
            >
              Role {sortField === 'role' && (sortDirection === 'asc' ? '↑' : '↓')}
            </th>
            <th className="px-4 py-2 text-left">Criado em</th>
          </tr>
        </thead>
        <tbody>
          {displayedUsers.map(user => (
            <tr key={user.id} className="border-b hover:bg-gray-50">
              <td className="px-4 py-2">{user.email}</td>
              <td className="px-4 py-2">{user.full_name}</td>
              <td className="px-4 py-2">
                <span className={`inline-block px-2 py-1 rounded text-xs badge-${getRoleBadge(user.role)}`}>
                  {formatRole(user.role)}
                </span>
              </td>
              <td className="px-4 py-2 text-sm text-gray-600">
                {formatDateTime(user.created_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ============================================
// EXEMPLO 2: Formulário com Validação
// ============================================

import {
  isValidEmail,
  isValidPassword,
  isValidName,
  showToast,
} from '../../utils/adminHelpers'

export function UserFormExample() {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
  })

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()

    // Validar
    if (!isValidName(formData.name)) {
      showToast('Nome deve ter pelo menos 3 caracteres', 'warning')
      return
    }

    if (!isValidEmail(formData.email)) {
      showToast('Email inválido', 'warning')
      return
    }

    if (!isValidPassword(formData.password)) {
      showToast('Senha deve ter pelo menos 6 caracteres', 'warning')
      return
    }

    // Se passou em todas as validações
    showToast('Formulário válido! Enviando...', 'info')
    // Fazer submissão aqui
  }

  return (
    <form onSubmit={handleSubmit} className="max-w-md">
      <div className="mb-4">
        <label className="block text-sm font-medium mb-2">Nome</label>
        <input
          type="text"
          name="name"
          value={formData.name}
          onChange={handleChange}
          placeholder="Digite seu nome completo"
          className="w-full px-4 py-2 border rounded"
        />
        {formData.name && !isValidName(formData.name) && (
          <p className="text-xs text-red-600 mt-1">Nome muito curto</p>
        )}
      </div>

      <div className="mb-4">
        <label className="block text-sm font-medium mb-2">Email</label>
        <input
          type="email"
          name="email"
          value={formData.email}
          onChange={handleChange}
          placeholder="email@example.com"
          className="w-full px-4 py-2 border rounded"
        />
        {formData.email && !isValidEmail(formData.email) && (
          <p className="text-xs text-red-600 mt-1">Email inválido</p>
        )}
      </div>

      <div className="mb-4">
        <label className="block text-sm font-medium mb-2">Senha</label>
        <input
          type="password"
          name="password"
          value={formData.password}
          onChange={handleChange}
          placeholder="Mínimo 6 caracteres"
          className="w-full px-4 py-2 border rounded"
        />
        {formData.password && !isValidPassword(formData.password) && (
          <p className="text-xs text-red-600 mt-1">Senha muito fraca</p>
        )}
      </div>

      <button
        type="submit"
        className="w-full px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
      >
        Enviar
      </button>
    </form>
  )
}

// ============================================
// EXEMPLO 3: Diálogo de Confirmação
// ============================================

import { showConfirmDialog, showToast } from '../../utils/adminHelpers'

export function DeleteUserExample({ userId, userName }) {
  const handleDelete = async () => {
    const confirmed = await showConfirmDialog(
      'Deletar Usuário',
      `Tem certeza que deseja deletar ${userName}? Esta ação não pode ser desfeita.`,
      async () => {
        // Usuário confirmou
        showToast('Deletando usuário...', 'info')
        // Fazer chamada à API aqui
      },
      () => {
        // Usuário cancelou
        showToast('Operação cancelada', 'info')
      }
    )
  }

  return (
    <button
      onClick={handleDelete}
      className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
    >
      Deletar
    </button>
  )
}

// ============================================
// EXEMPLO 4: Persisting Preferences
// ============================================

import { useEffect, useState } from 'react'
import { saveToStorage, getFromStorage } from '../../utils/adminHelpers'

export function PreferencesExample() {
  const [theme, setTheme] = useState('light')
  const [language, setLanguage] = useState('pt-BR')

  // Carregar preferências ao montar
  useEffect(() => {
    const saved = getFromStorage('app_preferences', {
      theme: 'light',
      language: 'pt-BR',
    })
    setTheme(saved.theme)
    setLanguage(saved.language)
  }, [])

  // Salvar quando mudar
  const handleThemeChange = (newTheme) => {
    setTheme(newTheme)
    const prefs = getFromStorage('app_preferences', {})
    saveToStorage('app_preferences', { ...prefs, theme: newTheme })
  }

  return (
    <div>
      <select value={theme} onChange={(e) => handleThemeChange(e.target.value)}>
        <option value="light">Light</option>
        <option value="dark">Dark</option>
      </select>
    </div>
  )
}

// ============================================
// EXEMPLO 5: Toast Notifications
// ============================================

import { showToast } from '../../utils/adminHelpers'

export function NotificationsExample() {
  const handleSuccess = () => {
    showToast('✓ Operação concluída com sucesso!', 'success', 3000)
  }

  const handleError = () => {
    showToast('✗ Erro ao processar a operação', 'error', 4000)
  }

  const handleWarning = () => {
    showToast('⚠ Ação não pode ser desfeita', 'warning', 3000)
  }

  const handleInfo = () => {
    showToast('ℹ Processando sua solicitação...', 'info', 2000)
  }

  return (
    <div className="space-y-4">
      <button onClick={handleSuccess} className="px-4 py-2 bg-green-500 text-white rounded">
        Sucesso
      </button>
      <button onClick={handleError} className="px-4 py-2 bg-red-500 text-white rounded">
        Erro
      </button>
      <button onClick={handleWarning} className="px-4 py-2 bg-yellow-500 text-white rounded">
        Aviso
      </button>
      <button onClick={handleInfo} className="px-4 py-2 bg-blue-500 text-white rounded">
        Info
      </button>
    </div>
  )
}

// ============================================
// EXEMPLO 6: Debounce em Busca de API
// ============================================

import { useState } from 'react'
import { debounce } from '../../utils/adminHelpers'
import { apiRequest } from '../../utils/api'

export function APISearchExample() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)

  // Busca na API com debounce
  const debouncedSearch = debounce(async (searchQuery) => {
    if (!searchQuery.trim()) {
      setResults([])
      return
    }

    try {
      setLoading(true)
      const data = await apiRequest(`users/search?q=${searchQuery}`)
      setResults(data)
    } catch (error) {
      console.error('Erro na busca:', error)
      setResults([])
    } finally {
      setLoading(false)
    }
  }, 500) // Aguarda 500ms após parar de digitar

  const handleChange = (e) => {
    const value = e.target.value
    setQuery(value)
    debouncedSearch(value)
  }

  return (
    <div>
      <input
        type="text"
        value={query}
        onChange={handleChange}
        placeholder="Buscar usuários..."
        className="w-full px-4 py-2 border rounded"
      />

      {loading && <p>Buscando...</p>}

      <ul className="mt-4">
        {results.map(user => (
          <li key={user.id} className="p-2 border-b">
            {user.name} ({user.email})
          </li>
        ))}
      </ul>
    </div>
  )
}

// ============================================
// EXEMPLO 7: Combinando Múltiplos Helpers
// ============================================

import { useState, useEffect } from 'react'
import {
  formatRole,
  formatDateTime,
  filterUsers,
  sortUsers,
  debounce,
  showToast,
  getRoleBadge,
} from '../../utils/adminHelpers'
import { apiRequest } from '../../utils/api'

export function AdvancedDashboardExample() {
  const [users, setUsers] = useState([])
  const [searchTerm, setSearchTerm] = useState('')
  const [sortField, setSortField] = useState('created_at')
  const [sortDirection, setSortDirection] = useState('desc')
  const [selectedUser, setSelectedUser] = useState(null)
  const [loading, setLoading] = useState(true)

  // Carregar usuários
  useEffect(() => {
    const loadUsers = async () => {
      try {
        const data = await apiRequest('users')
        setUsers(data)
      } catch (error) {
        showToast('Erro ao carregar usuários', 'error')
      } finally {
        setLoading(false)
      }
    }
    loadUsers()
  }, [])

  // Debounce para busca em tempo real
  const debouncedSearch = debounce((term) => {
    // Se precisar refinar busca na API
    console.log('Buscando:', term)
  }, 300)

  const handleSearch = (term) => {
    setSearchTerm(term)
    debouncedSearch(term)
  }

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('asc')
    }
  }

  const displayedUsers = sortUsers(
    filterUsers(users, searchTerm),
    sortField,
    sortDirection
  )

  if (loading) {
    return <div className="p-4">Carregando...</div>
  }

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-4">Gestão de Usuários</h2>

      {/* Search */}
      <input
        type="text"
        placeholder="Buscar..."
        value={searchTerm}
        onChange={(e) => handleSearch(e.target.value)}
        className="w-full px-4 py-2 border rounded mb-4"
      />

      {/* Info */}
      <p className="text-sm text-gray-600 mb-4">
        {displayedUsers.length} de {users.length} usuários
      </p>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead className="bg-gray-50">
            <tr>
              <th
                onClick={() => handleSort('email')}
                className="cursor-pointer px-4 py-2 text-left hover:bg-gray-100 border"
              >
                Email {sortField === 'email' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th
                onClick={() => handleSort('full_name')}
                className="cursor-pointer px-4 py-2 text-left hover:bg-gray-100 border"
              >
                Nome {sortField === 'full_name' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th
                onClick={() => handleSort('role')}
                className="cursor-pointer px-4 py-2 text-left hover:bg-gray-100 border"
              >
                Role {sortField === 'role' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th className="px-4 py-2 text-left border">Criado em</th>
              <th className="px-4 py-2 text-left border">Ação</th>
            </tr>
          </thead>
          <tbody>
            {displayedUsers.map(user => (
              <tr
                key={user.id}
                className="border-b hover:bg-gray-50"
                onClick={() => setSelectedUser(user)}
              >
                <td className="px-4 py-2 border">{user.email}</td>
                <td className="px-4 py-2 border">{user.full_name}</td>
                <td className="px-4 py-2 border">
                  <span className={`inline-block px-2 py-1 rounded text-xs badge-${getRoleBadge(user.role)}`}>
                    {formatRole(user.role)}
                  </span>
                </td>
                <td className="px-4 py-2 border text-sm">
                  {formatDateTime(user.created_at)}
                </td>
                <td className="px-4 py-2 border">
                  <button
                    className="px-2 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600"
                  >
                    Editar
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Detalhes do usuário selecionado */}
      {selectedUser && (
        <div className="mt-6 p-4 border rounded bg-gray-50">
          <h3 className="font-bold mb-2">{selectedUser.full_name}</h3>
          <p>Email: {selectedUser.email}</p>
          <p>Role: {formatRole(selectedUser.role)}</p>
          <p>Criado em: {formatDateTime(selectedUser.created_at)}</p>
        </div>
      )}
    </div>
  )
}

// ============================================
// EXEMPLO 8: Modal com Helpers
// ============================================

import { useState } from 'react'
import { openModal, closeModal } from '../../utils/adminHelpers'

export function ModalExample() {
  const handleOpen = () => {
    openModal('my-modal')
  }

  const handleClose = () => {
    closeModal('my-modal')
  }

  return (
    <div>
      <button onClick={handleOpen} className="px-4 py-2 bg-blue-500 text-white rounded">
        Abrir Modal
      </button>

      <div id="my-modal" className="hidden">
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-white p-6 rounded shadow-lg">
            <h2 className="text-lg font-bold mb-4">Modal Title</h2>
            <p className="mb-4">Modal content here...</p>
            <button
              onClick={handleClose}
              className="px-4 py-2 bg-gray-300 text-gray-800 rounded hover:bg-gray-400"
            >
              Fechar
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
