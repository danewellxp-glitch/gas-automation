import { Zap, TrendingUp, AlertCircle, CheckCircle2, Star } from 'lucide-react'

export default function ExecutiveInsights({ data }) {
    if (!data) return null

    const getInsights = () => {
        const insights = []
        const { financial, operational, customer_metrics } = data.cards || {}

        // Insight de Faturamento/Ticket Médio
        if (financial?.average_ticket > 100) {
            insights.push({
                type: 'success',
                icon: TrendingUp,
                title: 'TICKET MÉDIO ALTO',
                text: `Sua média de R$ ${financial.average_ticket.toFixed(2)} supera os benchs do setor.`
            })
        }

        // Insight de Eficiência Operacional
        if (operational?.on_time_delivery_rate > 90) {
            insights.push({
                type: 'info',
                icon: Zap,
                title: 'OPERAÇÃO DE ELITE',
                text: `Eficiência de ${operational.on_time_delivery_rate.toFixed(1)}%. Ritmo ideal de entregas.`
            })
        } else if (operational?.on_time_delivery_rate < 70) {
            insights.push({
                type: 'warning',
                icon: AlertCircle,
                title: 'GARGALO LOGÍSTICO',
                text: `Taxa de ${operational.on_time_delivery_rate.toFixed(1)}%. Alerta para rotas lentas.`
            })
        }

        // Insight de Retenção
        if (customer_metrics?.repeat_rate > 30) {
            insights.push({
                type: 'priority',
                icon: Star,
                title: 'FIDELIDADE ROBUSTA',
                text: `${customer_metrics.repeat_rate.toFixed(1)}% de churn negativo. Foco em Customer Success.`
            })
        }

        return insights.slice(0, 3)
    }

    const insights = getInsights()

    return (
        <div className="grid gap-6 md:grid-cols-3 mb-10">
            {insights.map((insight, idx) => (
                <div
                    key={idx}
                    className="glass-card flex flex-col items-start gap-4 p-6 rounded-3xl border border-white/5 shadow-2xl animate-fade-in stagger-1 hover:-translate-y-1 transition-transform duration-300"
                >
                    <div className="p-3 rounded-2xl bg-white dark:bg-slate-800/50 shadow-sm border border-gray-100 dark:border-white/5">
                        <div className={
                            insight.type === 'success' ? 'text-emerald-500' :
                                insight.type === 'warning' ? 'text-rose-500' :
                                    insight.type === 'priority' ? 'text-amber-500' :
                                        'text-sky-500'
                        }>
                            <insight.icon size={22} strokeWidth={2.5} />
                        </div>
                    </div>
                    <div>
                        <h4 className="text-[10px] font-bold tracking-widest mb-1 text-slate-950 dark:text-slate-200 uppercase">{insight.title}</h4>
                        <p className="text-sm font-semibold text-slate-800 dark:text-white leading-relaxed">
                            {insight.text}
                        </p>
                    </div>
                </div>
            ))}
        </div>
    )
}
