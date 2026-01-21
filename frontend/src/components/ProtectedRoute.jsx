import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export default function ProtectedRoute({ children, requiredRole = null }) {
  const { isAuthenticated, loading, user } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Carregando...</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  // Verificar se a role é permitida (se requiredRole foi especificado)
  if (requiredRole && user?.role !== requiredRole) {
    // Redirecionar para o dashboard correto da role do usuário
    const roleRoutes = {
      admin: '/admin',
      operator: '/operador',
      owner: '/owner',
      driver: '/driver/dashboard',
      user: '/operador'
    }
    const targetRoute = roleRoutes[user?.role] || '/operador'
    return <Navigate to={targetRoute} replace />
  }

  return children
}
