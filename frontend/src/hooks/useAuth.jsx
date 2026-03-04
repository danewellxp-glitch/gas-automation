import { createContext, useContext, useState, useCallback, useEffect } from 'react'

const AuthContext = createContext(null)

function getApiUrl() {
  return import.meta.env.VITE_API_URL || 'http://192.168.10.167:8000/api'
}

function safeJsonParse(value) {
  try {
    return JSON.parse(value)
  } catch {
    return null
  }
}

function parseJwtPayload(token) {
  try {
    const [, payload] = token.split('.')
    if (!payload) return null
    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/')
    const json = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => `%${(`00${c.charCodeAt(0).toString(16)}`).slice(-2)}`)
        .join('')
    )
    return JSON.parse(json)
  } catch {
    return null
  }
}

function isJwtExpired(token) {
  const payload = parseJwtPayload(token)
  if (!payload?.exp) return false
  // exp é em segundos
  return Date.now() >= payload.exp * 1000
}

function clearStoredSession() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('user')
  localStorage.removeItem('username')
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(null)
  const [loading, setLoading] = useState(true)

  const refreshMe = useCallback(async (accessToken) => {
    const t = accessToken || token || localStorage.getItem('access_token') || localStorage.getItem('token')
    if (!t) return null

    const meRes = await fetch(`${getApiUrl()}/auth/users/me`, {
      headers: { Authorization: `Bearer ${t}` },
    })

    if (!meRes.ok) {
      throw new Error('Falha ao validar sessão')
    }

    const me = await meRes.json()

    localStorage.setItem('access_token', t)
    localStorage.setItem('token', t)
    localStorage.setItem(
      'user',
      JSON.stringify({
        username: me.username,
        email: me.email,
        role: me.role,
        full_name: me.full_name,
        must_change_password: !!me.must_change_password,
      })
    )
    if (me.username) localStorage.setItem('username', me.username)

    setUser({
      username: me.username,
      email: me.email,
      role: me.role,
      full_name: me.full_name,
      must_change_password: !!me.must_change_password,
    })

    return me
  }, [token])

  const logout = useCallback(() => {
    clearStoredSession()
    setToken(null)
    setUser(null)
  }, [])

  // Carregar token do localStorage e VALIDAR ao iniciar
  useEffect(() => {
    let cancelled = false

    async function bootstrap() {
      setLoading(true)

      const savedToken = localStorage.getItem('access_token') || localStorage.getItem('token')
      const savedUserRaw = localStorage.getItem('user')
      const savedUser = savedUserRaw ? safeJsonParse(savedUserRaw) : null

      if (!savedToken) {
        if (!cancelled) setLoading(false)
        return
      }

      // Token expirado → limpa e volta para login (evita tela branca)
      if (isJwtExpired(savedToken)) {
        logout()
        if (!cancelled) setLoading(false)
        return
      }

      // Seta estado inicial para permitir UI carregar (ProtectedRoute mostra loading)
      if (!cancelled) {
        setToken(savedToken)
        if (savedUser) setUser(savedUser)
      }

      // Validar token no backend e sincronizar dados do usuário
      try {
        await refreshMe(savedToken)
      } catch {
        // Falha de rede: não derruba sessão imediatamente, mas evita ficar travado
        // Mantém o estado atual e deixa as chamadas seguintes determinarem 401
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    bootstrap()
    return () => {
      cancelled = true
    }
  }, [logout])

  const login = useCallback(async (email, password) => {
    try {
      // Backend usa OAuth2PasswordRequestForm em /auth/token (form-urlencoded)
      const apiUrl = getApiUrl()
      const loginUrl = `${apiUrl}/auth/token`

      const body = new URLSearchParams()
      body.append('username', email) // aqui \"email\" é o input; no backend é \"username\"
      body.append('password', password)

      const response = await fetch(loginUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body,
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Erro ao fazer login')
      }

      const data = await response.json()
      
      // Salvar token (padronizado) e usuário
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('token', data.access_token) // compatibilidade
      localStorage.setItem('username', email)
      localStorage.setItem(
        'user',
        JSON.stringify({
          username: email,
          email: data.email || email,
          role: data.role || 'operator',
          must_change_password: !!data.must_change_password,
        })
      )

      setToken(data.access_token)
      setUser({
        username: email,
        email: data.email || email,
        role: data.role || 'operator',
        must_change_password: !!data.must_change_password,
      })
    } catch (error) {
      console.error('Login error:', error)
      throw error
    }
  }, [])

  const value = {
    user,
    token,
    loading,
    login,
    logout,
    refreshMe,
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
