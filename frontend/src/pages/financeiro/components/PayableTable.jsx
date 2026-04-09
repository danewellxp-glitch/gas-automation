export default function PayableTable({ payables, onPay, fmt }) {
  const today = new Date().toISOString().split('T')[0]

  const statusColor = (status, due) => {
    if (status === 'pago') return 'bg-emerald-50 text-emerald-700 border-emerald-200'
    if (status === 'cancelado') return 'bg-gray-100 text-gray-500 border-gray-200'
    if (due < today) return 'bg-red-50 text-red-600 border-red-200'
    const daysUntil = Math.ceil((new Date(due) - new Date()) / 86400000)
    if (daysUntil <= 3) return 'bg-orange-50 text-orange-700 border-orange-200'
    return 'bg-amber-50 text-amber-700 border-amber-200'
  }

  const statusLabel = (status, due) => {
    if (status === 'pago') return 'Pago'
    if (status === 'cancelado') return 'Cancelado'
    if (due < today) return 'Vencido'
    const daysUntil = Math.ceil((new Date(due) - new Date()) / 86400000)
    if (daysUntil <= 3) return `Vence em ${daysUntil}d`
    return 'Pendente'
  }

  const CATEGORY_LABELS = {
    compra_gas: 'Compra de Gás',
    combustivel: 'Combustível',
    manutencao_veiculo: 'Manutenção',
    salarios: 'Salários',
    comissao_entregador: 'Comissão',
    aluguel: 'Aluguel',
    energia_agua: 'Energia/Água',
    impostos: 'Impostos',
    marketing: 'Marketing',
    outras_despesas: 'Outras',
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-gray-500 border-b border-gray-200">
            <th className="text-left py-3 px-3 text-xs font-medium uppercase tracking-wide">Vencimento</th>
            <th className="text-left py-3 px-3 text-xs font-medium uppercase tracking-wide">Descrição</th>
            <th className="text-left py-3 px-3 text-xs font-medium uppercase tracking-wide">Categoria</th>
            <th className="text-right py-3 px-3 text-xs font-medium uppercase tracking-wide">Valor</th>
            <th className="text-center py-3 px-3 text-xs font-medium uppercase tracking-wide">Status</th>
            <th className="text-center py-3 px-3 text-xs font-medium uppercase tracking-wide">Ação</th>
          </tr>
        </thead>
        <tbody>
          {payables.length === 0 ? (
            <tr>
              <td colSpan={6} className="text-center text-gray-400 py-10">
                Nenhuma conta a pagar
              </td>
            </tr>
          ) : payables.map(p => (
            <tr key={p.id} className="border-b border-gray-100 hover:bg-gray-50">
              <td className="py-3 px-3 text-gray-600">
                {new Date(p.due_date).toLocaleDateString('pt-BR')}
              </td>
              <td className="py-3 px-3 text-gray-900 font-medium truncate max-w-xs">{p.description}</td>
              <td className="py-3 px-3 text-gray-500 text-xs">
                {CATEGORY_LABELS[p.category] || p.category}
              </td>
              <td className="py-3 px-3 text-right text-red-500 font-semibold">{fmt(p.amount)}</td>
              <td className="py-3 px-3 text-center">
                <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${statusColor(p.status, p.due_date)}`}>
                  {statusLabel(p.status, p.due_date)}
                </span>
              </td>
              <td className="py-3 px-3 text-center">
                {p.status === 'pendente' && (
                  <button
                    onClick={() => onPay(p.id)}
                    className="text-xs bg-blue-600 hover:bg-blue-700 text-white px-2.5 py-1 rounded-md transition-colors"
                  >
                    Pagar
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
