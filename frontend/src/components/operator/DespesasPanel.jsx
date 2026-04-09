/**
 * DespesasPanel — Despesas operacionais refinado para distribuidora de gás
 */

import { useState, useEffect, useCallback } from 'react'
import {
  Receipt, RefreshCw, Search, CheckCircle2, Clock, AlertTriangle,
  Bell, Plus, Pencil, Trash2, X, ChevronDown, Flame,
} from 'lucide-react'
import { toast } from 'react-hot-toast'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

const GRUPOS = [
  { value: 'glp',           label: 'Compra de GLP',         color: 'orange' },
  { value: 'frota',         label: 'Frota / Manutenção',    color: 'blue'   },
  { value: 'pessoal',       label: 'Pessoal / Folha',       color: 'violet' },
  { value: 'fixo',          label: 'Custos Fixos',          color: 'gray'   },
  { value: 'aluguel',       label: 'Aluguel / Imóvel',      color: 'yellow' },
  { value: 'impostos',      label: 'Impostos e Taxas',      color: 'red'    },
  { value: 'contabilidade', label: 'Contabilidade',         color: 'teal'   },
  { value: 'telecom',       label: 'Telefone / Internet',   color: 'sky'    },
  { value: 'seguro',        label: 'Seguros',               color: 'indigo' },
  { value: 'estoque',       label: 'Estoque / Material',    color: 'lime'   },
  { value: 'financeiro',    label: 'Financeiro / Bancário', color: 'emerald'},
  { value: 'outros',        label: 'Outros',                color: 'gray'   },
]

const GRUPO_MAP = Object.fromEntries(GRUPOS.map(g => [g.value, g]))

const COLOR_CLASSES = {
  orange:  'bg-orange-100 text-orange-700',
  blue:    'bg-blue-100 text-blue-700',
  violet:  'bg-violet-100 text-violet-700',
  gray:    'bg-gray-100 text-gray-600',
  yellow:  'bg-yellow-100 text-yellow-700',
  red:     'bg-red-100 text-red-700',
  teal:    'bg-teal-100 text-teal-700',
  sky:     'bg-sky-100 text-sky-700',
  indigo:  'bg-indigo-100 text-indigo-700',
  lime:    'bg-lime-100 text-lime-700',
  emerald: 'bg-emerald-100 text-emerald-700',
}

function fmtBRL(v) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(v || 0)
}
function fmtDate(s) {
  if (!s) return '—'
  return new Date(s + 'T12:00:00').toLocaleDateString('pt-BR')
}

function GrupoBadge({ grupo }) {
  const g = GRUPO_MAP[grupo]
  if (!g) return <span className="text-xs text-gray-400">{grupo || '—'}</span>
  const cls = COLOR_CLASSES[g.color] || 'bg-gray-100 text-gray-600'
  return <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>{g.label}</span>
}

function StatusBadge({ pago, dataVenc }) {
  if (pago) return (
    <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium bg-emerald-100 text-emerald-700">
      <CheckCircle2 className="h-3 w-3" /> Pago
    </span>
  )
  const today = new Date(); today.setHours(0,0,0,0)
  const venc  = dataVenc ? new Date(dataVenc + 'T12:00:00') : null
  if (venc && venc < today) return (
    <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium bg-red-100 text-red-700">
      <AlertTriangle className="h-3 w-3" /> Vencida
    </span>
  )
  if (venc && (venc - today) / 86400000 <= 7) return (
    <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium bg-amber-100 text-amber-700">
      <Clock className="h-3 w-3" /> Vence em breve
    </span>
  )
  return (
    <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-600">
      <Clock className="h-3 w-3" /> Pendente
    </span>
  )
}

// ── Modal Nova/Editar Despesa ─────────────────────────────
const EMPTY_FORM = {
  descricao: '', grupo: 'glp', tipo: '', fornecedor: '',
  valor: '', valor_parcela: '', parcelas_total: '1', parcela_atual: '1',
  data_vencimento: '', pago: false,
}

function DespesaModal({ initial, token, onClose, onSaved }) {
  const [form, setForm] = useState(initial ? {
    descricao: initial.descricao || '',
    grupo: initial.grupo || 'glp',
    tipo: initial.tipo || '',
    fornecedor: initial.fornecedor || '',
    valor: initial.valor ?? '',
    valor_parcela: initial.valor_parcela ?? '',
    parcelas_total: initial.parcelas_total ?? '1',
    parcela_atual: initial.parcela_atual ?? '1',
    data_vencimento: initial.data_vencimento || '',
    pago: initial.pago || false,
  } : { ...EMPTY_FORM })
  const [saving, setSaving] = useState(false)

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const save = async () => {
    if (!form.descricao.trim()) return toast.error('Descrição obrigatória')
    if (!form.valor)            return toast.error('Valor obrigatório')
    setSaving(true)
    try {
      const body = {
        ...form,
        valor: parseFloat(form.valor),
        valor_parcela: form.valor_parcela ? parseFloat(form.valor_parcela) : parseFloat(form.valor),
        parcelas_total: parseInt(form.parcelas_total) || 1,
        parcela_atual: parseInt(form.parcela_atual) || 1,
      }
      const url = initial
        ? `${API_BASE}/financeiro/despesas/${initial.id}`
        : `${API_BASE}/financeiro/despesas`
      const res = await fetch(url, {
        method: initial ? 'PUT' : 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) throw new Error()
      toast.success(initial ? 'Despesa atualizada!' : 'Despesa criada!')
      onSaved()
    } catch {
      toast.error('Erro ao salvar despesa')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-2xl bg-white shadow-xl">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h3 className="text-base font-semibold text-gray-900">
            {initial ? 'Editar Despesa' : 'Nova Despesa'}
          </h3>
          <button onClick={onClose} className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="px-6 py-4 space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Descrição *</label>
            <input value={form.descricao} onChange={e => set('descricao', e.target.value)}
              placeholder="Ex: Compra GLP P13 — Ultragaz"
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-orange-500 focus:ring-1 focus:ring-orange-500 focus:outline-none" />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Categoria *</label>
              <select value={form.grupo} onChange={e => set('grupo', e.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-orange-500 focus:ring-1 focus:ring-orange-500 focus:outline-none">
                {GRUPOS.map(g => <option key={g.value} value={g.value}>{g.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Tipo / Sub-categoria</label>
              <input value={form.tipo} onChange={e => set('tipo', e.target.value)}
                placeholder="Ex: combustível, salário…"
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-orange-500 focus:ring-1 focus:ring-orange-500 focus:outline-none" />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Fornecedor</label>
            <input value={form.fornecedor} onChange={e => set('fornecedor', e.target.value)}
              placeholder="Ex: Ultragaz, Petrobras…"
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-orange-500 focus:ring-1 focus:ring-orange-500 focus:outline-none" />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Valor Total (R$) *</label>
              <input type="number" step="0.01" value={form.valor} onChange={e => set('valor', e.target.value)}
                placeholder="0,00"
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-orange-500 focus:ring-1 focus:ring-orange-500 focus:outline-none" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Valor da Parcela (R$)</label>
              <input type="number" step="0.01" value={form.valor_parcela} onChange={e => set('valor_parcela', e.target.value)}
                placeholder="Deixe vazio = valor total"
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-orange-500 focus:ring-1 focus:ring-orange-500 focus:outline-none" />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Vencimento</label>
              <input type="date" value={form.data_vencimento} onChange={e => set('data_vencimento', e.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-orange-500 focus:ring-1 focus:ring-orange-500 focus:outline-none" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Total Parcelas</label>
              <input type="number" min="1" value={form.parcelas_total} onChange={e => set('parcelas_total', e.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-orange-500 focus:ring-1 focus:ring-orange-500 focus:outline-none" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Parcela Nº</label>
              <input type="number" min="1" value={form.parcela_atual} onChange={e => set('parcela_atual', e.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-orange-500 focus:ring-1 focus:ring-orange-500 focus:outline-none" />
            </div>
          </div>

          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={form.pago} onChange={e => set('pago', e.target.checked)}
              className="rounded border-gray-300 text-orange-500 focus:ring-orange-500" />
            <span className="text-sm text-gray-700">Já paga</span>
          </label>
        </div>

        <div className="flex justify-end gap-2 px-6 py-4 border-t border-gray-100">
          <button onClick={onClose} disabled={saving}
            className="px-4 py-2 rounded-lg border border-gray-200 text-sm font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-50">
            Cancelar
          </button>
          <button onClick={save} disabled={saving}
            className="px-4 py-2 rounded-lg bg-orange-500 text-sm font-medium text-white hover:bg-orange-600 disabled:opacity-50">
            {saving ? 'Salvando…' : initial ? 'Salvar Alterações' : 'Criar Despesa'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Main ─────────────────────────────────────────────────
export default function DespesasPanel() {
  const [despesas, setDespesas]   = useState([])
  const [alertas, setAlertas]     = useState({ vencidas: [], vencendo_7_dias: [] })
  const [loading, setLoading]     = useState(false)
  const [view, setView]           = useState('lista')
  const [grupoFilter, setGrupo]   = useState('')
  const [pagoFilter, setPago]     = useState('')
  const [search, setSearch]       = useState('')
  const [modal, setModal]         = useState(null) // null | 'new' | despesa-object
  const token = localStorage.getItem('access_token')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      let url = `${API_BASE}/financeiro/despesas?limit=300&`
      if (grupoFilter) url += `grupo=${grupoFilter}&`
      if (pagoFilter !== '') url += `pago=${pagoFilter}&`
      const [res, alertRes] = await Promise.all([
        fetch(url, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API_BASE}/financeiro/despesas/alertas`, { headers: { Authorization: `Bearer ${token}` } }),
      ])
      if (!res.ok) throw new Error()
      setDespesas(await res.json())
      if (alertRes.ok) setAlertas(await alertRes.json())
    } catch {
      toast.error('Erro ao carregar despesas')
    } finally {
      setLoading(false)
    }
  }, [grupoFilter, pagoFilter, token])

  useEffect(() => { load() }, [load])

  const handlePagar = async (id) => {
    if (!confirm('Confirmar pagamento?')) return
    try {
      const res = await fetch(`${API_BASE}/financeiro/despesas/${id}/pagar`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      })
      if (!res.ok) throw new Error()
      toast.success('Marcada como paga!')
      load()
    } catch {
      toast.error('Erro ao registrar pagamento')
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('Excluir esta despesa?')) return
    try {
      const res = await fetch(`${API_BASE}/financeiro/despesas/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error()
      toast.success('Despesa excluída')
      load()
    } catch {
      toast.error('Erro ao excluir despesa')
    }
  }

  // KPIs
  const now = new Date(); now.setHours(0, 0, 0, 0)
  const thisMonth = despesas.filter(d => {
    if (!d.data_vencimento) return false
    const dt = new Date(d.data_vencimento + 'T12:00:00')
    return dt.getMonth() === now.getMonth() && dt.getFullYear() === now.getFullYear()
  })
  const totalMes     = thisMonth.reduce((s, d) => s + parseFloat(d.valor_parcela || d.valor || 0), 0)
  const pagoMes      = thisMonth.filter(d => d.pago).reduce((s, d) => s + parseFloat(d.valor_parcela || d.valor || 0), 0)
  const pendenteMes  = totalMes - pagoMes
  const vencidas     = alertas.vencidas?.length || 0
  const vencendoBreve = alertas.vencendo_7_dias?.length || 0
  const alertCount   = vencidas + vencendoBreve

  const filtered = despesas.filter(d => {
    if (!search) return true
    const t = search.toLowerCase()
    return (
      (d.descricao || '').toLowerCase().includes(t) ||
      (d.tipo || '').toLowerCase().includes(t) ||
      (d.fornecedor || '').toLowerCase().includes(t)
    )
  })

  const TABS_VIEW = [
    { key: 'lista',       label: 'Todas' },
    { key: 'alertas',     label: alertCount > 0 ? `Alertas (${alertCount})` : 'Alertas', warn: alertCount > 0 },
    { key: 'vencimentos', label: 'Próx. Vencimentos' },
  ]

  return (
    <div className="space-y-5">
      {/* ── Header ── */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <Flame className="h-5 w-5 text-orange-500" />
            Despesas Operacionais
          </h2>
          <p className="text-xs text-gray-400 mt-0.5">Controle de gastos da distribuidora de gás</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={load} disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-gray-200 bg-white text-xs font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50">
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            Atualizar
          </button>
          <button onClick={() => setModal('new')}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-orange-500 text-xs font-semibold text-white hover:bg-orange-600">
            <Plus className="h-3.5 w-3.5" />
            Nova Despesa
          </button>
        </div>
      </div>

      {/* ── KPI Cards ── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Total do Mês',    value: fmtBRL(totalMes),    sub: `${thisMonth.length} lançamento(s)`,    color: 'text-gray-900' },
          { label: 'Pago no Mês',     value: fmtBRL(pagoMes),     sub: `${thisMonth.filter(d=>d.pago).length} quitado(s)`, color: 'text-emerald-600' },
          { label: 'Pendente Mês',    value: fmtBRL(pendenteMes), sub: `${thisMonth.filter(d=>!d.pago).length} a pagar`,   color: pendenteMes > 0 ? 'text-amber-600' : 'text-gray-900' },
          { label: 'Vencidas',        value: vencidas,            sub: `${vencendoBreve} vencem em 7d`,        color: vencidas > 0 ? 'text-red-600' : 'text-gray-900' },
        ].map((k, i) => (
          <div key={i} className="rounded-xl border border-gray-200 bg-white px-4 py-3">
            <p className="text-xs text-gray-400 mb-1">{k.label}</p>
            <p className={`text-xl font-bold ${k.color}`}>{k.value}</p>
            <p className="text-xs text-gray-400 mt-0.5">{k.sub}</p>
          </div>
        ))}
      </div>

      {/* ── Sub-tabs ── */}
      <div className="flex gap-1 border-b border-gray-200">
        {TABS_VIEW.map(t => (
          <button key={t.key} onClick={() => setView(t.key)}
            className={`px-3 py-2 text-xs font-medium border-b-2 transition-colors
              ${view === t.key
                ? 'border-orange-500 text-orange-600'
                : t.warn
                  ? 'border-transparent text-red-500 hover:text-red-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Alertas ── */}
      {view === 'alertas' && (
        <AlertasView alertas={alertas} onPagar={handlePagar} />
      )}

      {/* ── Próximos Vencimentos ── */}
      {view === 'vencimentos' && (
        <ProximosVencimentos token={token} />
      )}

      {/* ── Lista ── */}
      {view === 'lista' && (
        <>
          {/* Filtros */}
          <div className="flex flex-wrap gap-2">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-400" />
              <input type="text" placeholder="Buscar descrição, fornecedor…"
                value={search} onChange={e => setSearch(e.target.value)}
                className="rounded-lg border border-gray-200 pl-8 pr-3 py-2 text-sm w-56 focus:border-orange-500 focus:ring-1 focus:ring-orange-500 focus:outline-none" />
            </div>
            <select value={grupoFilter} onChange={e => setGrupo(e.target.value)}
              className="rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-orange-500 focus:ring-1 focus:ring-orange-500 focus:outline-none">
              <option value="">Todas as categorias</option>
              {GRUPOS.map(g => <option key={g.value} value={g.value}>{g.label}</option>)}
            </select>
            <select value={pagoFilter} onChange={e => setPago(e.target.value)}
              className="rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-orange-500 focus:ring-1 focus:ring-orange-500 focus:outline-none">
              <option value="">Todos os status</option>
              <option value="false">Pendentes</option>
              <option value="true">Pagas</option>
            </select>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-16">
              <div className="h-7 w-7 animate-spin rounded-full border-2 border-gray-200 border-t-orange-500" />
            </div>
          ) : filtered.length === 0 ? (
            <div className="rounded-xl border border-dashed border-gray-200 bg-white py-16 text-center">
              <Receipt className="mx-auto h-10 w-10 text-gray-200 mb-3" />
              <p className="text-sm text-gray-400">Nenhuma despesa encontrada</p>
              <button onClick={() => setModal('new')}
                className="mt-4 inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-orange-500 text-xs font-semibold text-white hover:bg-orange-600">
                <Plus className="h-3.5 w-3.5" /> Criar primeira despesa
              </button>
            </div>
          ) : (
            <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-100">
                  <thead className="bg-gray-50">
                    <tr>
                      {['Descrição / Fornecedor', 'Categoria', 'Vencimento', 'Parcela', 'Valor', 'Status', ''].map(h => (
                        <th key={h} className="px-3 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-gray-400">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {filtered.map(d => (
                      <tr key={d.id} className="hover:bg-orange-50/30 transition-colors group">
                        <td className="px-3 py-3 min-w-[180px]">
                          <p className="text-sm font-medium text-gray-900 truncate max-w-xs">{d.descricao}</p>
                          {d.fornecedor && <p className="text-xs text-gray-400 mt-0.5">{d.fornecedor}</p>}
                        </td>
                        <td className="px-3 py-3"><GrupoBadge grupo={d.grupo} /></td>
                        <td className="px-3 py-3 text-xs text-gray-600 whitespace-nowrap">{fmtDate(d.data_vencimento)}</td>
                        <td className="px-3 py-3 text-xs text-gray-500">
                          {d.parcelas_total > 1 ? `${d.parcela_atual}/${d.parcelas_total}` : '—'}
                        </td>
                        <td className="px-3 py-3 text-sm font-semibold text-gray-900 whitespace-nowrap">
                          {fmtBRL(d.valor_parcela || d.valor)}
                        </td>
                        <td className="px-3 py-3">
                          <StatusBadge pago={d.pago} dataVenc={d.data_vencimento} />
                        </td>
                        <td className="px-3 py-3">
                          <div className="flex items-center gap-1 justify-end opacity-0 group-hover:opacity-100 transition-opacity">
                            {!d.pago && (
                              <button onClick={() => handlePagar(d.id)}
                                className="rounded-lg border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700 hover:bg-emerald-100 whitespace-nowrap">
                                Pagar
                              </button>
                            )}
                            <button onClick={() => setModal(d)}
                              className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600">
                              <Pencil className="h-3.5 w-3.5" />
                            </button>
                            <button onClick={() => handleDelete(d.id)}
                              className="rounded-lg p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-500">
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="px-4 py-2 border-t border-gray-100 text-xs text-gray-400">
                {filtered.length} despesa(s) · Total: <span className="font-semibold text-gray-700">{fmtBRL(filtered.reduce((s,d)=>s+parseFloat(d.valor_parcela||d.valor||0),0))}</span>
              </div>
            </div>
          )}
        </>
      )}

      {/* ── Modal ── */}
      {modal && (
        <DespesaModal
          initial={modal === 'new' ? null : modal}
          token={token}
          onClose={() => setModal(null)}
          onSaved={() => { setModal(null); load() }}
        />
      )}
    </div>
  )
}

// ── Alertas view ─────────────────────────────────────────
function AlertasView({ alertas, onPagar }) {
  const all = [
    ...(alertas.vencidas || []).map(a => ({ ...a, _tipo: 'vencida' })),
    ...(alertas.vencendo_7_dias || []).map(a => ({ ...a, _tipo: 'soon' })),
  ]
  if (all.length === 0) return (
    <div className="rounded-xl border border-gray-200 bg-white py-12 text-center">
      <CheckCircle2 className="mx-auto h-10 w-10 text-emerald-400 mb-2" />
      <p className="text-sm text-gray-400">Sem alertas de vencimento</p>
    </div>
  )
  return (
    <div className="space-y-2">
      {all.map((a, i) => {
        const isVencida = a._tipo === 'vencida'
        return (
          <div key={i} className={`rounded-xl border p-3 flex items-center justify-between gap-4 ${
            isVencida ? 'border-red-200 bg-red-50' : 'border-amber-200 bg-amber-50'
          }`}>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">{a.descricao}</p>
              <p className="text-xs text-gray-500 mt-0.5">
                Venc. {a.data_vencimento ? new Date(a.data_vencimento+'T12:00:00').toLocaleDateString('pt-BR') : '—'}
                {' · '}<GrupoBadge grupo={a.grupo} />
                {a.parcelas_total > 1 && ` · Parcela ${a.parcela_atual}/${a.parcelas_total}`}
              </p>
            </div>
            <div className="text-right shrink-0">
              <p className="text-sm font-bold text-gray-900">
                {new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(a.valor_parcela||a.valor||0)}
              </p>
              <p className={`text-xs font-medium ${isVencida ? 'text-red-600' : 'text-amber-600'}`}>
                {isVencida ? 'Vencida' : 'Vence em breve'}
              </p>
            </div>
            {!a.pago && (
              <button onClick={() => onPagar(a.id)}
                className="rounded-lg border border-emerald-200 bg-white px-2.5 py-1 text-xs font-medium text-emerald-700 hover:bg-emerald-50 whitespace-nowrap">
                Pagar
              </button>
            )}
          </div>
        )
      })}
    </div>
  )
}

// ── Próximos Vencimentos ─────────────────────────────────
function ProximosVencimentos({ token }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API_BASE}/financeiro/despesas/proximos-vencimentos`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(d => setItems(Array.isArray(d) ? d : (d.items || [])))
      .catch(() => toast.error('Erro ao carregar vencimentos'))
      .finally(() => setLoading(false))
  }, [token])

  if (loading) return (
    <div className="flex items-center justify-center py-12">
      <div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-200 border-t-orange-500" />
    </div>
  )
  if (items.length === 0) return (
    <div className="rounded-xl border border-gray-200 bg-white py-12 text-center">
      <CheckCircle2 className="mx-auto h-10 w-10 text-emerald-400 mb-2" />
      <p className="text-sm text-gray-400">Nenhum vencimento nos próximos 30 dias</p>
    </div>
  )
  return (
    <div className="space-y-2">
      {items.map((item, i) => {
        const dias = item.dias_para_vencer
        const urgente = dias != null && dias <= 3
        return (
          <div key={i} className="rounded-xl border border-gray-200 bg-white p-3 flex items-center justify-between gap-4">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">{item.descricao}</p>
              <p className="text-xs text-gray-400 mt-0.5 flex items-center gap-2">
                <span>Venc. {new Date(item.data_vencimento+'T12:00:00').toLocaleDateString('pt-BR')}</span>
                <GrupoBadge grupo={item.grupo} />
                {item.parcelas_total > 1 && <span>Parcela {item.parcela_atual}/{item.parcelas_total}</span>}
              </p>
            </div>
            <div className="text-right shrink-0 flex items-center gap-3">
              {dias != null && (
                <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                  urgente ? 'bg-red-100 text-red-600' : 'bg-gray-100 text-gray-500'
                }`}>{dias === 0 ? 'Hoje' : `${dias}d`}</span>
              )}
              <p className="text-sm font-bold text-gray-900">
                {new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(item.valor_parcela||item.valor||0)}
              </p>
            </div>
          </div>
        )
      })}
    </div>
  )
}
