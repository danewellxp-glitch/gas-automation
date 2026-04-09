import { Bar } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Tooltip,
  Legend,
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, BarElement, LineElement, PointElement, Tooltip, Legend)

export default function CashFlowChart({ data }) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-sm text-gray-400">
        Sem dados disponíveis
      </div>
    )
  }

  const labels = data.map(d =>
    new Date(d.date + 'T00:00:00').toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
  )

  const chartData = {
    labels,
    datasets: [
      {
        type: 'bar',
        label: 'Entradas',
        data: data.map(d => parseFloat(d.income) || 0),
        backgroundColor: data.map(d => d.is_projected ? 'rgba(16,185,129,0.2)' : 'rgba(16,185,129,0.7)'),
        borderRadius: 4,
        borderSkipped: false,
        order: 2,
      },
      {
        type: 'bar',
        label: 'Saídas',
        data: data.map(d => parseFloat(d.expense) || 0),
        backgroundColor: data.map(d => d.is_projected ? 'rgba(239,68,68,0.2)' : 'rgba(239,68,68,0.65)'),
        borderRadius: 4,
        borderSkipped: false,
        order: 2,
      },
    ],
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: {
        labels: {
          color: '#9ca3af',
          boxWidth: 10,
          boxHeight: 10,
          padding: 16,
          font: { size: 12 },
          usePointStyle: true,
          pointStyle: 'rect',
        },
      },
      tooltip: {
        backgroundColor: '#ffffff',
        borderColor: '#e5e7eb',
        borderWidth: 1,
        titleColor: '#111827',
        bodyColor: '#6b7280',
        padding: 12,
        boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)',
        callbacks: {
          label: ctx =>
            ` ${ctx.dataset.label}: R$ ${ctx.raw.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`,
        },
      },
    },
    scales: {
      x: {
        ticks: { color: '#9ca3af', font: { size: 11 }, maxRotation: 0 },
        grid: { display: false },
        border: { display: false },
      },
      y: {
        ticks: {
          color: '#9ca3af',
          font: { size: 11 },
          callback: v => `R$${v >= 1000 ? (v / 1000).toFixed(0) + 'k' : v}`,
        },
        grid: { color: 'rgba(0,0,0,0.05)' },
        border: { display: false },
      },
    },
  }

  return (
    <div style={{ height: '300px' }}>
      <Bar data={chartData} options={options} />
    </div>
  )
}
