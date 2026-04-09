export default function ReceivableTable({ receivables, onReceive, fmt }) {
  const today = new Date().toISOString().split('T')[0]

  const statusColor = (status, due) => {
    if (status === 'recebido') return 'bg-emerald-50 text-emerald-700 border-emerald-200'
    if (status === 'cancelado') return 'bg-gray-100 text-gray-500 border-gray-200'
    if (due < today) return 'bg-red-50 text-red-600 border-red-200'
    return 'bg-amber-50 text-amber-700 border-amber-200'
  }

  const statusLabel = (status, due) => {
    if (status === 'recebido') return 'Recebido'
    if (status === 'cancelado') return 'Cancelado'
    if (due < today) return 'Vencido'
    return 'Pendente'
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-gray-500 border-b border-gray-200">
            <th className="text-left py-3 px-3 text-xs font-medium uppercase tracking-wide">Vencimento</th>
            <th className="text-left py-3 px-3 text-xs font-medium uppercase tracking-wide">Descrição</th>
            <th className="text-right py-3 px-3 text-xs font-medium uppercase tracking-wide">Valor</th>
            <th className="text-center py-3 px-3 text-xs font-medium uppercase tracking-wide">Status</th>
            <th className="text-center py-3 px-3 text-xs font-medium uppercase tracking-wide">Ação</th>
          </tr>
        </thead>
        <tbody>
          {receivables.length === 0 ? (
            <tr>
              <td colSpan={5} className="text-center text-gray-400 py-10">
                Nenhuma conta a receber
              </td>
            </tr>
          ) : receivables.map(r => (
            <tr key={r.id} className="border-b border-gray-100 hover:bg-gray-50">
              <td className="py-3 px-3 text-gray-600">
                {new Date(r.due_date).toLocaleDateString('pt-BR')}
              </td>
              <td className="py-3 px-3 text-gray-900 font-medium truncate max-w-xs">{r.description}</td>
              <td className="py-3 px-3 text-right text-emerald-600 font-semibold">{fmt(r.amount)}</td>
              <td className="py-3 px-3 text-center">
                <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${statusColor(r.status, r.due_date)}`}>
                  {statusLabel(r.status, r.due_date)}
                </span>
              </td>
              <td className="py-3 px-3 text-center">
                {r.status === 'pendente' && (
                  <button
                    onClick={() => onReceive(r.id)}
                    className="text-xs bg-emerald-600 hover:bg-emerald-700 text-white px-2.5 py-1 rounded-md transition-colors"
                  >
                    Dar baixa
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
