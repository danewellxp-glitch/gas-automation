/**
 * BusinessStatusWidget — badge "Aberta / Fechada" no header
 * Lê operating_hours e permite toggle rápido do dia corrente.
 */

import { useState, useEffect } from 'react'
import { apiRequest } from '../../utils/api'

const DAY_KEYS = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']

function computeIsOpen(operatingHours) {
  const now = new Date()
  const dayKey = DAY_KEYS[now.getDay()]
  const todayHours = operatingHours?.[dayKey]
  if (!todayHours?.enabled) return false
  const [oh, om] = (todayHours.open || '').split(':').map(Number)
  const [ch, cm] = (todayHours.close || '').split(':').map(Number)
  const nowMins = now.getHours() * 60 + now.getMinutes()
  return nowMins >= oh * 60 + om && nowMins < ch * 60 + cm
}

export default function BusinessStatusWidget() {
  const [operatingHours, setOperatingHours] = useState(null)
  const [fullSettings, setFullSettings] = useState(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    apiRequest('owner/settings')
      .then(d => {
        setOperatingHours(d?.operating_hours || null)
        setFullSettings(d || null)
      })
      .catch(() => {})
  }, [])

  if (!operatingHours || !fullSettings) return null

  const isOpen = computeIsOpen(operatingHours)
  const dayKey = DAY_KEYS[new Date().getDay()]

  const toggle = async () => {
    if (saving) return
    setSaving(true)
    try {
      const newHours = {
        ...operatingHours,
        [dayKey]: { ...operatingHours[dayKey], enabled: !isOpen },
      }
      const payload = { ...fullSettings, operating_hours: newHours }
      await apiRequest('owner/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      setOperatingHours(newHours)
      setFullSettings(payload)
    } catch (e) {
      console.error('Erro ao atualizar status da loja:', e)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex items-center gap-2">
      <div
        className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-bold border ${
          isOpen
            ? 'bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/30 text-emerald-700 dark:text-emerald-400'
            : 'bg-rose-50 dark:bg-rose-500/10 border-rose-200 dark:border-rose-500/30 text-rose-700 dark:text-rose-400'
        }`}
      >
        <span
          className={`h-1.5 w-1.5 rounded-full ${
            isOpen ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'
          }`}
        />
        {isOpen ? 'Aberta' : 'Fechada'}
      </div>
      <button
        onClick={toggle}
        disabled={saving}
        title={isOpen ? 'Fechar loja agora' : 'Abrir loja agora'}
        className="rounded-lg px-2.5 py-1.5 text-xs font-medium text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors disabled:opacity-40"
      >
        {saving ? '...' : isOpen ? 'Fechar' : 'Abrir'}
      </button>
    </div>
  )
}
