/**
 * Página de Perfil do Driver
 */

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { driverApi } from '../../utils/driverApi'

export default function DriverProfile() {
  const navigate = useNavigate()
  const [driver, setDriver] = useState(null)
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        const [profileData, statsData] = await Promise.all([
          driverApi.getProfile(),
          driverApi.getStats()
        ])
        setDriver(profileData)
        setStats(statsData)
      } catch (err) {
        console.error('Erro ao carregar perfil:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  const handleLogout = () => {
    const confirmed = window.confirm('Deseja realmente sair?')
    if (confirmed) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      navigate('/driver/login')
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <p className="text-gray-600">Carregando perfil...</p>
      </div>
    )
  }

  if (!driver || !stats) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
        <div className="text-center">
          <p className="text-gray-600 mb-4">Erro ao carregar perfil</p>
          <button
            onClick={() => navigate('/driver/dashboard')}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg"
          >
            Voltar
          </button>
        </div>
      </div>
    )
  }

  const memberSince = driver.created_at 
    ? new Date(driver.created_at).toLocaleDateString('pt-BR', { month: 'short', year: 'numeric' })
    : 'N/A'

  return (
    <div className="min-h-screen bg-gray-100 pb-24">
      {/* Header */}
      <div className="bg-white shadow-md p-4 mb-4">
        <button
          onClick={() => navigate('/driver/dashboard')}
          className="text-blue-600 hover:text-blue-700 mb-2"
        >
          ← Voltar
        </button>
        <h1 className="text-2xl font-bold text-gray-800">Meu Perfil</h1>
      </div>

      <div className="max-w-2xl mx-auto px-4 space-y-4">
        {/* Foto e Nome */}
        <div className="bg-white rounded-lg shadow p-6 text-center">
          <div className="w-24 h-24 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="text-5xl">👤</span>
          </div>
          <h2 className="text-2xl font-bold text-gray-800 mb-2">{driver.name}</h2>
          <div className="flex items-center justify-center gap-2 text-yellow-500">
            <span className="text-2xl">⭐</span>
            <span className="text-xl font-semibold">{driver.rating?.toFixed(1)}</span>
            <span className="text-gray-500 text-sm">
              ({stats.total_deliveries} avaliações)
            </span>
          </div>
        </div>

        {/* Estatísticas */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">📊 Estatísticas</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-600">Total de entregas:</span>
              <span className="font-bold text-gray-800">{stats.total_deliveries}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Entregas hoje:</span>
              <span className="font-bold text-gray-800">{stats.today_deliveries}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Entregas esta semana:</span>
              <span className="font-bold text-gray-800">{stats.week_deliveries}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Taxa de sucesso:</span>
              <span className="font-bold text-green-600">{stats.success_rate}%</span>
            </div>
            {stats.average_delivery_time_minutes && (
              <div className="flex justify-between">
                <span className="text-gray-600">Tempo médio:</span>
                <span className="font-bold text-gray-800">{Math.round(stats.average_delivery_time_minutes)} min</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-gray-600">Membro desde:</span>
              <span className="font-bold text-gray-800">{memberSince}</span>
            </div>
          </div>
        </div>

        {/* Contato */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">📞 Contato</h3>
          <div className="space-y-3">
            <div>
              <p className="text-sm text-gray-500">Username</p>
              <p className="font-medium text-gray-800">{driver.phone}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Email</p>
              <p className="font-medium text-gray-800">{driver.email || 'Não informado'}</p>
            </div>
          </div>
        </div>

        {/* Veículo */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">🚗 Veículo</h3>
          <div className="space-y-3">
            <div>
              <p className="text-sm text-gray-500">Tipo</p>
              <p className="font-medium text-gray-800">{driver.vehicle_type || 'Não informado'}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Placa</p>
              <p className="font-medium text-gray-800">{driver.license_plate || 'Não informado'}</p>
            </div>
          </div>
        </div>

        {/* Botão Sair */}
        <button
          onClick={handleLogout}
          className="w-full bg-red-600 text-white py-4 rounded-lg font-semibold hover:bg-red-700 active:bg-red-800 text-lg"
        >
          🚪 SAIR
        </button>
      </div>

      {/* Bottom Navigation */}
      <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 shadow-lg">
        <div className="flex justify-around items-center h-16">
          <button
            onClick={() => navigate('/driver/dashboard')}
            className="flex flex-col items-center justify-center flex-1 py-2 text-gray-600 hover:text-blue-600"
          >
            <span className="text-2xl">🏠</span>
            <span className="text-xs font-medium">Início</span>
          </button>
          <button
            onClick={() => navigate('/driver/history')}
            className="flex flex-col items-center justify-center flex-1 py-2 text-gray-600 hover:text-blue-600"
          >
            <span className="text-2xl">📦</span>
            <span className="text-xs font-medium">Histórico</span>
          </button>
          <button
            onClick={() => navigate('/driver/profile')}
            className="flex flex-col items-center justify-center flex-1 py-2 text-blue-600"
          >
            <span className="text-2xl">👤</span>
            <span className="text-xs font-medium">Perfil</span>
          </button>
        </div>
      </nav>
    </div>
  )
}
