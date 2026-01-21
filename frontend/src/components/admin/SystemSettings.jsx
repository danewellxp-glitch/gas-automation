/**
 * Painel de Configurações do Sistema para Admin
 */

import { useState } from 'react'

export default function SystemSettings() {
  const [settings, setSettings] = useState({
    systemName: 'Gas Automation',
    enableNotifications: true,
    enableWebSocket: true,
    autoAssignOrders: false,
    maxDeliveriesPerDriver: 5,
    deliveryRadius: 10,
    workingHoursStart: '08:00',
    workingHoursEnd: '20:00'
  })

  const [saved, setSaved] = useState(false)

  const handleSave = async () => {
    try {
      // Simular salvamento
      await new Promise(resolve => setTimeout(resolve, 1000))
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (error) {
      console.error('Erro ao salvar configurações:', error)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-800">⚙️ Configurações do Sistema</h2>
        <p className="text-gray-600">Gerencie as configurações gerais da aplicação</p>
      </div>

      {/* Mensagem de Sucesso */}
      {saved && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <p className="text-green-700 font-medium">✓ Configurações salvas com sucesso!</p>
        </div>
      )}

      {/* Seção: Informações Gerais */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-bold text-gray-800 mb-4">📝 Informações Gerais</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Nome do Sistema
            </label>
            <input
              type="text"
              value={settings.systemName}
              onChange={(e) => setSettings({...settings, systemName: e.target.value})}
              className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>
      </div>

      {/* Seção: Funcionalidades */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-bold text-gray-800 mb-4">🔧 Funcionalidades</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div>
              <p className="font-medium text-gray-800">Notificações Push</p>
              <p className="text-sm text-gray-600">Enviar notificações em tempo real</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={settings.enableNotifications}
                onChange={(e) => setSettings({...settings, enableNotifications: e.target.checked})}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
          </div>

          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div>
              <p className="font-medium text-gray-800">WebSocket em Tempo Real</p>
              <p className="text-sm text-gray-600">Comunicação bidirecional instantânea</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={settings.enableWebSocket}
                onChange={(e) => setSettings({...settings, enableWebSocket: e.target.checked})}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
          </div>

          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div>
              <p className="font-medium text-gray-800">Auto-atribuir Pedidos</p>
              <p className="text-sm text-gray-600">Atribuir automaticamente pedidos aos drivers</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={settings.autoAssignOrders}
                onChange={(e) => setSettings({...settings, autoAssignOrders: e.target.checked})}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
          </div>
        </div>
      </div>

      {/* Seção: Entregas */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-bold text-gray-800 mb-4">🚚 Configurações de Entregas</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Máx. Entregas por Driver
            </label>
            <input
              type="number"
              value={settings.maxDeliveriesPerDriver}
              onChange={(e) => setSettings({...settings, maxDeliveriesPerDriver: parseInt(e.target.value)})}
              className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:border-blue-500"
              min="1"
              max="20"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Raio de Entrega (km)
            </label>
            <input
              type="number"
              value={settings.deliveryRadius}
              onChange={(e) => setSettings({...settings, deliveryRadius: parseInt(e.target.value)})}
              className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:border-blue-500"
              min="1"
              max="50"
            />
          </div>
        </div>
      </div>

      {/* Seção: Horário de Funcionamento */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-bold text-gray-800 mb-4">🕒 Horário de Funcionamento</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Hora de Abertura
            </label>
            <input
              type="time"
              value={settings.workingHoursStart}
              onChange={(e) => setSettings({...settings, workingHoursStart: e.target.value})}
              className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:border-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Hora de Fechamento
            </label>
            <input
              type="time"
              value={settings.workingHoursEnd}
              onChange={(e) => setSettings({...settings, workingHoursEnd: e.target.value})}
              className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>
      </div>

      {/* Seção: Informações do Sistema */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-bold text-gray-800 mb-4">💻 Informações do Sistema</h3>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div className="p-3 bg-gray-50 rounded">
            <p className="text-gray-600">Versão</p>
            <p className="font-bold text-gray-800">v1.0.0</p>
          </div>
          <div className="p-3 bg-gray-50 rounded">
            <p className="text-gray-600">Ambiente</p>
            <p className="font-bold text-gray-800">Production</p>
          </div>
          <div className="p-3 bg-gray-50 rounded">
            <p className="text-gray-600">Backend</p>
            <p className="font-bold text-gray-800">192.168.10.156:8000</p>
          </div>
          <div className="p-3 bg-gray-50 rounded">
            <p className="text-gray-600">Frontend</p>
            <p className="font-bold text-gray-800">192.168.10.156:3001</p>
          </div>
        </div>
      </div>

      {/* Botão Salvar */}
      <div className="flex justify-end gap-3">
        <button
          onClick={() => window.location.reload()}
          className="px-6 py-3 bg-gray-300 text-gray-800 rounded-lg hover:bg-gray-400 transition font-medium"
        >
          Cancelar
        </button>
        <button
          onClick={handleSave}
          className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition font-medium"
        >
          💾 Salvar Configurações
        </button>
      </div>
    </div>
  )
}
