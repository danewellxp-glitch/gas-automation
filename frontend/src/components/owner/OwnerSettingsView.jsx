/**
 * Owner Settings View - Configurações de Negócio
 * Preços, bairros, horários, promoções, metas
 */

import { useState, useEffect } from 'react'
import { Save, RefreshCw, AlertCircle, CheckCircle2 } from 'lucide-react'
import { apiRequest } from '../../utils/api'

export default function OwnerSettingsView() {
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [success, setSuccess] = useState('')
  const [error, setError] = useState('')
  
  const [settings, setSettings] = useState({
    // Preços de produtos
    products: [],
    
    // Bairros
    bairros: [],
    enabled_bairros: [],
    
    // Horário de funcionamento
    operating_hours: {
      monday: { open: '08:00', close: '18:00', enabled: true },
      tuesday: { open: '08:00', close: '18:00', enabled: true },
      wednesday: { open: '08:00', close: '18:00', enabled: true },
      thursday: { open: '08:00', close: '18:00', enabled: true },
      friday: { open: '08:00', close: '18:00', enabled: true },
      saturday: { open: '08:00', close: '18:00', enabled: true },
      sunday: { open: '08:00', close: '18:00', enabled: false },
    },
    
    // Promoções
    promotions: [],
    
    // Metas mensais
    monthly_goals: {
      revenue: 0,
      orders: 0,
      new_customers: 0,
    },
  })

  useEffect(() => {
    fetchSettings()
  }, [])

  const fetchSettings = async () => {
    try {
      setLoading(true)
      const data = await apiRequest('owner/settings')
      setSettings(data)
    } catch (err) {
      console.error('Erro ao buscar configurações:', err)
      setError('Erro ao carregar configurações')
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    try {
      setSaving(true)
      setError('')
      setSuccess('')
      await apiRequest('owner/settings', {
        method: 'PUT',
        body: JSON.stringify(settings),
      })
      setSuccess('Configurações salvas com sucesso!')
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      console.error('Erro ao salvar configurações:', err)
      setError(err.message || 'Erro ao salvar configurações')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-gray-200 border-t-primary-600" />
          <p className="mt-4 text-gray-600">Carregando configurações...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Configurações de Negócio</h1>
          <p className="mt-1 text-sm text-gray-600">
            Gerencie preços, bairros, horários, promoções e metas do seu negócio
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={fetchSettings}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Atualizar
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          >
            <Save className="h-4 w-4" />
            Salvar Alterações
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4">
          <AlertCircle className="h-5 w-5 flex-shrink-0 text-red-600 mt-0.5" />
          <div className="flex-1">
            <div className="font-semibold text-red-800">Erro</div>
            <div className="mt-1 text-sm text-red-700">{error}</div>
          </div>
        </div>
      )}

      {success && (
        <div className="flex items-start gap-3 rounded-lg border border-green-200 bg-green-50 p-4">
          <CheckCircle2 className="h-5 w-5 flex-shrink-0 text-green-600 mt-0.5" />
          <div className="flex-1">
            <div className="font-semibold text-green-800">Sucesso</div>
            <div className="mt-1 text-sm text-green-700">{success}</div>
          </div>
        </div>
      )}

      {/* Preços de Produtos */}
      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">Preços de Produtos</h2>
        <p className="mb-4 text-sm text-gray-600">
          Configure os preços dos produtos disponíveis no sistema
        </p>
        <div className="space-y-3">
          {settings.products.length > 0 ? (
            settings.products.map((product) => (
              <div
                key={product.code}
                className="flex items-center justify-between rounded-lg border border-gray-200 bg-gray-50 p-4"
              >
                <div>
                  <div className="font-medium text-gray-900">{product.name}</div>
                  <div className="text-sm text-gray-500">Código: {product.code}</div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-600">R$</span>
                  <input
                    type="number"
                    step="0.01"
                    value={product.price || 0}
                    onChange={(e) => {
                      const newProducts = settings.products.map((p) =>
                        p.code === product.code
                          ? { ...p, price: parseFloat(e.target.value) || 0 }
                          : p
                      )
                      setSettings({ ...settings, products: newProducts })
                    }}
                    className="w-24 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-primary-500 focus:ring-primary-500"
                  />
                </div>
              </div>
            ))
          ) : (
            <p className="text-sm text-gray-500">Nenhum produto configurado</p>
          )}
        </div>
      </div>

      {/* Bairros */}
      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">Bairros Atendidos</h2>
        <p className="mb-4 text-sm text-gray-600">
          Ative ou desative bairros para entrega
        </p>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {settings.bairros.map((bairro) => (
            <label
              key={bairro}
              className="flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 p-3 hover:bg-gray-100 cursor-pointer"
            >
              <input
                type="checkbox"
                checked={settings.enabled_bairros.includes(bairro)}
                onChange={(e) => {
                  const newEnabled = e.target.checked
                    ? [...settings.enabled_bairros, bairro]
                    : settings.enabled_bairros.filter((b) => b !== bairro)
                  setSettings({ ...settings, enabled_bairros: newEnabled })
                }}
                className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm font-medium text-gray-900">{bairro}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Horário de Funcionamento */}
      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">Horário de Funcionamento</h2>
        <div className="space-y-3">
          {Object.entries(settings.operating_hours).map(([day, hours]) => (
            <div
              key={day}
              className="flex items-center gap-4 rounded-lg border border-gray-200 bg-gray-50 p-4"
            >
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={hours.enabled}
                  onChange={(e) => {
                    setSettings({
                      ...settings,
                      operating_hours: {
                        ...settings.operating_hours,
                        [day]: { ...hours, enabled: e.target.checked },
                      },
                    })
                  }}
                  className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="w-24 text-sm font-medium text-gray-900 capitalize">
                  {day === 'monday' ? 'Segunda' :
                   day === 'tuesday' ? 'Terça' :
                   day === 'wednesday' ? 'Quarta' :
                   day === 'thursday' ? 'Quinta' :
                   day === 'friday' ? 'Sexta' :
                   day === 'saturday' ? 'Sábado' : 'Domingo'}
                </span>
              </label>
              {hours.enabled && (
                <div className="flex items-center gap-2">
                  <input
                    type="time"
                    value={hours.open}
                    onChange={(e) => {
                      setSettings({
                        ...settings,
                        operating_hours: {
                          ...settings.operating_hours,
                          [day]: { ...hours, open: e.target.value },
                        },
                      })
                    }}
                    className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-primary-500 focus:ring-primary-500"
                  />
                  <span className="text-gray-600">até</span>
                  <input
                    type="time"
                    value={hours.close}
                    onChange={(e) => {
                      setSettings({
                        ...settings,
                        operating_hours: {
                          ...settings.operating_hours,
                          [day]: { ...hours, close: e.target.value },
                        },
                      })
                    }}
                    className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-primary-500 focus:ring-primary-500"
                  />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Metas Mensais */}
      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">Metas Mensais</h2>
        <p className="mb-4 text-sm text-gray-600">
          Defina metas para acompanhamento mensal
        </p>
        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">
              Meta de Receita (R$)
            </label>
            <input
              type="number"
              value={settings.monthly_goals.revenue || 0}
              onChange={(e) => {
                setSettings({
                  ...settings,
                  monthly_goals: {
                    ...settings.monthly_goals,
                    revenue: parseFloat(e.target.value) || 0,
                  },
                })
              }}
              className="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-primary-500 focus:ring-primary-500"
            />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">
              Meta de Pedidos
            </label>
            <input
              type="number"
              value={settings.monthly_goals.orders || 0}
              onChange={(e) => {
                setSettings({
                  ...settings,
                  monthly_goals: {
                    ...settings.monthly_goals,
                    orders: parseInt(e.target.value) || 0,
                  },
                })
              }}
              className="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-primary-500 focus:ring-primary-500"
            />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">
              Meta de Novos Clientes
            </label>
            <input
              type="number"
              value={settings.monthly_goals.new_customers || 0}
              onChange={(e) => {
                setSettings({
                  ...settings,
                  monthly_goals: {
                    ...settings.monthly_goals,
                    new_customers: parseInt(e.target.value) || 0,
                  },
                })
              }}
              className="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-primary-500 focus:ring-primary-500"
            />
          </div>
        </div>
      </div>

      {/* Aviso */}
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
        <p className="text-sm text-amber-800">
          <strong>Atenção:</strong> As alterações nas configurações de negócio afetam diretamente o funcionamento do sistema.
          Certifique-se de que as informações estão corretas antes de salvar.
        </p>
      </div>
    </div>
  )
}
