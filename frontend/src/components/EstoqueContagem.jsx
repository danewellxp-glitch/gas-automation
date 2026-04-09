/**
 * EstoqueContagem — Modal de contagem física de vasilhames
 * Usa a tabela vasilhame_estoque (fonte unificada com Financeiro).
 * Inclui: P13, P20, P45 e G20L (Galão Água 20L).
 */
import { useState, useEffect } from 'react'
import api from '../api/client'
import { ESTOQUE } from '../api/endpoints'

const LABELS = {
  P13: 'Botijão P13 (13kg)',
  P20: 'Botijão P20 (20kg)',
  P45: 'Botijão P45 (45kg)',
  G20L: 'Galão Água 20L',
}

export default function EstoqueContagem({ onClose, onSaved }) {
  const [vasilhames, setVasilhames] = useState([])
  const [quantities, setQuantities] = useState({}) // { tipo: { cheios, vazios } }
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [results, setResults] = useState(null)

  useEffect(() => {
    loadVasilhames()
  }, [])

  const loadVasilhames = async () => {
    try {
      setLoading(true)
      const res = await api.get(ESTOQUE.VASILHAMES_POSICAO)
      const data = res.data || []
      setVasilhames(data)
      // Pre-preenche com valores atuais
      const initQty = {}
      data.forEach(v => {
        initQty[v.tipo] = {
          cheios: String(v.qtd_cheios),
          vazios: String(v.qtd_vazios),
        }
      })
      setQuantities(initQty)
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao carregar estoque')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    const summary = []
    const errors = []

    for (const v of vasilhames) {
      const novosCheios = parseInt(quantities[v.tipo]?.cheios ?? v.qtd_cheios, 10)
      const novosVazios = parseInt(quantities[v.tipo]?.vazios ?? v.qtd_vazios, 10)
      const deltaCheios = novosCheios - v.qtd_cheios
      const deltaVazios = novosVazios - v.qtd_vazios

      if (deltaCheios === 0 && deltaVazios === 0) {
        summary.push({ tipo: v.tipo, status: 'sem alteração' })
        continue
      }

      try {
        await api.post(ESTOQUE.VASILHAMES_AJUSTE_DIRETO, {
          tipo: v.tipo,
          qtd_cheios: novosCheios,
          qtd_vazios: novosVazios,
          observacao: `Contagem física: cheios ${v.qtd_cheios}→${novosCheios}, vazios ${v.qtd_vazios}→${novosVazios}`,
        })
        const parts = []
        if (deltaCheios !== 0) parts.push(`cheios ${deltaCheios > 0 ? '+' : ''}${deltaCheios}`)
        if (deltaVazios !== 0) parts.push(`vazios ${deltaVazios > 0 ? '+' : ''}${deltaVazios}`)
        summary.push({ tipo: v.tipo, status: parts.join(', ') })
      } catch (err) {
        errors.push(`${v.tipo}: ${err.response?.data?.detail || 'Erro'}`)
      }
    }

    setSaving(false)

    if (errors.length > 0) setError(errors.join(' | '))
    setResults(summary)
    if (errors.length === 0 && onSaved) onSaved()
  }

  return (
    <div className="fixed inset-0 bg-black/75 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 rounded-2xl border border-gray-700 w-full max-w-lg shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-700">
          <div>
            <h2 className="text-xl font-bold text-white">Contagem de Estoque</h2>
            <p className="text-sm text-gray-400 mt-0.5">Digite a quantidade física atual no depósito</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-2xl leading-none">×</button>
        </div>

        {/* Body */}
        <div className="p-6">
          {loading && (
            <div className="text-center text-gray-400 py-8">Carregando estoque...</div>
          )}

          {!loading && !results && (
            <form onSubmit={handleSubmit} className="space-y-3">
              {vasilhames.length === 0 && (
                <div className="text-center text-gray-400 py-4">Nenhum produto cadastrado no estoque</div>
              )}

              {vasilhames.map(v => {
                const cheiosVal = quantities[v.tipo]?.cheios ?? String(v.qtd_cheios)
                const vaziosVal = quantities[v.tipo]?.vazios ?? String(v.qtd_vazios)
                const dc = parseInt(cheiosVal, 10) - v.qtd_cheios
                const dv = parseInt(vaziosVal, 10) - v.qtd_vazios
                return (
                  <div key={v.tipo} className="bg-gray-800 rounded-xl p-4 border border-gray-700">
                    <div className="mb-3">
                      <div className="font-bold text-white text-lg">{v.tipo}</div>
                      <div className="text-sm text-gray-400">{LABELS[v.tipo] || v.tipo}</div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="text-xs text-gray-400 block mb-1">Cheios</label>
                        <input
                          type="number" min="0" required
                          value={cheiosVal}
                          onChange={e => setQuantities(q => ({ ...q, [v.tipo]: { ...q[v.tipo], cheios: e.target.value } }))}
                          className="w-full bg-gray-700 border border-gray-600 rounded-lg px-2 py-2 text-white text-xl text-center font-bold focus:border-green-500 focus:outline-none"
                        />
                        {dc !== 0 && !isNaN(dc) && (
                          <span className={`text-xs font-semibold block text-center mt-1 ${dc > 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {dc > 0 ? `+${dc}` : dc}
                          </span>
                        )}
                      </div>
                      <div>
                        <label className="text-xs text-gray-400 block mb-1">Vazios</label>
                        <input
                          type="number" min="0" required
                          value={vaziosVal}
                          onChange={e => setQuantities(q => ({ ...q, [v.tipo]: { ...q[v.tipo], vazios: e.target.value } }))}
                          className="w-full bg-gray-700 border border-gray-600 rounded-lg px-2 py-2 text-white text-xl text-center font-bold focus:border-blue-500 focus:outline-none"
                        />
                        {dv !== 0 && !isNaN(dv) && (
                          <span className={`text-xs font-semibold block text-center mt-1 ${dv > 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {dv > 0 ? `+${dv}` : dv}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}

              {error && (
                <div className="text-red-400 text-sm bg-red-900/30 border border-red-700 rounded-lg p-3">{error}</div>
              )}

              <div className="flex gap-3 pt-2">
                <button type="button" onClick={onClose}
                  className="flex-1 py-3 bg-gray-700 hover:bg-gray-600 rounded-xl text-white font-medium transition-colors">
                  Cancelar
                </button>
                <button type="submit" disabled={saving || vasilhames.length === 0}
                  className="flex-1 py-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-xl text-white font-bold transition-colors">
                  {saving ? 'Salvando...' : 'Confirmar Contagem'}
                </button>
              </div>
            </form>
          )}

          {/* Resultado */}
          {results && (
            <div className="space-y-3">
              <div className="text-center text-green-400 font-bold text-lg mb-2">✓ Contagem aplicada</div>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {results.map((r, i) => (
                  <div key={i} className="flex items-center justify-between bg-gray-800 rounded-lg px-4 py-2">
                    <span className="font-bold text-white">{r.tipo}</span>
                    <span className="text-sm font-medium text-gray-300">{r.status}</span>
                  </div>
                ))}
              </div>
              {error && (
                <div className="text-red-400 text-sm bg-red-900/30 border border-red-700 rounded-lg p-3">{error}</div>
              )}
              <button onClick={onClose}
                className="w-full py-3 bg-gray-700 hover:bg-gray-600 rounded-xl text-white font-medium transition-colors">
                Fechar
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
