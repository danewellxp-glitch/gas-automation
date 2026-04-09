/**
 * Dashboard do Operador
 * Gerenciamento de pedidos, conversas, financeiro e comodatos
 */

import { useState, lazy, Suspense } from 'react'
import {
  LayoutDashboard, PlusCircle, Package, MessageSquare,
  History, Truck, FileText, Clock, Bot,
  Calendar, QrCode, Receipt, Boxes, ClipboardCheck,
} from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import FlowbiteLayout from '../../components/flowbite/FlowbiteLayout'

import OperatorDashboardOverview from '../../components/operator/OperatorDashboardOverview'
import PendingOrdersPanel from '../../components/operator/PendingOrdersPanel'
import CreateOrderPanel from '../../components/operator/CreateOrderPanel'
import OrderHistoryPanel from '../../components/operator/OrderHistoryPanel'
import ConversationsPanel from '../../components/operator/ConversationsPanel'
import OSPanel from '../../components/operator/OSPanel'
import AgendadosPanel from '../../components/operator/AgendadosPanel'
import PIXAsaasPanel from '../../components/operator/PIXAsaasPanel'
import DespesasPanel from '../../components/operator/DespesasPanel'
import ComodatoPanel from '../../components/operator/ComodatoPanel'
import AcertoTurnoPanel from '../../components/operator/AcertoTurnoPanel'

import useMapData from '../../hooks/useMapData'

const DeliveryMap = lazy(() => import('../../components/map/DeliveryMap'))

export default function OperatorDashboard() {
  const { user, logout } = useAuth()
  const [activeView, setActiveView] = useState('dashboard')

  const nav = (view) => () => setActiveView(view)

  return (
    <FlowbiteLayout
      appName="Gas Automation"
      logo="/logo_sistema.png"
      pageTitle="Operador"
      userEmail={user?.email || ''}
      onLogout={logout}
      activeNavKey={activeView}
      sidebarUserInfo={{ name: user?.full_name || user?.username || user?.email, role: user?.role, onLogout: logout }}
      navItems={[
        {
          key: 'dashboard',
          type: 'button',
          label: 'Dashboard',
          icon: LayoutDashboard,
          onClick: nav('dashboard'),
        },
        {
          key: 'conversations',
          type: 'button',
          label: 'Conversas Bot',
          icon: Bot,
          onClick: nav('conversations'),
        },
        {
          key: 'orders',
          type: 'group',
          label: 'Pedidos',
          icon: Package,
          children: [
            {
              key: 'create-order',
              type: 'button',
              label: 'Criar Pedido',
              icon: PlusCircle,
              onClick: nav('create-order'),
            },
            {
              key: 'orders-pending',
              type: 'button',
              label: 'Pendentes',
              icon: Clock,
              onClick: nav('orders-pending'),
            },
            {
              key: 'orders-all',
              type: 'button',
              label: 'Todos os Pedidos',
              icon: FileText,
              onClick: nav('orders-all'),
            },
            {
              key: 'orders-scheduled',
              type: 'button',
              label: 'Agendados',
              icon: Calendar,
              onClick: nav('orders-scheduled'),
            },
          ],
        },
        {
          key: 'financeiro',
          type: 'group',
          label: 'Financeiro',
          icon: Receipt,
          children: [
            {
              key: 'financeiro-pix',
              type: 'button',
              label: 'PIX Asaas',
              icon: QrCode,
              onClick: nav('financeiro-pix'),
            },
          ],
        },
        {
          key: 'drivers',
          type: 'button',
          label: 'Entregadores',
          icon: Truck,
          onClick: nav('drivers'),
        },
        {
          key: 'history',
          type: 'button',
          label: 'Histórico',
          icon: History,
          onClick: nav('history'),
        },
      ]}
    >
      {activeView === 'dashboard'          && <OperatorDashboardOverview />}
      {activeView === 'conversations'      && <ConversationsPanel />}
      {activeView === 'create-order'       && <CreateOrderPanel />}
      {activeView === 'orders-pending'     && <PendingOrdersPanel />}
      {activeView === 'orders-all'         && <OSPanel />}
      {activeView === 'orders-scheduled'   && <AgendadosPanel />}
      {activeView === 'financeiro-pix'     && <PIXAsaasPanel />}
      {activeView === 'financeiro-despesas'&& <DespesasPanel />}
      {activeView === 'comodatos'          && <ComodatoPanel />}
      {activeView === 'acerto-turno'       && <AcertoTurnoPanel />}
      {activeView === 'drivers'            && <DriversView />}
      {activeView === 'history'            && <OrderHistoryPanel />}
    </FlowbiteLayout>
  )
}

// Entregadores — monitoramento de motoristas + mapa
function DriversView() {
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
      <div className="rounded-xl border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/10 p-6 text-center">
        <p className="text-sm font-medium text-red-700 dark:text-red-400 mb-3">Erro ao carregar entregadores</p>
        <p className="text-xs text-red-600 dark:text-red-400 mb-4">{error}</p>
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

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Entregadores</h2>
          <p className="text-xs text-gray-500 dark:text-gray-400">Monitoramento em tempo real</p>
        </div>
        <button
          onClick={refresh}
          disabled={isLoading}
          className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 transition-colors"
        >
          {isLoading ? 'Atualizando...' : 'Atualizar'}
        </button>
      </div>

      {/* Status counts */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="rounded-xl border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/10 p-3">
          <p className="text-xl font-bold text-amber-600 dark:text-amber-400">{orderCounts.pending}</p>
          <p className="text-xs text-amber-700 dark:text-amber-500">Pendentes</p>
        </div>
        <div className="rounded-xl border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/10 p-3">
          <p className="text-xl font-bold text-blue-600 dark:text-blue-400">{orderCounts.in_route}</p>
          <p className="text-xs text-blue-700 dark:text-blue-500">Em Rota</p>
        </div>
        <div className="rounded-xl border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-900/10 p-3">
          <p className="text-xl font-bold text-emerald-600 dark:text-emerald-400">{orderCounts.completed}</p>
          <p className="text-xs text-emerald-700 dark:text-emerald-500">Concluídos</p>
        </div>
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-3">
          <p className="text-xl font-bold text-gray-700 dark:text-gray-300">{drivers.filter(d => d.location).length}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">Entregadores ativos</p>
        </div>
      </div>

      {/* Map */}
      <Suspense fallback={
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 flex items-center justify-center h-96">
          <div className="w-6 h-6 animate-spin rounded-full border-2 border-gray-200 border-t-primary-600" />
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
