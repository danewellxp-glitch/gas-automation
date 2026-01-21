/**
 * Dashboard Overview para Operador
 * Métricas de atendimento e pedidos
 */

import { useState, useEffect } from 'react'

export default function OperatorDashboardOverview() {
  const [metrics, setMetrics] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchMetrics()
    // Atualizar a cada 30 segundos
    const interval = setInterval(fetchMetrics, 30000)
    return () => clearInterval(interval)
  }, [])

  const fetchMetrics = async () => {
    try {
      setLoading(true)
      
      // Buscar métricas em paralelo usando api.js
      const apiUrl = import.meta.env.VITE_API_URL || 'http://192.168.10.156:8000/api'
      const token = localStorage.getItem('token')
      
      const [ordersRes, conversationsRes] = await Promise.all([
        fetch(`${apiUrl}/orders/pending`, {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
        fetch(`${apiUrl}/my-conversations`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
      ])

      const orders = ordersRes.ok ? await ordersRes.json() : []
      const conversations = conversationsRes.ok ? await conversationsRes.json() : []

      setMetrics({
        orders: {
          pending: orders.filter(o => o.status === 'pending').length,
          processing: orders.filter(o => o.status === 'processing').length,
          total: orders.length
        },
        conversations: {
          active: conversations.filter(c => c.status === 'active').length,
          waiting: conversations.filter(c => !c.assigned_to).length,
          mine: conversations.filter(c => c.assigned_to === localStorage.getItem('username')).length,
          total: conversations.length
        }
      })
    } catch (error) {
      console.error('Erro ao buscar métricas:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="text-gray-600 mt-4">Carregando métricas...</p>
        </div>
      </div>
    )
  }

  if (!metrics) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-700">Erro ao carregar métricas</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-800">📊 Painel do Operador</h2>
        <p className="text-gray-600">Visão geral de atendimento e pedidos</p>
      </div>

      {/* Cards de Métricas */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Pedidos Pendentes */}
        <div className="bg-gradient-to-br from-yellow-500 to-yellow-600 rounded-lg p-6 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-yellow-100 text-sm mb-1">Pedidos Pendentes</p>
              <p className="text-4xl font-bold">{metrics.orders.pending}</p>
              <p className="text-yellow-100 text-xs mt-2">
                Aguardando aprovação
              </p>
            </div>
            <div className="text-5xl opacity-20">⏳</div>
          </div>
        </div>

        {/* Em Processamento */}
        <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg p-6 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-blue-100 text-sm mb-1">Em Processamento</p>
              <p className="text-4xl font-bold">{metrics.orders.processing}</p>
              <p className="text-blue-100 text-xs mt-2">
                Sendo preparados
              </p>
            </div>
            <div className="text-5xl opacity-20">🔄</div>
          </div>
        </div>

        {/* Conversas Ativas */}
        <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-lg p-6 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-green-100 text-sm mb-1">Conversas Ativas</p>
              <p className="text-4xl font-bold">{metrics.conversations.active}</p>
              <p className="text-green-100 text-xs mt-2">
                {metrics.conversations.mine} minhas
              </p>
            </div>
            <div className="text-5xl opacity-20">💬</div>
          </div>
        </div>

        {/* Aguardando Atendimento */}
        <div className="bg-gradient-to-br from-red-500 to-red-600 rounded-lg p-6 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-red-100 text-sm mb-1">Aguardando</p>
              <p className="text-4xl font-bold">{metrics.conversations.waiting}</p>
              <p className="text-red-100 text-xs mt-2">
                Sem atendente
              </p>
            </div>
            <div className="text-5xl opacity-20">⚠️</div>
          </div>
        </div>
      </div>

      {/* Seção de Ações Rápidas */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-bold text-gray-800 mb-4">⚡ Ações Rápidas</h3>
        <div className="grid grid-cols-3 gap-4">
          <button 
            onClick={() => window.location.hash = '#orders'}
            className="p-4 bg-yellow-50 hover:bg-yellow-100 rounded-lg transition text-center"
          >
            <div className="text-3xl mb-2">📦</div>
            <p className="font-medium text-gray-800">Aprovar Pedidos</p>
            <p className="text-sm text-gray-600 mt-1">{metrics.orders.pending} pendentes</p>
          </button>

          <button 
            onClick={() => window.location.hash = '#conversations'}
            className="p-4 bg-green-50 hover:bg-green-100 rounded-lg transition text-center"
          >
            <div className="text-3xl mb-2">💬</div>
            <p className="font-medium text-gray-800">Conversas</p>
            <p className="text-sm text-gray-600 mt-1">{metrics.conversations.active} ativas</p>
          </button>

          <button 
            onClick={() => window.location.hash = '#history'}
            className="p-4 bg-blue-50 hover:bg-blue-100 rounded-lg transition text-center"
          >
            <div className="text-3xl mb-2">📋</div>
            <p className="font-medium text-gray-800">Histórico</p>
            <p className="text-sm text-gray-600 mt-1">Ver todos</p>
          </button>
        </div>
      </div>

      {/* Resumo de Atividade */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-bold text-gray-800 mb-4">📦 Status dos Pedidos</h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Pendentes</span>
              <span className="font-bold text-yellow-600">{metrics.orders.pending}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Processando</span>
              <span className="font-bold text-blue-600">{metrics.orders.processing}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Total</span>
              <span className="font-bold text-gray-800">{metrics.orders.total}</span>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-bold text-gray-800 mb-4">💬 Status das Conversas</h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Minhas</span>
              <span className="font-bold text-green-600">{metrics.conversations.mine}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Aguardando</span>
              <span className="font-bold text-red-600">{metrics.conversations.waiting}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Total Ativas</span>
              <span className="font-bold text-gray-800">{metrics.conversations.active}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Botão de Atualização */}
      <div className="text-center">
        <button
          onClick={fetchMetrics}
          className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition"
        >
          🔄 Atualizar Métricas
        </button>
        <p className="text-xs text-gray-500 mt-2">
          Atualização automática a cada 30 segundos
        </p>
      </div>
    </div>
  )
}
