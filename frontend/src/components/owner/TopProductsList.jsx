import { Package, TrendingUp, ShoppingCart } from 'lucide-react'

export default function TopProductsList({ data }) {
    if (!data || data.length === 0) {
        return (
            <div className="flex h-40 items-center justify-center text-center">
                <p className="text-sm text-gray-500 dark:text-gray-400 dark:text-gray-400 font-medium italic">Sem dados de produtos disponíveis</p>
            </div>
        )
    }

    const top5 = data.slice(0, 5)
    const maxRevenue = Math.max(...top5.map(p => p.revenue || 0))

    return (
        <div className="space-y-6">
            {top5.map((product, idx) => {
                const percentage = maxRevenue > 0 ? ((product.revenue || 0) / maxRevenue) * 100 : 0

                return (
                    <div key={idx} className="group flex items-center gap-5">
                        <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-2xl bg-white dark:bg-slate-800 text-emerald-600 dark:text-emerald-400 border border-gray-100 dark:border-white/5 shadow-sm">
                            <ShoppingCart size={20} />
                        </div>

                        <div className="flex-1 min-w-0">
                            <div className="flex justify-between items-end mb-2">
                                <div className="truncate">
                                    <span className="text-sm font-bold text-gray-950 dark:text-white uppercase tracking-tight">{product.code || 'S.C'}</span>
                                    <span className="ml-2 text-[11px] font-bold text-slate-800 dark:text-slate-300 uppercase tracking-widest">{product.name || 'Produto Principal'}</span>
                                </div>
                                <span className="text-sm font-bold text-emerald-700 dark:text-emerald-400 font-mono">
                                    {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(product.revenue || 0)}
                                </span>
                            </div>

                            <div className="h-2 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-slate-800 shadow-inner">
                                <div
                                    className="h-full rounded-full bg-gradient-to-r from-emerald-600 to-emerald-400 dark:from-emerald-500 dark:to-emerald-300 transition-all duration-1000 ease-out shadow-lg shadow-emerald-500/20"
                                    style={{ width: `${percentage}%` }}
                                />
                            </div>
                            <div className="mt-1.5 flex justify-between items-center">
                                <span className="text-[10px] font-bold text-slate-700 dark:text-slate-400 uppercase tracking-widest">{product.quantity || 0} UNIDADES VENDIDAS</span>
                                <div className="flex items-center gap-1 text-[10px] font-bold text-emerald-500">
                                    <TrendingUp size={10} />
                                    <span>ALTA DEMANDA</span>
                                </div>
                            </div>
                        </div>
                    </div>
                )
            })}
        </div>
    )
}
