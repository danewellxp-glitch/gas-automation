import { useState } from 'react'
import api from '../../../api/client'
import { FINANCEIRO } from '../../../api/endpoints'

const CATEGORIES = {
  receita: [
    { value: 'venda_gas', label: 'Venda de Gás' },
    { value: 'deposito_vasilhame', label: 'Depósito Vasilhame' },
    { value: 'outras_receitas', label: 'Outras Receitas' },
  ],
  despesa: [
    { value: 'compra_gas', label: 'Compra de Gás' },
    { value: 'combustivel', label: 'Combustível' },
    { value: 'manutencao_veiculo', label: 'Manutenção Veículo' },
    { value: 'salarios', label: 'Salários' },
    { value: 'comissao_entregador', label: 'Comissão Entregador' },
    { value: 'aluguel', label: 'Aluguel' },
    { value: 'energia_agua', label: 'Energia/Água' },
    { value: 'impostos', label: 'Impostos' },
    { value: 'marketing', label: 'Marketing' },
    { value: 'outras_despesas', label: 'Outras Despesas' },
  ],
}

export default function TransactionModal({ accounts, onClose, onCreated }) {
  const today = new Date().toISOString().split('T')[0]
  const [form, setForm] = useState({
    type: 'receita',
    category: 'venda_gas',
    description: '',
    amount: '',
    reference_date: today,
    due_date: '',
    account_id: accounts[0]?.id || '',
    is_paid: true,
    notes: '',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const handleTypeChange = (type) => {
    setForm(f => ({
      ...f,
      type,
      category: CATEGORIES[type][0].value,
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (!form.amount || parseFloat(form.amount) <= 0) {
      setError('Informe um valor válido')
      return
    }
    if (!form.account_id) {
      setError('Selecione uma conta')
      return
    }
    setSaving(true)
    try {
      const payload = {
        ...form,
        amount: parseFloat(form.amount),
        direction: form.type === 'receita' ? 'entrada' : 'saida',
        due_date: form.due_date || null,
        notes: form.notes || null,
      }
      await api.post(FINANCEIRO.TRANSACTIONS, payload)
      onCreated()
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao salvar lançamento')
    } finally {
      setSaving(false)
    }
  }

  const inputClass = "w-full bg-white border border-gray-200 rounded-lg px-3 py-2 text-gray-900 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900/10 focus:border-gray-400 transition-colors"
  const labelClass = "text-xs font-medium text-gray-600 block mb-1.5"

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl border border-gray-200 w-full max-w-md shadow-xl">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <h2 className="text-base font-semibold text-gray-900">Novo Lançamento</h2>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors text-lg leading-none"
          >
            &times;
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-600 text-sm px-3 py-2 rounded-lg">
              {error}
            </div>
          )}

          {/* Tipo */}
          <div>
            <label className={labelClass}>Tipo</label>
            <div className="flex gap-2">
              {['receita', 'despesa'].map(t => (
                <button
                  key={t}
                  type="button"
                  onClick={() => handleTypeChange(t)}
                  className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors border ${
                    form.type === t
                      ? t === 'receita'
                        ? 'bg-emerald-600 text-white border-emerald-600'
                        : 'bg-red-500 text-white border-red-500'
                      : 'bg-white text-gray-500 border-gray-200 hover:border-gray-300'
                  }`}
                >
                  {t === 'receita' ? 'Receita' : 'Despesa'}
                </button>
              ))}
            </div>
          </div>

          {/* Categoria */}
          <div>
            <label className={labelClass}>Categoria</label>
            <select
              value={form.category}
              onChange={e => setForm(f => ({ ...f, category: e.target.value }))}
              className={inputClass}
            >
              {(CATEGORIES[form.type] || []).map(c => (
                <option key={c.value} value={c.value}>{c.label}</option>
              ))}
            </select>
          </div>

          {/* Descrição */}
          <div>
            <label className={labelClass}>Descrição</label>
            <input
              type="text"
              required
              value={form.description}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              className={inputClass}
              placeholder="Ex: Pagamento fornecedor XYZ"
            />
          </div>

          {/* Valor */}
          <div>
            <label className={labelClass}>Valor (R$)</label>
            <input
              type="number"
              required
              min="0.01"
              step="0.01"
              value={form.amount}
              onChange={e => setForm(f => ({ ...f, amount: e.target.value }))}
              className={inputClass}
              placeholder="0,00"
            />
          </div>

          {/* Datas */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass}>Data Competência</label>
              <input
                type="date"
                required
                value={form.reference_date}
                onChange={e => setForm(f => ({ ...f, reference_date: e.target.value }))}
                className={inputClass}
              />
            </div>
            <div>
              <label className={labelClass}>Vencimento</label>
              <input
                type="date"
                value={form.due_date}
                onChange={e => setForm(f => ({ ...f, due_date: e.target.value }))}
                className={inputClass}
              />
            </div>
          </div>

          {/* Conta */}
          <div>
            <label className={labelClass}>Conta</label>
            <select
              value={form.account_id}
              onChange={e => setForm(f => ({ ...f, account_id: e.target.value }))}
              className={inputClass}
            >
              {accounts.map(a => (
                <option key={a.id} value={a.id}>{a.name}</option>
              ))}
            </select>
          </div>

          {/* Status */}
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="is_paid"
              checked={form.is_paid}
              onChange={e => setForm(f => ({ ...f, is_paid: e.target.checked }))}
              className="rounded border-gray-300"
            />
            <label htmlFor="is_paid" className="text-sm text-gray-700">Já pago/recebido</label>
          </div>

          {/* Observações */}
          <div>
            <label className={labelClass}>Observações</label>
            <textarea
              value={form.notes}
              onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
              rows={2}
              className={`${inputClass} resize-none`}
            />
          </div>

          <div className="flex gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2.5 border border-gray-200 hover:bg-gray-50 text-gray-700 rounded-lg text-sm font-medium transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving}
              className="flex-1 py-2.5 bg-gray-900 hover:bg-gray-800 text-white rounded-lg text-sm font-medium disabled:opacity-50 transition-colors"
            >
              {saving ? 'Salvando...' : 'Salvar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
