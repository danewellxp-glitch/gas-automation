export default function StockBalanceCards({ balances, totalInTransit }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
      {balances.map(b => {
        const isLow = b.is_low_stock
        const total = b.quantity_depot + b.quantity_in_transit
        const progress = total > 0 ? (b.quantity_depot / (b.quantity_depot + b.quantity_in_transit + b.quantity_with_customers + 1)) * 100 : 0

        return (
          <div
            key={b.stock_product_id}
            className={`rounded-xl p-5 border-2 ${
              isLow
                ? 'bg-red-950 border-red-600 animate-pulse-slow'
                : 'bg-gray-800 border-gray-700'
            }`}
          >
            <div className="flex items-center justify-between mb-3">
              <div>
                <div className="text-2xl font-bold text-white">{b.product_code}</div>
                <div className="text-sm text-gray-400">{b.product_name}</div>
              </div>
              {isLow && (
                <span className="text-2xl" title="Estoque baixo">⚠️</span>
              )}
            </div>

            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">No depósito</span>
                <span className={`font-bold text-xl ${isLow ? 'text-red-400' : 'text-white'}`}>
                  {b.quantity_depot}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Em trânsito</span>
                <span className="text-yellow-400 font-medium">{b.quantity_in_transit}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Com clientes</span>
                <span className="text-blue-400">{b.quantity_with_customers}</span>
              </div>
            </div>

            {/* Progress bar */}
            <div className="mt-3 h-2 bg-gray-700 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${isLow ? 'bg-red-500' : 'bg-green-500'}`}
                style={{ width: `${Math.min(100, progress)}%` }}
              />
            </div>
          </div>
        )
      })}

      {/* In-transit summary card */}
      <div className="rounded-xl p-5 bg-gray-800 border-2 border-yellow-700">
        <div className="text-2xl font-bold text-yellow-400 mb-1">🚛 Em Trânsito</div>
        <div className="text-4xl font-black text-white mt-2">{totalInTransit}</div>
        <div className="text-gray-400 text-sm mt-1">botijões nos caminhões agora</div>
      </div>
    </div>
  )
}
