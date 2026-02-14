/**
 * NotificationBell - Sino com badge contador
 * 
 * Componente simples que exibe um sino com contador de notificações
 * não lidas, com animação de pulso quando há pendências.
 */

import { Bell } from 'lucide-react'

export default function NotificationBell({ count = 0, onClick }) {
  return (
    <button
      onClick={onClick}
      className="relative p-2 text-gray-600 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary-500 rounded-full transition-colors"
      aria-label={`${count} notificações pendentes`}
      type="button"
    >
      <Bell className="w-6 h-6" />
      
      {count > 0 && (
        <span className="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-600 text-xs font-bold text-white animate-pulse">
          {count > 9 ? '9+' : count}
        </span>
      )}
    </button>
  )
}
