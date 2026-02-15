/**
 * Dashboard do Operador - Versão Modernizada
 * Gerenciamento de pedidos e conversas
 */

import { useState, lazy, Suspense } from 'react'
import { LayoutDashboard, PlusCircle, Package, MessageSquare, History, Map as MapIcon } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import FlowbiteLayout from '../../components/flowbite/FlowbiteLayout'

// Importar componentes
import OperatorDashboardOverview from '../../components/operator/OperatorDashboardOverview'
import PendingOrdersPanel from '../../components/operator/PendingOrdersPanel'
import CreateOrderPanel from '../../components/operator/CreateOrderPanel'
import OrderHistoryPanel from '../../components/operator/OrderHistoryPanel'
import ConversationsPanel from '../../components/operator/ConversationsPanel'

// Lazy load do mapa (componente pesado)
const DeliveryMap = lazy(() => import('../../components/map/DeliveryMap'))
import useMapData from '../../hooks/useMapData'

export default function OperatorDashboard() {
  const { user, logout } = useAuth()
  const [activeView, setActiveView] = useState('dashboard')

  return (
    <FlowbiteLayout
      appName="Gas Automation"
      pageTitle="Operador"
      userEmail={user?.email || ''}
      onLogout={logout}
      navItems={[
        { key: 'dashboard', type: 'button', label: 'Dashboard', icon: LayoutDashboard, onClick: () => setActiveView('dashboard') },
        { key: 'create-order', type: 'button', label: 'Criar pedido', icon: PlusCircle, onClick: () => setActiveView('create-order') },
        { key: 'orders', type: 'button', label: 'Pedidos pendentes', icon: Package, onClick: () => setActiveView('orders') },
        { key: 'conversations', type: 'button', label: 'Conversas', icon: MessageSquare, onClick: () => setActiveView('conversations') },
        { key: 'history', type: 'button', label: 'Histórico', icon: History, onClick: () => setActiveView('history') },
        { key: 'map', type: 'button', label: 'Mapa', icon: MapIcon, onClick: () => setActiveView('map') },
      ]}
    >
      {/* Renderizar view baseada no estado */}
      {activeView === 'dashboard' && <OperatorDashboardOverview />}

      {activeView === 'create-order' && <CreateOrderPanel />}

      {activeView === 'orders' && <PendingOrdersPanel />}

      {activeView === 'conversations' && <ConversationsPanel />}

      {activeView === 'history' && <OrderHistoryPanel />}

      {activeView === 'map' && <MapView />}
    </FlowbiteLayout>
  )
}

// Componente separado para o mapa (usa hooks)
function MapView() {
  const {
    drivers,
    orders,
    deliveries,
    customerLocations,
    isLoading,
    error,
    refresh,
    orderCounts,
  } = useMapData({ autoRefresh: true, refreshInterval: 30000, todayOnly: true })

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-8 text-center">
        <h2 className="text-2xl font-semibold text-red-700 mb-2">Erro ao carregar mapa</h2>
        <p className="text-gray-600 mb-4">{error}</p>
        <button
          onClick={refresh}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
        >
          Tentar novamente
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold text-gray-900">Mapa de Pedidos - Hoje</h2>
        <button
          onClick={refresh}
          disabled={isLoading}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
        >
          {isLoading ? 'Atualizando...' : 'Atualizar'}
        </button>
      </div>

      {/* Cards de resumo por status */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 shadow-sm">
          <p className="text-2xl font-bold text-amber-600">{orderCounts.pending}</p>
          <p className="text-xs text-amber-700">Pendentes</p>
        </div>
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 shadow-sm">
          <p className="text-2xl font-bold text-blue-600">{orderCounts.in_route}</p>
          <p className="text-xs text-blue-700">Em Rota</p>
        </div>
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 shadow-sm">
          <p className="text-2xl font-bold text-emerald-600">{orderCounts.completed}</p>
          <p className="text-xs text-emerald-700">Concluidos</p>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-3 shadow-sm">
          <p className="text-2xl font-bold text-gray-700">{drivers.filter(d => d.location).length}</p>
          <p className="text-xs text-gray-500">Entregadores</p>
        </div>
      </div>

      <Suspense fallback={
        <div className="rounded-lg border border-gray-200 bg-white p-8 text-center shadow-sm">
          <div className="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-gray-200 border-t-primary-600" />
          <p className="mt-3 text-sm text-gray-600">Carregando mapa...</p>
        </div>
      }>
        <DeliveryMap
          drivers={drivers}
          orders={orders}
          deliveries={deliveries}
          customerLocations={customerLocations}
          height="600px"
          onDriverClick={(driver) => console.log('Driver clicked:', driver)}
          onOrderClick={(order) => console.log('Order clicked:', order)}
          onDeliveryClick={(delivery) => console.log('Delivery clicked:', delivery)}
        />
      </Suspense>
    </div>
  )
}
