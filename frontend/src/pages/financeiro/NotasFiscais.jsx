import { useState, useEffect, useCallback } from 'react'
import api from '../../api/client'
import { FINANCEIRO } from '../../api/endpoints'
import { useToast } from '../../components/ui/Toast'
import { useConfirm } from '../../components/ui/ConfirmDialog'
import BaseModal from '../../components/ui/BaseModal'

function fmt(val) {
  const n = parseFloat(val) || 0
  return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

const STATUS_MAP = {
  rascunho:     { label: 'Rascunho',    cls: 'bg-gray-100 text-gray-500' },
  enviada:      { label: 'Enviada',     cls: 'bg-blue-100 text-blue-700' },
  autorizada:   { label: 'Autorizada',  cls: 'bg-green-100 text-green-700' },
  rejeitada:    { label: 'Rejeitada',   cls: 'bg-red-100 text-red-700' },
  cancelada:    { label: 'Cancelada',   cls: 'bg-gray-100 text-gray-400 line-through' },
  erro_emissao: { label: 'Erro',        cls: 'bg-orange-100 text-orange-700' },
}

function StatusBadge({ status }) {
  const { label, cls } = STATUS_MAP[status] || { label: status, cls: 'bg-gray-100 text-gray-500' }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${cls}`}>
      {label}
    </span>
  )
}

function SummaryCard({ title, value, color }) {
  const clsMap = {
    green:  'border-green-400 text-green-600',
    blue:   'border-blue-400 text-blue-600',
    red:    'border-red-400 text-red-600',
    gray:   'border-gray-300 text-gray-500',
    orange: 'border-orange-400 text-orange-600',
  }
  return (
    <div className={`rounded-xl border-l-4 ${clsMap[color].split(' ')[0]} bg-white border border-gray-200 p-4`}>
      <p className="text-xs text-gray-500 mb-1">{title}</p>
      <p className={`text-2xl font-bold ${clsMap[color].split(' ')[1]}`}>{value}</p>
    </div>
  )
}

function EmitirModal({ onClose, onSuccess }) {
  const toast = useToast()
  const [pedidoId, setPedidoId] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async () => {
    if (!pedidoId.trim()) return
    setLoading(true)
    try {
      await api.post(FINANCEIRO.NFE_EMITIR, { pedido_id: pedidoId.trim() })
      onSuccess()
      onClose()
      toast.success('NF-e emitida — verifique o status na lista')
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Erro ao emitir NF-e')
    } finally {
      setLoading(false)
    }
  }

  return (
    <BaseModal onClose={onClose} maxWidth="max-w-sm">
      <div className="p-6">
        <h2 className="text-base font-semibold text-gray-900 mb-4">Emitir NF-e</h2>
        <div className="space-y-3">
          <div>
            <label className="block text-xs text-gray-500 mb-1">ID do Pedido (UUID)</label>
            <input
              type="text" value={pedidoId} onChange={e => setPedidoId(e.target.value)}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900"
              placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            />
          </div>
          <p className="text-xs text-amber-600 bg-amber-50 rounded-lg px-3 py-2">
            ⚠️ Configure UNIMAKE_API_TOKEN e dados fiscais no .env antes de emitir em produção.
          </p>
        </div>
        <div className="flex gap-2 mt-5">
          <button onClick={onClose} className="flex-1 px-4 py-2 rounded-lg border border-gray-200 text-sm text-gray-600 hover:bg-gray-50">Cancelar</button>
          <button onClick={submit} disabled={loading || !pedidoId.trim()} className="flex-1 px-4 py-2 rounded-lg bg-gray-900 text-white text-sm font-medium hover:bg-gray-800 disabled:opacity-50">
            {loading ? 'Emitindo...' : 'Emitir'}
          </button>
        </div>
      </div>
    </BaseModal>
  )
}

function DetalheModal({ nf, onClose, onRefresh }) {
  const toast = useToast()
  const confirm = useConfirm()
  const [cancelMotivo, setCancelMotivo] = useState('')
  const [showCancel, setShowCancel] = useState(false)
  const [loading, setLoading] = useState(false)

  const cancelar = async () => {
    if (cancelMotivo.trim().length < 15) {
      toast.warning('Motivo deve ter ao menos 15 caracteres')
      return
    }
    const ok = await confirm({
      title: 'Cancelar NF-e',
      message: 'Esta ação é irreversível. Confirma o cancelamento desta NF-e?',
      confirmLabel: 'Cancelar NF-e',
      danger: true,
    })
    if (!ok) return
    setLoading(true)
    try {
      await api.post(FINANCEIRO.NFE_CANCELAR(nf.id), { motivo: cancelMotivo })
      onRefresh()
      onClose()
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Erro ao cancelar')
    } finally {
      setLoading(false)
    }
  }

  const reenviarWA = async () => {
    try {
      await api.post(FINANCEIRO.NFE_REENVIAR_WA(nf.id))
      toast.success('DANFE reenviado')
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Erro ao reenviar')
    }
  }

  return (
    <BaseModal onClose={onClose} maxWidth="max-w-lg">
      <div className="p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-gray-900">
            NF-e {nf.numero ? `Nº ${nf.numero}` : '(sem número)'}
          </h2>
          <StatusBadge status={nf.status} />
        </div>

        <dl className="space-y-2 text-sm">
          <div className="flex justify-between">
            <dt className="text-gray-500">Tipo</dt>
            <dd className="text-gray-900">{nf.tipo === '55' ? 'NF-e (55)' : 'NFC-e (65)'}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-500">Valor Total</dt>
            <dd className="font-semibold text-gray-900">{fmt(nf.valor_total)}</dd>
          </div>
          {nf.chave_acesso && (
            <div>
              <dt className="text-gray-500 mb-1">Chave de Acesso</dt>
              <dd className="text-xs font-mono bg-gray-50 rounded p-2 break-all">{nf.chave_acesso}</dd>
            </div>
          )}
          {nf.motivo_rejeicao && (
            <div>
              <dt className="text-gray-500 mb-1">Motivo Rejeição</dt>
              <dd className="text-xs text-red-600 bg-red-50 rounded p-2">{nf.motivo_rejeicao}</dd>
            </div>
          )}
          <div className="flex justify-between">
            <dt className="text-gray-500">WA Enviado</dt>
            <dd>{nf.enviada_whatsapp ? '✅ Sim' : '—'}</dd>
          </div>
        </dl>

        {nf.pdf_danfe_url && (
          <a
            href={nf.pdf_danfe_url} target="_blank" rel="noopener noreferrer"
            className="mt-4 flex items-center justify-center gap-2 w-full px-4 py-2 rounded-lg border border-gray-200 text-sm text-gray-700 hover:bg-gray-50"
          >
            📄 Baixar DANFE
          </a>
        )}

        <div className="flex gap-2 mt-4">
          {nf.status === 'autorizada' && (
            <button
              onClick={reenviarWA}
              className="flex-1 px-3 py-2 rounded-lg bg-green-50 text-green-700 text-sm hover:bg-green-100"
            >
              📲 Reenviar WA
            </button>
          )}
          {nf.status === 'autorizada' && !showCancel && (
            <button
              onClick={() => setShowCancel(true)}
              className="flex-1 px-3 py-2 rounded-lg bg-red-50 text-red-700 text-sm hover:bg-red-100"
            >
              Cancelar NF-e
            </button>
          )}
        </div>

        {showCancel && (
          <div className="mt-3 space-y-2">
            <textarea
              value={cancelMotivo} onChange={e => setCancelMotivo(e.target.value)}
              rows={3} placeholder="Motivo do cancelamento (mínimo 15 caracteres)"
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
            />
            <div className="flex gap-2">
              <button onClick={() => setShowCancel(false)} className="flex-1 px-3 py-2 rounded-lg border border-gray-200 text-sm text-gray-600">Voltar</button>
              <button onClick={cancelar} disabled={loading} className="flex-1 px-3 py-2 rounded-lg bg-red-600 text-white text-sm hover:bg-red-700 disabled:opacity-50">
                {loading ? 'Cancelando...' : 'Confirmar Cancelamento'}
              </button>
            </div>
          </div>
        )}

        <button onClick={onClose} className="w-full mt-3 px-4 py-2 rounded-lg border border-gray-200 text-sm text-gray-600 hover:bg-gray-50">
          Fechar
        </button>
      </div>
    </BaseModal>
  )
}

export default function NotasFiscais() {
  const [nfes, setNfes]         = useState([])
  const [resumo, setResumo]     = useState(null)
  const [loading, setLoading]   = useState(true)
  const [showEmitir, setEmitir] = useState(false)
  const [detalhe, setDetalhe]   = useState(null)
  const [page, setPage]         = useState(1)
  const [total, setTotal]       = useState(0)
  const LIMIT = 50

  const load = useCallback(async (p = 1) => {
    setLoading(true)
    try {
      const [listR, resumoR] = await Promise.all([
        api.get(FINANCEIRO.NFE_LIST, { params: { page: p, limit: LIMIT } }).catch(() => ({ data: [] })),
        api.get(FINANCEIRO.NFE_RESUMO).catch(() => ({ data: {} })),
      ])
      const data = Array.isArray(listR.data) ? listR.data : (listR.data?.items || [])
      setNfes(data)
      setTotal(listR.data?.total || data.length)
      setResumo(resumoR.data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load(page) }, [load, page])

  const rejeitadas = nfes.filter(n => n.status === 'rejeitada')

  return (
    <div className="space-y-6">
      {/* Alerta de rejeições */}
      {rejeitadas.length > 0 && (
        <div className="flex items-start gap-3 px-4 py-3 rounded-lg border border-red-200 bg-red-50 text-sm">
          <span className="text-red-500 font-bold text-base">✕</span>
          <div>
            <p className="font-medium text-red-700">{rejeitadas.length} NF-e(s) rejeitada(s)</p>
            <p className="text-red-500 text-xs mt-0.5">{rejeitadas[0]?.motivo_rejeicao || 'Verifique o motivo na NF-e'}</p>
          </div>
        </div>
      )}

      {/* Cards resumo */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard title="Autorizadas" value={resumo?.autorizada || '—'} color="green" />
        <SummaryCard title="Enviadas/Pendentes" value={resumo?.enviada || '—'} color="blue" />
        <SummaryCard title="Rejeitadas" value={resumo?.rejeitada || '—'} color="red" />
        <SummaryCard title="Canceladas" value={resumo?.cancelada || '—'} color="gray" />
      </div>

      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">{total} nota(s) fiscal(is)</p>
        <button
          onClick={() => setEmitir(true)}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-900 text-white text-sm font-medium hover:bg-gray-800"
        >
          + Emitir NF-e
        </button>
      </div>

      {/* Tabela */}
      <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16 text-sm text-gray-400">Carregando...</div>
        ) : nfes.length === 0 ? (
          <div className="flex items-center justify-center py-16 text-sm text-gray-400">Nenhuma NF-e emitida.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50">
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">Número</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">Tipo</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500">Valor</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500">Status</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500">Emitida em</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500">WA</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {nfes.map(nf => (
                  <tr key={nf.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 font-mono text-gray-700">
                      {nf.numero ? `#${nf.numero}` : <span className="text-gray-400">—</span>}
                    </td>
                    <td className="px-4 py-3 text-gray-500">{nf.tipo === '55' ? 'NF-e' : 'NFC-e'}</td>
                    <td className="px-4 py-3 text-right font-medium text-gray-900">{fmt(nf.valor_total)}</td>
                    <td className="px-4 py-3 text-center"><StatusBadge status={nf.status} /></td>
                    <td className="px-4 py-3 text-center text-gray-500 text-xs">
                      {nf.emitida_at
                        ? new Date(nf.emitida_at).toLocaleDateString('pt-BR')
                        : new Date(nf.created_at).toLocaleDateString('pt-BR')}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {nf.enviada_whatsapp ? '✅' : '—'}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={() => setDetalhe(nf)}
                        className="px-2 py-1 rounded-md text-xs bg-gray-100 text-gray-700 hover:bg-gray-200 transition-colors"
                      >
                        Detalhes
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {total > LIMIT && (
          <div className="flex items-center justify-between px-6 py-3 border-t border-gray-100">
            <span className="text-xs text-gray-500">{total} notas</span>
            <div className="flex gap-2">
              <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="px-3 py-1 rounded border border-gray-200 text-xs disabled:opacity-40">Anterior</button>
              <span className="px-3 py-1 text-xs text-gray-500">Pág {page}</span>
              <button onClick={() => setPage(p => p + 1)} disabled={page * LIMIT >= total} className="px-3 py-1 rounded border border-gray-200 text-xs disabled:opacity-40">Próxima</button>
            </div>
          </div>
        )}
      </div>

      {showEmitir && <EmitirModal onClose={() => setEmitir(false)} onSuccess={() => load(page)} />}
      {detalhe && <DetalheModal nf={detalhe} onClose={() => setDetalhe(null)} onRefresh={() => load(page)} />}
    </div>
  )
}
