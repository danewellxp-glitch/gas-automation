import { Users, AlertTriangle, MessageSquare, ExternalLink, Shield } from 'lucide-react'

export default function RetentionRadar({ data }) {
    const topCustomers = data?.customer_metrics?.top_customers || []

    const getRiskStatus = (lastOrderDate) => {
        if (!lastOrderDate) return { label: 'Sem dados', color: 'text-gray-400', bg: 'bg-gray-100', icon: AlertTriangle }

        const lastDate = new Date(lastOrderDate)
        const now = new Date()
        const diffDays = Math.floor((now - lastDate) / (1000 * 60 * 60 * 24))

        if (diffDays > 15) return { label: 'ALTO RISCO', level: 3 }
        if (diffDays > 7) return { label: 'ATENÇÃO', level: 2 }
        return { label: 'ATIVO', level: 1 }
    }

    const customersAtRisk = topCustomers
        .map(c => ({ ...c, risk: getRiskStatus(c.last_order_date) }))
        .filter(c => c.risk.level >= 2)
        .sort((a, b) => b.risk.level - a.risk.level)
        .slice(0, 5)

    if (customersAtRisk.length === 0) return (
        <div className="glass-card rounded-3xl p-8 h-full flex flex-col items-center justify-center text-center shadow-lg">
            <div className="p-4 rounded-2xl bg-emerald-50 text-emerald-600 mb-4 shadow-sm border border-emerald-100">
                <Shield size={32} strokeWidth={2.5} />
            </div>
            <h3 className="text-lg font-bold text-gray-900 dark:text-white tracking-tight">Fidelidade Blindada</h3>
            <p className="text-sm text-gray-500 dark:text-slate-400 mt-2 font-medium">Seus principais clientes estão ativos na base.</p>
        </div>
    )

    return (
        <div className="glass-card rounded-3xl p-8 h-full flex flex-col animate-fade-in stagger-2 shadow-2xl border border-white/5">
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h3 className="text-xl font-bold text-gray-950 dark:text-white tracking-tight">Radar de Churn</h3>
                    <p className="text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-widest mt-1">Controle de Retenção</p>
                </div>
                <div className="p-3 rounded-2xl bg-white dark:bg-slate-800/50 text-rose-500 shadow-sm border border-gray-100 dark:border-white/5">
                    <AlertTriangle size={24} />
                </div>
            </div>

            <div className="space-y-6 flex-1">
                {customersAtRisk.map((customer, idx) => (
                    <div key={idx} className="flex items-center justify-between group p-3 rounded-2xl hover:bg-gray-50 dark:hover:bg-slate-800/40 transition-colors">
                        <div className="flex items-center gap-4">
                            <div className="h-12 w-12 rounded-2xl bg-white dark:bg-slate-800/80 flex items-center justify-center font-bold text-gray-600 dark:text-slate-400 shadow-sm border border-gray-100 dark:border-white/5">
                                {customer.name.slice(0, 1).toUpperCase()}
                            </div>
                            <div className="min-w-0">
                                <p className="text-sm font-bold text-gray-950 dark:text-white uppercase truncate max-w-[140px]">
                                    {customer.name}
                                </p>
                                <div className="flex items-center gap-2 mt-1">
                                    <span className={`text-[9px] px-2 py-0.5 rounded-lg font-bold tracking-widest border ${customer.risk.level === 3
                                        ? 'bg-rose-100 border-rose-200 text-rose-800 dark:bg-rose-900/40 dark:border-rose-500/20 dark:text-rose-400'
                                        : 'bg-amber-100 border-amber-200 text-amber-800 dark:bg-amber-900/40 dark:border-amber-500/20 dark:text-amber-400'
                                        }`}>
                                        {customer.risk.label}
                                    </span>
                                </div>
                            </div>
                        </div>

                        <button
                            className="h-10 w-10 flex items-center justify-center rounded-xl bg-emerald-500 text-white shadow-lg shadow-emerald-500/30 opacity-0 group-hover:opacity-100 transition-all hover:scale-110 active:scale-95"
                            title="Reativar via WhatsApp"
                        >
                            <MessageSquare size={18} fill="currentColor" />
                        </button>
                    </div>
                ))}
            </div>

            <button className="mt-8 w-full py-4 rounded-2xl border-2 border-dashed border-gray-100 dark:border-slate-800/50 text-[10px] font-black uppercase tracking-widest text-gray-400 hover:text-primary-500 hover:border-primary-500/50 transition-all flex items-center justify-center gap-2">
                ACESSAR PAINEL VIP COMPLETO <ExternalLink size={14} />
            </button>
        </div>
    )
}
