/**
 * MonthlySparkline — gráfico de barras CSS com receita dia a dia do mês corrente
 */

import { useState, useEffect } from 'react'
import { BarChart2 } from 'lucide-react'
import { apiRequest } from '../../utils/api'

const fmt = (v) =>
  new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    maximumFractionDigits: 0,
  }).format(v || 0)

export default function MonthlySparkline() {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiRequest('owner/monthly-revenue')
      .then((d) => setData(Array.isArray(d) ? d : []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const now = new Date()
  const today = now.getDate()
  const monthDays = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate()

  const byDay = {}
  data.forEach((p) => {
    const d = new Date(p.date + 'T12:00:00').getDate()
    byDay[d] = p
  })

  const bars = Array.from({ length: monthDays }, (_, i) => ({
    day: i + 1,
    revenue: byDay[i + 1]?.revenue || 0,
    orders: byDay[i + 1]?.orders || 0,
  }))

  const maxRevenue = Math.max(...bars.map((b) => b.revenue), 1)
  const totalRevenue = data.reduce((sum, p) => sum + p.revenue, 0)
  const totalOrders = data.reduce((sum, p) => sum + p.orders, 0)

  return (
    <div className="rounded-2xl border border-gray-200 dark:border-gray-700/60 bg-white dark:bg-gray-800/60 p-6 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-gradient-to-br from-violet-400 to-purple-600 p-2.5 shadow-md shadow-violet-500/25">
            <BarChart2 className="h-4 w-4 text-white" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">Receita do Mês</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Dia a dia — {totalOrders} pedidos no mês
            </p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-lg font-black text-gray-900 dark:text-white">{fmt(totalRevenue)}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">acumulado</p>
        </div>
      </div>

      {loading ? (
        <div className="h-24 flex items-center justify-center">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-200 border-t-violet-500" />
        </div>
      ) : (
        <>
          <div className="flex items-stretch gap-px h-36">
            {bars.map(({ day, revenue, orders }) => {
              const pct = (revenue / maxRevenue) * 100
              const isToday = day === today
              const isFuture = day > today
              const fmtShort = (v) =>
                v >= 1000 ? `${(v / 1000).toFixed(1)}k` : `${Math.round(v)}`

              return (
                <div key={day} className="group relative flex-1 flex flex-col justify-end items-center">
                  {/* Valor acima da barra */}
                  {!isFuture && revenue > 0 && (
                    <span className={`text-[9px] font-bold leading-tight mb-0.5 ${isToday ? 'text-violet-400' : 'text-gray-400 dark:text-gray-500'}`}>
                      {fmtShort(revenue)}
                    </span>
                  )}
                  <div
                    className={`w-full rounded-t transition-all duration-500 ${
                      isFuture
                        ? 'bg-gray-100 dark:bg-gray-700/30'
                        : isToday
                        ? 'bg-gradient-to-t from-violet-600 to-purple-400'
                        : 'bg-gradient-to-t from-violet-800/70 to-violet-500/50 dark:from-violet-600/60 dark:to-violet-400/40'
                    }`}
                    style={{
                      height: isFuture
                        ? '3px'
                        : revenue > 0
                        ? `${Math.max(pct, 6)}%`
                        : '2px',
                      opacity: isFuture ? 0.25 : revenue > 0 ? 1 : 0.2,
                    }}
                  />

                  {/* Tooltip on hover */}
                  {!isFuture && revenue > 0 && (
                    <div className="absolute bottom-full mb-1 z-20 hidden group-hover:block bg-gray-900 text-white text-xs rounded-lg px-2.5 py-1.5 whitespace-nowrap pointer-events-none shadow-xl">
                      <span className="font-bold">Dia {day}</span>
                      <br />
                      {fmt(revenue)}
                      <br />
                      <span className="text-gray-400">{orders} pedidos</span>
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          <div className="mt-1.5 flex justify-between text-xs text-gray-400">
            <span>1</span>
            <span className="font-bold text-violet-500">{today}</span>
            <span>{monthDays}</span>
          </div>
        </>
      )}
    </div>
  )
}
