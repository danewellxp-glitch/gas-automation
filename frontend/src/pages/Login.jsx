import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

// Componente para campo de senha com ícone de olho
function PasswordInput({ id, value, onChange, placeholder, required }) {
  const [showPassword, setShowPassword] = useState(false)

  const togglePasswordVisibility = () => {
    setShowPassword(!showPassword)
  }

  return (
    <div className="relative">
      <input
        id={id}
        type={showPassword ? "text" : "password"}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        required={required}
        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent pr-12"
        autoComplete="current-password"
      />
      <button
        type="button"
        onClick={togglePasswordVisibility}
        className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 hover:text-gray-700 focus:outline-none"
        title={showPassword ? "Ocultar senha" : "Mostrar senha"}
      >
        {showPassword ? (
          // Ícone de olho fechado (senha oculta)
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21" />
          </svg>
        ) : (
          // Ícone de olho aberto (senha visível)
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          </svg>
        )}
      </button>
    </div>
  )
}

const ROLE_ROUTES = {
  admin: '/admin',
  operator: '/operador',
  owner: '/owner',
  user: '/operador'
}

export default function Login() {
  const [email, setEmail] = useState('admin@gasautomation.local')
  const [password, setPassword] = useState('Admin@123456')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  
  const navigate = useNavigate()
  const location = useLocation()
  const { login } = useAuth()

  const from = location.state?.from?.pathname || '/'

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      await login(email, password)
      
      // Obter a role do usuário salva
      const savedUser = JSON.parse(localStorage.getItem('user'))
      const userRole = savedUser?.role || 'user'
      
      // Redirecionar baseado na role
      const targetRoute = ROLE_ROUTES[userRole] || '/operador'
      navigate(targetRoute, { replace: true })
    } catch (err) {
      setError(err.message || 'Erro ao fazer login')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-600 to-blue-800 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-white rounded-lg shadow-2xl p-8">
        {/* Logo/Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">Gas Automation</h1>
          <p className="text-gray-600">Sistema de Gerenciamento</p>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
            {error}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Email Input */}
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
              placeholder="seu@email.com"
              required
            />
          </div>

          {/* Password Input */}
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
              Senha
            </label>
            <PasswordInput
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Sua senha"
              required
            />
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-semibold py-2 px-4 rounded-lg transition duration-200"
          >
            {loading ? 'Entrando...' : 'Entrar'}
          </button>
        </form>

        {/* Demo Credentials */}
        <div className="mt-8 pt-6 border-t border-gray-200">
          <p className="text-sm text-gray-600 text-center mb-3">Credenciais de teste:</p>
          <div className="bg-gray-50 p-3 rounded text-sm text-gray-700 space-y-2">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="font-semibold text-blue-600">👑 Admin</p>
                <p className="font-mono text-xs">admin@gasautomation.local</p>
                <p className="font-mono text-xs">Admin@123456</p>
              </div>
              <div>
                <p className="font-semibold text-green-600">👤 Operador</p>
                <p className="font-mono text-xs">operador@gasautomation.local</p>
                <p className="font-mono text-xs">Teste@123456</p>
              </div>
              <div>
                <p className="font-semibold text-purple-600">💼 Owner</p>
                <p className="font-mono text-xs">dono@gasautomation.local</p>
                <p className="font-mono text-xs">Teste@123456</p>
              </div>
              <div>
                <p className="font-semibold text-orange-600">📦 User</p>
                <p className="font-mono text-xs">usuario@gasautomation.local</p>
                <p className="font-mono text-xs">Teste@123456</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
