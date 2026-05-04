import { Truck, CheckCircle2, Clock, PackageCheck } from 'lucide-react'

const STATUS_META = {
  em_rota: {
    label: 'Em Rota',
    Icon: Truck,
    classes: 'bg-amber-50 text-amber-800 border-amber-200',
  },
  encerrada: {
    label: 'Encerrada',
    Icon: CheckCircle2,
    classes: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  },
}

function StatusBadge({ status }) {
  const meta = STATUS_META[status] || {
    label: status || 'Pendente',
    Icon: Clock,
    classes: 'bg-slate-50 text-slate-600 border-slate-200',
  }
  const { Icon } = meta
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-medium ${meta.classes}`}
      role="status"
      aria-label={`Status da carga: ${meta.label}`}
    >
      <Icon className="w-3.5 h-3.5" strokeWidth={2} aria-hidden="true" />
      {meta.label}
    </span>
  )
}

function formatDriverName(load, driverMap) {
  const id = load.driver_id
  if (id && driverMap[id]?.name) return driverMap[id].name
  if (load.driver_name) return load.driver_name
  if (id) return `Motorista ${String(id).slice(0, 8)}`
  return 'Motorista não atribuído'
}

function formatLoadDate(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString('pt-BR')
}

export default function VehicleLoadTable({ loads = [], products = [], drivers = [], onClose, onOpenLoad }) {
  const productMap = {}
  products.forEach(p => { productMap[p.id] = p })
  const driverMap = {}
  drivers.forEach(d => { driverMap[d.id] = d })

  if (!loads.length) {
    return (
      <div
        className="flex flex-col items-center justify-center text-center py-10 px-4 rounded-xl border border-dashed border-slate-300 bg-slate-50"
        role="status"
      >
        <div className="w-14 h-14 rounded-full bg-white border border-slate-200 flex items-center justify-center mb-3">
          <Truck className="w-7 h-7 text-slate-400" strokeWidth={2} aria-hidden="true" />
        </div>
        <h3 className="text-base font-semibold text-slate-900">Nenhuma carga aberta</h3>
        <p className="text-sm text-slate-600 mt-1 max-w-sm">
          Abra uma nova carga para começar a despachar entregas com este veículo.
        </p>
        {onOpenLoad && (
          <button
            type="button"
            onClick={onOpenLoad}
            className="mt-4 inline-flex items-center gap-2 min-h-[48px] px-5 rounded-lg bg-primary-600 hover:bg-primary-700 text-white text-sm font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
          >
            <Truck className="w-4 h-4" strokeWidth={2} aria-hidden="true" />
            Abrir Carga
          </button>
        )}
      </div>
    )
  }

  return (
    <div>
      {/* Mobile card layout (<768px) */}
      <ul className="md:hidden space-y-3" role="list">
        {loads.map(load => {
          const totalLoaded = (load.items || []).reduce((s, i) => s + (i.quantity_loaded || 0), 0)
          const totalDelivered = (load.items || []).reduce((s, i) => s + (i.quantity_delivered || 0), 0)
          return (
            <li
              key={load.id}
              className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm"
            >
              <div className="flex items-start justify-between gap-3 mb-3">
                <div>
                  <div className="text-sm font-semibold text-slate-900">
                    {formatDriverName(load, driverMap)}
                  </div>
                  <div className="text-xs text-slate-500 mt-0.5">
                    {formatLoadDate(load.load_date)}
                  </div>
                </div>
                <StatusBadge status={load.status} />
              </div>

              <div className="space-y-1.5 mb-3">
                {(load.items || []).map(item => (
                  <div key={item.id} className="flex items-center justify-between text-sm">
                    <span className="text-slate-500">
                      {productMap[item.stock_product_id]?.code || '?'}
                    </span>
                    <span className="text-slate-900 font-medium">
                      {item.quantity_loaded}
                      {item.quantity_delivered > 0 && (
                        <span className="text-emerald-700 ml-1.5 font-normal">
                          (-{item.quantity_delivered} entregues)
                        </span>
                      )}
                    </span>
                  </div>
                ))}
              </div>

              <div className="flex items-center justify-between gap-3 pt-3 border-t border-slate-100">
                <span className="inline-flex items-center gap-1.5 text-xs text-slate-600">
                  <PackageCheck className="w-3.5 h-3.5" strokeWidth={2} aria-hidden="true" />
                  {totalDelivered}/{totalLoaded} entregues
                </span>
                {load.status !== 'encerrada' && (
                  <button
                    type="button"
                    onClick={() => onClose && onClose(load)}
                    className="inline-flex items-center justify-center min-h-[48px] px-4 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2"
                  >
                    Encerrar
                  </button>
                )}
              </div>
            </li>
          )
        })}
      </ul>

      {/* Desktop/tablet table layout (>=768px) */}
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-slate-500 border-b border-slate-200">
              <th className="text-left py-2 px-3 font-medium">Entregador</th>
              <th className="text-left py-2 px-3 font-medium">Data</th>
              <th className="text-left py-2 px-3 font-medium">Produtos Carregados</th>
              <th className="text-center py-2 px-3 font-medium">Status</th>
              <th className="text-center py-2 px-3 font-medium">Ação</th>
            </tr>
          </thead>
          <tbody>
            {loads.map(load => {
              const totalLoaded = (load.items || []).reduce((s, i) => s + (i.quantity_loaded || 0), 0)
              const totalDelivered = (load.items || []).reduce((s, i) => s + (i.quantity_delivered || 0), 0)
              return (
                <tr key={load.id} className="border-b border-slate-100 hover:bg-slate-50/60 transition-colors">
                  <td className="py-3 px-3 text-slate-900 font-medium">
                    {formatDriverName(load, driverMap)}
                  </td>
                  <td className="py-3 px-3 text-slate-600">
                    {formatLoadDate(load.load_date)}
                  </td>
                  <td className="py-3 px-3">
                    <div className="space-y-1">
                      {(load.items || []).map(item => (
                        <div key={item.id} className="text-sm">
                          <span className="text-slate-500">
                            {productMap[item.stock_product_id]?.code || '?'}:
                          </span>
                          <span className="text-slate-900 ml-1 font-medium">{item.quantity_loaded}</span>
                          {item.quantity_delivered > 0 && (
                            <span className="text-emerald-700 ml-1">(-{item.quantity_delivered} entregues)</span>
                          )}
                        </div>
                      ))}
                      <div className="text-xs text-slate-500 pt-0.5">
                        Total: {totalDelivered}/{totalLoaded} entregues
                      </div>
                    </div>
                  </td>
                  <td className="py-3 px-3 text-center">
                    <StatusBadge status={load.status} />
                  </td>
                  <td className="py-3 px-3 text-center">
                    {load.status !== 'encerrada' && (
                      <button
                        type="button"
                        onClick={() => onClose && onClose(load)}
                        className="inline-flex items-center justify-center min-h-[48px] px-4 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2"
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
    </div>
  )
}
