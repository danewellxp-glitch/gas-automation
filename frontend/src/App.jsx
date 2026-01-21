import { Routes, Route, Navigate } from 'react-router-dom'
import { useCallback } from 'react'
import { AuthProvider, useAuth } from './hooks/useAuth'
import ProtectedRoute from './components/ProtectedRoute'
import Layout from './components/Layout'

// Pages
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Orders from './pages/Orders'
import Chats from './pages/Chats'

// Pages por Role
import OperatorDashboard from './pages/operator/OperatorDashboard'
import AdminDashboard from './pages/admin/AdminDashboard'
import OwnerDashboard from './pages/owner/OwnerDashboard'

// Pages do Driver
import DriverLogin from './pages/driver/DriverLogin'
import DriverDashboard from './pages/driver/DriverDashboard'
import DeliveryDetail from './pages/driver/DeliveryDetail'
import DeliveryHistory from './pages/driver/DeliveryHistory'
import DriverProfile from './pages/driver/DriverProfile'

function AppRoutes() {
  const { isAuthenticated, user } = useAuth()

  // Função para obter o dashboard correto baseado na role
  const getDashboardPath = useCallback(() => {
    if (!user?.role) return '/login'
    
    const roleRoutes = {
      'driver': '/driver/dashboard',
      'admin': '/admin',
      'owner': '/owner',
      'operator': '/operador',
      'user': '/operador'
    }
    
    return roleRoutes[user.role] || '/dashboard'
  }, [user])

  return (
    <Routes>
      {/* Home redireciona para login ou dashboard baseado em autenticação e role */}
      <Route 
        path="/" 
        element={
          isAuthenticated ? (
            <Navigate to={getDashboardPath()} replace />
          ) : (
            <Navigate to="/login" replace />
          )
        } 
      />

      {/* Login redireciona para o dashboard correto se já autenticado */}
      <Route 
        path="/login" 
        element={isAuthenticated ? <Navigate to={getDashboardPath()} replace /> : <Login />} 
      />

      {/* Dashboard padrão (protegido) */}
      <Route 
        path="/dashboard" 
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="pedidos" element={<Orders />} />
        <Route path="chats" element={<Chats />} />
      </Route>

      {/* Paineis por Role (com layout próprio) */}
      <Route 
        path="/operador" 
        element={
          <ProtectedRoute requiredRole="operator">
            <OperatorDashboard />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/admin" 
        element={
          <ProtectedRoute requiredRole="admin">
            <AdminDashboard />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/owner" 
        element={
          <ProtectedRoute requiredRole="owner">
            <OwnerDashboard />
          </ProtectedRoute>
        } 
      />

      {/* Rotas do Driver */}
      <Route 
        path="/driver/login" 
        element={
          isAuthenticated ? <Navigate to="/driver/dashboard" replace /> : <DriverLogin />
        } 
      />
      <Route 
        path="/driver/dashboard" 
        element={
          <ProtectedRoute requiredRole="driver">
            <DriverDashboard />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/driver/delivery/:id" 
        element={
          <ProtectedRoute requiredRole="driver">
            <DeliveryDetail />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/driver/history" 
        element={
          <ProtectedRoute requiredRole="driver">
            <DeliveryHistory />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/driver/profile" 
        element={
          <ProtectedRoute requiredRole="driver">
            <DriverProfile />
          </ProtectedRoute>
        } 
      />

      {/* Fallback para login */}
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}

function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}

export default App
