/**
 * Owner Reports View — Relatórios Exportáveis
 * Design Preline-inspired: cards brancos, sem glassmorphism.
 */

import { useState } from 'react'
import { Download, FileText, Calendar } from 'lucide-react'

const REPORTS = [
  { type: 'revenue',     title: 'Faturamento',   subtitle: 'Receita por período',  iconBg: 'bg-blue-50 dark:bg-blue-900/20',     iconColor: 'text-blue-500' },
  { type: 'orders',      title: 'Pedidos',        subtitle: 'Por produto',           iconBg: 'bg-emerald-50 dark:bg-emerald-900/20', iconColor: 'text-emerald-500' },
  { type: 'drivers',     title: 'Comissões',      subtitle: 'Entregadores',          iconBg: 'bg-violet-50 dark:bg-violet-900/20', iconColor: 'text-violet-500' },
  { type: 'performance', title: 'Desempenho',     subtitle: 'Mensal completo',       iconBg: 'bg-amber-50 dark:bg-amber-900/20',   iconColor: 'text-amber-500' },
]

export default function OwnerReportsView() {
  const [loading, setLoading] = useState(false)
  const [startDate, setStartDate] = useState(() => {
    const date = new Date()
    date.setDate(1)
    return date.toISOString().split('T')[0]
  })
  const [endDate, setEndDate] = useState(() => new Date().toISOString().split('T')[0])

  const handleExport = async (format, type) => {
    try {
      setLoading(true)
      const token = localStorage.getItem('token')
      const baseUrl = import.meta.env.VITE_API_URL || 'http://192.168.10.167:8000/api'
      const url = `${baseUrl}/owner/reports/${type}?start_date=${startDate}&end_date=${endDate}&format=${format}`

      const response = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}` },
      })

      if (!response.ok) throw new Error('Erro ao gerar relatório')

      const blob = await response.blob()
      const blobUrl = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = blobUrl
      link.setAttribute('download', `relatorio_${type}_${startDate}_${endDate}.${format}`)
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(blobUrl)
    } catch (err) {
      console.error('Erro ao exportar relatório:', err)
      alert('Erro ao exportar relatório. Tente novamente.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">

      {/* Header */}
      <div>
        <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Relatórios</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">Gere relatórios exportáveis para análise e tomada de decisão</p>
      </div>

      {/* Filtros */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
        <div className="flex items-center gap-2 mb-4">
          <Calendar className="w-4 h-4 text-gray-400 dark:text-gray-500" />
          <span className="text-sm font-semibold text-gray-900 dark:text-white">Período</span>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5">Data Inicial</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="block w-full rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5">Data Final</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="block w-full rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          </div>
        </div>
      </div>

      {/* Report Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {REPORTS.map((report) => (
          <div
            key={report.type}
            className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5"
          >
            <div className="flex items-center gap-3 mb-4">
              <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${report.iconBg}`}>
                <FileText className={`w-4 h-4 ${report.iconColor}`} />
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-900 dark:text-white">{report.title}</p>
                <p className="text-xs text-gray-400 dark:text-gray-500">{report.subtitle}</p>
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => handleExport('csv', report.type)}
                disabled={loading}
                className="flex flex-1 items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-xs font-medium text-white bg-primary-600 hover:bg-primary-700 transition-colors disabled:opacity-40"
              >
                <Download className="w-3.5 h-3.5" />
                CSV
              </button>
              <button
                onClick={() => handleExport('pdf', report.type)}
                disabled={loading}
                className="flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors disabled:opacity-40"
              >
                <FileText className="w-3.5 h-3.5" />
                PDF
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Info */}
      <div className="rounded-xl border border-blue-200 dark:border-blue-700/40 bg-blue-50 dark:bg-blue-900/10 p-4">
        <p className="text-sm text-blue-700 dark:text-blue-400">
          Os relatórios são gerados com base no período selecionado. Arquivos CSV podem ser abertos no Excel ou Google Sheets. PDFs são formatados para impressão.
        </p>
      </div>

    </div>
  )
}
