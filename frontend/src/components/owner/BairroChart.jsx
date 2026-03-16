import { Bar } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

export default function BairroChart({ data }) {
  if (!data || data.length === 0) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-gray-500">Sem dados para exibir</p>
      </div>
    )
  }

  const isDark = document.documentElement.classList.contains('dark')
  const textColor = isDark ? '#9ca3af' : '#6b7280'
  const gridColor = isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)'

  const top10 = data.slice(0, 10)

  return (
    <div className="h-full">
      <Bar
        data={{
          labels: top10.map(b => b.bairro || 'Sem nome'),
          datasets: [
            {
              label: 'Receita',
              data: top10.map(b => b.revenue || 0),
              backgroundColor: 'rgba(59, 130, 246, 0.7)',
              borderColor: 'rgb(59, 130, 246)',
              borderWidth: 1,
              borderRadius: 4,
            },
          ],
        }}
        options={{
          responsive: true,
          maintainAspectRatio: true,
          aspectRatio: 1.2,
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: 'rgba(0, 0, 0, 0.8)',
              padding: 12,
              titleFont: { size: 13, weight: 'bold' },
              bodyFont: { size: 12 },
              callbacks: {
                label: function(context) {
                  const bairro = top10[context.dataIndex]
                  return [
                    `Receita: ${new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 2 }).format(context.parsed.y)}`,
                    `Pedidos: ${bairro.orders_count || 0}`,
                  ]
                },
              },
            },
          },
          scales: {
            x: {
              grid: { display: false },
              ticks: { color: textColor, font: { size: 11 }, maxRotation: 45, minRotation: 45 },
            },
            y: {
              beginAtZero: true,
              grid: { color: gridColor },
              ticks: {
                color: textColor,
                font: { size: 11 },
                callback: function(value) {
                  if (value >= 1000) return 'R$ ' + (value / 1000).toFixed(1) + 'k'
                  return 'R$ ' + value.toLocaleString('pt-BR')
                },
              },
            },
          },
        }}
      />
    </div>
  )
}
