const TYPE_LABELS = {
  compra: { label: 'Compra', color: 'text-green-400', icon: '📦' },
  venda: { label: 'Venda', color: 'text-blue-400', icon: '💰' },
  carga_veiculo: { label: 'Carga Veículo', color: 'text-yellow-400', icon: '🚛' },
  retorno_veiculo: { label: 'Retorno Veículo', color: 'text-purple-400', icon: '↩️' },
  devolucao_cliente: { label: 'Devolução', color: 'text-cyan-400', icon: '🔄' },
  ajuste_entrada: { label: 'Ajuste +', color: 'text-emerald-400', icon: '➕' },
  ajuste_saida: { label: 'Ajuste -', color: 'text-orange-400', icon: '➖' },
  perda: { label: 'Perda', color: 'text-red-400', icon: '❌' },
}

export default function MovementLog({ movements, products }) {
  const productMap = {}
  products.forEach(p => { productMap[p.id] = p })

  if (movements.length === 0) {
    return <div className="text-gray-500 text-center py-8">Nenhuma movimentação registrada hoje</div>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-gray-400 border-b border-gray-700">
            <th className="text-left py-2 px-3">Horário</th>
            <th className="text-left py-2 px-3">Tipo</th>
            <th className="text-left py-2 px-3">Produto</th>
            <th className="text-center py-2 px-3">Quantidade</th>
            <th className="text-left py-2 px-3">Obs</th>
          </tr>
        </thead>
        <tbody>
          {movements.map(m => {
            const meta = TYPE_LABELS[m.movement_type] || { label: m.movement_type, color: 'text-gray-400', icon: '•' }
            const product = productMap[m.stock_product_id]
            return (
              <tr key={m.id} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                <td className="py-2 px-3 text-gray-400 text-xs">
                  {new Date(m.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                </td>
                <td className="py-2 px-3">
                  <span className={`${meta.color} text-xs`}>
                    {meta.icon} {meta.label}
                  </span>
                </td>
                <td className="py-2 px-3 text-white">
                  {product?.code || m.stock_product_id.toString().slice(0, 8)}
                </td>
                <td className="py-2 px-3 text-center">
                  <span className={m.direction === 'entrada' ? 'text-green-400' : 'text-red-400'}>
                    {m.direction === 'entrada' ? '+' : '-'}{m.quantity}
                  </span>
                </td>
                <td className="py-2 px-3 text-gray-500 text-xs truncate max-w-xs">
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
