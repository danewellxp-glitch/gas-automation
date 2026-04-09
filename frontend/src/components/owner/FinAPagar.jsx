/**
 * Financeiro › A Pagar — Despesas e obrigações a pagar
 */

import { useState, useEffect } from 'react'
import { ArrowUpCircle, RefreshCw, Download, Plus, AlertCircle, CheckCircle, Clock, X } from 'lucide-react'
import { apiRequest } from '../../utils/api'

const fmt = (v) =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 2 }).format(v || 0)

const STATUS = {
  pending:   { label: 'Pendente', color: 'text-amber-600 dark:text-amber-400', bg: 'bg-amber-50 dark:bg-amber-900/20', icon: Clock },
  paid:      { label: 'Pago',     color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-50 dark:bg-emerald-900/20', icon: CheckCircle },
  overdue:   { label: 'Vencido', color: 'text-red-600 dark:text-red-400', bg: 'bg-red-50 dark:bg-red-900/20', icon: AlertCircle },
}

const CATS = ['Fornecedor', 'Aluguel', 'Salário', 'Comissão', 'Utilitários', 'Marketing', 'Manutenção', 'Outros']

export default function FinAPagar() {
  const [loading, setLoading] = useState(true)
  const [items, setItems]     = useState([])
  const [error, setError]     = useState('')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ description: '', value: '', due_date: '', category: 'Outros', recurrence: 'once' })

  useEffect(() => { fetchData() }, [])

  const fetchData = async () => {
    try {
      setLoading(true); setError('')
      const data = await apiRequest('financial/payables')
      const list = Array.isArray(data) ? data : (data?.items || data?.payables || [])
      setItems(list)
    } catch {
      // fallback: despesas já cadastradas
      try {
        const data = await apiRequest('expenses?status=pending')
        const list = Array.isArray(data) ? data : (data?.items || data?.expenses || [])
        setItems(list.map(e => ({ ...e, status: 'pending', value: e.amount || e.value || 0 })))
      } catch {
        setError('Endpoint de contas a pagar não encontrado. Configure as despesas aqui.')
        setItems([])
      }
    } finally { setLoading(false) }
  }

  const total = items.reduce((s, i) => s + (i.value || i.amount || 0), 0)
  const overdue = items.filter(i => i.status === 'overdue' || (i.due_date && new Date(i.due_date) < new Date() && i.status !== 'paid')).length
  const pending = items.filter(i => i.status === 'pending').length

  const handleExport = () => {
    const header = 'Vencimento,Descrição,Categoria,Status,Valor\n'
    const rows = items.map(i =>
      `${i.due_date ? new Date(i.due_date).toLocaleDateString('pt-BR') : ''},"${i.description||''}","${i.category||''}","${i.status||''}",${(i.value||i.amount||0).toFixed(2)}`
    ).join('\n')
    const blob = new Blob([header + rows], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url
    a.download = 'a_pagar.csv'; a.click(); URL.revokeObjectURL(url)
  }

  const getStatus = (item) => {
    if (item.status === 'paid') return 'paid'
    if (item.due_date && new Date(item.due_date) < new Date()) return 'overdue'
    return item.status || 'pending'
  }

  return (
    <div className="space-y-5">

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">A Pagar</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Despesas e obrigações financeiras</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setShowForm(v => !v)} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary-600 text-white text-xs font-medium hover:bg-primary-700 transition-colors">
            <Plus className="w-3.5 h-3.5" /> Nova conta
          </button>
          <button onClick={handleExport} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 transition-colors">
            <Download className="w-3.5 h-3.5" /> CSV
          </button>
          <button onClick={fetchData} disabled={loading} className="p-1.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-500 hover:bg-gray-50 disabled:opacity-50">
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Form nova conta */}
      {showForm && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-primary-200 dark:border-primary-800 p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Nova Conta a Pagar</h3>
            <button onClick={() => setShowForm(false)} className="text-gray-400 hover:text-gray-600"><X className="w-4 h-4" /></button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {[
              { key: 'description', label: 'Descrição', type: 'text', placeholder: 'Ex: Aluguel galpão' },
              { key: 'value', label: 'Valor (R$)', type: 'number', placeholder: '0,00' },
              { key: 'due_date', label: 'Vencimento', type: 'date' },
            ].map(({ key, label, type, placeholder }) => (
              <div key={key}>
                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">{label}</label>
                <input type={type} placeholder={placeholder} value={form[key]} onChange={e => setForm(p => ({ ...p, [key]: e.target.value }))}
                  className="w-full rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-primary-500" />
              </div>
            ))}
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Categoria</label>
              <select value={form.category} onChange={e => setForm(p => ({ ...p, category: e.target.value }))}
                className="w-full rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-primary-500">
                {CATS.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
          </div>
          <div className="mt-4 flex justify-end gap-2">
            <button onClick={() => setShowForm(false)} className="px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors">Cancelar</button>
            <button className="px-4 py-2 bg-primary-600 text-white text-sm font-medium rounded-lg hover:bg-primary-700 transition-colors">Salvar</button>
          </div>
        </div>
      )}

      {/* KPIs */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-red-50 dark:bg-red-900/20 border border-gray-200 dark:border-gray-700 rounded-xl p-4">
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Total a Pagar</p>
          <p className="mt-1 text-2xl font-bold text-red-600 dark:text-red-400">{fmt(total)}</p>
          <p className="mt-0.5 text-xs text-gray-400">{items.length} contas</p>
        </div>
        <div className="bg-amber-50 dark:bg-amber-900/20 border border-gray-200 dark:border-gray-700 rounded-xl p-4">
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Pendentes</p>
          <p className="mt-1 text-2xl font-bold text-amber-600 dark:text-amber-400">{pending}</p>
          <p className="mt-0.5 text-xs text-gray-400">a vencer</p>
        </div>
        <div className="bg-red-100 dark:bg-red-900/30 border border-gray-200 dark:border-gray-700 rounded-xl p-4">
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Vencidos</p>
          <p className="mt-1 text-2xl font-bold text-red-700 dark:text-red-400">{overdue}</p>
          <p className="mt-0.5 text-xs text-red-500 dark:text-red-400">atenção imediata</p>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl text-sm text-amber-700 dark:text-amber-400">
          <AlertCircle className="w-4 h-4 shrink-0" /> {error}
        </div>
      )}

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50">
                {['Vencimento', 'Descrição', 'Categoria', 'Status', 'Valor'].map(h => (
                  <th key={h} className={`px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide ${h === 'Valor' ? 'text-right' : 'text-left'}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {loading ? (
                [...Array(4)].map((_, i) => (
                  <tr key={i}>{[...Array(5)].map((_, j) => (
                    <td key={j} className="px-4 py-3"><div className="h-4 bg-gray-100 dark:bg-gray-700 rounded animate-pulse" /></td>
                  ))}</tr>
                ))
              ) : items.length === 0 ? (
                <tr><td colSpan={5} className="px-4 py-10 text-center text-sm text-gray-400 dark:text-gray-500">
                  Nenhuma conta a pagar cadastrada.
                </td></tr>
              ) : (
                items.map((item, idx) => {
                  const stKey = getStatus(item)
                  const st = STATUS[stKey] || STATUS.pending
                  const StIcon = st.icon
                  return (
                    <tr key={item.id || idx} className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                      <td className="px-4 py-3 text-gray-500 dark:text-gray-400 text-xs whitespace-nowrap">
                        {item.due_date ? new Date(item.due_date).toLocaleDateString('pt-BR') : '—'}
                      </td>
                      <td className="px-4 py-3 text-gray-800 dark:text-gray-200">{item.description || '—'}</td>
                      <td className="px-4 py-3">
                        <span className="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400">
                          {item.category || 'Outros'}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${st.bg} ${st.color}`}>
                          <StIcon className="w-3 h-3" /> {st.label}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right font-semibold text-red-600 dark:text-red-400">
                        {fmt(item.value || item.amount || 0)}
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
            {items.length > 0 && (
              <tfoot>
                <tr className="border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50">
                  <td colSpan={4} className="px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400">{items.length} registros</td>
                  <td className="px-4 py-3 text-right text-sm font-bold text-red-600 dark:text-red-400">{fmt(total)}</td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      </div>

    </div>
  )
}
