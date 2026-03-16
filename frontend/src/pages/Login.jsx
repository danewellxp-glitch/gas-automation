import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

const ROLE_ROUTES = {
  admin: '/admin',
  operator: '/operador',
  owner: '/owner',
  user: '/operador',
  driver: '/driver/dashboard',
}

function PasswordInput({ id, value, onChange, placeholder, required }) {
  const [showPassword, setShowPassword] = useState(false)
  return (
    <div className="relative">
      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
        </svg>
      </span>
      <input
        id={id}
        type={showPassword ? 'text' : 'password'}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        required={required}
        className="w-full pl-11 pr-12 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-900 transition-colors text-gray-700 text-sm"
        autoComplete="current-password"
      />
      <button
        type="button"
        onClick={() => setShowPassword(v => !v)}
        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
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

export default function Login() {
  const [email, setEmail] = useState('admin@gasautomation.local')
  const [password, setPassword] = useState('admin123')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const navigate = useNavigate()
  const location = useLocation()
  const { login } = useAuth()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      await login(email, password)
      const savedUser = JSON.parse(localStorage.getItem('user'))
      const userRole = savedUser?.role || 'user'
      navigate(ROLE_ROUTES[userRole] || '/operador', { replace: true })
    } catch (err) {
      setError('Email ou senha incorretos')
    } finally {
      setLoading(false)
    }
  }

  const setDemo = (role) => {
    const demos = {
      Admin: { email: 'admin@gasautomation.local', password: 'admin123' },
      Owner: { email: 'owner@gasautomation.local', password: 'owner123' },
      Operador: { email: 'operator@gasautomation.local', password: 'operator123' },
    }
    if (demos[role]) {
      setEmail(demos[role].email)
      setPassword(demos[role].password)
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Lado esquerdo - Brand */}
      <div
        className="hidden lg:flex lg:w-1/2 flex-col justify-between p-12 relative overflow-hidden"
        style={{ background: 'linear-gradient(135deg, #0D1117 0%, #1a0a00 40%, #c2390a 100%)' }}
      >
        {/* Decorative blur circles */}
        <div className="absolute top-0 right-0 w-96 h-96 rounded-full opacity-20 blur-3xl" style={{ background: '#E31E24' }} />
        <div className="absolute bottom-0 left-0 w-80 h-80 rounded-full opacity-10 blur-3xl" style={{ background: '#FFD100' }} />

        {/* Logo Gásmaster */}
        <div className="relative z-10 flex items-center gap-3">
          <div className="flex items-center gap-2">
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
              <circle cx="24" cy="24" r="24" fill="#E31E24" opacity="0.15" />
              <path d="M24 8 C20 14 14 18 16 26 C18 32 24 36 24 36 C24 36 30 32 32 26 C34 18 28 14 24 8Z" fill="#FFD100" />
              <path d="M24 16 C22 20 18 22 20 27 C21 30 24 32 24 32 C24 32 27 30 28 27 C30 22 26 20 24 16Z" fill="#E31E24" />
            </svg>
            <div>
              <div className="text-white font-bold text-2xl tracking-wide">GÁSMASTER</div>
              <div className="text-orange-300 text-xs tracking-widest font-medium">DISTRIBUIDORA</div>
            </div>
          </div>
        </div>

        {/* Texto central */}
        <div className="relative z-10">
          <h1 className="text-white text-4xl font-bold leading-tight mb-4">
            Plataforma de<br />Atendimento
          </h1>
          <p className="text-gray-300 text-sm leading-relaxed max-w-sm">
            Gestão inteligente e comunicação corporativa em um novo ritmo.
            Integrando o padrão de qualidade Gasmaster com a automação
            em tempo real do sistema MercuryGas
          </p>
        </div>

        {/* Footer */}
        <div className="relative z-10 flex items-center gap-2">
          <div className="w-8 h-px bg-gray-500" />
          <span className="text-gray-500 text-xs tracking-widest font-medium">POWERED BY MAXWARE</span>
        </div>
      </div>

      {/* Lado direito - Login form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center bg-white p-8">
        <div className="w-full max-w-sm">
          {/* Logo MercuryGas */}
          <div className="text-center mb-8">
            <div className="flex justify-center mb-3">
              <svg width="72" height="72" viewBox="0 0 72 72" fill="none">
                <circle cx="36" cy="36" r="36" fill="#EFF6FF" />
                {/* Wings */}
                <path d="M12 32 C18 24 26 28 30 32" stroke="#1d4ed8" strokeWidth="2.5" strokeLinecap="round" fill="none" />
                <path d="M60 32 C54 24 46 28 42 32" stroke="#1d4ed8" strokeWidth="2.5" strokeLinecap="round" fill="none" />
                <path d="M10 36 C16 30 24 32 30 36" stroke="#1d4ed8" strokeWidth="2" strokeLinecap="round" fill="none" opacity="0.6" />
                <path d="M62 36 C56 30 48 32 42 36" stroke="#1d4ed8" strokeWidth="2" strokeLinecap="round" fill="none" opacity="0.6" />
                {/* Flame */}
                <path d="M36 18 C32 24 28 28 30 34 C32 40 36 43 36 43 C36 43 40 40 42 34 C44 28 40 24 36 18Z" fill="#f97316" />
                <path d="M36 24 C34 28 32 30 33 34 C34 37 36 39 36 39 C36 39 38 37 39 34 C40 30 38 28 36 24Z" fill="#FFD100" />
                {/* Gas cylinder */}
                <rect x="30" y="43" width="12" height="14" rx="3" fill="#1d4ed8" />
                <rect x="33" y="41" width="6" height="4" rx="1" fill="#1d4ed8" opacity="0.7" />
              </svg>
            </div>
            <div className="text-2xl font-bold text-gray-900 tracking-tight">
              MERCURY<span className="text-blue-700">GAS</span>
            </div>
            <div className="text-xs text-gray-400 tracking-widest mt-0.5">powered by maxware</div>
          </div>

          <h2 className="text-xl font-semibold text-gray-900 text-center mb-1">Acesso ao Sistema</h2>
          <p className="text-sm text-gray-500 text-center mb-6">Entre com suas credenciais para acessar o painel</p>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm text-center">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207" />
                </svg>
              </span>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="seu@email.com"
                required
                className="w-full pl-11 pr-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-900 text-gray-700 text-sm"
                autoComplete="email"
              />
            </div>

            <PasswordInput
              id="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 rounded-lg text-white font-semibold text-sm transition-all"
              style={{ background: '#1B3A57' }}
            >
              {loading ? 'Entrando...' : 'Entrar na Plataforma'}
            </button>
          </form>

          <p className="text-center text-xs text-gray-400 mt-4 cursor-pointer hover:text-gray-600">
            Problemas com o acesso? / Esqueci minha senha
          </p>

          {/* Demo badges */}
          <div className="mt-8 pt-6 border-t border-gray-100 text-center">
            <p className="text-xs text-gray-400 mb-3">Ambiente de Demonstração</p>
            <div className="flex justify-center gap-2">
              {['Admin', 'Owner', 'Operador'].map(role => (
                <button
                  key={role}
                  type="button"
                  onClick={() => setDemo(role)}
                  className="px-3 py-1 text-xs border border-gray-200 rounded-full text-gray-500 hover:bg-gray-50 hover:text-gray-700 transition-colors"
                >
                  {role}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
