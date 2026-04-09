import { useState, useEffect } from 'react'
import api from '../../../api/client'
import { ESTOQUE } from '../../../api/endpoints'

export default function PurchaseOrderForm({ products, onClose, onCreated }) {
  const today = new Date().toISOString().split('T')[0]
  const [suppliers, setSuppliers] = useState([])
  const [supplierId, setSupplierId] = useState('')
  const [orderDate, setOrderDate] = useState(today)
  const [items, setItems] = useState(products.map(p => ({
    stock_product_id: p.id, code: p.code, name: p.name,
    quantity_ordered: 0, unit_cost: parseFloat(p.cost_price) || 0,
  })))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get(ESTOQUE.SUPPLIERS).then(res => setSuppliers(res.data || []))
  }, [])

  const updateItem = (idx, field, val) => {
    setItems(prev => prev.map((item, i) =>
      i === idx ? { ...item, [field]: parseFloat(val) || 0 } : item
    ))
  }

  const selectedItems = items.filter(i => i.quantity_ordered > 0)
  const total = selectedItems.reduce((s, i) => s + (i.quantity_ordered * i.unit_cost), 0)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (!supplierId) { setError('Selecione um fornecedor'); return }
    if (selectedItems.length === 0) { setError('Informe pelo menos um produto'); return }
    setSaving(true)
    try {
      await api.post(ESTOQUE.PURCHASE_ORDERS, {
        supplier_id: supplierId,
        order_date: orderDate,
        items: selectedItems.map(i => ({
          stock_product_id: i.stock_product_id,
          quantity_ordered: i.quantity_ordered,
          unit_cost: i.unit_cost,
        })),
      })
      onCreated()
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao criar pedido')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-xl border border-gray-600 w-full max-w-lg p-6 overflow-y-auto max-h-screen">
        <h2 className="text-2xl font-bold mb-5">Registrar Compra de Fornecedor</h2>

        {error && (
          <div className="bg-red-900/50 border border-red-700 text-red-300 text-sm px-3 py-2 rounded mb-4">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-gray-400 text-sm block mb-1">Fornecedor</label>
            <select
              required
              value={supplierId}
              onChange={e => setSupplierId(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-3 text-white text-lg"
            >
              <option value="">Selecionar fornecedor</option>
              {suppliers.map(s => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
            {suppliers.length === 0 && (
              <p className="text-yellow-400 text-xs mt-1">Nenhum fornecedor cadastrado. Cadastre primeiro em Fornecedores.</p>
            )}
          </div>

          <div>
            <label className="text-gray-400 text-sm block mb-1">Data do Pedido</label>
            <input
              type="date"
              required
              value={orderDate}
              onChange={e => setOrderDate(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-3 text-white text-lg"
            />
          </div>

          <div>
            <label className="text-gray-400 text-sm block mb-2">Produtos</label>
            <div className="space-y-3">
              {items.map((item, idx) => (
                <div key={item.stock_product_id} className="bg-gray-700/50 rounded-lg p-3">
                  <div className="font-bold text-white mb-2">{item.code} — {item.name}</div>
                  <div className="flex gap-3">
                    <div className="flex-1">
                      <label className="text-xs text-gray-400 block mb-1">Qtd</label>
                      <input
                        type="number"
                        min="0"
                        value={item.quantity_ordered}
                        onChange={e => updateItem(idx, 'quantity_ordered', e.target.value)}
                        className="w-full bg-gray-700 border border-gray-600 rounded px-2 py-2 text-white text-center"
                      />
                    </div>
                    <div className="flex-1">
                      <label className="text-xs text-gray-400 block mb-1">Custo unit. (R$)</label>
                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        value={item.unit_cost}
                        onChange={e => updateItem(idx, 'unit_cost', e.target.value)}
                        className="w-full bg-gray-700 border border-gray-600 rounded px-2 py-2 text-white text-center"
                      />
                    </div>
                    <div className="flex-none text-center">
                      <label className="text-xs text-gray-400 block mb-1">Subtotal</label>
                      <div className="py-2 text-green-400 font-medium">
                        R${(item.quantity_ordered * item.unit_cost).toFixed(2)}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {selectedItems.length > 0 && (
            <div className="bg-gray-700 rounded-lg p-3 text-right">
              <span className="text-gray-400 text-sm">Total: </span>
              <span className="text-white font-bold text-xl">
                R${total.toFixed(2)}
              </span>
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="flex-1 py-4 bg-gray-700 rounded-xl text-lg">
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving}
              className="flex-1 py-4 bg-purple-600 hover:bg-purple-500 rounded-xl text-lg font-bold disabled:opacity-50"
            >
              {saving ? 'Salvando...' : 'REGISTRAR COMPRA'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
