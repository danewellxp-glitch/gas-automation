import api from '../../../api/client'
import { FINANCEIRO } from '../../../api/endpoints'

const CATEGORY_LABELS = {
  venda_gas: 'Venda de Gás',
  deposito_vasilhame: 'Depósito Vasilhame',
  outras_receitas: 'Outras Receitas',
  compra_gas: 'Compra de Gás',
  combustivel: 'Combustível',
  manutencao_veiculo: 'Manutenção Veículo',
  salarios: 'Salários',
  comissao_entregador: 'Comissão Entregador',
  aluguel: 'Aluguel',
  energia_agua: 'Energia/Água',
  impostos: 'Impostos',
  marketing: 'Marketing',
  outras_despesas: 'Outras Despesas',
  transferencia: 'Transferência',
}

export default function TransactionTable({ transactions, total, page, onPageChange, fmt, onRefresh }) {
  const handleDelete = async (id) => {
    if (!confirm('Excluir este lançamento?')) return
    await api.delete(FINANCEIRO.TRANSACTION(id))
    onRefresh()
  }

  const handlePay = async (id) => {
    await api.post(FINANCEIRO.TRANSACTION_PAY(id))
    onRefresh()
  }

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-500 border-b border-gray-200">
              <th className="text-left py-3 px-3 text-xs font-medium uppercase tracking-wide">Data</th>
              <th className="text-left py-3 px-3 text-xs font-medium uppercase tracking-wide">Descrição</th>
              <th className="text-left py-3 px-3 text-xs font-medium uppercase tracking-wide">Categoria</th>
              <th className="text-right py-3 px-3 text-xs font-medium uppercase tracking-wide">Valor</th>
              <th className="text-center py-3 px-3 text-xs font-medium uppercase tracking-wide">Status</th>
              <th className="text-center py-3 px-3 text-xs font-medium uppercase tracking-wide">Ações</th>
            </tr>
          </thead>
          <tbody>
            {transactions.length === 0 ? (
              <tr>
                <td colSpan={6} className="text-center text-gray-400 py-10">
                  Nenhum lançamento encontrado
                </td>
              </tr>
            ) : transactions.map(tx => (
              <tr key={tx.id} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="py-3 px-3 text-gray-600">
                  {new Date(tx.reference_date).toLocaleDateString('pt-BR')}
                </td>
                <td className="py-3 px-3 text-gray-900 font-medium max-w-xs truncate">{tx.description}</td>
                <td className="py-3 px-3 text-gray-500 text-xs">
                  {CATEGORY_LABELS[tx.category] || tx.category}
                </td>
                <td className={`py-3 px-3 text-right font-semibold ${
                  tx.direction === 'entrada' ? 'text-emerald-600' : 'text-red-500'
                }`}>
                  {tx.direction === 'entrada' ? '+' : '-'}{fmt(tx.amount)}
                </td>
                <td className="py-3 px-3 text-center">
                  <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${
                    tx.is_paid
                      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                      : 'bg-amber-50 text-amber-700 border-amber-200'
                  }`}>
                    {tx.is_paid ? 'Pago' : 'Pendente'}
                  </span>
                </td>
                <td className="py-3 px-3 text-center">
                  <div className="flex items-center justify-center gap-2">
                    {!tx.is_paid && (
                      <button
                        onClick={() => handlePay(tx.id)}
                        className="text-xs bg-emerald-600 hover:bg-emerald-700 text-white px-2.5 py-1 rounded-md transition-colors"
                      >
                        Pagar
                      </button>
                    )}
                    <button
                      onClick={() => handleDelete(tx.id)}
                      className="text-xs border border-red-200 text-red-600 hover:bg-red-50 px-2.5 py-1 rounded-md transition-colors"
                    >
                      Excluir
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {total > 50 && (
        <div className="flex items-center justify-between mt-4 text-sm text-gray-500">
          <span>Total: {total} lançamentos</span>
          <div className="flex gap-2">
            <button
              disabled={page <= 1}
              onClick={() => onPageChange(page - 1)}
              className="px-3 py-1 border border-gray-200 rounded-md bg-white hover:bg-gray-50 disabled:opacity-40 transition-colors"
            >
              Anterior
            </button>
            <span className="px-3 py-1 text-gray-600">Página {page}</span>
            <button
              disabled={page * 50 >= total}
              onClick={() => onPageChange(page + 1)}
              className="px-3 py-1 border border-gray-200 rounded-md bg-white hover:bg-gray-50 disabled:opacity-40 transition-colors"
            >
              Próxima
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
