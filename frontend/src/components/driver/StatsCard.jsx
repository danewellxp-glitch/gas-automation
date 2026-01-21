/**
 * Card de Estatísticas do Driver
 */

export default function StatsCard({ stats }) {
  if (!stats) return null

  return (
    <div className="grid grid-cols-3 gap-3">
      {/* Entregas Hoje */}
      <div className="bg-white rounded-lg shadow p-4 text-center">
        <div className="text-3xl font-bold text-blue-600 mb-1">
          {stats.today_deliveries}
        </div>
        <div className="text-xs text-gray-600">Entregas</div>
        <div className="text-xs text-gray-500">hoje</div>
      </div>

      {/* Rating */}
      <div className="bg-white rounded-lg shadow p-4 text-center">
        <div className="text-3xl font-bold text-yellow-500 mb-1">
          {stats.rating?.toFixed(1)}
        </div>
        <div className="text-xs text-gray-600">Rating</div>
        <div className="text-xs text-gray-500">⭐</div>
      </div>

      {/* Tempo Médio */}
      <div className="bg-white rounded-lg shadow p-4 text-center">
        <div className="text-3xl font-bold text-green-600 mb-1">
          {stats.average_delivery_time_minutes 
            ? Math.round(stats.average_delivery_time_minutes)
            : '--'
          }
        </div>
        <div className="text-xs text-gray-600">Tempo</div>
        <div className="text-xs text-gray-500">min médio</div>
      </div>
    </div>
  )
}
