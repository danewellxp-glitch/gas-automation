/**
 * Página de Perfil do Driver - Novo Estilo
 */

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Loader, User, Star, Package, TrendingUp, Clock, LogOut, Phone, Mail, Car } from 'lucide-react'
import { driverApi } from '../../utils/driverApi'
import '../../styles/driver-dashboard.css'

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
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <Loader className="w-12 h-12 text-emerald-400 animate-spin mx-auto mb-4" />
          <p className="text-slate-300 text-lg font-medium">Carregando perfil...</p>
        </div>
      </div>
    )
  }

  if (!driver || !stats) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
        <div className="bg-slate-800 rounded-2xl shadow-2xl p-8 max-w-md w-full text-center border border-slate-700/50">
          <p className="text-slate-300 mb-4">Erro ao carregar perfil</p>
          <button
            onClick={() => navigate('/driver/dashboard')}
            className="bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white px-6 py-3 rounded-xl font-semibold transition-all duration-200"
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
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 pb-24">
      {/* Header */}
      <header className="bg-slate-800/80 backdrop-blur-lg border-b border-slate-700/50 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/driver/dashboard')}
              className="w-10 h-10 bg-slate-700/50 hover:bg-slate-700 rounded-full flex items-center justify-center transition-all duration-200"
            >
              <ArrowLeft className="w-5 h-5 text-slate-300" />
            </button>
            <h1 className="text-white font-bold text-xl">Meu Perfil</h1>
          </div>
        </div>
      </header>

      <div className="max-w-2xl mx-auto px-4 py-6 space-y-6">
        {/* Foto e Nome */}
        <div className="bg-gradient-to-r from-slate-800/90 to-slate-700/90 backdrop-blur-lg rounded-2xl p-8 text-center border border-slate-600/30 shadow-xl">
          <div className="w-24 h-24 bg-gradient-to-br from-emerald-400 to-teal-500 rounded-full flex items-center justify-center mx-auto mb-4 shadow-lg shadow-emerald-500/30">
            <span className="text-5xl text-white font-bold">{driver.name?.charAt(0) || 'D'}</span>
          </div>
          <h2 className="text-2xl font-bold text-white mb-3">{driver.name}</h2>
          <div className="flex items-center justify-center gap-2">
            <Star className="w-6 h-6 text-amber-400 fill-amber-400" />
            <span className="text-2xl font-bold text-white">{driver.rating?.toFixed(1) || '5.0'}</span>
            <span className="text-slate-400 text-sm">
              ({stats.total_deliveries} entregas)
            </span>
          </div>
        </div>

        {/* Estatísticas */}
        <div className="bg-slate-800/70 backdrop-blur-lg rounded-2xl p-6 border border-slate-700/50 shadow-lg">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-emerald-400" />
            Estatísticas
          </h3>
          <div className="space-y-4">
            <div className="flex justify-between items-center py-2 border-b border-slate-700/50">
              <span className="text-slate-400">Total de entregas:</span>
              <span className="font-bold text-white text-lg">{stats.total_deliveries}</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-slate-700/50">
              <span className="text-slate-400">Entregas hoje:</span>
              <span className="font-bold text-emerald-400">{stats.today_deliveries}</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-slate-700/50">
              <span className="text-slate-400">Entregas esta semana:</span>
              <span className="font-bold text-white">{stats.week_deliveries}</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-slate-700/50">
              <span className="text-slate-400">Taxa de sucesso:</span>
              <span className="font-bold text-emerald-400">{stats.success_rate}%</span>
            </div>
            {stats.average_delivery_time_minutes && (
              <div className="flex justify-between items-center py-2 border-b border-slate-700/50">
                <span className="text-slate-400">Tempo médio:</span>
                <span className="font-bold text-white">{Math.round(stats.average_delivery_time_minutes)} min</span>
              </div>
            )}
            <div className="flex justify-between items-center py-2">
              <span className="text-slate-400">Membro desde:</span>
              <span className="font-bold text-white">{memberSince}</span>
            </div>
          </div>
        </div>

        {/* Contato */}
        <div className="bg-slate-800/70 backdrop-blur-lg rounded-2xl p-6 border border-slate-700/50 shadow-lg">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Phone className="w-5 h-5 text-emerald-400" />
            Contato
          </h3>
          <div className="space-y-4">
            <div>
              <p className="text-sm text-slate-400 mb-1">Telefone</p>
              <p className="font-medium text-white">{driver.phone}</p>
            </div>
            <div>
              <p className="text-sm text-slate-400 mb-1">Email</p>
              <p className="font-medium text-white">{driver.email || 'Não informado'}</p>
            </div>
          </div>
        </div>

        {/* Veículo */}
        <div className="bg-slate-800/70 backdrop-blur-lg rounded-2xl p-6 border border-slate-700/50 shadow-lg">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Car className="w-5 h-5 text-emerald-400" />
            Veículo
          </h3>
          <div className="space-y-4">
            <div>
              <p className="text-sm text-slate-400 mb-1">Tipo</p>
              <p className="font-medium text-white">{driver.vehicle_type || 'Não informado'}</p>
            </div>
            <div>
              <p className="text-sm text-slate-400 mb-1">Placa</p>
              <p className="font-medium text-white">{driver.license_plate || 'Não informado'}</p>
            </div>
          </div>
        </div>

        {/* Botão Sair */}
        <button
          onClick={handleLogout}
          className="w-full bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white py-4 rounded-xl font-semibold transition-all duration-200 shadow-lg shadow-red-500/30 hover:shadow-red-500/50 flex items-center justify-center gap-2"
        >
          <LogOut className="w-5 h-5" />
          SAIR
        </button>
      </div>
    </div>
  )
}
