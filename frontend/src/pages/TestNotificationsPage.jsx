/**
 * Página de Teste - Sistema de Notificações V2
 * 
 * Página isolada para testar o sistema de notificações
 * sem interferir no dashboard principal
 */

import { useNotifications } from '../hooks/useNotifications'
import NotificationBell from '../components/notifications/NotificationBell'

export default function TestNotificationsPage() {
  const { 
    pendingCount,
    history,
    permissionGranted,
    test,
    clearHistory,
    requestPermission,
    markAsRead,
  } = useNotifications({ enabled: true })
  
  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-4xl font-bold mb-8 text-gray-900">
          🔔 Teste de Notificações V2
        </h1>
        
        {/* Status */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Status do Sistema</h2>
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-blue-50 p-4 rounded">
              <p className="text-sm text-gray-600">Contador</p>
              <p className="text-3xl font-bold text-blue-600">{pendingCount}</p>
            </div>
            <div className="bg-green-50 p-4 rounded">
              <p className="text-sm text-gray-600">Total</p>
              <p className="text-3xl font-bold text-green-600">{history.length}</p>
            </div>
            <div className="bg-purple-50 p-4 rounded col-span-2">
              <p className="text-sm text-gray-600">Permissão Nativa</p>
              <p className="text-lg font-bold text-purple-600">
                {permissionGranted ? '✅ Concedida' : '❌ Não concedida'}
              </p>
            </div>
          </div>
        </div>
        
        {/* Ações */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Ações de Teste</h2>
          <div className="space-y-3">
            <button
              onClick={test}
              className="w-full bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors"
            >
              🧪 Testar Notificação
            </button>
            
            <button
              onClick={requestPermission}
              className="w-full bg-purple-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-purple-700 transition-colors"
            >
              🔐 Solicitar Permissão Nativa
            </button>
            
            <button
              onClick={clearHistory}
              className="w-full bg-red-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-red-700 transition-colors"
            >
              🗑️ Limpar Histórico
            </button>
          </div>
        </div>
        
        {/* Sino de Teste */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Componente Sino</h2>
          <div className="flex items-center justify-center p-8 bg-gray-50 rounded">
            <NotificationBell
              count={pendingCount}
              onClick={() => alert(`${pendingCount} notificações pendentes!`)}
            />
          </div>
        </div>
        
        {/* Histórico */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Histórico de Notificações</h2>
          {history.length === 0 ? (
            <p className="text-gray-500 text-center py-8">
              Nenhuma notificação ainda. Clique em "Testar Notificação" acima.
            </p>
          ) : (
            <div className="space-y-3">
              {history.map((notif) => (
                <div
                  key={notif.id}
                  className={`p-4 rounded-lg border ${
                    notif.read ? 'bg-gray-50 border-gray-200' : 'bg-blue-50 border-blue-200'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <p className="font-semibold text-gray-900">{notif.title}</p>
                      <p className="text-sm text-gray-600 mt-1">{notif.message}</p>
                      <p className="text-xs text-gray-400 mt-2">
                        {new Date(notif.timestamp).toLocaleString('pt-BR')}
                      </p>
                    </div>
                    {!notif.read && (
                      <button
                        onClick={() => markAsRead(notif.id)}
                        className="ml-4 text-sm text-blue-600 hover:text-blue-800"
                      >
                        Marcar lida
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
        
        {/* Instruções */}
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 mt-6">
          <h3 className="font-semibold text-yellow-900 mb-2">📝 Instruções:</h3>
          <ol className="list-decimal list-inside space-y-1 text-sm text-yellow-800">
            <li>Clique em "🧪 Testar Notificação" para simular um pedido</li>
            <li>Verifique se o toast aparece no canto superior direito</li>
            <li>Observe o contador aumentar</li>
            <li>Se permitir, verá notificação nativa também</li>
            <li>O som deve tocar (se tiver notification.mp3)</li>
          </ol>
        </div>
      </div>
    </div>
  )
}
