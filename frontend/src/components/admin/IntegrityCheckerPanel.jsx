/**
 * IntegrityCheckerPanel - Verificação de integridade do banco de dados
 * Endpoint: GET /api/integrity-check
 * 5 verificações: pedidos sem delivery, entregues sem pagamento,
 * telefones duplicados, entregas órfãs, pedidos sem itens.
 */

import { useState } from 'react'
import {
    ShieldCheck, ShieldAlert, RefreshCw, ChevronDown,
    ChevronRight, CheckCircle2, AlertTriangle, XCircle,
} from 'lucide-react'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

function fmt(dateStr) {
    if (!dateStr) return '—'
    return new Date(dateStr).toLocaleString('pt-BR', {
        day: '2-digit', month: '2-digit', year: '2-digit',
        hour: '2-digit', minute: '2-digit',
    })
}

const CHECKS_CONFIG = {
    paid_orders_without_delivery: {
        label: 'Pedidos aprovados sem entrega',
        description: 'Pedidos com status pago/preparando/em rota mas sem registro de entrega associado',
    },
    delivered_orders_without_payment: {
        label: 'Entregues sem pagamento confirmado',
        description: 'Pedidos marcados como entregues sem pagamento registrado no sistema',
    },
    duplicate_customer_phones: {
        label: 'Telefones duplicados',
        description: 'Mais de um cliente cadastrado com o mesmo número de telefone',
    },
    orphan_deliveries: {
        label: 'Entregas órfãs',
        description: 'Registros de entrega sem pedido associado válido',
    },
    orders_without_items: {
        label: 'Pedidos sem itens',
        description: 'Pedidos ativos que não possuem nenhum produto registrado',
    },
}

function CheckCard({ checkKey, data }) {
    const [expanded, setExpanded] = useState(false)
    const config = CHECKS_CONFIG[checkKey]
    if (!config) return null

    const count = data?.count ?? 0
    const items = data?.items ?? []
    const hasError = !!data?.error
    const isOk = !hasError && count === 0

    return (
        <div className={`rounded-xl border overflow-hidden ${
            hasError ? 'border-gray-200' :
            isOk ? 'border-emerald-200 bg-emerald-50/30' :
            'border-red-200 bg-red-50/30'
        }`}>
            <div className="flex items-center gap-3 px-4 py-3">
                {hasError ? (
                    <XCircle className="h-5 w-5 text-gray-400 shrink-0" />
                ) : isOk ? (
                    <CheckCircle2 className="h-5 w-5 text-emerald-500 shrink-0" />
                ) : (
                    <AlertTriangle className="h-5 w-5 text-red-500 shrink-0" />
                )}

                <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">{config.label}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{config.description}</p>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                    {hasError ? (
                        <span className="text-xs text-gray-400">Erro</span>
                    ) : (
                        <span className={`text-sm font-bold ${isOk ? 'text-emerald-600' : 'text-red-600'}`}>
                            {count} {count === 1 ? 'problema' : 'problemas'}
                        </span>
                    )}

                    {items.length > 0 && (
                        <button
                            onClick={() => setExpanded(e => !e)}
                            className="text-gray-400 hover:text-gray-600"
                        >
                            {expanded
                                ? <ChevronDown className="h-4 w-4" />
                                : <ChevronRight className="h-4 w-4" />
                            }
                        </button>
                    )}
                </div>
            </div>

            {expanded && items.length > 0 && (
                <div className="border-t border-gray-100 bg-white px-4 py-3">
                    <div className="space-y-1 max-h-52 overflow-y-auto">
                        {items.map((item, i) => (
                            <div key={i} className="text-xs text-gray-600 bg-gray-50 rounded px-3 py-1.5 font-mono">
                                {checkKey === 'duplicate_customer_phones' ? (
                                    <span>Tel: <strong>{item.phone}</strong> — {item.count} cadastros</span>
                                ) : checkKey === 'orphan_deliveries' ? (
                                    <span>Entrega <strong>{item.delivery_id?.slice(0, 8)}</strong> · status: {item.status} · {fmt(item.created_at)}</span>
                                ) : checkKey === 'delivered_orders_without_payment' ? (
                                    <span>OS <strong>#{item.order_number}</strong> · {item.payment_method} · R$ {item.total_amount?.toFixed(2)}</span>
                                ) : (
                                    <span>OS <strong>#{item.order_number}</strong> · status: {item.status} · {fmt(item.created_at)}</span>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    )
}

export default function IntegrityCheckerPanel() {
    const [result, setResult] = useState(null)
    const [loading, setLoading] = useState(false)
    const token = localStorage.getItem('token')

    const runCheck = async () => {
        setLoading(true)
        try {
            const res = await fetch(`${API_BASE}/integrity-check`, {
                headers: { Authorization: `Bearer ${token}` },
            })
            if (!res.ok) throw new Error(`HTTP ${res.status}`)
            setResult(await res.json())
        } catch (e) {
            alert('Erro ao executar verificação: ' + e.message)
        } finally {
            setLoading(false)
        }
    }

    const summary = result?.summary
    const isOk = summary?.status === 'ok'

    return (
        <div className="space-y-4">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                        <ShieldCheck className="h-5 w-5 text-blue-600" />
                        Integrity Checker
                    </h2>
                    <p className="text-xs text-gray-500 mt-0.5">
                        Verificação automática roda a cada 24h — execute manualmente para resultado imediato
                    </p>
                </div>
                <button
                    onClick={runCheck}
                    disabled={loading}
                    className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                    <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                    {loading ? 'Verificando...' : 'Executar verificação'}
                </button>
            </div>

            {/* Resultado do summary */}
            {summary && (
                <div className={`rounded-xl border px-4 py-3 flex items-center gap-3 ${
                    isOk
                        ? 'border-emerald-200 bg-emerald-50'
                        : 'border-red-200 bg-red-50'
                }`}>
                    {isOk
                        ? <ShieldCheck className="h-6 w-6 text-emerald-600 shrink-0" />
                        : <ShieldAlert className="h-6 w-6 text-red-600 shrink-0" />
                    }
                    <div>
                        <p className={`text-sm font-semibold ${isOk ? 'text-emerald-800' : 'text-red-800'}`}>
                            {isOk
                                ? 'Banco de dados íntegro — nenhuma inconsistência encontrada'
                                : `${summary.total_issues} inconsistência${summary.total_issues !== 1 ? 's' : ''} encontrada${summary.total_issues !== 1 ? 's' : ''}`
                            }
                        </p>
                        <p className="text-xs text-gray-500 mt-0.5">Verificado em {fmt(summary.checked_at)}</p>
                    </div>
                </div>
            )}

            {/* Estado inicial */}
            {!result && !loading && (
                <div className="rounded-xl border border-dashed border-gray-300 bg-gray-50 py-16 text-center">
                    <ShieldCheck className="mx-auto h-10 w-10 text-gray-300 mb-3" />
                    <p className="text-sm font-medium text-gray-500">Nenhuma verificação executada</p>
                    <p className="text-xs text-gray-400 mt-1">Clique em "Executar verificação" para analisar o banco</p>
                </div>
            )}

            {/* Cards de cada verificação */}
            {result && (
                <div className="space-y-2">
                    {Object.keys(CHECKS_CONFIG).map(key => (
                        <CheckCard key={key} checkKey={key} data={result[key]} />
                    ))}
                </div>
            )}
        </div>
    )
}
