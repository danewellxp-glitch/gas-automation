import { MapPin, TrendingUp } from 'lucide-react'

export default function BairroList({ data }) {
    if (!data || data.length === 0) {
        return (
            <div className="flex h-40 items-center justify-center text-center">
                <p className="text-sm text-gray-500 dark:text-gray-400 dark:text-gray-400 font-medium italic">Sem dados regionais disponíveis</p>
            </div>
        )
    }

    const top5 = data.slice(0, 5)
    const maxRevenue = Math.max(...top5.map(b => b.revenue || 0))

    return (
        <div className="space-y-6">
            {top5.map((bairro, idx) => {
                const percentage = maxRevenue > 0 ? ((bairro.revenue || 0) / maxRevenue) * 100 : 0

                return (
                    <div key={idx} className="group flex items-center gap-5">
                        <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-2xl bg-white dark:bg-slate-800 text-primary-600 dark:text-primary-400 border border-gray-100 dark:border-white/5 shadow-sm">
                            <span className="font-black text-lg">{idx + 1}º</span>
                        </div>

                        <div className="flex-1 min-w-0">
                            <div className="flex justify-between items-end mb-2">
                                <div className="truncate">
                                    <span className="text-sm font-bold text-gray-950 dark:text-white uppercase tracking-tight">{bairro.bairro || 'Região S.N'}</span>
                                </div>
                                <span className="text-sm font-bold text-gray-950 dark:text-white font-mono">
                                    {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(bairro.revenue || 0)}
                                </span>
                            </div>

                            <div className="h-2 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-slate-800 shadow-inner">
                                <div
                                    className="h-full rounded-full bg-gradient-to-r from-primary-600 to-primary-400 dark:from-primary-500 dark:to-primary-300 transition-all duration-1000 ease-out shadow-lg"
                                    style={{ width: `${percentage}%` }}
                                />
                            </div>
                            <div className="mt-1.5 flex justify-between items-center">
                                <span className="text-[10px] font-bold text-gray-400 dark:text-slate-500 uppercase tracking-widest">{bairro.orders_count || 0} PEDIDOS</span>
                                <div className="flex items-center gap-1 text-[10px] font-bold text-green-500">
                                    <TrendingUp size={10} />
                                    <span>DESTAQUE</span>
                                </div>
                            </div>
                        </div>
                    </div>
                )
            })}
        </div>
    )
}
