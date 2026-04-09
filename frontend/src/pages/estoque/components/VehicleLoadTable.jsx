export default function VehicleLoadTable({ loads, products, onClose }) {
  const productMap = {}
  products.forEach(p => { productMap[p.id] = p })

  const statusColor = (status) => {
    if (status === 'em_rota') return 'bg-yellow-900/50 text-yellow-400'
    if (status === 'encerrada') return 'bg-green-900/50 text-green-400'
    return 'bg-gray-700 text-gray-400'
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-gray-400 border-b border-gray-700">
            <th className="text-left py-2 px-3">Driver</th>
            <th className="text-left py-2 px-3">Data</th>
            <th className="text-left py-2 px-3">Produtos Carregados</th>
            <th className="text-center py-2 px-3">Status</th>
            <th className="text-center py-2 px-3">Ação</th>
          </tr>
        </thead>
        <tbody>
          {loads.map(load => {
            const totalLoaded = (load.items || []).reduce((s, i) => s + i.quantity_loaded, 0)
            const totalDelivered = (load.items || []).reduce((s, i) => s + i.quantity_delivered, 0)
            return (
              <tr key={load.id} className="border-b border-gray-700/50">
                <td className="py-3 px-3 text-white font-medium">
                  {load.driver_id?.toString().slice(0, 8)}...
                </td>
                <td className="py-3 px-3 text-gray-300">
                  {new Date(load.load_date).toLocaleDateString('pt-BR')}
                </td>
                <td className="py-3 px-3">
                  <div className="space-y-1">
                    {(load.items || []).map(item => (
                      <div key={item.id} className="text-sm">
                        <span className="text-gray-400">
                          {productMap[item.stock_product_id]?.code || '?'}:
                        </span>
                        <span className="text-white ml-1">{item.quantity_loaded}</span>
                        {item.quantity_delivered > 0 && (
                          <span className="text-green-400 ml-1">(-{item.quantity_delivered} entregues)</span>
                        )}
                      </div>
                    ))}
                  </div>
                </td>
                <td className="py-3 px-3 text-center">
                  <span className={`text-xs px-2 py-1 rounded-full ${statusColor(load.status)}`}>
                    {load.status === 'em_rota' ? 'Em Rota' : load.status}
                  </span>
                </td>
                <td className="py-3 px-3 text-center">
                  {load.status !== 'encerrada' && (
                    <button
                      onClick={() => onClose(load)}
                      className="bg-green-700 hover:bg-green-600 text-white px-4 py-2 rounded-lg font-medium text-sm"
                    >
                      Encerrar
                    </button>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
