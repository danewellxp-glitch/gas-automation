import { Routes, Route, Navigate } from 'react-router-dom'
import { useCallback } from 'react'
import { Toaster } from 'react-hot-toast'
import { AuthProvider, useAuth } from './hooks/useAuth'
import ErrorBoundary from './components/ErrorBoundary'
import ProtectedRoute from './components/ProtectedRoute'
import Layout from './components/Layout'

// Pages
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Orders from './pages/Orders'
import Chats from './pages/Chats'
import VeloceChatDashboard from './pages/VeloceChatDashboard'
import ChangePassword from './pages/ChangePassword'

// Página de Teste - Notificações V2
import TestNotificationsPage from './pages/TestNotificationsPage'

// Pages por Role
import OperatorDashboard from './pages/operator/OperatorDashboard'
import AdminDashboard from './pages/admin/AdminDashboard'
import OwnerDashboard from './pages/owner/OwnerDashboard'
import FinanceiroDashboard from './pages/financeiro/FinanceiroDashboard'
import EstoqueDashboard from './pages/estoque/EstoqueDashboard'

// Pages do Driver
import DriverLogin from './pages/driver/DriverLogin'
import DriverDashboard from './pages/driver/DriverDashboard'
import DeliveryDetail from './pages/driver/DeliveryDetail'
import DeliveryHistory from './pages/driver/DeliveryHistory'
import DriverProfile from './pages/driver/DriverProfile'
import AcertoCarga from './pages/driver/AcertoCarga'

function AppRoutes() {
  const { isAuthenticated, user } = useAuth()

  // Função para obter o dashboard correto baseado na role
  const getDashboardPath = useCallback(() => {
    if (!user?.role) return '/login'

    if (user?.must_change_password) return '/change-password'

    const roleRoutes = {
      'driver': '/driver/dashboard',
      'admin': '/admin',
      'owner': '/owner',
      'operator': '/operador',
      'financeiro': '/financeiro',
      'estoque': '/estoque',
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

      <Route
        path="/change-password"
        element={
          <ProtectedRoute>
            <ChangePassword />
          </ProtectedRoute>
        }
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
        <Route path="chats" element={<VeloceChatDashboard />} />
      </Route>

      {/* Página de Teste - Notificações V2 (sem autenticação para facilitar testes) */}
      <Route path="/test-notifications-v2" element={<TestNotificationsPage />} />

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

      {/* Painel Financeiro */}
      <Route
        path="/financeiro"
        element={
          <ProtectedRoute allowedRoles={['financeiro', 'admin', 'owner']}>
            <FinanceiroDashboard />
          </ProtectedRoute>
        }
      />

      {/* Painel de Estoque */}
      <Route
        path="/estoque"
        element={
          <ProtectedRoute allowedRoles={['estoque', 'admin']}>
            <EstoqueDashboard />
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
      <Route
        path="/driver/carga/acerto"
        element={
          <ProtectedRoute requiredRole="driver">
            <AcertoCarga />
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
    <ErrorBoundary>
      <AuthProvider>
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: '#333',
              color: '#fff',
            },
            success: {
              iconTheme: { primary: '#22c55e', secondary: '#fff' },
            },
            error: {
              iconTheme: { primary: '#ef4444', secondary: '#fff' },
            },
          }}
        />
        <AppRoutes />
      </AuthProvider>
    </ErrorBoundary>
  )
}

export default App
