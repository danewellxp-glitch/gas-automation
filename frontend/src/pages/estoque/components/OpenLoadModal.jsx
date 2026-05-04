import { useState } from 'react'
import { AlertCircle } from 'lucide-react'
import api from '../../../api/client'
import { ESTOQUE } from '../../../api/endpoints'

export default function OpenLoadModal({ drivers, products, onClose, onCreated }) {
  const today = new Date().toISOString().split('T')[0]
  const [driverId, setDriverId] = useState('')
  const [loadDate, setLoadDate] = useState(today)
  const [items, setItems] = useState(products.map(p => ({ stock_product_id: p.id, quantity_loaded: 0, code: p.code, name: p.name })))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const updateQty = (idx, val) => {
    setItems(prev => prev.map((item, i) => i === idx ? { ...item, quantity_loaded: parseInt(val) || 0 } : item))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (!driverId) { setError('Selecione um entregador'); return }
    const selectedItems = items.filter(i => i.quantity_loaded > 0)
    if (selectedItems.length === 0) { setError('Informe pelo menos um produto'); return }

    setSaving(true)
    try {
      await api.post(ESTOQUE.VEHICLE_LOADS, {
        driver_id: driverId,
        load_date: loadDate,
        items: selectedItems.map(i => ({
          stock_product_id: i.stock_product_id,
          quantity_loaded: i.quantity_loaded,
        })),
      })
      onCreated()
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao abrir carga')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-xl border border-gray-600 w-full max-w-lg p-6">
        <h2 className="text-2xl font-bold mb-5">Abrir Carga do Dia</h2>

        {error && (
          <div role="alert" className="flex items-start gap-2 bg-rose-50 text-rose-700 border border-rose-200 px-3 py-2 rounded-lg text-sm mb-4">
            <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" strokeWidth={1.75} aria-hidden="true" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-gray-400 text-sm block mb-1">Entregador</label>
            <select
              required
              value={driverId}
              onChange={e => setDriverId(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-3 text-white text-lg"
            >
              <option value="">Selecionar entregador</option>
              {drivers.map(d => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-gray-400 text-sm block mb-1">Data da Carga</label>
            <input
              type="date"
              required
              value={loadDate}
              onChange={e => setLoadDate(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-3 text-white text-lg"
            />
          </div>

          <div>
            <label className="text-gray-400 text-sm block mb-2">Quantidade por Produto</label>
            <div className="space-y-3">
              {items.map((item, idx) => (
                <div key={item.stock_product_id} className="flex items-center gap-3">
                  <div className="flex-1">
                    <div className="text-white font-bold">{item.code}</div>
                    <div className="text-gray-400 text-sm">{item.name}</div>
                  </div>
                  <input
                    type="number"
                    min="0"
                    value={item.quantity_loaded}
                    onChange={e => updateQty(idx, e.target.value)}
                    className="w-24 bg-gray-700 border border-gray-600 rounded px-3 py-3 text-white text-xl text-center"
                  />
                </div>
              ))}
            </div>
          </div>

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="flex-1 py-4 bg-gray-700 rounded-xl text-lg">
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving}
              className="flex-1 py-4 bg-blue-600 hover:bg-blue-500 rounded-xl text-lg font-bold disabled:opacity-50"
            >
              {saving ? 'Abrindo...' : 'ABRIR CARGA'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
