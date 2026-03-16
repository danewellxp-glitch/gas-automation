import { TrendingUp, Target, TrendingDown } from 'lucide-react'

export default function ForecastCard({ currentRevenue, onClick }) {
    // Configurações do Forecating (Idealmente viria do backend)
    const today = new Date();
    const currentDay = today.getDate();
    const daysInMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0).getDate();

    // Cálculo de projeção linear básica
    const averageDailyRevenue = currentDay > 0 ? (currentRevenue || 0) / currentDay : 0;
    const projectedMonthlyRevenue = averageDailyRevenue * daysInMonth;

    // Exemplo de Meta (Mock - R$ 100k)
    const monthlyGoal = 100000;

    const percentageToGoal = monthlyGoal > 0 ? (currentRevenue / monthlyGoal) * 100 : 0;
    const isProjectedToHitGoal = projectedMonthlyRevenue >= monthlyGoal;

    return (
        <button
            onClick={onClick}
            className="glass-card glow-card rounded-3xl border border-gray-100 dark:border-white/5 p-6 lg:p-7 text-left transition-all hover:border-primary-300 dark:hover:border-primary-500 hover:-translate-y-2 cursor-pointer w-full relative overflow-hidden"
        >
            <div className="absolute right-0 top-0 h-full w-2 bg-gradient-to-b from-indigo-400 to-indigo-600 dark:from-indigo-500 dark:to-indigo-700"></div>
            <div className="flex items-start justify-between">
                <div className="flex-1 w-full relative z-10">
                    <div className="flex items-center gap-3 mb-3">
                        <div className="p-2.5 rounded-2xl bg-indigo-500/10 dark:bg-indigo-500/20 shadow-inner border border-indigo-500/20">
                            <Target className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
                        </div>
                        <p className="text-sm font-bold text-gray-700 dark:text-slate-300 uppercase tracking-widest drop-shadow-sm">Projeção do Mês</p>
                    </div>

                    <p className="text-3xl font-black text-gray-900 dark:text-white truncate drop-shadow-md">
                        {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(projectedMonthlyRevenue)}
                    </p>

                    <div className="mt-5 w-full">
                        <div className="flex justify-between text-xs font-bold text-slate-500 dark:text-slate-400 mb-2 uppercase tracking-wide">
                            <span>Atual: {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(currentRevenue || 0)}</span>
                            <span className="text-indigo-600 dark:text-indigo-400">Meta: {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(monthlyGoal)}</span>
                        </div>

                        <div className="h-2 w-full bg-gray-100 dark:bg-slate-800 rounded-full overflow-hidden shadow-inner">
                            <div
                                className="h-full bg-gradient-to-r from-indigo-400 to-indigo-600 dark:from-indigo-500 dark:to-indigo-400 transition-all duration-1000 ease-out shadow-sm"
                                style={{ width: `${Math.min(percentageToGoal, 100)}%` }}
                            ></div>
                        </div>
                    </div>

                    <div className="mt-4 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider">
                        {isProjectedToHitGoal ? (
                            <span className="text-green-600 dark:text-green-400 flex items-center gap-1.5 bg-green-500/10 dark:bg-green-500/20 px-2 py-1 rounded-lg">
                                <TrendingUp className="h-3.5 w-3.5" /> No ritmo da meta
                            </span>
                        ) : (
                            <span className="text-amber-600 dark:text-amber-400 flex items-center gap-1.5 bg-amber-500/10 dark:bg-amber-500/20 px-2 py-1 rounded-lg">
                                <TrendingDown className="h-3.5 w-3.5" /> Abaixo do ritmo esperado
                            </span>
                        )}
                    </div>
                </div>
            </div>
        </button>
    );
}
