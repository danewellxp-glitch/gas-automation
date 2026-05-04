import { AlertTriangle } from 'lucide-react'

const LOW_STOCK_THRESHOLD = 3

const COLUMN_META = [
  { key: 'qtd_cheios', label: 'Cheios', color: 'text-emerald-600' },
  { key: 'qtd_em_campo', label: 'Em Campo', color: 'text-amber-600' },
  { key: 'qtd_vazios', label: 'Vazios', color: 'text-slate-600' },
]

const PROGRESS_COLORS = ['bg-emerald-500', 'bg-amber-500', 'bg-slate-500']

export default function VasilhameCard({ item, label }) {
  const total = (item.qtd_cheios || 0) + (item.qtd_em_campo || 0) + (item.qtd_vazios || 0)
  const isLowStock = (item.qtd_cheios || 0) <= LOW_STOCK_THRESHOLD

  return (
    <div
      className={`bg-white rounded-xl p-4 border-2 ${
        isLowStock
          ? 'border-rose-400 bg-rose-50/30'
          : 'border-slate-200'
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="text-lg font-bold text-slate-900">{item.tipo}</div>
          <div className="text-xs text-slate-400 mt-0.5">{label || item.tipo}</div>
        </div>
        {isLowStock && (
          <span title="Estoque baixo" className="text-rose-500 shrink-0">
            <AlertTriangle className="w-5 h-5" strokeWidth={2} aria-hidden="true" />
          </span>
        )}
      </div>

      {/* 3-column mini-tile */}
      <div className="grid grid-cols-3 gap-1 mb-3">
        {COLUMN_META.map(({ key, label: colLabel, color }) => (
          <div key={key} className="text-center">
            <div className="text-xs text-slate-400 mb-0.5">{colLabel}</div>
            <div className={`text-[28px] font-bold leading-tight ${color}`}>
              {item[key] ?? 0}
            </div>
          </div>
        ))}
      </div>

      {/* Progress bar */}
      {total > 0 && (
        <div className="space-y-1">
          <div className="flex h-2 rounded-full overflow-hidden bg-slate-100">
            {COLUMN_META.map(({ key }, i) => {
              const value = item[key] || 0
              const pct = (value / total) * 100
              return pct > 0 ? (
                <div
                  key={key}
                  className={`${PROGRESS_COLORS[i]} transition-all`}
                  style={{ width: `${pct}%` }}
                />
              ) : null
            })}
          </div>
          <div className="text-[10px] text-slate-400 text-right">
            Total: {total} unidades
          </div>
        </div>
      )}
    </div>
  )
}
