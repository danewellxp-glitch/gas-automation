import { History } from 'lucide-react'

const TYPE_LABELS = {
  compra: { label: 'Compra', color: 'text-green-700', icon: '📦' },
  venda: { label: 'Venda', color: 'text-blue-700', icon: '💰' },
  carga_veiculo: { label: 'Carga Veículo', color: 'text-amber-700', icon: '🚛' },
  retorno_veiculo: { label: 'Retorno Veículo', color: 'text-purple-700', icon: '↩️' },
  devolucao_cliente: { label: 'Devolução', color: 'text-cyan-700', icon: '🔄' },
  ajuste_entrada: { label: 'Ajuste +', color: 'text-emerald-700', icon: '➕' },
  ajuste_saida: { label: 'Ajuste -', color: 'text-orange-700', icon: '➖' },
  perda: { label: 'Perda', color: 'text-red-700', icon: '❌' },
}

export default function MovementLog({ movements, products }) {
  const productMap = {}
  products.forEach(p => { productMap[p.id] = p })

  if (movements.length === 0) {
    return (
      <div
        className="flex flex-col items-center justify-center text-center py-10 px-4 rounded-xl border border-dashed border-slate-300 bg-slate-50"
        role="status"
      >
        <div className="w-14 h-14 rounded-full bg-white border border-slate-200 flex items-center justify-center mb-3">
          <History className="w-7 h-7 text-slate-400" strokeWidth={2} aria-hidden="true" />
        </div>
        <h3 className="text-base font-semibold text-slate-900">Nenhuma movimentação hoje</h3>
        <p className="text-sm text-slate-600 mt-1 max-w-sm">
          Compras, vendas, cargas e ajustes aparecerão aqui assim que forem registrados.
        </p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-slate-500 border-b border-slate-200">
            <th className="text-left py-2 px-3">Horário</th>
            <th className="text-left py-2 px-3">Tipo</th>
            <th className="text-left py-2 px-3">Produto</th>
            <th className="text-center py-2 px-3">Quantidade</th>
            <th className="text-left py-2 px-3">Obs</th>
          </tr>
        </thead>
        <tbody>
          {movements.map(m => {
            const meta = TYPE_LABELS[m.movement_type] || { label: m.movement_type, color: 'text-slate-600', icon: '•' }
            const product = productMap[m.stock_product_id]
            return (
              <tr key={m.id} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="py-2 px-3 text-slate-500 text-xs">
                  {new Date(m.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                </td>
                <td className="py-2 px-3">
                  <span className={`${meta.color} text-xs`}>
                    {meta.icon} {meta.label}
                  </span>
                </td>
                <td className="py-2 px-3 text-slate-900">
                  {product?.code || m.stock_product_id.toString().slice(0, 8)}
                </td>
                <td className="py-2 px-3 text-center">
                  <span className={m.direction === 'entrada' ? 'text-emerald-700' : 'text-red-700'}>
                    {m.direction === 'entrada' ? '+' : '-'}{m.quantity}
                  </span>
                </td>
                <td className="py-2 px-3 text-slate-500 text-xs truncate max-w-xs">
                  {m.notes || '-'}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
