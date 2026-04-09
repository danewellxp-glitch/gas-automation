export default function KPICards({ kpis, fmt }) {
  const profit = parseFloat(kpis.revenue_month) - parseFloat(kpis.expense_month)
  const profitPositive = profit >= 0

  const cards = [
    {
      label: 'Saldo Total',
      value: fmt(kpis.total_balance),
      color: 'text-blue-400',
      bg: 'bg-blue-900/30 border-blue-800',
      icon: '💰',
    },
    {
      label: 'Receita do Mês',
      value: fmt(kpis.revenue_month),
      color: 'text-green-400',
      bg: 'bg-green-900/30 border-green-800',
      icon: '📈',
    },
    {
      label: 'Despesa do Mês',
      value: fmt(kpis.expense_month),
      color: 'text-red-400',
      bg: 'bg-red-900/30 border-red-800',
      icon: '📉',
    },
    {
      label: 'Lucro / Prejuízo',
      value: fmt(profit),
      color: profitPositive ? 'text-emerald-400' : 'text-red-400',
      bg: profitPositive ? 'bg-emerald-900/30 border-emerald-800' : 'bg-red-900/30 border-red-800',
      icon: profitPositive ? '✅' : '⚠️',
    },
    {
      label: 'A Receber Vencido',
      value: kpis.overdue_receivables,
      suffix: ' contas',
      color: kpis.overdue_receivables > 0 ? 'text-red-400' : 'text-gray-400',
      bg: kpis.overdue_receivables > 0 ? 'bg-red-900/30 border-red-800' : 'bg-gray-800 border-gray-700',
      icon: '🔴',
      isCount: true,
    },
    {
      label: 'A Pagar Vencido',
      value: kpis.overdue_payables,
      suffix: ' contas',
      color: kpis.overdue_payables > 0 ? 'text-red-400' : 'text-gray-400',
      bg: kpis.overdue_payables > 0 ? 'bg-red-900/30 border-red-800' : 'bg-gray-800 border-gray-700',
      icon: '🔴',
      isCount: true,
    },
  ]

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
      {cards.map((card, i) => (
        <div key={i} className={`rounded-xl border p-4 ${card.bg}`}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-gray-400">{card.label}</span>
            <span className="text-lg">{card.icon}</span>
          </div>
          <div className={`text-xl font-bold ${card.color}`}>
            {card.isCount ? `${card.value}${card.suffix}` : card.value}
          </div>
        </div>
      ))}
    </div>
  )
}
