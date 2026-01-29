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

      {activeView === 'conversations' && (
        <div className="rounded-lg border border-gray-200 bg-white p-8 text-center shadow-sm">
          <h2 className="text-2xl font-semibold text-gray-900 mb-2">Conversas</h2>
          <p className="text-gray-600 mb-6">Painel de conversas em desenvolvimento.</p>
          <p className="text-sm text-gray-500">Em breve: Chat em tempo real com WebSocket</p>
        </div>
      )}

      {activeView === 'history' && <OrderHistoryPanel />}

      {activeView === 'map' && <MapView />}
    </FlowbiteLayout>
  )
}

// Componente separado para o mapa (usa hooks)
function MapView() {
  const {
    drivers,
    deliveries,
    customerLocations,
    isLoading,
    error,
    refresh
  } = useMapData({ autoRefresh: true, refreshInterval: 30000 })

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
        <h2 className="text-2xl font-semibold text-gray-900">Mapa de Entregas</h2>
        <button
          onClick={refresh}
          disabled={isLoading}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
        >
          {isLoading ? 'Atualizando...' : 'Atualizar'}
        </button>
      </div>

      <Suspense fallback={
        <div className="rounded-lg border border-gray-200 bg-white p-8 text-center shadow-sm">
          <div className="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-gray-200 border-t-primary-600" />
          <p className="mt-3 text-sm text-gray-600">Carregando mapa...</p>
        </div>
      }>
        <DeliveryMap
          drivers={drivers}
          deliveries={deliveries}
          customerLocations={customerLocations}
          height="500px"
          onDriverClick={(driver) => console.log('Driver clicked:', driver)}
          onDeliveryClick={(delivery) => console.log('Delivery clicked:', delivery)}
        />
      </Suspense>

      {/* Resumo */}
      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <div className="flex items-center gap-3">
            <div>
              <p className="text-2xl font-bold text-primary-700">{drivers.length}</p>
              <p className="text-sm text-gray-500">Entregadores</p>
            </div>
          </div>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <div className="flex items-center gap-3">
            <div>
              <p className="text-2xl font-bold text-green-600">{deliveries.length}</p>
              <p className="text-sm text-gray-500">Entregas Ativas</p>
            </div>
          </div>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <div className="flex items-center gap-3">
            <div>
              <p className="text-2xl font-bold text-red-600">{customerLocations.length}</p>
              <p className="text-sm text-gray-500">Localizações</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
