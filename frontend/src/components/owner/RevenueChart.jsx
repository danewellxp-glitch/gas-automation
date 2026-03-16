import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

export default function RevenueChart({ data }) {
  try {
    if (!data || (!data.current && !data.previous)) {
      return (
        <div className="flex h-64 items-center justify-center">
          <p className="text-gray-500">Sem dados para exibir</p>
        </div>
      )
    }

    const current = Array.isArray(data.current) ? data.current : []
    const previous = Array.isArray(data.previous) ? data.previous : []

    if (current.length === 0 && previous.length === 0) {
      return (
        <div className="flex h-64 items-center justify-center">
          <p className="text-gray-500">Sem dados para exibir</p>
        </div>
      )
    }

    // Formatar labels de data
    const formatDate = (dateStr) => {
      try {
        const date = new Date(dateStr)
        if (isNaN(date.getTime())) return dateStr
        if (data.period === 'day') {
          return date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
        } else if (data.period === 'week') {
          return date.toLocaleDateString('pt-BR', { weekday: 'short', day: '2-digit' })
        } else {
          return date.toLocaleDateString('pt-BR', { month: 'short', day: '2-digit' })
        }
      } catch (e) {
        return dateStr
      }
    }

    const currentLabels = current.map(p => formatDate(p?.date || ''))
    const previousLabels = previous.map(p => formatDate(p?.date || ''))

    // Garantir que ambos tenham o mesmo número de pontos (preencher com zeros se necessário)
    const maxLength = Math.max(currentLabels.length, previousLabels.length)
    const currentRevenue = current.map(p => parseFloat(p?.revenue || 0))
    const previousRevenue = previous.map(p => parseFloat(p?.revenue || 0))

    while (currentRevenue.length < maxLength) currentRevenue.push(0)
    while (previousRevenue.length < maxLength) previousRevenue.push(0)

    const isDark = document.documentElement.classList.contains('dark')
    const textColor = isDark ? '#9ca3af' : '#6b7280'
    const gridColor = isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)'

    return (
    <Line
      data={{
        labels: currentLabels.length > 0 ? currentLabels : previousLabels,
        datasets: [
          {
            label: 'Período Atual',
            data: currentRevenue,
            borderColor: 'rgb(34, 197, 94)',
            backgroundColor: 'rgba(34, 197, 94, 0.1)',
            tension: 0.4,
            fill: true,
          },
          {
            label: 'Período Anterior',
            data: previousRevenue,
            borderColor: 'rgb(156, 163, 175)',
            backgroundColor: 'rgba(156, 163, 175, 0.1)',
            tension: 0.4,
            fill: true,
            borderDash: [5, 5],
          },
        ],
      }}
      options={{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            position: 'top',
            labels: { color: textColor },
          },
          tooltip: {
            callbacks: {
              label: function(context) {
                return `${context.dataset.label}: ${new Intl.NumberFormat('pt-BR', {
                  style: 'currency',
                  currency: 'BRL',
                }).format(context.parsed.y)}`
              },
            },
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              color: textColor,
              callback: function(value) {
                return 'R$ ' + value.toLocaleString('pt-BR')
              },
            },
            grid: { color: gridColor },
          },
        },
      }}
      height={300}
    />
    )
  } catch (error) {
    console.error('Error rendering RevenueChart:', error)
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="text-center">
          <p className="text-red-500">Erro ao renderizar gráfico</p>
          <p className="text-xs text-gray-500 mt-1">{error.message}</p>
        </div>
      </div>
    )
  }
}
