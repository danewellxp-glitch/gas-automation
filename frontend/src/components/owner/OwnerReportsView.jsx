/**
 * Owner Reports View - Relatórios Exportáveis
 * Faturamento, pedidos por produto, comissões, desempenho mensal
 */

import { useState } from 'react'
import { Download, FileText, Calendar } from 'lucide-react'

export default function OwnerReportsView() {
  const [loading, setLoading] = useState(false)
  const [startDate, setStartDate] = useState(() => {
    const date = new Date()
    date.setDate(1)
    return date.toISOString().split('T')[0]
  })
  const [endDate, setEndDate] = useState(() => {
    return new Date().toISOString().split('T')[0]
  })

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

  const reports = [
    {
      type: 'revenue',
      title: 'Faturamento',
      subtitle: 'Receita por período',
      cardBorder: 'border-blue-500/20',
      cardShadow: 'shadow-blue-500/10',
      iconBg: 'bg-blue-500/10 ring-blue-500/20',
      iconColor: 'text-blue-400',
      labelColor: 'text-blue-400/80',
      csvBtn: 'bg-blue-600 hover:bg-blue-500',
    },
    {
      type: 'orders',
      title: 'Pedidos',
      subtitle: 'Por produto',
      cardBorder: 'border-emerald-500/20',
      cardShadow: 'shadow-emerald-500/10',
      iconBg: 'bg-emerald-500/10 ring-emerald-500/20',
      iconColor: 'text-emerald-400',
      labelColor: 'text-emerald-400/80',
      csvBtn: 'bg-emerald-600 hover:bg-emerald-500',
    },
    {
      type: 'drivers',
      title: 'Comissões',
      subtitle: 'Entregadores',
      cardBorder: 'border-violet-500/20',
      cardShadow: 'shadow-violet-500/10',
      iconBg: 'bg-violet-500/10 ring-violet-500/20',
      iconColor: 'text-violet-400',
      labelColor: 'text-violet-400/80',
      csvBtn: 'bg-violet-600 hover:bg-violet-500',
    },
    {
      type: 'performance',
      title: 'Desempenho',
      subtitle: 'Mensal completo',
      cardBorder: 'border-amber-500/20',
      cardShadow: 'shadow-amber-500/10',
      iconBg: 'bg-amber-500/10 ring-amber-500/20',
      iconColor: 'text-amber-400',
      labelColor: 'text-amber-400/80',
      csvBtn: 'bg-amber-600 hover:bg-amber-500',
    },
  ]

  return (
    <div className="space-y-6">

      {/* Header */}
      <div>
        <h1 className="text-2xl font-black tracking-tight text-white">Relatórios</h1>
        <p className="mt-1 text-xs text-gray-500">Gere relatórios exportáveis para análise e tomada de decisão</p>
      </div>

      {/* Filtros */}
      <div className="rounded-2xl border border-gray-700/40 bg-gray-900 p-5">
        <div className="mb-4 flex items-center gap-2">
          <Calendar className="h-4 w-4 text-gray-400" />
          <span className="text-xs font-bold uppercase tracking-widest text-gray-400">Filtros de Período</span>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-2 block text-xs font-semibold text-gray-400 uppercase tracking-wider">
              Data Inicial
            </label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="block w-full rounded-xl border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-2 block text-xs font-semibold text-gray-400 uppercase tracking-wider">
              Data Final
            </label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="block w-full rounded-xl border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none"
            />
          </div>
        </div>
      </div>

      {/* Report Cards */}
      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {reports.map((report) => (
          <div
            key={report.type}
            className={`rounded-2xl border ${report.cardBorder} bg-gray-900 p-5 shadow-lg ${report.cardShadow}`}
          >
            <div className="mb-4 flex items-center gap-3">
              <div className={`rounded-xl ${report.iconBg} ring-1 p-3`}>
                <FileText className={`h-5 w-5 ${report.iconColor}`} />
              </div>
              <div>
                <p className={`text-xs font-bold uppercase tracking-widest ${report.labelColor}`}>
                  {report.title}
                </p>
                <p className="text-xs text-gray-500">{report.subtitle}</p>
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => handleExport('csv', report.type)}
                disabled={loading}
                className={`flex flex-1 items-center justify-center gap-1.5 rounded-xl px-3 py-2 text-xs font-bold text-white transition-colors ${report.csvBtn} disabled:opacity-40`}
              >
                <Download className="h-3.5 w-3.5" />
                CSV
              </button>
              <button
                onClick={() => handleExport('pdf', report.type)}
                disabled={loading}
                className="flex flex-1 items-center justify-center gap-1.5 rounded-xl border border-gray-700 bg-gray-800 px-3 py-2 text-xs font-bold text-gray-300 transition-colors hover:bg-gray-700 disabled:opacity-40"
              >
                <FileText className="h-3.5 w-3.5" />
                PDF
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Info Banner */}
      <div className="rounded-2xl border border-blue-500/20 bg-blue-950/20 p-4">
        <p className="text-xs text-blue-300/80">
          <strong>Nota:</strong> Os relatórios são gerados com base nos filtros selecionados e podem levar alguns segundos para processar.
          Os arquivos CSV podem ser abertos no Excel ou Google Sheets. Os PDFs são formatados para impressão.
        </p>
      </div>

    </div>
  )
}
