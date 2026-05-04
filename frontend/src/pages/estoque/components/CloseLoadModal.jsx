import { useState, useEffect } from 'react'
import { AlertCircle } from 'lucide-react'
import api from '../../../api/client'
import { ESTOQUE } from '../../../api/endpoints'

export default function CloseLoadModal({ loads, selectedLoad, products, onClose, onClosed }) {
  const [loadId, setLoadId] = useState(selectedLoad?.id || '')
  const [currentLoad, setCurrentLoad] = useState(selectedLoad)
  const [returnItems, setReturnItems] = useState([])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const productMap = {}
  products.forEach(p => { productMap[p.id] = p })

  useEffect(() => {
    if (selectedLoad) {
      setLoadId(selectedLoad.id)
      setCurrentLoad(selectedLoad)
      initReturnItems(selectedLoad)
    }
  }, [selectedLoad])

  const initReturnItems = (load) => {
    if (load?.items) {
      setReturnItems(load.items.map(i => ({
        stock_product_id: i.stock_product_id,
        quantity_loaded: i.quantity_loaded,
        // Preenchimento inteligente: assume que voltaram todos os não entregues como cheios
        cheios_retornados: i.quantity_loaded - i.quantity_delivered,
        vazios_retornados: 0,
        code: productMap[i.stock_product_id]?.code || '?',
      })))
    }
  }

  const handleLoadSelect = (id) => {
    setLoadId(id)
    const load = loads.find(l => l.id === id)
    if (load) {
      setCurrentLoad(load)
      initReturnItems(load)
    }
  }

  const updateItem = (idx, field, val) => {
    setReturnItems(prev => prev.map((item, i) => {
      if (i !== idx) return item
      const updated = { ...item, [field]: Math.max(0, parseInt(val) || 0) }
      // Cheios voltaram não pode ultrapassar o total carregado
      if (updated.cheios_retornados > item.quantity_loaded) {
        updated.cheios_retornados = item.quantity_loaded
      }
      return updated
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (!loadId) { setError('Selecione uma carga'); return }
    setSaving(true)
    try {
      await api.post(ESTOQUE.VEHICLE_LOAD_CLOSE(loadId), {
        returned_items: returnItems.map(i => ({
          stock_product_id: i.stock_product_id,
          // quantity_returned = apenas cheios que voltaram (não foram entregues)
          // Vazios voltaram = troca com cliente; não revertem a carga, só atualizam vasilhame_estoque
          quantity_returned: i.cheios_retornados,
          cheios_retornados: i.cheios_retornados,
          vazios_retornados: i.vazios_retornados,
        })),
      })
      onClosed()
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao encerrar carga')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-xl border border-gray-600 w-full max-w-xl p-6">
        <h2 className="text-2xl font-bold mb-5">Encerrar Carga do Dia</h2>

        {error && (
          <div role="alert" className="flex items-start gap-2 bg-rose-50 text-rose-700 border border-rose-200 px-3 py-2 rounded-lg text-sm mb-4">
            <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" strokeWidth={1.75} aria-hidden="true" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {!selectedLoad && (
            <div>
              <label className="text-gray-400 text-sm block mb-1">Carga</label>
              <select
                required
                value={loadId}
                onChange={e => handleLoadSelect(e.target.value)}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-3 text-white text-lg"
              >
                <option value="">Selecionar carga</option>
                {loads.map(l => (
                  <option key={l.id} value={l.id}>
                    Driver: {l.driver_id?.toString().slice(0, 8)}... — {new Date(l.load_date).toLocaleDateString('pt-BR')}
                  </option>
                ))}
              </select>
            </div>
          )}

          {returnItems.length > 0 && (
            <div>
              <label className="text-gray-400 text-sm block mb-3">Retorno por Produto</label>
              <div className="space-y-3">
                {returnItems.map((item, idx) => {
                  // Entregou = Saiu - Cheios que voltaram
                  // (Vazios que voltaram = troca com cliente = entrega confirmada, não conta como "não entregou")
                  const entregou = item.quantity_loaded - item.cheios_retornados
                  return (
                    <div key={item.stock_product_id} className="bg-gray-700/60 rounded-xl p-4 border border-gray-600">
                      <div className="flex items-center justify-between mb-3">
                        <div>
                          <span className="text-white font-bold text-lg">{item.code}</span>
                          <span className="text-gray-400 text-sm ml-2">Saiu: {item.quantity_loaded}</span>
                        </div>
                        <div className="text-right">
                          <div className="text-xs text-gray-400">Entregou</div>
                          <div className={`text-xl font-bold ${entregou > 0 ? 'text-green-400' : 'text-gray-400'}`}>
                            {entregou >= 0 ? entregou : 0}
                          </div>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-3">
                        {/* Cheios sobraram — NÃO foram entregues */}
                        <div>
                          <label className="text-xs text-green-400 font-semibold block mb-1">
                            🟢 Cheios sobraram (não entregou)
                          </label>
                          <input
                            type="number"
                            min="0"
                            max={item.quantity_loaded}
                            value={item.cheios_retornados}
                            onChange={e => updateItem(idx, 'cheios_retornados', e.target.value)}
                            className="w-full bg-gray-800 border border-green-700/50 rounded-lg px-3 py-2.5 text-white text-xl text-center font-bold focus:border-green-500 focus:outline-none"
                          />
                        </div>
                        {/* Vazios coletados — troca realizada, entrega confirmada */}
                        <div>
                          <label className="text-xs text-blue-400 font-semibold block mb-1">
                            ⬜ Vazios coletados (troca)
                          </label>
                          <input
                            type="number"
                            min="0"
                            value={item.vazios_retornados}
                            onChange={e => updateItem(idx, 'vazios_retornados', e.target.value)}
                            className="w-full bg-gray-800 border border-blue-700/50 rounded-lg px-3 py-2.5 text-white text-xl text-center font-bold focus:border-blue-500 focus:outline-none"
                          />
                        </div>
                      </div>

                      {item.cheios_retornados > item.quantity_loaded && (
                        <div className="mt-2 text-xs text-red-400">⚠️ Cheios sobraram ({item.cheios_retornados}) não pode superar o carregado ({item.quantity_loaded})</div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="flex-1 py-4 bg-gray-700 rounded-xl text-lg">
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving || !loadId}
              className="flex-1 py-4 bg-green-600 hover:bg-green-500 rounded-xl text-lg font-bold disabled:opacity-50"
            >
              {saving ? 'Encerrando...' : 'ENCERRAR CARGA'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
