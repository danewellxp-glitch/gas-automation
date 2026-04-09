import { useState, useEffect, useCallback, useRef } from 'react'
import api from '../../api/client'
import { ESTOQUE } from '../../api/endpoints'
import { useAuth } from '../../hooks/useAuth'
import VehicleLoadTable from './components/VehicleLoadTable'
import OpenLoadModal from './components/OpenLoadModal'
import CloseLoadModal from './components/CloseLoadModal'
import MovementLog from './components/MovementLog'
import PurchaseOrderForm from './components/PurchaseOrderForm'
import EstoqueContagem from '../../components/EstoqueContagem'

const VASILHAME_LABELS = { P13: 'Botijão 13kg', P20: 'Botijão 20kg', P45: 'Botijão 45kg', G20L: 'Galão Água 20L' }

export default function EstoqueDashboard() {
  const { user, logout } = useAuth()
  const [balances, setBalances] = useState([])
  const [vasilhames, setVasilhames] = useState([])
  const [openLoads, setOpenLoads] = useState([])
  const [movements, setMovements] = useState([])
  const [products, setProducts] = useState([])
  const [drivers, setDrivers] = useState([])
  const [loading, setLoading] = useState(true)
  const [modal, setModal] = useState(null)
  const [selectedLoad, setSelectedLoad] = useState(null)
  const [adjustmentForm, setAdjustmentForm] = useState({ tipo: '', campo: 'cheios', direction: 'entrada', quantidade: 1, notes: '' })
  const [adjusting, setAdjusting] = useState(false)
  const wsRef = useRef(null)

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      const [balRes, loadsRes, movRes, prodRes, vasRes] = await Promise.all([
        api.get(ESTOQUE.BALANCE),
        api.get(ESTOQUE.VEHICLE_LOADS_OPEN),
        api.get(ESTOQUE.MOVEMENTS, { params: { per_page: 50 } }),
        api.get(ESTOQUE.PRODUCTS),
        api.get(ESTOQUE.VASILHAMES_POSICAO).catch(() => ({ data: [] })),
      ])
      setBalances(balRes.data || [])
      setOpenLoads(loadsRes.data || [])
      setMovements(movRes.data || [])
      setProducts(prodRes.data || [])
      setVasilhames(Array.isArray(vasRes.data) ? vasRes.data : [])
    } catch (err) {
      console.error('Erro ao carregar estoque:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  const loadDrivers = useCallback(async () => {
    try {
      const res = await api.get('/api/drivers')
      setDrivers(res.data || [])
    } catch (err) {
      console.error('Erro ao carregar drivers:', err)
    }
  }, [])

  useEffect(() => {
    loadData()
    loadDrivers()
  }, [loadData, loadDrivers])

  useEffect(() => {
    const token = localStorage.getItem('token') || sessionStorage.getItem('token')
    if (!token) return
    const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://192.168.10.167:5688'
    const wsUrl = API_BASE.replace('http', 'ws') + `/ws/dashboard?token=${token}`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        if (msg.type === 'vasilhame_update' && Array.isArray(msg.data)) {
          setVasilhames(msg.data)
        }
      } catch {}
    }
    return () => ws.close()
  }, [])

  const handleVasilhameAdjustment = async (e) => {
    e.preventDefault()
    const { tipo, campo, quantidade, direction, notes } = adjustmentForm
    if (!tipo || !notes.trim()) { alert('Selecione o produto e informe o motivo'); return }
    setAdjusting(true)
    try {
      const current = vasilhames.find(v => v.tipo === tipo) || {}
      const atual = campo === 'cheios' ? (current.qtd_cheios || 0) : (current.qtd_vazios || 0)
      const novo = direction === 'entrada' ? atual + parseInt(quantidade) : Math.max(0, atual - parseInt(quantidade))
      const payload = { tipo, observacao: notes }
      if (campo === 'cheios') payload.qtd_cheios = novo
      else payload.qtd_vazios = novo
      await api.post(ESTOQUE.VASILHAMES_AJUSTE_DIRETO, payload)
      setModal(null)
      setAdjustmentForm({ tipo: '', campo: 'cheios', direction: 'entrada', quantidade: 1, notes: '' })
      loadData()
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao registrar ajuste')
    } finally {
      setAdjusting(false)
    }
  }

  if (loading && vasilhames.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="w-8 h-8 animate-spin rounded-full border-2 border-gray-200 border-t-primary-500" />
      </div>
    )
  }

  return (
    <div className="flex min-h-screen bg-gray-50">

      {/* ── Sidebar (Desktop) ── */}
      <aside className="hidden w-64 flex-col bg-[#14283b] text-white md:flex flex-shrink-0">
        <div className="flex flex-col items-center justify-center p-6 border-b border-white/10">
          <img src="/logo_sistema.png" alt="Mercury Gas" className="h-[136px] object-contain max-w-full mb-6 brightness-0 invert opacity-90" />

          <div className="w-full bg-white/5 rounded-xl border border-white/10 p-4 text-center mb-4">
            <h2 className="text-[10px] font-semibold text-white/50 tracking-widest uppercase mb-1">Operador Logado</h2>
            <p className="text-sm font-semibold text-white truncate w-full" title={user?.full_name || user?.username}>
              {user?.full_name || user?.username}
            </p>
            <span className="mt-2 inline-flex items-center rounded-full bg-primary-500/20 px-2.5 py-0.5 text-xs font-medium text-primary-300 capitalize">
              {user?.role || 'Estoque'}
            </span>
          </div>

          <button
            onClick={logout}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-red-500/10 px-4 py-2.5 text-sm font-medium text-red-400 hover:bg-red-500/20 transition-colors"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path><polyline points="16 17 21 12 16 7"></polyline><line x1="21" y1="12" x2="9" y2="12"></line></svg>
            Sair do Sistema
          </button>
        </div>
        <div className="flex-1" />
      </aside>

      {/* ── Main Content ── */}
      <main className="flex-1 w-full overflow-y-auto p-4 md:p-6">

        {/* Header */}
        <div className="mb-6">
          <h1 className="text-xl font-semibold text-gray-900">Terminal de Estoque</h1>
          <p className="text-sm text-gray-500 mt-0.5">Depósito — Controle de botijões em tempo real</p>
        </div>

        {/* Vasilhames */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-gray-900">Posição de Vasilhames</h2>
            <span className="text-xs text-emerald-600 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-full font-medium">
              Sincronizado em tempo real
            </span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {vasilhames.map(v => (
              <div key={v.tipo} className="bg-white border border-gray-200 rounded-xl p-4">
                <div className="mb-3">
                  <div className="text-base font-bold text-gray-900">{v.tipo}</div>
                  <div className="text-xs text-gray-400 mt-0.5">{VASILHAME_LABELS[v.tipo] || v.tipo}</div>
                </div>
                <div className="space-y-1.5 text-sm">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-500">Cheios</span>
                    <span className="font-bold text-emerald-600 text-base">{v.qtd_cheios}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-500">Em Campo</span>
                    <span className="font-bold text-amber-600 text-base">{v.qtd_em_campo}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-500">Vazios</span>
                    <span className="font-bold text-gray-600 text-base">{v.qtd_vazios}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mb-8">
          <ActionButton icon="🚛" label="Abrir Carga"         color="bg-blue-600 hover:bg-blue-700"     onClick={() => setModal('open_load')} />
          <ActionButton icon="✅" label="Encerrar Carga"      color="bg-emerald-600 hover:bg-emerald-700" onClick={() => setModal('close_load')} disabled={openLoads.length === 0} badge={openLoads.length > 0 ? openLoads.length : null} />
          <ActionButton icon="📦" label="Registrar Compra"    color="bg-violet-600 hover:bg-violet-700"  onClick={() => setModal('purchase')} />
          <ActionButton icon="🔧" label="Ajuste de Estoque"   color="bg-primary-600 hover:bg-primary-700" onClick={() => setModal('adjustment')} />
          <ActionButton icon="🔢" label="Contar Estoque"      color="bg-teal-600 hover:bg-teal-700"      onClick={() => setModal('contagem')} />
        </div>

        {/* Cargas abertas */}
        {openLoads.length > 0 && (
          <div className="bg-white border border-amber-200 rounded-xl p-5 mb-6">
            <h2 className="text-sm font-semibold text-gray-900 mb-4">Cargas Abertas Agora</h2>
            <VehicleLoadTable
              loads={openLoads}
              products={products}
              onClose={(load) => { setSelectedLoad(load); setModal('close_load') }}
            />
          </div>
        )}

        {/* Movimentações */}
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-gray-900 mb-4">Movimentações do Dia</h2>
          <MovementLog movements={movements} products={products} />
        </div>

        {/* Modais */}
        {modal === 'open_load' && (
          <OpenLoadModal
            drivers={drivers}
            products={products}
            onClose={() => setModal(null)}
            onCreated={() => { setModal(null); loadData() }}
          />
        )}

        {modal === 'close_load' && (
          <CloseLoadModal
            loads={openLoads}
            selectedLoad={selectedLoad}
            products={products}
            onClose={() => { setModal(null); setSelectedLoad(null) }}
            onClosed={() => { setModal(null); setSelectedLoad(null); loadData() }}
          />
        )}

        {modal === 'purchase' && (
          <PurchaseOrderForm
            products={products}
            onClose={() => setModal(null)}
            onCreated={() => { setModal(null); loadData() }}
          />
        )}

        {modal === 'contagem' && (
          <EstoqueContagem
            onClose={() => setModal(null)}
            onSaved={() => { setModal(null); loadData() }}
          />
        )}

        {modal === 'adjustment' && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl border border-gray-200 w-full max-w-md p-6 shadow-xl">
              <h2 className="text-base font-semibold text-gray-900 mb-4">Ajuste Manual de Estoque</h2>
              <form onSubmit={handleVasilhameAdjustment} className="space-y-4">
                <div>
                  <label className="text-xs font-medium text-gray-500 block mb-1.5">Produto</label>
                  <select
                    required
                    value={adjustmentForm.tipo}
                    onChange={e => setAdjustmentForm(f => ({ ...f, tipo: e.target.value }))}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-900 bg-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                  >
                    <option value="">Selecionar produto</option>
                    {vasilhames.map(v => (
                      <option key={v.tipo} value={v.tipo}>{v.tipo} — {VASILHAME_LABELS[v.tipo] || v.tipo}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-500 block mb-1.5">Campo</label>
                  <div className="flex gap-2">
                    {[['cheios', 'Cheios'], ['vazios', 'Vazios']].map(([val, lbl]) => (
                      <button key={val} type="button"
                        onClick={() => setAdjustmentForm(f => ({ ...f, campo: val }))}
                        className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors border ${
                          adjustmentForm.campo === val
                            ? 'bg-primary-600 text-white border-primary-600'
                            : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'
                        }`}>
                        {lbl}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-500 block mb-1.5">Tipo de Ajuste</label>
                  <div className="flex gap-2">
                    {['entrada', 'saida'].map(d => (
                      <button key={d} type="button"
                        onClick={() => setAdjustmentForm(f => ({ ...f, direction: d }))}
                        className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition-colors border ${
                          adjustmentForm.direction === d
                            ? d === 'entrada' ? 'bg-emerald-600 text-white border-emerald-600' : 'bg-red-600 text-white border-red-600'
                            : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'
                        }`}>
                        {d === 'entrada' ? '+ Entrada' : '− Saída'}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-500 block mb-1.5">Quantidade</label>
                  <input type="number" required min="1"
                    value={adjustmentForm.quantidade}
                    onChange={e => setAdjustmentForm(f => ({ ...f, quantidade: e.target.value }))}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-900 text-center focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-500 block mb-1.5">Motivo (obrigatório)</label>
                  <textarea required
                    value={adjustmentForm.notes}
                    onChange={e => setAdjustmentForm(f => ({ ...f, notes: e.target.value }))}
                    placeholder="Descreva o motivo do ajuste..."
                    rows={3}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-900 resize-none focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
                <div className="flex gap-3">
                  <button type="button" onClick={() => setModal(null)}
                    className="flex-1 py-2.5 rounded-lg text-sm font-medium border border-gray-200 text-gray-700 hover:bg-gray-50 transition-colors">
                    Cancelar
                  </button>
                  <button type="submit" disabled={adjusting}
                    className="flex-1 py-2.5 rounded-lg text-sm font-medium bg-primary-600 hover:bg-primary-700 text-white transition-colors disabled:opacity-50">
                    {adjusting ? 'Salvando...' : 'Confirmar'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

      </main>
    </div>
  )
}

function ActionButton({ icon, label, color, onClick, disabled = false, badge = null }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`${color} text-white rounded-xl p-4 text-center transition-colors disabled:opacity-40 disabled:cursor-not-allowed relative`}
    >
      <div className="text-3xl mb-1.5">{icon}</div>
      <div className="text-xs font-semibold">{label}</div>
      {badge && (
        <span className="absolute top-2 right-2 bg-amber-400 text-gray-900 text-[10px] font-bold px-1.5 py-0.5 rounded-full">
          {badge}
        </span>
      )}
    </button>
  )
}
