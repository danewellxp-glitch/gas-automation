function fmt(val) {
  return parseFloat(val || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

function daysUntil(dateStr) {
  if (!dateStr) return null
  return Math.ceil((new Date(dateStr + 'T00:00:00') - new Date()) / 86400000)
}

function DueLabel({ days }) {
  if (days == null) return null
  if (days < 0) return <span className="text-xs text-red-500">{Math.abs(days)}d em atraso</span>
  if (days === 0) return <span className="text-xs text-amber-600">vence hoje</span>
  if (days <= 3) return <span className="text-xs text-amber-600">vence em {days}d</span>
  return <span className="text-xs text-gray-400">vence em {days}d</span>
}

export default function BillsWidget({ payables = [], receivables = [], onPay, onReceive }) {
  const urgentPayables = payables
    .filter(p => p.status !== 'pago')
    .map(p => ({ ...p, days: daysUntil(p.due_date), kind: 'pagar' }))
    .filter(p => p.days != null && p.days <= 7)
    .sort((a, b) => a.days - b.days)
    .slice(0, 4)

  const overdueReceivables = receivables
    .filter(r => r.status !== 'recebido')
    .map(r => ({ ...r, days: daysUntil(r.due_date), kind: 'receber' }))
    .filter(r => r.days != null && r.days < 0)
    .sort((a, b) => a.days - b.days)
    .slice(0, 4)

  const items = [...overdueReceivables, ...urgentPayables]

  if (!items.length) {
    return (
      <div className="py-12 text-center">
        <p className="text-sm text-gray-500">Nenhuma pendência urgente</p>
        <p className="text-xs text-gray-400 mt-1">Todos os pagamentos estão em dia</p>
      </div>
    )
  }

  return (
    <div className="space-y-0">
      {items.map((item, i) => {
        const isPagar = item.kind === 'pagar'
        return (
          <div
            key={item.id || i}
            className="flex items-center gap-3 py-3 border-b border-gray-100 last:border-0 group"
          >
            {/* Status dot */}
            <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
              item.days < 0 ? 'bg-red-500' : item.days === 0 ? 'bg-amber-400' : 'bg-gray-300'
            }`} />

            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">
                {item.description || (isPagar ? 'Conta a pagar' : 'A receber')}
              </p>
              <div className="flex items-center gap-2 mt-0.5">
                <DueLabel days={item.days} />
                {item.supplier_name && (
                  <span className="text-xs text-gray-400">{item.supplier_name}</span>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2 flex-shrink-0">
              <span className={`text-sm font-semibold tabular-nums ${isPagar ? 'text-gray-800' : 'text-emerald-600'}`}>
                {fmt(item.amount)}
              </span>
              {isPagar && onPay && (
                <button
                  onClick={() => onPay(item.id)}
                  className="hidden group-hover:inline-flex text-xs px-2.5 py-1 rounded-md border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors"
                >
                  Pagar
                </button>
              )}
              {!isPagar && onReceive && (
                <button
                  onClick={() => onReceive(item.id)}
                  className="hidden group-hover:inline-flex text-xs px-2.5 py-1 rounded-md border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors"
                >
                  Baixar
                </button>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
