/**
 * Dashboard do Operador - Versão Modernizada
 * Gerenciamento de pedidos e conversas
 */

import { useState } from 'react'
import { useAuth } from '../../hooks/useAuth'

// Importar componentes
import OperatorDashboardOverview from '../../components/operator/OperatorDashboardOverview'
import PendingOrdersPanel from '../../components/operator/PendingOrdersPanel'
import CreateOrderPanel from '../../components/operator/CreateOrderPanel'

export default function OperatorDashboard() {
  const { user, logout } = useAuth()
  const [activeView, setActiveView] = useState('dashboard')

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <div className="w-64 bg-white shadow-lg flex flex-col">
        <div className="p-6 border-b">
          <h1 className="text-xl font-bold text-gray-800">Gas Automation</h1>
          <p className="text-sm text-gray-500">Painel do Operador</p>
        </div>
        
        <nav className="p-4 flex-1">
          <div className="space-y-2">
            <button
              onClick={() => setActiveView('dashboard')}
              className={`w-full text-left px-4 py-3 rounded transition ${
                activeView === 'dashboard'
                  ? 'bg-blue-500 text-white'
                  : 'hover:bg-gray-100'
              }`}
            >
              📊 Dashboard
            </button>
            <button
              onClick={() => setActiveView('create-order')}
              className={`w-full text-left px-4 py-3 rounded transition ${
                activeView === 'create-order'
                  ? 'bg-blue-500 text-white'
                  : 'hover:bg-gray-100'
              }`}
            >
              ➕ Criar Pedido
            </button>
            <button
              onClick={() => setActiveView('orders')}
              className={`w-full text-left px-4 py-3 rounded transition ${
                activeView === 'orders'
                  ? 'bg-blue-500 text-white'
                  : 'hover:bg-gray-100'
              }`}
            >
              📦 Pedidos Pendentes
            </button>
            <button
              onClick={() => setActiveView('conversations')}
              className={`w-full text-left px-4 py-3 rounded transition ${
                activeView === 'conversations'
                  ? 'bg-blue-500 text-white'
                  : 'hover:bg-gray-100'
              }`}
            >
              💬 Conversas
            </button>
            <button
              onClick={() => setActiveView('history')}
              className={`w-full text-left px-4 py-3 rounded transition ${
                activeView === 'history'
                  ? 'bg-blue-500 text-white'
                  : 'hover:bg-gray-100'
              }`}
            >
              📋 Histórico
            </button>
          </div>
        </nav>

        {/* User Info */}
        <div className="border-t p-4">
          <div className="flex items-center justify-between gap-2">
            <div className="text-sm min-w-0">
              <p className="font-semibold text-gray-800 truncate">{user?.email}</p>
              <p className="text-gray-500 text-xs uppercase font-bold">
                👤 {user?.role}
              </p>
            </div>
            <button 
              onClick={logout}
              className="px-3 py-1 bg-red-500 text-white rounded text-xs hover:bg-red-600 transition whitespace-nowrap"
            >
              Sair
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto">
        <div className="p-8">
          {/* Renderizar view baseada no estado */}
          {activeView === 'dashboard' && <OperatorDashboardOverview />}
          
          {activeView === 'create-order' && <CreateOrderPanel />}
          
          {activeView === 'orders' && <PendingOrdersPanel />}
          
          {activeView === 'conversations' && (
            <div className="bg-white rounded-lg shadow p-8 text-center">
              <div className="text-6xl mb-4">💬</div>
              <h2 className="text-2xl font-bold text-gray-800 mb-2">Conversas</h2>
              <p className="text-gray-600 mb-6">
                Painel de conversas em desenvolvimento.
              </p>
              <p className="text-sm text-gray-500">
                Em breve: Chat em tempo real com WebSocket
              </p>
            </div>
          )}
          
          {activeView === 'history' && (
            <div className="bg-white rounded-lg shadow p-8 text-center">
              <div className="text-6xl mb-4">📋</div>
              <h2 className="text-2xl font-bold text-gray-800 mb-2">Histórico</h2>
              <p className="text-gray-600 mb-6">
                Visualize pedidos e conversas anteriores.
              </p>
              <p className="text-sm text-gray-500">
                Em desenvolvimento
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
