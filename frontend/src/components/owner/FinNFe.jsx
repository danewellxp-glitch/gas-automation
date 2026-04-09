/**
 * Financeiro › NF-e — Gerenciamento de Notas Fiscais Eletrônicas
 */

import { useState } from 'react'
import { FileCheck, Download, Plus, AlertCircle, CheckCircle, Clock, XCircle, ExternalLink } from 'lucide-react'

const fmt = (v) =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 2 }).format(v || 0)

const STATUS = {
  authorized: { label: 'Autorizada', color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-50 dark:bg-emerald-900/20', icon: CheckCircle },
  pending:    { label: 'Pendente',   color: 'text-amber-600 dark:text-amber-400',     bg: 'bg-amber-50 dark:bg-amber-900/20',     icon: Clock },
  cancelled:  { label: 'Cancelada', color: 'text-red-600 dark:text-red-400',          bg: 'bg-red-50 dark:bg-red-900/20',          icon: XCircle },
  rejected:   { label: 'Rejeitada', color: 'text-red-600 dark:text-red-400',          bg: 'bg-red-50 dark:bg-red-900/20',          icon: XCircle },
}

// Dados de exemplo — conectar ao backend/SEFAZ quando disponível
const SAMPLE_NF = [
  { id: 1, number: '000001', serie: '1', key: '35250312345678901234550010000000011234567890', date: '2026-03-01', customer: 'Consumidor Final', value: 350.00, status: 'authorized' },
  { id: 2, number: '000002', serie: '1', key: '35250312345678901234550010000000021234567891', date: '2026-03-05', customer: 'João da Silva', value: 125.00, status: 'authorized' },
  { id: 3, number: '000003', serie: '1', key: '35250312345678901234550010000000031234567892', date: '2026-03-10', customer: 'Maria Souza', value: 87.50, status: 'pending' },
  { id: 4, number: '000004', serie: '1', key: '35250312345678901234550010000000041234567893', date: '2026-03-12', customer: 'Consumidor Final', value: 200.00, status: 'cancelled' },
]

export default function FinNFe() {
  const [filter, setFilter] = useState('all')

  const items = filter === 'all' ? SAMPLE_NF : SAMPLE_NF.filter(n => n.status === filter)
  const totalAuthorized = SAMPLE_NF.filter(n => n.status === 'authorized').reduce((s, n) => s + n.value, 0)

  return (
    <div className="space-y-5">

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">NF-e</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Notas Fiscais Eletrônicas emitidas</p>
        </div>
        <button className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary-600 text-white text-xs font-medium hover:bg-primary-700 transition-colors">
          <Plus className="w-3.5 h-3.5" /> Emitir NF-e
        </button>
      </div>

      {/* Aviso integração */}
      <div className="flex items-start gap-3 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl">
        <AlertCircle className="w-4 h-4 text-blue-600 dark:text-blue-400 shrink-0 mt-0.5" />
        <div>
          <p className="text-sm font-semibold text-blue-700 dark:text-blue-300">Integração com SEFAZ</p>
          <p className="text-xs text-blue-600 dark:text-blue-400 mt-0.5">
            Para emissão real de NF-e, configure a integração com a SEFAZ do seu estado e insira o certificado digital A1.
            Os dados abaixo são demonstrativos.
          </p>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: 'Total Emitido', value: fmt(totalAuthorized), color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-50 dark:bg-emerald-900/20' },
          { label: 'Autorizadas', value: SAMPLE_NF.filter(n => n.status === 'authorized').length, color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-white dark:bg-gray-800' },
          { label: 'Pendentes',   value: SAMPLE_NF.filter(n => n.status === 'pending').length,    color: 'text-amber-600 dark:text-amber-400', bg: 'bg-white dark:bg-gray-800' },
          { label: 'Canceladas',  value: SAMPLE_NF.filter(n => n.status === 'cancelled').length,  color: 'text-red-600 dark:text-red-400', bg: 'bg-white dark:bg-gray-800' },
        ].map(({ label, value, color, bg }) => (
          <div key={label} className={`${bg} border border-gray-200 dark:border-gray-700 rounded-xl p-4`}>
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">{label}</p>
            <p className={`mt-1 text-2xl font-bold ${color}`}>{value}</p>
          </div>
        ))}
      </div>

      {/* Filtros */}
      <div className="flex gap-2 flex-wrap">
        {[{ v: 'all', l: 'Todas' }, { v: 'authorized', l: 'Autorizadas' }, { v: 'pending', l: 'Pendentes' }, { v: 'cancelled', l: 'Canceladas' }].map(({ v, l }) => (
          <button key={v} onClick={() => setFilter(v)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${filter === v ? 'bg-primary-600 text-white border-primary-600' : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700'}`}>
            {l}
          </button>
        ))}
      </div>

      {/* Tabela */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50">
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Número</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Data</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Destinatário</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Chave NF-e</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Status</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Valor</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {items.map((nf) => {
                const st = STATUS[nf.status] || STATUS.pending
                const StIcon = st.icon
                return (
                  <tr key={nf.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                    <td className="px-4 py-3 font-medium text-gray-800 dark:text-gray-200">
                      {nf.number} <span className="text-xs text-gray-400">s{nf.serie}</span>
                    </td>
                    <td className="px-4 py-3 text-gray-500 dark:text-gray-400 text-xs whitespace-nowrap">
                      {new Date(nf.date).toLocaleDateString('pt-BR')}
                    </td>
                    <td className="px-4 py-3 text-gray-700 dark:text-gray-300">{nf.customer}</td>
                    <td className="px-4 py-3">
                      <span className="text-xs text-gray-400 font-mono">{nf.key.slice(0, 20)}…</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${st.bg} ${st.color}`}>
                        <StIcon className="w-3 h-3" /> {st.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-semibold text-gray-800 dark:text-gray-200">
                      {fmt(nf.value)}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1 justify-end">
                        <button className="p-1 text-gray-400 hover:text-primary-600 transition-colors" title="Download XML">
                          <Download className="w-3.5 h-3.5" />
                        </button>
                        <button className="p-1 text-gray-400 hover:text-primary-600 transition-colors" title="Visualizar DANFE">
                          <ExternalLink className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  )
}
