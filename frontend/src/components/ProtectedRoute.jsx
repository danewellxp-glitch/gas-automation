import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export default function ProtectedRoute({ children, requiredRole = null, allowedRoles = null }) {
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

  // Troca obrigatória de senha (primeiro login / reset)
  if (user?.must_change_password && location.pathname !== '/change-password') {
    return <Navigate to="/change-password" replace />
  }

  // Verificar se a role é permitida
  const roleRoutes = {
    admin: '/admin',
    operator: '/operador',
    owner: '/owner',
    driver: '/driver/dashboard',
    financeiro: '/financeiro',
    estoque: '/estoque',
    user: '/operador'
  }

  if (allowedRoles && !allowedRoles.includes(user?.role)) {
    const targetRoute = roleRoutes[user?.role] || '/operador'
    return <Navigate to={targetRoute} replace />
  }

  if (requiredRole && user?.role !== requiredRole) {
    const targetRoute = roleRoutes[user?.role] || '/operador'
    return <Navigate to={targetRoute} replace />
  }

  return children
}
