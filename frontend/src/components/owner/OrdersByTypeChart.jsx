import { Doughnut } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend
} from 'chart.js'

ChartJS.register(ArcElement, Tooltip, Legend)

export default function OrdersByTypeChart({ data }) {
  try {
    if (!data) {
      return (
        <div className="flex h-full items-center justify-center">
          <p className="text-sm text-gray-500">Sem dados para exibir</p>
        </div>
      )
    }

    const troca = parseInt(data.troca || 0)
    const venda = parseInt(data.venda || 0)
    const retira = parseInt(data.retira || 0)
    const total = troca + venda + retira

    if (total === 0) {
      return (
        <div className="flex h-full items-center justify-center">
          <p className="text-sm text-gray-500">Sem pedidos para exibir</p>
        </div>
      )
    }

    const chartData = {
      labels: ['Troca', 'Venda', 'Retira'],
      datasets: [
        {
          data: [troca, venda, retira],
          backgroundColor: [
            'rgba(59, 130, 246, 0.8)',   // blue-500
            'rgba(34, 197, 94, 0.8)',    // green-500
            'rgba(251, 146, 60, 0.8)',   // orange-400
          ],
          borderColor: [
            'rgb(59, 130, 246)',
            'rgb(34, 197, 94)',
            'rgb(251, 146, 60)',
          ],
          borderWidth: 2,
        },
      ],
    }

    return (
      <div className="flex h-full flex-col">
        <div className="flex-1 flex items-center justify-center">
          <div className="w-full max-w-xs">
            <Doughnut
              data={chartData}
              options={{
                responsive: true,
                maintainAspectRatio: true,
                aspectRatio: 1,
                plugins: {
                  legend: {
                    position: 'bottom',
                    labels: {
                      padding: 15,
                      font: {
                        size: 12,
                      },
                      usePointStyle: true,
                    },
                  },
                  tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 12,
                    titleFont: {
                      size: 14,
                      weight: 'bold',
                    },
                    bodyFont: {
                      size: 13,
                    },
                    callbacks: {
                      label: function(context) {
                        const label = context.label || ''
                        const value = context.parsed || 0
                        const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0
                        return `${label}: ${value} pedidos (${percentage}%)`
                      },
                    },
                  },
                },
              }}
            />
          </div>
        </div>
        <div className="mt-4 grid grid-cols-3 gap-3 border-t border-gray-200 pt-4">
          <div className="text-center">
            <div className="text-xl font-bold text-blue-600">{troca}</div>
            <div className="text-xs font-medium text-gray-600">Troca</div>
            <div className="mt-1 text-xs text-gray-700">
              {new Intl.NumberFormat('pt-BR', {
                style: 'currency',
                currency: 'BRL',
                minimumFractionDigits: 2,
              }).format(parseFloat(data.troca_revenue || 0))}
            </div>
          </div>
          <div className="text-center">
            <div className="text-xl font-bold text-green-600">{venda}</div>
            <div className="text-xs font-medium text-gray-600">Venda</div>
            <div className="mt-1 text-xs text-gray-700">
              {new Intl.NumberFormat('pt-BR', {
                style: 'currency',
                currency: 'BRL',
                minimumFractionDigits: 2,
              }).format(parseFloat(data.venda_revenue || 0))}
            </div>
          </div>
          <div className="text-center">
            <div className="text-xl font-bold text-orange-600">{retira}</div>
            <div className="text-xs font-medium text-gray-600">Retira</div>
            <div className="mt-1 text-xs text-gray-700">
              {new Intl.NumberFormat('pt-BR', {
                style: 'currency',
                currency: 'BRL',
                minimumFractionDigits: 2,
              }).format(parseFloat(data.retira_revenue || 0))}
            </div>
          </div>
        </div>
      </div>
    )
  } catch (error) {
    console.error('Error rendering OrdersByTypeChart:', error)
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <p className="text-sm font-medium text-red-600">Erro ao renderizar gráfico</p>
          <p className="mt-1 text-xs text-gray-500">{error.message}</p>
        </div>
      </div>
    )
  }
}
