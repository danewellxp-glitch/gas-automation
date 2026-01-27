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
      
      const response = await fetch(loginUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Erro ao fazer login')
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
