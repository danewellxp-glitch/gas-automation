/**
 * NotificationTester - Componente para testar sistema de notificações
 * 
 * Use este componente para testar todas as funcionalidades
 * do sistema de notificações em ambiente React.
 * 
 * Para usar: adicione <NotificationTester /> em qualquer página
 * 
 * @author Gas Automation
 * @version 1.0.0
 */

import React from 'react'
import { useNotifications } from '../hooks/useNotifications'
import NotificationBell, { NotificationButton, NotificationBadge } from './notifications/NotificationBell'

export default function NotificationTester() {
  const {
    pendingCount,
    history,
    permissionGranted,
    settings,
    isInitialized,
    markAsRead,
    markAllAsRead,
    clearHistory,
    requestPermission,
    updateSetting,
    test,
    notify,
    hasUnread,
    unreadNotifications,
    totalNotifications,
  } = useNotifications({
    enabled: true,
    autoRequestPermission: false,
    onNotification: (notif) => {
      console.log('🔔 Callback customizado:', notif)
    },
    onOrderCreated: (orderData) => {
      console.log('📦 Callback de novo pedido:', orderData)
    }
  })
  
  // Handler de teste
  const handleTestNotification = () => {
    notify({
      order_id: `test-${Date.now()}`,
      order_number: Math.floor(Math.random() * 1000),
      customer_name: 'Cliente Teste',
      customer_phone: '5541999999999',
      total_amount: 150.00 + Math.random() * 100,
      bairro: ['Centro', 'Batel', 'Água Verde', 'Portão'][Math.floor(Math.random() * 4)],
      status: 'pending'
    })
  }
  
  const handleTestMultiple = () => {
    for (let i = 0; i < 3; i++) {
      setTimeout(() => handleTestNotification(), i * 1000)
    }
  }
  
  return (
    <div className="fixed bottom-4 right-4 z-50 bg-white rounded-lg shadow-2xl p-6 max-w-md border-2 border-primary-200">
      <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
        🧪 Teste de Notificações
      </h3>
      
      {/* Status */}
      <div className="grid grid-cols-2 gap-2 mb-4 text-xs">
        <div className="bg-blue-50 p-2 rounded">
          <div className="font-semibold text-blue-900">Status</div>
          <div className="text-blue-600">{isInitialized ? '✅ Ativo' : '⏳ Carregando'}</div>
        </div>
        <div className="bg-green-50 p-2 rounded">
          <div className="font-semibold text-green-900">Permissão</div>
          <div className="text-green-600">{permissionGranted ? '✅ Sim' : '❌ Não'}</div>
        </div>
        <div className="bg-purple-50 p-2 rounded">
          <div className="font-semibold text-purple-900">Pendentes</div>
          <div className="text-purple-600 text-xl font-bold">{pendingCount}</div>
        </div>
        <div className="bg-orange-50 p-2 rounded">
          <div className="font-semibold text-orange-900">Total</div>
          <div className="text-orange-600 text-xl font-bold">{totalNotifications}</div>
        </div>
      </div>
      
      {/* Componentes de Badge */}
      <div className="mb-4 flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
        <span className="text-sm font-medium">Componentes:</span>
        <NotificationBell count={pendingCount} onClick={() => console.log('Bell clicked')} />
        <NotificationBadge count={pendingCount} onClick={() => console.log('Badge clicked')} />
        <NotificationButton count={pendingCount} onClick={() => console.log('Button clicked')} />
      </div>
      
      {/* Botões de teste */}
      <div className="space-y-2">
        <button
          onClick={handleTestNotification}
          className="w-full bg-primary-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-primary-700 transition-colors text-sm"
          disabled={!isInitialized}
        >
          🔔 Notificação de Teste
        </button>
        
        <button
          onClick={handleTestMultiple}
          className="w-full bg-purple-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-purple-700 transition-colors text-sm"
          disabled={!isInitialized}
        >
          🔔🔔🔔 3 Notificações
        </button>
        
        <button
          onClick={test}
          className="w-full bg-blue-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-blue-700 transition-colors text-sm"
          disabled={!isInitialized}
        >
          🧪 Teste do Serviço
        </button>
        
        {!permissionGranted && (
          <button
            onClick={requestPermission}
            className="w-full bg-yellow-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-yellow-700 transition-colors text-sm"
          >
            🔐 Solicitar Permissão
          </button>
        )}
        
        {hasUnread && (
          <button
            onClick={markAllAsRead}
            className="w-full bg-green-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-green-700 transition-colors text-sm"
          >
            ✓ Marcar Todas como Lidas
          </button>
        )}
        
        {totalNotifications > 0 && (
          <button
            onClick={clearHistory}
            className="w-full bg-red-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-red-700 transition-colors text-sm"
          >
            🗑️ Limpar Histórico
          </button>
        )}
      </div>
      
      {/* Configurações rápidas */}
      <div className="mt-4 pt-4 border-t space-y-2">
        <div className="text-xs font-semibold text-gray-700 mb-2">⚙️ Configurações:</div>
        
        <label className="flex items-center justify-between text-xs">
          <span>🔊 Som</span>
          <input
            type="checkbox"
            checked={settings.sound}
            onChange={(e) => updateSetting('sound', e.target.checked)}
            className="rounded text-primary-600"
          />
        </label>
        
        <label className="flex items-center justify-between text-xs">
          <span>📳 Vibração</span>
          <input
            type="checkbox"
            checked={settings.vibration}
            onChange={(e) => updateSetting('vibration', e.target.checked)}
            className="rounded text-primary-600"
          />
        </label>
        
        <label className="flex items-center justify-between text-xs">
          <span>💻 Nativas</span>
          <input
            type="checkbox"
            checked={settings.nativeNotifications}
            onChange={(e) => updateSetting('nativeNotifications', e.target.checked)}
            className="rounded text-primary-600"
          />
        </label>
        
        <div>
          <label className="text-xs block mb-1">
            Volume: {Math.round((settings.soundVolume || 0.7) * 100)}%
          </label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={settings.soundVolume || 0.7}
            onChange={(e) => updateSetting('soundVolume', parseFloat(e.target.value))}
            className="w-full h-1 bg-gray-200 rounded-lg appearance-none cursor-pointer"
          />
        </div>
      </div>
      
      {/* Histórico resumido */}
      {history.length > 0 && (
        <div className="mt-4 pt-4 border-t">
          <div className="text-xs font-semibold text-gray-700 mb-2">
            📜 Últimas {Math.min(3, history.length)} notificações:
          </div>
          <div className="space-y-2">
            {history.slice(0, 3).map((notif, idx) => (
              <div
                key={notif.id}
                className={`text-xs p-2 rounded ${notif.read ? 'bg-gray-100' : 'bg-blue-50'}`}
              >
                <div className="font-medium">{notif.title}</div>
                <div className="text-gray-600 truncate">{notif.message}</div>
                <div className="text-gray-400 mt-1">
                  {new Date(notif.timestamp).toLocaleTimeString()}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
