import { useEffect, useMemo, useState } from 'react'
import { CheckCircle2, PlusCircle, RefreshCcw } from 'lucide-react'
import { apiRequest } from '../../utils/api'

function Badge({ status }) {
  const s = (status || '').toLowerCase()
  const cls =
    s === 'open'
      ? 'bg-red-100 text-red-700'
      : s === 'known'
      ? 'bg-amber-100 text-amber-800'
      : s === 'incident'
      ? 'bg-purple-100 text-purple-800'
      : 'bg-gray-100 text-gray-700'
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${cls}`}>{status || '-'}</span>
}

export default function ErrorCenterPanel() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [items, setItems] = useState([])

  const [filters, setFilters] = useState({
    service: '',
    error_type: '',
    status: '',
    q: '',
    since_hours: 72,
  })

  const [modal, setModal] = useState(null) // { type, id }
  const [modalText, setModalText] = useState('')

  const buildQuery = () => {
    const params = new URLSearchParams()
    if (filters.service) params.set('service', filters.service)
    if (filters.error_type) params.set('error_type', filters.error_type)
    if (filters.status) params.set('status_filter', filters.status)
    if (filters.q) params.set('q', filters.q)
    if (filters.since_hours !== null && filters.since_hours !== undefined) params.set('since_hours', String(filters.since_hours))
    return params.toString()
  }

  const fetchErrors = async () => {
    try {
      setLoading(true)
      setError('')
      const query = buildQuery()
      const res = await apiRequest(`admin/errors${query ? `?${query}` : ''}`)
      setItems(res || [])
    } catch (e) {
      setError(e.message || 'Erro ao carregar central de erros')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchErrors()
  }, [])

  const services = useMemo(() => {
    const set = new Set(items.map((i) => i.service).filter(Boolean))
    return Array.from(set).sort()
  }, [items])

  const types = useMemo(() => {
    const set = new Set(items.map((i) => i.error_type).filter(Boolean))
    return Array.from(set).sort()
  }, [items])

  const submitModal = async () => {
    if (!modal?.id) return
    try {
      setError('')
      if (modal.type === 'known') {
        await apiRequest(`admin/errors/${modal.id}/mark-known`, { method: 'POST', body: JSON.stringify({ known_reason: modalText }) })
      } else if (modal.type === 'incident') {
        await apiRequest(`admin/errors/${modal.id}/create-incident`, {
          method: 'POST',
          body: JSON.stringify({ incident_title: modalText }),
        })
      }
      setModal(null)
      setModalText('')
      await fetchErrors()
    } catch (e) {
      setError(e.message || 'Erro ao executar ação')
    }
  }

  return (
    <div>
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-gray-900">Central de Logs & Erros</h2>
          <p className="text-gray-600">Erros agregados por fingerprint com frequência e última ocorrência</p>
        </div>
        <button
          onClick={fetchErrors}
          className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          <RefreshCcw className="h-4 w-4" />
          Atualizar
        </button>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>
      )}

      <div className="mb-4 grid gap-3 rounded-lg border border-gray-200 bg-white p-4 shadow-sm md:grid-cols-5">
        <select
          value={filters.service}
          onChange={(e) => setFilters((p) => ({ ...p, service: e.target.value }))}
          className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900"
        >
          <option value="">Serviço</option>
          {services.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <select
          value={filters.error_type}
          onChange={(e) => setFilters((p) => ({ ...p, error_type: e.target.value }))}
          className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900"
        >
          <option value="">Tipo</option>
          {types.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <select
          value={filters.status}
          onChange={(e) => setFilters((p) => ({ ...p, status: e.target.value }))}
          className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900"
        >
          <option value="">Status</option>
          <option value="open">open</option>
          <option value="known">known</option>
          <option value="incident">incident</option>
        </select>
        <input
          value={filters.q}
          onChange={(e) => setFilters((p) => ({ ...p, q: e.target.value }))}
          className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900"
          placeholder="Buscar mensagem..."
        />
        <div className="flex gap-2">
          <input
            type="number"
            value={filters.since_hours}
            onChange={(e) => setFilters((p) => ({ ...p, since_hours: Number(e.target.value) }))}
            className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900"
            placeholder="h"
            min={1}
          />
          <button
            onClick={fetchErrors}
            className="rounded-lg bg-primary-600 px-3 py-2 text-sm font-medium text-white hover:bg-primary-700"
          >
            Filtrar
          </button>
        </div>
      </div>

      <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
        {loading ? (
          <div className="p-8 text-center">
            <div className="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-gray-200 border-t-primary-600" />
            <p className="mt-3 text-sm text-gray-600">Carregando erros...</p>
          </div>
        ) : items.length === 0 ? (
          <div className="p-8 text-center text-sm text-gray-600">Nenhum erro encontrado</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-gray-700">
              <thead className="bg-gray-50 text-xs uppercase text-gray-700">
                <tr>
                  <th className="px-4 py-3">Serviço</th>
                  <th className="px-4 py-3">Tipo</th>
                  <th className="px-4 py-3">Mensagem</th>
                  <th className="px-4 py-3">Frequência</th>
                  <th className="px-4 py-3">Última ocorrência</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Ações</th>
                </tr>
              </thead>
              <tbody>
                {items.map((it) => (
                  <tr key={it.id} className="border-t border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-3">{it.service}</td>
                    <td className="px-4 py-3">{it.error_type}</td>
                    <td className="px-4 py-3">
                      <div className="max-w-xl truncate">{it.message}</div>
                      <div className="mt-1 font-mono text-[11px] text-gray-400">{it.fingerprint}</div>
                    </td>
                    <td className="px-4 py-3">{it.count}</td>
                    <td className="px-4 py-3 text-gray-600">{new Date(it.last_seen).toLocaleString()}</td>
                    <td className="px-4 py-3">
                      <Badge status={it.status} />
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-2">
                        <button
                          onClick={() => {
                            setModal({ type: 'known', id: it.id })
                            setModalText('')
                          }}
                          className="inline-flex items-center gap-1 rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-700"
                        >
                          <CheckCircle2 className="h-4 w-4" />
                          Marcar conhecido
                        </button>
                        <button
                          onClick={() => {
                            setModal({ type: 'incident', id: it.id })
                            setModalText('')
                          }}
                          className="inline-flex items-center gap-1 rounded-lg bg-purple-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-purple-700"
                        >
                          <PlusCircle className="h-4 w-4" />
                          Criar incidente
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/50 p-4">
          <div className="w-full max-w-md overflow-hidden rounded-xl bg-white shadow-xl">
            <div className="border-b border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900">
                {modal.type === 'known' ? 'Marcar como conhecido' : 'Criar incidente'}
              </h3>
              <p className="mt-1 text-sm text-gray-500">ID: {modal.id}</p>
            </div>
            <div className="p-6">
              <label className="block text-sm font-medium text-gray-700">
                {modal.type === 'known' ? 'Motivo' : 'Título do incidente'}
              </label>
              <textarea
                value={modalText}
                onChange={(e) => setModalText(e.target.value)}
                rows={3}
                className="mt-2 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900"
                placeholder={modal.type === 'known' ? 'Ex: erro intermitente já monitorado' : 'Ex: Incidente - Integração WAHA indisponível'}
              />
            </div>
            <div className="flex gap-3 border-t border-gray-200 bg-gray-50 p-6">
              <button
                onClick={() => setModal(null)}
                className="flex-1 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                onClick={submitModal}
                disabled={!modalText}
                className="flex-1 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
              >
                Confirmar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

