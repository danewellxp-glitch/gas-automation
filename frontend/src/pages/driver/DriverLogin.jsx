/**
 * Página de Login do Driver
 */

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { driverApi } from '../../utils/driverApi'
import { useAuth } from '../../hooks/useAuth'

export default function DriverLogin() {
  const navigate = useNavigate()
  const { isAuthenticated, user } = useAuth()
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: ''
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [showPassword, setShowPassword] = useState(false)

  // Redirecionar se já estiver autenticado como driver
  useEffect(() => {
    if (isAuthenticated && user?.role === 'driver') {
      navigate('/driver/dashboard', { replace: true })
    }
  }, [isAuthenticated, user, navigate])

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    })
    setError('') // Limpar erro ao digitar
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    // Validações
    if (!formData.username || !formData.email || !formData.password) {
      setError('Todos os campos são obrigatórios')
      return
    }

    if (formData.password.length < 6) {
      setError('Senha deve ter no mínimo 6 caracteres')
      return
    }

    try {
      setLoading(true)
      setError('')

      const response = await driverApi.login(
        formData.username,
        formData.email,
        formData.password
      )

      // Salvar token e dados do usuário
      localStorage.setItem('token', response.access_token)
      localStorage.setItem('user', JSON.stringify({
        email: formData.email,
        role: response.role,
        username: formData.username
      }))

      // Forçar reload da página para o useAuth pegar o novo estado
      window.location.href = '/driver/dashboard'
    } catch (err) {
      console.error('Erro no login:', err)
      setError(err.message || 'Erro ao fazer login. Verifique suas credenciais.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl p-8 w-full max-w-md">
        {/* Logo e Título */}
        <div className="text-center mb-8">
          <div className="text-6xl mb-4">🚚</div>
          <h1 className="text-3xl font-bold text-gray-800 mb-2">Gas Automation</h1>
          <p className="text-gray-600">Portal do Entregador</p>
        </div>

        {/* Formulário */}
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Username */}
          <div>
            <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-2">
              Username
            </label>
            <input
              type="text"
              id="username"
              name="username"
              value={formData.username}
              onChange={handleChange}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="joao.driver"
              disabled={loading}
            />
          </div>

          {/* Email */}
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
              Email
            </label>
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="joao.driver@gasautomation.com"
              disabled={loading}
            />
          </div>

          {/* Senha */}
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
              Senha
            </label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                id="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent pr-12"
                placeholder="••••••••"
                disabled={loading}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 hover:text-gray-700"
                disabled={loading}
              >
                {showPassword ? '🙈' : '👁️'}
              </button>
            </div>
          </div>

          {/* Erro */}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
              {error}
            </div>
          )}

          {/* Botão Submit */}
          <button
            type="submit"
            disabled={loading}
            className={`w-full py-3 px-4 rounded-lg font-semibold text-white transition-colors ${
              loading
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700 active:bg-blue-800'
            }`}
          >
            {loading ? (
              <span className="flex items-center justify-center">
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Entrando...
              </span>
            ) : (
              'ENTRAR'
            )}
          </button>
        </form>

        {/* Footer */}
        <div className="mt-6 text-center text-sm text-gray-500">
          <a href="#" className="hover:text-blue-600">Esqueci minha senha</a>
        </div>

        {/* Credenciais de Teste (apenas em dev) */}
        {import.meta.env.DEV && (
          <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg text-xs">
            <p className="font-semibold text-yellow-800 mb-2">🔧 Credenciais de Teste:</p>
            <p className="text-yellow-700">Username: joao.driver</p>
            <p className="text-yellow-700">Email: joao.driver@gasautomation.com</p>
            <p className="text-yellow-700">Senha: driver123</p>
          </div>
        )}
      </div>
    </div>
  )
}
