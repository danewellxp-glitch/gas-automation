import { useState, useEffect, useCallback } from 'react'
import api from '../../api/client'
import { useToast } from '../../components/ui/Toast'
import { useConfirm } from '../../components/ui/ConfirmDialog'
import { useCountUp } from '../../hooks/useCountUp'
import { useReducedMotion } from '../../hooks/useReducedMotion'
import SkeletonRow from '../../components/ui/SkeletonRow'
import BaseModal from '../../components/ui/BaseModal'

function fmt(val) {
  const n = parseFloat(val) || 0
  return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

function Badge({ status }) {
  const map = {
    em_aberto:    'bg-blue-50 text-blue-700 border-blue-200',
    pago_parcial: 'bg-amber-50 text-amber-700 border-amber-200',
    pago:         'bg-emerald-50 text-emerald-700 border-emerald-200',
    vencido:      'bg-red-50 text-red-700 border-red-200',
    negociado:    'bg-purple-50 text-purple-700 border-purple-200',
  }
  const label = {
    em_aberto:    'Em Aberto',
    pago_parcial: 'Pago Parcial',
    pago:         'Pago',
    vencido:      'Vencido',
    negociado:    'Negociado',
  }
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${map[status] || 'bg-gray-100 text-gray-500 border-gray-200'}`}>
      {label[status] || status}
    </span>
  )
}

function AgingCard({ label, color, valor, clientes, count, delay = 0 }) {
  const reduced = useReducedMotion()
  const animatedValor = useCountUp(parseFloat(valor) || 0, { duration: reduced ? 0 : 900 })
  const colorMap = {
    green:  { bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-700', val: 'text-emerald-800' },
    yellow: { bg: 'bg-amber-50',   border: 'border-amber-200',   text: 'text-amber-700',   val: 'text-amber-800' },
    orange: { bg: 'bg-orange-50',  border: 'border-orange-200',  text: 'text-orange-700',  val: 'text-orange-800' },
    red:    { bg: 'bg-red-50',     border: 'border-red-200',     text: 'text-red-700',     val: 'text-red-800' },
  }
  const c = colorMap[color] || colorMap.green
  return (
    <div
      style={{ animationDelay: `${delay}ms` }}
      className={`rounded-xl border ${c.border} ${c.bg} p-5 animate-fade-in-up transition-transform duration-200 hover:-translate-y-0.5`}
    >
      <p className={`text-xs font-semibold uppercase tracking-wide ${c.text} mb-3`}>{label}</p>
      <p className={`text-2xl font-bold tabular-nums ${c.val}`}>{fmt(animatedValor)}</p>
      <p className={`text-xs ${c.text} mt-1`}>{clientes} cliente(s) · {count} registro(s)</p>
    </div>
  )
}

function PagarModal({ entry, onClose, onSuccess }) {
  const [valor, setValor] = useState('')
  const [metodo, setMetodo] = useState('dinheiro')
  const [loading, setLoading] = useState(false)
  const [erro, setErro] = useState('')

  const pendente = parseFloat(entry.valor_pendente || 0)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setErro('')
    const v = parseFloat(valor)
    if (!v || v <= 0) { setErro('Valor inválido'); return }
    if (v > pendente) { setErro('Valor maior que o saldo pendente'); return }
    setLoading(true)
    try {
      await api.post(`/api/financeiro/fiado/entries/${entry.id}/pagar`, { valor: v, metodo })
      onSuccess()
    } catch (err) {
      setErro(err?.response?.data?.detail || 'Erro ao registrar pagamento')
    } finally {
      setLoading(false)
    }
  }

  return (
    <BaseModal onClose={onClose} maxWidth="max-w-md">
      <div className="p-6">
        <h2 className="text-base font-semibold text-gray-900 mb-4">Registrar Pagamento</h2>
        <p className="text-sm text-gray-500 mb-4">
          Saldo pendente: <span className="font-semibold text-red-600">{fmt(pendente)}</span>
        </p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Valor (R$)</label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              max={pendente}
              value={valor}
              onChange={e => setValor(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-400"
              placeholder={`Máx. ${fmt(pendente)}`}
              required
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Método</label>
            <select
              value={metodo}
              onChange={e => setMetodo(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-400"
            >
              <option value="dinheiro">Dinheiro</option>
              <option value="pix">PIX</option>
              <option value="cartao">Cartão</option>
              <option value="transferencia">Transferência</option>
              <option value="outro">Outro</option>
            </select>
          </div>
          {erro && <p className="text-xs text-red-600">{erro}</p>}
          <div className="flex gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 rounded-lg border border-gray-200 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 px-4 py-2 rounded-lg bg-gray-900 text-white text-sm font-medium hover:bg-gray-800 disabled:opacity-50 transition-colors"
            >
              {loading ? 'Salvando...' : 'Registrar'}
            </button>
          </div>
        </form>
      </div>
    </BaseModal>
  )
}

export default function FiadoPanel() {
  const toast = useToast()
  const confirm = useConfirm()
  const [aging, setAging]           = useState(null)
  const [entries, setEntries]       = useState([])
  const [total, setTotal]           = useState(0)
  const [page, setPage]             = useState(1)
  const [loading, setLoading]       = useState(true)
  const [modalEntry, setModalEntry] = useState(null)
  const [loteLoading, setLoteLoading] = useState(false)
  const [loteMsg, setLoteMsg]       = useState('')

  const loadData = useCallback(async (p = 1) => {
    setLoading(true)
    try {
      const [agingR, entriesR] = await Promise.all([
        api.get('/api/financeiro/fiado/aging'),
        api.get('/api/financeiro/fiado/entries', { params: { page: p, limit: 50 } }),
      ])
      setAging(agingR.data)
      setEntries(entriesR.data?.items || [])
      setTotal(entriesR.data?.total || 0)
      setPage(p)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadData(1) }, [loadData])

  const handleCobrarWA = async (entry) => {
    try {
      await api.post(`/api/financeiro/fiado/entries/${entry.id}/cobrar-whatsapp`)
      toast.success('Cobrança enviada')
      loadData(page)
    } catch {
      toast.error('Erro ao enviar cobrança')
    }
  }

  const handleLote = async () => {
    const ok = await confirm({
      title: 'Cobrança em lote',
      message: 'Enviar cobrança WhatsApp para TODOS os clientes com fiado vencido?',
      confirmLabel: 'Enviar',
      danger: true,
    })
    if (!ok) return
    setLoteLoading(true)
    setLoteMsg('')
    try {
      const r = await api.post('/api/financeiro/fiado/cobranca-lote')
      setLoteMsg(`Processados: ${r.data.total_processados} clientes`)
      loadData(page)
    } catch (err) {
      setLoteMsg(err?.response?.data?.detail || 'Erro na cobrança em lote')
    } finally {
      setLoteLoading(false)
    }
  }

  const today = new Date()
  const diasAtraso = (vencimentoStr) => {
    const v = new Date(vencimentoStr)
    const diff = Math.floor((today - v) / 86400000)
    return diff
  }

  return (
    <div className="space-y-6">
      {/* Aging cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <AgingCard
          label="0 a 7 dias"
          color="green"
          valor={aging?.['0_7_dias']?.valor || 0}
          clientes={aging?.['0_7_dias']?.clientes || 0}
          count={aging?.['0_7_dias']?.count || 0}
          delay={0}
        />
        <AgingCard
          label="8 a 15 dias"
          color="yellow"
          valor={aging?.['8_15_dias']?.valor || 0}
          clientes={aging?.['8_15_dias']?.clientes || 0}
          count={aging?.['8_15_dias']?.count || 0}
          delay={80}
        />
        <AgingCard
          label="16 a 30 dias"
          color="orange"
          valor={aging?.['16_30_dias']?.valor || 0}
          clientes={aging?.['16_30_dias']?.clientes || 0}
          count={aging?.['16_30_dias']?.count || 0}
          delay={160}
        />
        <AgingCard
          label="Acima de 30 dias"
          color="red"
          valor={aging?.['acima_30_dias']?.valor || 0}
          clientes={aging?.['acima_30_dias']?.clientes || 0}
          count={aging?.['acima_30_dias']?.count || 0}
          delay={240}
        />
      </div>

      {/* Table */}
      <div className="rounded-xl border border-gray-200 bg-white">
        <div className="flex items-center justify-between px-6 pt-6 pb-4">
          <div>
            <h3 className="text-base font-semibold text-gray-900">Devedores</h3>
            <p className="text-sm text-gray-400 mt-0.5">{total} registro(s)</p>
          </div>
          <div className="flex items-center gap-2">
            {loteMsg && <span className="text-xs text-gray-500">{loteMsg}</span>}
            <button
              onClick={handleLote}
              disabled={loteLoading}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-red-600 text-white text-sm font-medium hover:bg-red-700 disabled:opacity-50 transition-colors"
            >
              {loteLoading ? 'Enviando...' : 'Cobrança em Lote'}
            </button>
          </div>
        </div>

        {loading ? (
          <div className="px-6 pb-6 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Cliente</th>
                  <th className="py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wide">Valor Pendente</th>
                  <th className="py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wide">Vencimento</th>
                  <th className="py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wide">Dias Atraso</th>
                  <th className="py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wide">Status</th>
                  <th className="py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wide">Ações</th>
                </tr>
              </thead>
              <tbody>
                {Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} cols={6} />)}
              </tbody>
            </table>
          </div>
        ) : entries.length === 0 ? (
          <div className="px-6 pb-8 text-center text-sm text-gray-400">Nenhum registro de fiado encontrado</div>
        ) : (
          <div className="px-6 pb-6 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Cliente</th>
                  <th className="py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wide">Valor Pendente</th>
                  <th className="py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wide">Vencimento</th>
                  <th className="py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wide">Dias Atraso</th>
                  <th className="py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wide">Status</th>
                  <th className="py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wide">Ações</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((e) => {
                  const dias = diasAtraso(e.vencimento)
                  return (
                    <tr key={e.id} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-3">
                        <div className="font-medium text-gray-900 text-xs">{e.customer_id}</div>
                      </td>
                      <td className="py-3 text-right font-semibold text-red-600">
                        {fmt(e.valor_pendente)}
                      </td>
                      <td className="py-3 text-right text-gray-600">
                        {new Date(e.vencimento).toLocaleDateString('pt-BR')}
                      </td>
                      <td className="py-3 text-right">
                        {dias > 0 ? (
                          <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${
                            dias > 30 ? 'bg-red-50 text-red-700 border-red-200'
                            : dias > 15 ? 'bg-orange-50 text-orange-700 border-orange-200'
                            : 'bg-amber-50 text-amber-700 border-amber-200'
                          }`}>
                            {dias}d
                          </span>
                        ) : (
                          <span className="text-xs text-gray-400">No prazo</span>
                        )}
                      </td>
                      <td className="py-3 text-center">
                        <Badge status={e.status} />
                      </td>
                      <td className="py-3 text-center">
                        <div className="flex items-center justify-center gap-1">
                          <button
                            onClick={() => handleCobrarWA(e)}
                            className="px-2 py-1 rounded text-xs bg-green-50 text-green-700 border border-green-200 hover:bg-green-100 transition-colors"
                          >
                            Cobrar WA
                          </button>
                          <button
                            onClick={() => setModalEntry(e)}
                            className="px-2 py-1 rounded text-xs bg-gray-100 text-gray-700 border border-gray-200 hover:bg-gray-200 transition-colors"
                          >
                            Registrar Pgto
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>

            {/* Pagination */}
            {total > 50 && (
              <div className="flex justify-center gap-2 pt-4">
                <button
                  onClick={() => loadData(page - 1)}
                  disabled={page === 1}
                  className="px-3 py-1.5 rounded-lg border border-gray-200 text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-40"
                >
                  Anterior
                </button>
                <span className="px-3 py-1.5 text-sm text-gray-500">Página {page}</span>
                <button
                  onClick={() => loadData(page + 1)}
                  disabled={entries.length < 50}
                  className="px-3 py-1.5 rounded-lg border border-gray-200 text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-40"
                >
                  Próxima
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Modal Registrar Pagamento */}
      {modalEntry && (
        <PagarModal
          entry={modalEntry}
          onClose={() => setModalEntry(null)}
          onSuccess={() => { setModalEntry(null); loadData(page) }}
        />
      )}
    </div>
  )
}
