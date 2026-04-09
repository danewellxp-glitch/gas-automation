// Shadcn-style stat card — flat, no gradients, no emojis
function TrendUp() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" />
      <polyline points="16 7 22 7 22 13" />
    </svg>
  )
}
function TrendDown() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 17 13.5 8.5 8.5 13.5 2 7" />
      <polyline points="16 17 22 17 22 11" />
    </svg>
  )
}

export default function MetricCard({ title, value, change, changeLabel, icon: Icon, loading = false }) {
  const isPositive = change == null ? null : parseFloat(change) >= 0

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium text-gray-500">{title}</span>
        {Icon && (
          <div className="text-gray-400">
            <Icon />
          </div>
        )}
      </div>

      {loading ? (
        <>
          <div className="h-8 w-28 rounded bg-gray-100 animate-pulse mb-2" />
          <div className="h-4 w-20 rounded bg-gray-100 animate-pulse" />
        </>
      ) : (
        <>
          <div className="text-2xl font-bold text-gray-900 tracking-tight">{value}</div>
          {change != null && (
            <div className={`flex items-center gap-1 mt-2 text-xs font-medium ${isPositive ? 'text-emerald-600' : 'text-red-500'}`}>
              {isPositive ? <TrendUp /> : <TrendDown />}
              <span>{isPositive ? '+' : ''}{parseFloat(change).toFixed(1)}%</span>
              {changeLabel && <span className="text-gray-400 font-normal ml-0.5">{changeLabel}</span>}
            </div>
          )}
          {change == null && changeLabel && (
            <p className="mt-2 text-xs text-gray-400">{changeLabel}</p>
          )}
        </>
      )}
    </div>
  )
}
