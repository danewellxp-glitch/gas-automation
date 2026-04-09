/**
 * MonthlySparkline — gráfico de barras CSS com receita dia a dia do mês corrente
 * Design Preline-inspired: card branco, sem glassmorphism.
 */

import { useState, useEffect } from 'react'
import { BarChart2 } from 'lucide-react'
import { apiRequest } from '../../utils/api'

const fmtPrice = (v) =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 2 }).format(v || 0)

const fmt = (v) =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 }).format(v || 0)

export default function MonthlySparkline() {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [priceChanges, setPriceChanges] = useState({})

  useEffect(() => {
    apiRequest('owner/monthly-revenue')
      .then((d) => setData(Array.isArray(d) ? d : []))
      .catch(() => {})
      .finally(() => setLoading(false))

    apiRequest('owner/price-changes-this-month')
      .then((d) => {
        const map = {}
        if (Array.isArray(d)) d.forEach(({ date, changes }) => { map[date] = changes })
        setPriceChanges(map)
      })
      .catch(() => {})
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
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-primary-50 dark:bg-primary-900/20 flex items-center justify-center">
            <BarChart2 className="w-4 h-4 text-primary-500" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Receita do Mês</h3>
            <p className="text-xs text-gray-400 dark:text-gray-500">
              {totalOrders} pedidos no mês
            </p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-base font-bold text-gray-900 dark:text-white">{fmt(totalRevenue)}</p>
          <p className="text-xs text-gray-400 dark:text-gray-500">acumulado</p>
        </div>
      </div>

      {loading ? (
        <div className="h-24 flex items-center justify-center">
          <div className="w-5 h-5 animate-spin rounded-full border-2 border-gray-200 border-t-primary-500" />
        </div>
      ) : (
        <>
          <div className="flex items-stretch gap-px h-32">
            {bars.map(({ day, revenue, orders }) => {
              const pct = (revenue / maxRevenue) * 100
              const isToday = day === today
              const isFuture = day > today
              const fmtShort = (v) => v >= 1000 ? `${(v / 1000).toFixed(1)}k` : `${Math.round(v)}`

              const dateKey = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
              const changes = priceChanges[dateKey] || []
              const hasChange = changes.length > 0

              return (
                <div key={day} className="group relative flex-1 flex flex-col justify-end items-center">
                  {!isFuture && revenue > 0 && (
                    <span className={`text-[9px] leading-tight mb-0.5 ${isToday ? 'text-primary-500 font-semibold' : 'text-gray-400 dark:text-gray-500'}`}>
                      {fmtShort(revenue)}
                    </span>
                  )}
                  <div
                    className={`w-full rounded-t transition-all duration-500 ${
                      isFuture
                        ? 'bg-gray-100 dark:bg-gray-700'
                        : isToday
                        ? 'bg-primary-500'
                        : 'bg-primary-200 dark:bg-primary-800'
                    }`}
                    style={{
                      height: isFuture ? '2px' : revenue > 0 ? `${Math.max(pct, 6)}%` : '2px',
                      opacity: isFuture ? 0.3 : revenue > 0 ? 1 : 0.25,
                    }}
                  />

                  {hasChange && (
                    <div className="price-change-marker absolute -bottom-3 left-1/2 -translate-x-1/2 z-10">
                      <div className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                      <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 z-30 hidden group-hover:block bg-gray-900 dark:bg-gray-700 text-white text-[10px] rounded-lg px-2 py-1.5 whitespace-nowrap pointer-events-none shadow-xl min-w-max">
                        <p className="font-semibold text-amber-400 mb-1">Preço alterado</p>
                        {changes.map((c, i) => (
                          <p key={i} className="text-gray-300">{c.product_name}: {fmtPrice(c.old_price)} → {fmtPrice(c.new_price)}</p>
                        ))}
                      </div>
                    </div>
                  )}

                  {!isFuture && revenue > 0 && (
                    <div className="absolute bottom-full mb-1 z-20 hidden group-hover:block bg-gray-900 text-white text-xs rounded-lg px-2.5 py-1.5 whitespace-nowrap pointer-events-none shadow-xl">
                      <span className="font-semibold">Dia {day}</span>
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

          <div className="mt-1.5 flex justify-between text-xs text-gray-400 dark:text-gray-500">
            <span>1</span>
            <span className="font-semibold text-primary-500">{today}</span>
            <span>{monthDays}</span>
          </div>
        </>
      )}
    </div>
  )
}
