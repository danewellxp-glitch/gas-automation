import { Routes, Route, Navigate } from 'react-router-dom'
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

function AppRoutes() {
  const { isAuthenticated } = useAuth()

  return (
    <Routes>
      {/* Home redireciona para login ou dashboard baseado em autenticação */}
      <Route 
        path="/" 
        element={
          isAuthenticated ? (
            <Navigate to="/dashboard" replace />
          ) : (
            <Navigate to="/login" replace />
          )
        } 
      />

      {/* Login */}
      <Route 
        path="/login" 
        element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <Login />} 
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
