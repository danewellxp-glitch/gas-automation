import { useEffect, useRef, useState } from 'react'

const CATEGORY_LABEL = {
  venda_gas:           'Venda de Gás',
  deposito_vasilhame:  'Dep. Vasilhame',
  outras_receitas:     'Outras Receitas',
  compra_gas:          'Compra de Gás',
  combustivel:         'Combustível',
  manutencao_veiculo:  'Manutenção',
  salarios:            'Salários',
  comissao_entregador: 'Comissão',
  aluguel:             'Aluguel',
  energia_agua:        'Energia / Água',
  impostos:            'Impostos',
  marketing:           'Marketing',
  outras_despesas:     'Outras Despesas',
}

function fmt(val) {
  return parseFloat(val || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

function fmtDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
}

function Avatar({ text }) {
  return (
    <div className="w-9 h-9 rounded-full bg-gray-100 border border-gray-200 flex items-center justify-center text-xs font-semibold text-gray-600 flex-shrink-0">
      {text}
    </div>
  )
}

export default function RecentTransactions({ transactions = [], newTxFromWs = null }) {
  const [highlightedId, setHighlightedId] = useState(null)
  const seenIds = useRef(new Set())

  useEffect(() => {
    if (!newTxFromWs?.id || seenIds.current.has(newTxFromWs.id)) return
    seenIds.current.add(newTxFromWs.id)
    setHighlightedId(newTxFromWs.id)
    const t = setTimeout(() => setHighlightedId(null), 1800)
    return () => clearTimeout(t)
  }, [newTxFromWs])

  if (!transactions.length) {
    return (
      <div className="py-12 text-center text-sm text-gray-400">
        Nenhuma transação registrada
      </div>
    )
  }

  return (
    <div className="space-y-0">
      {transactions.slice(0, 8).map((tx, i) => {
        const isEntrada = tx.direction === 'entrada' || tx.type === 'receita'
        const catLabel = CATEGORY_LABEL[tx.category] || tx.category || '—'
        const initials = catLabel.slice(0, 2).toUpperCase()
        const isHighlighted = tx.id === highlightedId

        return (
          <div
            key={tx.id || i}
            style={{ animationDelay: `${Math.min(i, 8) * 50}ms` }}
            className={`flex items-center gap-3 py-3 border-b border-gray-100 last:border-0 animate-fade-in-up ${
              isHighlighted ? 'animate-highlight-fade' : ''
            }`}
          >
            <Avatar text={initials} />

            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">
                {tx.description || catLabel}
              </p>
              <p className="text-xs text-gray-400 mt-0.5">
                {catLabel} · {fmtDate(tx.reference_date || tx.created_at)}
                {!tx.is_paid && (
                  <span className="ml-2 text-amber-600">pendente</span>
                )}
              </p>
            </div>

            <span className={`text-sm font-semibold tabular-nums ${isEntrada ? 'text-emerald-600' : 'text-gray-700'}`}>
              {isEntrada ? '+' : '-'}{fmt(tx.amount)}
            </span>
          </div>
        )
      })}
    </div>
  )
}
