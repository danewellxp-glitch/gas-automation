/**
 * Owner Reports View - Relatórios Exportáveis
 * Faturamento, pedidos por produto, comissões, desempenho mensal
 */

import { useState } from 'react'
import { Download, FileText } from 'lucide-react'

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
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })
      
      if (!response.ok) {
        throw new Error('Erro ao gerar relatório')
      }
      
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
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Relatórios</h1>
        <p className="mt-1 text-sm text-gray-600">
          Gere relatórios exportáveis para análise e tomada de decisão
        </p>
      </div>

      {/* Filtros */}
      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">Filtros</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">
              Data Inicial
            </label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-primary-500 focus:ring-primary-500"
            />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">
              Data Final
            </label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-primary-500 focus:ring-primary-500"
            />
          </div>
        </div>
      </div>

      {/* Cards de Relatórios */}
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center gap-3">
            <div className="rounded-lg bg-blue-50 p-3">
              <FileText className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Faturamento</h3>
              <p className="text-xs text-gray-500">Receita por período</p>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => handleExport('csv', 'revenue')}
              disabled={loading}
              className="flex-1 rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              <Download className="mr-2 inline h-4 w-4" />
              CSV
            </button>
            <button
              onClick={() => handleExport('pdf', 'revenue')}
              disabled={loading}
              className="flex-1 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              PDF
            </button>
          </div>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center gap-3">
            <div className="rounded-lg bg-green-50 p-3">
              <FileText className="h-6 w-6 text-green-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Pedidos</h3>
              <p className="text-xs text-gray-500">Por produto</p>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => handleExport('csv', 'orders')}
              disabled={loading}
              className="flex-1 rounded-lg bg-green-600 px-3 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
            >
              <Download className="mr-2 inline h-4 w-4" />
              CSV
            </button>
            <button
              onClick={() => handleExport('pdf', 'orders')}
              disabled={loading}
              className="flex-1 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              PDF
            </button>
          </div>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center gap-3">
            <div className="rounded-lg bg-purple-50 p-3">
              <FileText className="h-6 w-6 text-purple-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Comissões</h3>
              <p className="text-xs text-gray-500">Entregadores</p>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => handleExport('csv', 'drivers')}
              disabled={loading}
              className="flex-1 rounded-lg bg-purple-600 px-3 py-2 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50"
            >
              <Download className="mr-2 inline h-4 w-4" />
              CSV
            </button>
            <button
              onClick={() => handleExport('pdf', 'drivers')}
              disabled={loading}
              className="flex-1 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              PDF
            </button>
          </div>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center gap-3">
            <div className="rounded-lg bg-amber-50 p-3">
              <FileText className="h-6 w-6 text-amber-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Desempenho</h3>
              <p className="text-xs text-gray-500">Mensal completo</p>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => handleExport('csv', 'performance')}
              disabled={loading}
              className="flex-1 rounded-lg bg-amber-600 px-3 py-2 text-sm font-medium text-white hover:bg-amber-700 disabled:opacity-50"
            >
              <Download className="mr-2 inline h-4 w-4" />
              CSV
            </button>
            <button
              onClick={() => handleExport('pdf', 'performance')}
              disabled={loading}
              className="flex-1 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              PDF
            </button>
          </div>
        </div>
      </div>

      {/* Informações */}
      <div className="rounded-lg border border-gray-200 bg-blue-50 p-4">
        <p className="text-sm text-blue-800">
          <strong>Nota:</strong> Os relatórios são gerados com base nos filtros selecionados e podem levar alguns segundos para processar.
          Os arquivos CSV podem ser abertos no Excel ou Google Sheets. Os PDFs são formatados para impressão.
        </p>
      </div>
    </div>
  )
}
