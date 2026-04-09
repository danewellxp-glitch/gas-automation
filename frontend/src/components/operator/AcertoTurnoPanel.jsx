/**
 * AcertoTurnoPanel - Aprovação de acerto de turno dos entregadores
 * Operador vê turnos aguardando aprovação, confere os itens e aprova/rejeita.
 * Endpoint base: /api/drivers/turno/
 */

import { useState, useEffect, useCallback } from 'react'
import {
    ClipboardCheck, RefreshCw, CheckCircle2, XCircle,
    ChevronDown, ChevronRight, TrendingUp, TrendingDown,
    Minus, Truck, Clock, AlertTriangle,
} from 'lucide-react'
import { toast } from 'react-hot-toast'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

function fmtBRL(v) {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(v || 0)
}
function fmtDate(s) {
    if (!s) return '—'
    return new Date(s).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

const PAYMENT_LABELS = {
    pix: 'PIX', cash: 'Dinheiro', credit_card: 'Cartão Crédito',
    debit_card: 'Cartão Débito', boleto: 'Boleto',
}

function DiferencaBadge({ diferenca }) {
    if (!diferenca && diferenca !== 0) return null
    const d = Number(diferenca)
    if (d > 0)  return <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-700 bg-emerald-100 rounded-full px-2 py-0.5"><TrendingUp className="h-3 w-3" />+{fmtBRL(d)}</span>
    if (d < 0)  return <span className="inline-flex items-center gap-1 text-xs font-semibold text-red-700 bg-red-100 rounded-full px-2 py-0.5"><TrendingDown className="h-3 w-3" />{fmtBRL(d)}</span>
    return <span className="inline-flex items-center gap-1 text-xs font-semibold text-gray-600 bg-gray-100 rounded-full px-2 py-0.5"><Minus className="h-3 w-3" />Zerado</span>
}

export default function AcertoTurnoPanel() {
    const [turnos, setTurnos] = useState([])
    const [drivers, setDrivers] = useState({}) // id → name
    const [loading, setLoading] = useState(false)
    const [expanded, setExpanded] = useState(new Set())
    const [details, setDetails] = useState({}) // turno_id → itens
    const [loadingDetail, setLoadingDetail] = useState(new Set())
    const [modal, setModal] = useState(null) // { turno, action: 'aprovar'|'rejeitar' }
    const [motivo, setMotivo] = useState('')
    const [processing, setProcessing] = useState(false)
    const token = localStorage.getItem('token')

    const load = useCallback(async () => {
        setLoading(true)
        try {
            const [turnosRes, driversRes] = await Promise.all([
                fetch(`${API_BASE}/drivers/turno/pendentes`, { headers: { Authorization: `Bearer ${token}` } }),
                fetch(`${API_BASE}/drivers/`, { headers: { Authorization: `Bearer ${token}` } }),
            ])
            if (!turnosRes.ok) throw new Error(`HTTP ${turnosRes.status}`)
            const turnosData = await turnosRes.json()
            setTurnos(turnosData)

            if (driversRes.ok) {
                const driversData = await driversRes.json()
                const map = {}
                ;(driversData || []).forEach(d => { map[d.id] = d.name })
                setDrivers(map)
            }
        } catch {
            toast.error('Erro ao carregar turnos pendentes')
        } finally {
            setLoading(false)
        }
    }, [token])

    useEffect(() => { load() }, [load])

    const toggleExpand = async (turno) => {
        const id = turno.id
        setExpanded(prev => {
            const next = new Set(prev)
            if (next.has(id)) { next.delete(id); return next }
            next.add(id)
            return next
        })
        // Carrega detalhes se ainda não carregou
        if (!details[id]) {
            setLoadingDetail(prev => new Set([...prev, id]))
            try {
                const res = await fetch(`${API_BASE}/drivers/turno/${id}`, {
                    headers: { Authorization: `Bearer ${token}` },
                })
                if (res.ok) {
                    const data = await res.json()
                    setDetails(prev => ({ ...prev, [id]: data.itens || [] }))
                }
            } catch {
                toast.error('Erro ao carregar detalhes do turno')
            } finally {
                setLoadingDetail(prev => { const next = new Set(prev); next.delete(id); return next })
            }
        }
    }

    const handleAprovar = async () => {
        if (!modal) return
        setProcessing(true)
        try {
            const res = await fetch(`${API_BASE}/drivers/turno/${modal.turno.id}/aprovar`, {
                method: 'POST',
                headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ observacao: motivo || null }),
            })
            if (!res.ok) throw new Error()
            toast.success('Turno aprovado!')
            setModal(null)
            setMotivo('')
            load()
        } catch {
            toast.error('Erro ao aprovar turno')
        } finally {
            setProcessing(false)
        }
    }

    const handleRejeitar = async () => {
        if (!motivo.trim()) { toast.error('Informe o motivo da rejeição'); return }
        setProcessing(true)
        try {
            const res = await fetch(`${API_BASE}/drivers/turno/${modal.turno.id}/rejeitar`, {
                method: 'POST',
                headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ observacao: motivo }),
            })
            if (!res.ok) throw new Error()
            toast.success('Turno rejeitado')
            setModal(null)
            setMotivo('')
            load()
        } catch {
            toast.error('Erro ao rejeitar turno')
        } finally {
            setProcessing(false)
        }
    }

    return (
        <div className="space-y-4">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                        <ClipboardCheck className="h-5 w-5 text-violet-600" />
                        Acerto de Turno
                    </h2>
                    <p className="text-xs text-gray-500 mt-0.5">Turnos aguardando aprovação do operador</p>
                </div>
                <button onClick={load} disabled={loading}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-200 bg-white text-gray-600 hover:bg-gray-50 disabled:opacity-50">
                    <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
                    Atualizar
                </button>
            </div>

            {/* Lista */}
            {loading ? (
                <div className="flex items-center justify-center py-16">
                    <div className="h-7 w-7 animate-spin rounded-full border-2 border-gray-200 border-t-violet-600" />
                </div>
            ) : turnos.length === 0 ? (
                <div className="rounded-xl border border-gray-200 bg-white py-16 text-center">
                    <ClipboardCheck className="mx-auto h-10 w-10 text-gray-300 mb-3" />
                    <p className="text-sm font-medium text-gray-500">Nenhum turno aguardando aprovação</p>
                    <p className="text-xs text-gray-400 mt-1">Os entregadores precisam finalizar o turno pelo app</p>
                </div>
            ) : (
                <div className="space-y-2">
                    {turnos.map(turno => {
                        const isExp = expanded.has(turno.id)
                        const isLoadingDet = loadingDetail.has(turno.id)
                        const itens = details[turno.id] || []
                        const driverName = drivers[turno.driver_id] || `Motorista ${turno.driver_id?.slice(0, 8)}`
                        const diferenca = turno.diferenca

                        return (
                            <div key={turno.id} className="rounded-xl border border-gray-200 bg-white overflow-hidden">
                                {/* Linha principal */}
                                <div className="flex items-center gap-3 px-4 py-3">
                                    <button onClick={() => toggleExpand(turno)}
                                        className="text-gray-400 hover:text-gray-600 shrink-0">
                                        {isExp ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                                    </button>

                                    <Truck className="h-4 w-4 text-violet-500 shrink-0" />

                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm font-semibold text-gray-900">{driverName}</p>
                                        <p className="text-xs text-gray-500 mt-0.5">
                                            <Clock className="inline h-3 w-3 mr-0.5" />
                                            {fmtDate(turno.iniciado_em)} → {fmtDate(turno.finalizado_em)}
                                        </p>
                                    </div>

                                    {/* Totais */}
                                    <div className="hidden sm:flex flex-col items-end gap-0.5 shrink-0">
                                        <p className="text-xs text-gray-500">Esperado: <span className="font-medium text-gray-700">{fmtBRL(turno.total_esperado)}</span></p>
                                        <p className="text-xs text-gray-500">Cobrado: <span className="font-medium text-gray-700">{fmtBRL(turno.total_cobrado)}</span></p>
                                    </div>

                                    <DiferencaBadge diferenca={diferenca} />

                                    {/* Ações */}
                                    <div className="flex gap-1.5 shrink-0">
                                        <button
                                            onClick={() => { setModal({ turno, action: 'aprovar' }); setMotivo('') }}
                                            className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-700 hover:bg-emerald-100">
                                            <CheckCircle2 className="h-3.5 w-3.5" />
                                            Aprovar
                                        </button>
                                        <button
                                            onClick={() => { setModal({ turno, action: 'rejeitar' }); setMotivo('') }}
                                            className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-lg bg-red-50 border border-red-200 text-red-700 hover:bg-red-100">
                                            <XCircle className="h-3.5 w-3.5" />
                                            Rejeitar
                                        </button>
                                    </div>
                                </div>

                                {/* Detalhes expandidos */}
                                {isExp && (
                                    <div className="border-t border-gray-100 bg-gray-50 px-4 py-3">
                                        {turno.observacao && (
                                            <p className="text-xs text-amber-700 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2 mb-3">
                                                Obs: {turno.observacao}
                                            </p>
                                        )}

                                        {isLoadingDet ? (
                                            <div className="flex justify-center py-4">
                                                <div className="h-5 w-5 animate-spin rounded-full border-2 border-gray-200 border-t-violet-600" />
                                            </div>
                                        ) : itens.length === 0 ? (
                                            <p className="text-xs text-gray-400 text-center py-3">Nenhum item lançado</p>
                                        ) : (
                                            <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
                                                <table className="min-w-full text-xs">
                                                    <thead className="bg-gray-50">
                                                        <tr>
                                                            <th className="px-3 py-2 text-left font-medium text-gray-500">#</th>
                                                            <th className="px-3 py-2 text-right font-medium text-gray-500">Esperado</th>
                                                            <th className="px-3 py-2 text-right font-medium text-gray-500">Cobrado</th>
                                                            <th className="px-3 py-2 text-left font-medium text-gray-500">Pagto.</th>
                                                            <th className="px-3 py-2 text-center font-medium text-gray-500">Entregue</th>
                                                            <th className="px-3 py-2 text-left font-medium text-gray-500">Obs</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody className="divide-y divide-gray-50">
                                                        {itens.map((item, i) => {
                                                            const diff = Number(item.valor_cobrado) - Number(item.valor_pedido)
                                                            return (
                                                                <tr key={item.id} className="hover:bg-gray-50">
                                                                    <td className="px-3 py-2 text-gray-500">{i + 1}</td>
                                                                    <td className="px-3 py-2 text-right text-gray-700">{fmtBRL(item.valor_pedido)}</td>
                                                                    <td className={`px-3 py-2 text-right font-medium ${diff < 0 ? 'text-red-600' : diff > 0 ? 'text-emerald-600' : 'text-gray-900'}`}>
                                                                        {fmtBRL(item.valor_cobrado)}
                                                                    </td>
                                                                    <td className="px-3 py-2 text-gray-600">{PAYMENT_LABELS[item.payment_method] || item.payment_method || '—'}</td>
                                                                    <td className="px-3 py-2 text-center">
                                                                        {item.entregue
                                                                            ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 mx-auto" />
                                                                            : <AlertTriangle className="h-3.5 w-3.5 text-amber-500 mx-auto" />
                                                                        }
                                                                    </td>
                                                                    <td className="px-3 py-2 text-gray-500 max-w-xs truncate">{item.observacao || '—'}</td>
                                                                </tr>
                                                            )
                                                        })}
                                                    </tbody>
                                                    <tfoot className="bg-gray-50 border-t border-gray-200">
                                                        <tr>
                                                            <td className="px-3 py-2 text-xs font-semibold text-gray-600" colSpan={2}>Total</td>
                                                            <td className="px-3 py-2 text-right text-xs font-bold text-gray-900">{fmtBRL(turno.total_cobrado)}</td>
                                                            <td colSpan={3} className="px-3 py-2">
                                                                <DiferencaBadge diferenca={diferenca} />
                                                            </td>
                                                        </tr>
                                                    </tfoot>
                                                </table>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        )
                    })}
                </div>
            )}

            {/* Modal aprovar/rejeitar */}
            {modal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
                    <div className="w-full max-w-sm rounded-xl bg-white shadow-2xl overflow-hidden">
                        <div className={`px-6 py-4 border-b border-gray-100 ${modal.action === 'aprovar' ? 'bg-emerald-50' : 'bg-red-50'}`}>
                            <h3 className="text-base font-semibold text-gray-900">
                                {modal.action === 'aprovar' ? 'Aprovar turno' : 'Rejeitar turno'}
                            </h3>
                            <p className="text-sm text-gray-500 mt-0.5">
                                {drivers[modal.turno.driver_id] || 'Motorista'} · Diferença: <DiferencaBadge diferenca={modal.turno.diferenca} />
                            </p>
                        </div>
                        <div className="px-6 py-4">
                            <label className="block text-sm font-medium text-gray-700 mb-1.5">
                                {modal.action === 'aprovar' ? 'Observação (opcional)' : 'Motivo da rejeição *'}
                            </label>
                            <textarea
                                value={motivo}
                                onChange={e => setMotivo(e.target.value)}
                                rows={3}
                                placeholder={modal.action === 'aprovar' ? 'Ex: conferido com recibos' : 'Ex: valor cobrado divergente'}
                                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-violet-500 focus:ring-1 focus:ring-violet-500 focus:outline-none"
                            />
                        </div>
                        <div className="flex gap-3 px-6 pb-6">
                            <button onClick={() => { setModal(null); setMotivo('') }} disabled={processing}
                                className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50">
                                Cancelar
                            </button>
                            <button
                                onClick={modal.action === 'aprovar' ? handleAprovar : handleRejeitar}
                                disabled={processing}
                                className={`flex-1 rounded-lg px-4 py-2 text-sm font-medium text-white disabled:opacity-50 ${modal.action === 'aprovar' ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-red-600 hover:bg-red-700'}`}>
                                {processing ? 'Processando...' : modal.action === 'aprovar' ? 'Confirmar aprovação' : 'Confirmar rejeição'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
