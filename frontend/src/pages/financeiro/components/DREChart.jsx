import { Doughnut } from 'react-chartjs-2'
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js'

ChartJS.register(ArcElement, Tooltip, Legend)

const LABELS = {
  compra_gas:          'Compra de Gás',
  combustivel:         'Combustível',
  manutencao_veiculo:  'Manutenção',
  salarios:            'Salários',
  comissao_entregador: 'Comissões',
  aluguel:             'Aluguel',
  energia_agua:        'Energia/Água',
  impostos:            'Impostos',
  marketing:           'Marketing',
  outras_despesas:     'Outros',
}

// Muted, professional palette for light background
const PALETTE = ['#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#3b82f6', '#ef4444', '#14b8a6']

export default function DREChart({ data }) {
  if (!data?.categories?.length) {
    return (
      <div className="flex items-center justify-center h-52 text-sm text-gray-400">
        Sem dados no período
      </div>
    )
  }

  const values = data.categories.map(c => parseFloat(c.total))
  const total = values.reduce((a, b) => a + b, 0)

  const chartData = {
    labels: data.categories.map(c => LABELS[c.category] || c.category),
    datasets: [{
      data: values,
      backgroundColor: PALETTE.slice(0, values.length),
      borderWidth: 2,
      borderColor: '#ffffff',
      hoverOffset: 4,
    }],
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: '68%',
    animation: {
      duration: 800,
      easing: 'easeOutCubic',
      animateRotate: true,
      animateScale: true,
    },
    transitions: {
      active: { animation: { duration: 200 } },
    },
    plugins: {
      legend: {
        position: 'bottom',
        labels: {
          color: '#6b7280',
          padding: 12,
          font: { size: 11 },
          boxWidth: 8,
          boxHeight: 8,
          usePointStyle: true,
          pointStyle: 'circle',
        },
      },
      tooltip: {
        backgroundColor: '#ffffff',
        borderColor: '#e5e7eb',
        borderWidth: 1,
        titleColor: '#111827',
        bodyColor: '#6b7280',
        callbacks: {
          label: ctx => {
            const pct = total > 0 ? ((ctx.raw / total) * 100).toFixed(1) : 0
            return ` ${ctx.label}: R$ ${ctx.raw.toLocaleString('pt-BR', { minimumFractionDigits: 2 })} · ${pct}%`
          },
        },
      },
    },
  }

  return (
    <div key={data.period || data.categories.length} className="relative animate-fade-in" style={{ height: '220px' }}>
      <Doughnut data={chartData} options={options} />
      <div
        className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none"
        style={{ bottom: '60px' }}
      >
        <div className="text-[10px] uppercase tracking-widest text-gray-400">Total</div>
        <div className="text-sm font-semibold text-gray-900">
          R$ {total >= 1000 ? `${(total / 1000).toFixed(1)}k` : total.toFixed(0)}
        </div>
      </div>
    </div>
  )
}
