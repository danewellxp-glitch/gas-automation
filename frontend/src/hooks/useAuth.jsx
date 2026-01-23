import { createContext, useContext, useState, useCallback, useEffect } from 'react'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(null)
  const [loading, setLoading] = useState(true)

  // Carregar token do localStorage ao iniciar
  useEffect(() => {
    const savedToken = localStorage.getItem('token')
    const savedUser = localStorage.getItem('user')
    
    if (savedToken && savedUser) {
      setToken(savedToken)
      setUser(JSON.parse(savedUser))
    }
    
    setLoading(false)
  }, [])

  const login = useCallback(async (email, password) => {
    try {
      // Usar variável de ambiente para URL da API
      const apiUrl = import.meta.env.VITE_API_URL || 'http://192.168.10.156:8000/api'
      const loginUrl = `${apiUrl}/auth/login`
      
      console.log('[useAuth] Tentando login em:', loginUrl)
      
      const response = await fetch(loginUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      })

      if (!response.ok) {
        let errorMessage = 'Erro ao fazer login'
        try {
          const error = await response.json()
          errorMessage = error.detail || error.message || errorMessage
        } catch (e) {
          // Se não conseguir parsear JSON, usar status text
          errorMessage = response.statusText || `Erro ${response.status}`
        }
        throw new Error(errorMessage)
      }

      const data = await response.json()
      
      // Salvar token e usuário
      localStorage.setItem('token', data.access_token)
      localStorage.setItem('user', JSON.stringify({
        email,
        role: data.role || 'operator',
      }))

      setToken(data.access_token)
      setUser({
        email,
        role: data.role || 'operator',
      })
    } catch (error) {
      console.error('Login error:', error)
      
      // Tratar erros de rede/CORS
      if (error.message === 'Failed to fetch' || error.name === 'TypeError') {
        const apiUrl = import.meta.env.VITE_API_URL || 'http://192.168.10.156:8000/api'
        throw new Error(
          `Não foi possível conectar ao servidor. Verifique se o backend está rodando em ${apiUrl}`
        )
      }
      
      throw error
    }
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setToken(null)
    setUser(null)
  }, [])

  const value = {
    user,
    token,
    loading,
    login,
    logout,
    isAuthenticated: !!token,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
