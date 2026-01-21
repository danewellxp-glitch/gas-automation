/**
 * Header do Driver com Status Toggle
 */

import { useState } from 'react'

const STATUS_OPTIONS = [
  { value: 'offline', label: 'Offline', icon: '🔴', color: 'text-gray-600' },
  { value: 'available', label: 'Online', icon: '🟢', color: 'text-green-600' },
  { value: 'busy', label: 'Ocupado', icon: '🔵', color: 'text-blue-600' },
  { value: 'break', label: 'Pausa', icon: '🟡', color: 'text-yellow-600' }
]

export default function DriverHeader({ driver, onStatusChange, wsConnected }) {
  const [showStatusMenu, setShowStatusMenu] = useState(false)

  if (!driver) return null

  const currentStatus = STATUS_OPTIONS.find(s => s.value === driver.status) || STATUS_OPTIONS[0]

  const handleStatusClick = async (newStatus) => {
    setShowStatusMenu(false)
    if (newStatus !== driver.status) {
      await onStatusChange(newStatus)
    }
  }

  return (
    <div className="bg-white shadow-md p-4 mb-4">
      <div className="flex items-center justify-between">
        {/* Foto e Nome */}
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
            <span className="text-2xl">👤</span>
          </div>
          <div>
            <h2 className="font-bold text-gray-800">{driver.name}</h2>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowStatusMenu(!showStatusMenu)}
                className={`text-sm font-medium ${currentStatus.color} flex items-center gap-1`}
              >
                {currentStatus.icon} {currentStatus.label}
                <span className="ml-1">▼</span>
              </button>
              {wsConnected && (
                <span className="text-xs text-green-600" title="WebSocket conectado">
                  🔗
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Rating */}
        <div className="text-right">
          <div className="flex items-center gap-1">
            <span className="text-yellow-500 text-xl">⭐</span>
            <span className="font-bold text-gray-800">{driver.rating?.toFixed(1)}</span>
          </div>
          <p className="text-xs text-gray-500">{driver.total_deliveries} entregas</p>
        </div>
      </div>

      {/* Status Menu */}
      {showStatusMenu && (
        <div className="absolute top-20 left-4 bg-white border border-gray-200 rounded-lg shadow-lg z-50 overflow-hidden">
          {STATUS_OPTIONS.map((status) => (
            <button
              key={status.value}
              onClick={() => handleStatusClick(status.value)}
              className={`w-full px-6 py-3 text-left hover:bg-gray-50 flex items-center gap-3 ${
                status.value === driver.status ? 'bg-blue-50' : ''
              }`}
            >
              <span className="text-2xl">{status.icon}</span>
              <span className={`font-medium ${status.color}`}>{status.label}</span>
              {status.value === driver.status && <span className="ml-auto text-blue-600">✓</span>}
            </button>
          ))}
        </div>
      )}

      {/* Overlay para fechar menu */}
      {showStatusMenu && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setShowStatusMenu(false)}
        />
      )}
    </div>
  )
}
