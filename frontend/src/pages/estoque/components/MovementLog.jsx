import { useMemo, useState } from 'react'
import {
  CircleDollarSign,
  Inbox,
  MinusCircle,
  PackagePlus,
  PlusCircle,
  RotateCcw,
  Truck,
  Undo2,
  XCircle,
} from 'lucide-react'

const TYPE_META = {
  compra: { label: 'Compra', color: 'text-emerald-600', Icon: PackagePlus },
  venda: { label: 'Venda', color: 'text-sky-600', Icon: CircleDollarSign },
  carga_veiculo: { label: 'Carga Veículo', color: 'text-amber-600', Icon: Truck },
  retorno_veiculo: { label: 'Retorno Veículo', color: 'text-violet-600', Icon: Undo2 },
  devolucao_cliente: { label: 'Devolução', color: 'text-cyan-600', Icon: RotateCcw },
  ajuste_entrada: { label: 'Ajuste +', color: 'text-emerald-600', Icon: PlusCircle },
  ajuste_saida: { label: 'Ajuste -', color: 'text-orange-600', Icon: MinusCircle },
  perda: { label: 'Perda', color: 'text-rose-600', Icon: XCircle },
}

const FILTERS = [
  { id: 'todos', label: 'Todos', types: null },
  { id: 'compras', label: 'Compras', types: ['compra'] },
  { id: 'vendas', label: 'Vendas', types: ['venda'] },
  { id: 'cargas', label: 'Cargas', types: ['carga_veiculo', 'retorno_veiculo'] },
  { id: 'ajustes', label: 'Ajustes', types: ['ajuste_entrada', 'ajuste_saida', 'devolucao_cliente', 'perda'] },
]

export default function MovementLog({ movements, products }) {
  const [activeFilter, setActiveFilter] = useState('todos')

  const productMap = useMemo(() => {
    const map = {}
    products.forEach((p) => { map[p.id] = p })
    return map
  }, [products])

  const filtered = useMemo(() => {
    const filter = FILTERS.find((f) => f.id === activeFilter) || FILTERS[0]
    if (!filter.types) return movements
    const allowed = new Set(filter.types)
    return movements.filter((m) => allowed.has(m.movement_type))
  }, [movements, activeFilter])

  const chips = (
    <div className="flex flex-wrap gap-2 mb-4" role="tablist" aria-label="Filtrar movimentações">
      {FILTERS.map((f) => {
        const active = f.id === activeFilter
        return (
          <button
            key={f.id}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => setActiveFilter(f.id)}
            className={`min-h-[36px] px-3.5 rounded-full text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 ${
              active
                ? 'bg-primary-500 text-white'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
            }`}
          >
            {f.label}
          </button>
        )
      })}
    </div>
  )

  if (movements.length === 0) {
    return (
      <div>
        {chips}
        <div className="py-12 text-center">
          <Inbox className="mx-auto text-slate-300" size={40} aria-hidden="true" />
          <p className="text-sm text-slate-600 mt-2">Nenhuma movimentação registrada hoje</p>
          <p className="text-xs text-slate-500 mt-1">As movimentações aparecerão aqui ao longo do dia.</p>
        </div>
      </div>
    )
  }

  if (filtered.length === 0) {
    return (
      <div>
        {chips}
        <div className="py-12 text-center">
          <Inbox className="mx-auto text-slate-300" size={40} aria-hidden="true" />
          <p className="text-sm text-slate-600 mt-2">Nenhuma movimentação neste filtro</p>
          <p className="text-xs text-slate-500 mt-1">Tente outro filtro acima.</p>
        </div>
      </div>
    )
  }

  return (
    <div>
      {chips}
      <div className="overflow-x-auto">
        <table className="w-full text-sm" aria-label="Movimentações do dia">
          <thead>
            <tr className="text-slate-600 border-b border-slate-200">
              <th scope="col" className="text-left py-3 px-4 font-semibold">Horário</th>
              <th scope="col" className="text-left py-3 px-4 font-semibold">Tipo</th>
              <th scope="col" className="text-left py-3 px-4 font-semibold">Produto</th>
              <th scope="col" className="text-center py-3 px-4 font-semibold">Quantidade</th>
              <th scope="col" className="text-left py-3 px-4 font-semibold">Obs</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((m) => {
              const meta = TYPE_META[m.movement_type] || {
                label: m.movement_type,
                color: 'text-slate-600',
                Icon: Inbox,
              }
              const { Icon } = meta
              const product = productMap[m.stock_product_id]
              const isEntrada = m.direction === 'entrada'
              return (
                <tr key={m.id} className="border-b border-slate-100 hover:bg-slate-50">
                  <td className="py-3 px-4 text-slate-600 text-xs">
                    {new Date(m.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                  </td>
                  <td className="py-3 px-4">
                    <span className={`inline-flex items-center gap-1.5 ${meta.color}`}>
                      <Icon size={16} aria-hidden="true" />
                      <span className="text-sm">{meta.label}</span>
                    </span>
                  </td>
                  <td className="py-3 px-4 text-slate-900">
                    {product?.code || m.stock_product_id.toString().slice(0, 8)}
                  </td>
                  <td className="py-3 px-4 text-center">
                    <span className={`font-bold text-base ${isEntrada ? 'text-emerald-700' : 'text-rose-700'}`}>
                      {isEntrada ? '+' : '-'}{m.quantity}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-slate-600 text-xs truncate max-w-xs">
                    {m.notes || '-'}
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
