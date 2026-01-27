import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

// Cores corporativas Gasmaster
// Vermelho: #E31E24 (principal)
// Amarelo: #FFD100 (destaque)
// Azul escuro: #1B3A57 (textos)

// Componente para campo de senha com ícone de olho
function PasswordInput({ id, value, onChange, placeholder, required }) {
  const [showPassword, setShowPassword] = useState(false)

  const togglePasswordVisibility = () => {
    setShowPassword(!showPassword)
  }

  return (
    <div className="relative">
      <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400">
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
        </svg>
      </span>
      <input
        id={id}
        type={showPassword ? "text" : "password"}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        required={required}
        className="w-full pl-11 pr-12 py-3 border-2 border-gray-200 rounded-lg focus:outline-none focus:border-red-500 transition-colors text-gray-700"
        autoComplete="current-password"
      />
      <button
        type="button"
        onClick={togglePasswordVisibility}
        className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-red-600 focus:outline-none transition-colors"
        title={showPassword ? "Ocultar senha" : "Mostrar senha"}
      >
        {showPassword ? (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21" />
          </svg>
        ) : (
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
  const [password, setPassword] = useState('admin123')
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
      
      const savedUser = JSON.parse(localStorage.getItem('user'))
      const userRole = savedUser?.role || 'user'
      
      const targetRoute = ROLE_ROUTES[userRole] || '/operador'
      navigate(targetRoute, { replace: true })
    } catch (err) {
      setError(err.message || 'Erro ao fazer login')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div 
      className="min-h-screen flex items-center justify-center p-4"
      style={{ 
        background: 'linear-gradient(135deg, #1B3A57 0%, #0D1F2D 50%, #1B3A57 100%)'
      }}
    >
      {/* Decorative elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div 
          className="absolute -top-20 -right-20 w-96 h-96 rounded-full opacity-10"
          style={{ background: '#E31E24' }}
        />
        <div 
          className="absolute -bottom-32 -left-32 w-[500px] h-[500px] rounded-full opacity-10"
          style={{ background: '#FFD100' }}
        />
      </div>

      <div className="w-full max-w-md relative z-10">
        {/* Card principal */}
        <div className="bg-white rounded-2xl shadow-2xl overflow-hidden">
          {/* Header com logo */}
          <div 
            className="px-8 py-6 text-center bg-white"
          >
            <img 
              src="https://www.grupogasmaster.com.br/wp-content/uploads/2020/11/gasmaster-distribuidora-de-gas-em-curitiba.png"
              alt="Gasmaster - Distribuidora de Gás em Curitiba"
              className="h-20 mx-auto mb-3 object-contain drop-shadow-sm"
            />
            <p className="text-gray-600 text-sm font-medium">Sistema de Gerenciamento</p>
          </div>

          {/* Faixa amarela decorativa */}
          <div 
            className="h-1.5"
            style={{ background: 'linear-gradient(90deg, #E31E24 0%, #FFD100 50%, #E31E24 100%)' }}
          />

          {/* Conteúdo do form */}
          <div className="p-8">
            {/* Error Message */}
            {error && (
              <div 
                className="mb-6 p-4 rounded-lg flex items-center gap-3"
                style={{ background: '#FEE2E2', border: '1px solid #E31E24' }}
              >
                <svg className="w-5 h-5 flex-shrink-0" style={{ color: '#E31E24' }} fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                <span style={{ color: '#991B1B' }}>{error}</span>
              </div>
            )}

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Email Input */}
              <div>
                <label 
                  htmlFor="email" 
                  className="block text-sm font-semibold mb-2"
                  style={{ color: '#1B3A57' }}
                >
                  Email
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207" />
                    </svg>
                  </span>
                  <input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full pl-11 pr-4 py-3 border-2 border-gray-200 rounded-lg focus:outline-none focus:border-red-500 transition-colors text-gray-700"
                    placeholder="seu@email.com"
                    required
                  />
                </div>
              </div>

              {/* Password Input */}
              <div>
                <label 
                  htmlFor="password" 
                  className="block text-sm font-semibold mb-2"
                  style={{ color: '#1B3A57' }}
                >
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
                className="w-full py-3.5 px-4 rounded-lg font-bold text-white transition-all duration-300 transform hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none shadow-lg"
                style={{ 
                  background: loading ? '#9CA3AF' : 'linear-gradient(135deg, #E31E24 0%, #C41A1F 100%)',
                  boxShadow: loading ? 'none' : '0 4px 15px rgba(227, 30, 36, 0.4)'
                }}
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                    </svg>
                    Entrando...
                  </span>
                ) : 'Entrar'}
              </button>
            </form>

          </div>
        </div>

        {/* Footer */}
        <div className="mt-6 text-center">
          <p className="text-gray-400 text-sm">
            Gasmaster Distribuidora de Gás
          </p>
          <p className="text-gray-500 text-xs mt-1">
            Curitiba - Umbará e Região
          </p>
        </div>

        {/* Demo Credentials (dev only) */}
        <div className="mt-6 bg-white/10 backdrop-blur-sm rounded-xl p-4 border border-white/20">
          <p className="text-xs text-gray-300 text-center mb-3 font-medium">Credenciais de teste (desenvolvimento)</p>
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="bg-white/10 rounded-lg p-2">
              <p className="font-semibold text-yellow-400">Admin</p>
              <p className="text-gray-300 font-mono">admin@gasautomation.local</p>
              <p className="text-gray-400 font-mono">admin123</p>
            </div>
            <div className="bg-white/10 rounded-lg p-2">
              <p className="font-semibold text-green-400">Operador</p>
              <p className="text-gray-300 font-mono">operador@gasautomation.local</p>
              <p className="text-gray-400 font-mono">Teste@123456</p>
            </div>
            <div className="bg-white/10 rounded-lg p-2">
              <p className="font-semibold text-purple-400">Owner</p>
              <p className="text-gray-300 font-mono">dono@gasautomation.local</p>
              <p className="text-gray-400 font-mono">Teste@123456</p>
            </div>
            <div className="bg-white/10 rounded-lg p-2">
              <p className="font-semibold text-orange-400">User</p>
              <p className="text-gray-300 font-mono">usuario@gasautomation.local</p>
              <p className="text-gray-400 font-mono">Teste@123456</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
