/**
 * Página de Acerto de Carga do Motorista - Novo Estilo
 */

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { Package, ArrowLeft, Loader, CheckCircle, AlertCircle } from 'lucide-react'
import { driverApi } from '../../utils/driverApi'
import '../../styles/driver-dashboard.css'

export default function AcertoCarga() {
  const navigate = useNavigate()
  const [carga, setCarga] = useState(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [itensAcerto, setItensAcerto] = useState([])
  const [observacoes, setObservacoes] = useState('')

  // Carregar carga atual
  useEffect(() => {
    const fetchCarga = async () => {
      try {
        setLoading(true)
        setError('')
        const data = await driverApi.getCargaAtual()

        // Verificar se retornou dados válidos
        if (!data || typeof data !== 'object') {
          setError('Erro ao carregar dados da carga.')
          return
        }

        if (!data.tem_carga || !data.carga) {
          setError('Você não possui uma carga ativa no momento.')
          return
        }

        if (data.carga.status === 'criada') {
          setError('A carga ainda não foi iniciada. Registre a saída primeiro.')
          return
        }

        if (data.carga.status === 'finalizada') {
          setError('Esta carga já foi finalizada.')
          return
        }

        setCarga(data.carga)

        // Inicializar itens de acerto com valores padrão
        if (data.carga.itens && Array.isArray(data.carga.itens)) {
          const itensIniciais = data.carga.itens.map(item => ({
            produto_id: item.produto_id,
            produto_nome: item.produto_nome || 'Produto',
            produto_codigo: item.produto_codigo || '',
            qtd_saida: item.qtd_saida || 0,
            qtd_retorno_cheio: 0,
            qtd_retorno_vazio: 0,
            qtd_vendida: item.qtd_saida || 0 // Por padrão, assume que vendeu tudo
          }))
          setItensAcerto(itensIniciais)
        }

      } catch (err) {
        console.error('Erro ao carregar carga:', err)
        // Se erro de autenticação, redirecionar
        if (err.message && (err.message.includes('Sessão expirada') || err.message.includes('401'))) {
          localStorage.removeItem('token')
          localStorage.removeItem('user')
          navigate('/driver/login')
          return
        }
        setError(err.message || 'Erro ao carregar carga atual')
      } finally {
        setLoading(false)
      }
    }

    fetchCarga()
  }, [navigate])

  // Atualizar item de acerto
  const handleItemChange = (index, field, value) => {
    const newItens = [...itensAcerto]
    newItens[index][field] = parseInt(value) || 0
    setItensAcerto(newItens)
  }

  // Calcular automaticamente vendido baseado nos retornos
  const calcularVendido = (index) => {
    const item = itensAcerto[index]
    const vendido = item.qtd_saida - item.qtd_retorno_cheio
    handleItemChange(index, 'qtd_vendida', vendido)
  }

  // Validar acerto
  const validarAcerto = () => {
    for (const item of itensAcerto) {
      const totalRetorno = item.qtd_vendida + item.qtd_retorno_cheio
      if (totalRetorno > item.qtd_saida) {
        return `${item.produto_nome}: Total (vendido + retorno cheio) não pode exceder a saída`
      }
      if (item.qtd_vendida < 0 || item.qtd_retorno_cheio < 0 || item.qtd_retorno_vazio < 0) {
        return `${item.produto_nome}: Valores não podem ser negativos`
      }
    }
    return null
  }

  // Enviar acerto
  const handleSubmit = async () => {
    const erro = validarAcerto()
    if (erro) {
      toast.error(erro)
      return
    }

    const confirmado = window.confirm(
      'Confirmar o acerto da carga?\n\nEsta ação não pode ser desfeita.'
    )

    if (!confirmado) return

    try {
      setSubmitting(true)

      const itensParaEnviar = itensAcerto.map(item => ({
        produto_id: item.produto_id,
        qtd_retorno_cheio: item.qtd_retorno_cheio,
        qtd_retorno_vazio: item.qtd_retorno_vazio,
        qtd_vendida: item.qtd_vendida
      }))

      await driverApi.realizarAcertoCarga(carga.id, itensParaEnviar, observacoes)

      toast.success('Acerto realizado com sucesso!')

      setTimeout(() => {
        navigate('/driver/dashboard')
      }, 1500)

    } catch (err) {
      console.error('Erro ao realizar acerto:', err)
      toast.error('Erro ao realizar acerto: ' + err.message)
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <Loader className="w-12 h-12 text-emerald-400 animate-spin mx-auto mb-4" />
          <p className="text-slate-300 text-lg font-medium">Carregando carga...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
        <div className="bg-slate-800 rounded-2xl shadow-2xl p-8 max-w-md w-full text-center border border-slate-700/50">
          <AlertCircle className="w-16 h-16 text-slate-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-white mb-4">Sem Carga Ativa</h2>
          <p className="text-slate-400 mb-6">{error}</p>
          <button
            onClick={() => navigate('/driver/dashboard')}
            className="bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white px-6 py-3 rounded-xl font-semibold transition-all duration-200 shadow-lg shadow-emerald-500/30"
          >
            Voltar ao Dashboard
          </button>
        </div>
      </div>
    )
  }

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
            <div>
              <h1 className="text-white font-bold text-xl">Acerto de Carga</h1>
              <p className="text-slate-400 text-sm">
                Saída: {carga?.data_saida ? new Date(carga.data_saida).toLocaleString('pt-BR') : 'N/A'}
              </p>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-2xl mx-auto px-4 py-6 space-y-6">
        {/* Instruções */}
        <div className="bg-gradient-to-r from-blue-500/20 to-blue-600/20 backdrop-blur-lg rounded-2xl p-6 border border-blue-500/30 shadow-xl">
          <h3 className="font-semibold text-blue-300 mb-3 flex items-center gap-2">
            <Package className="w-5 h-5" />
            Como fazer o acerto:
          </h3>
          <ul className="text-sm text-blue-200 space-y-2">
            <li>• Informe quantos produtos <strong>voltaram cheios</strong></li>
            <li>• Informe quantos <strong>vazios</strong> você trouxe de volta</li>
            <li>• O sistema calcula automaticamente o <strong>vendido</strong></li>
          </ul>
        </div>

        {/* Lista de Itens */}
        {itensAcerto.map((item, index) => (
          <div key={item.produto_id} className="bg-slate-800/70 backdrop-blur-lg rounded-2xl p-6 border border-slate-700/50 shadow-lg">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="font-semibold text-white text-lg">{item.produto_nome}</h3>
                {item.produto_codigo && (
                  <span className="text-sm text-slate-400">{item.produto_codigo}</span>
                )}
              </div>
              <span className="bg-emerald-500/20 text-emerald-300 px-4 py-2 rounded-full text-sm font-medium border border-emerald-500/30">
                Saiu: {item.qtd_saida}
              </span>
            </div>

            <div className="grid grid-cols-3 gap-4">
              {/* Retornou Cheio */}
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-2">
                  Retornou Cheio
                </label>
                <input
                  type="number"
                  min="0"
                  max={item.qtd_saida}
                  value={item.qtd_retorno_cheio}
                  onChange={(e) => {
                    handleItemChange(index, 'qtd_retorno_cheio', e.target.value)
                    setTimeout(() => calcularVendido(index), 0)
                  }}
                  className="w-full px-3 py-3 bg-slate-700/50 border border-slate-600 rounded-xl text-center text-lg font-semibold text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              {/* Retornou Vazio */}
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-2">
                  Vazios Trocados
                </label>
                <input
                  type="number"
                  min="0"
                  value={item.qtd_retorno_vazio}
                  onChange={(e) => handleItemChange(index, 'qtd_retorno_vazio', e.target.value)}
                  className="w-full px-3 py-3 bg-slate-700/50 border border-slate-600 rounded-xl text-center text-lg font-semibold text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              {/* Vendido (calculado) */}
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-2">
                  Vendido
                </label>
                <input
                  type="number"
                  min="0"
                  max={item.qtd_saida}
                  value={item.qtd_vendida}
                  onChange={(e) => handleItemChange(index, 'qtd_vendida', e.target.value)}
                  className="w-full px-3 py-3 bg-emerald-500/20 border border-emerald-500/30 rounded-xl text-center text-lg font-semibold text-emerald-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
                />
              </div>
            </div>

            {/* Validação visual */}
            {item.qtd_vendida + item.qtd_retorno_cheio !== item.qtd_saida && (
              <p className="text-xs text-amber-400 mt-3 flex items-center gap-1">
                <AlertCircle className="w-4 h-4" />
                Atenção: Vendido ({item.qtd_vendida}) + Retorno Cheio ({item.qtd_retorno_cheio}) = {item.qtd_vendida + item.qtd_retorno_cheio} (Saída: {item.qtd_saida})
              </p>
            )}
          </div>
        ))}

        {/* Observações */}
        <div className="bg-slate-800/70 backdrop-blur-lg rounded-2xl p-6 border border-slate-700/50 shadow-lg">
          <label className="block text-sm font-medium text-slate-300 mb-3">
            Observações (opcional)
          </label>
          <textarea
            value={observacoes}
            onChange={(e) => setObservacoes(e.target.value)}
            rows={3}
            className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-xl text-white placeholder-slate-500 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="Ex: Cliente X não estava em casa, produto Y danificado..."
          />
        </div>

        {/* Resumo */}
        <div className="bg-gradient-to-r from-slate-800/90 to-slate-700/90 backdrop-blur-lg rounded-2xl p-6 border border-slate-600/30 shadow-xl">
          <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-emerald-400" />
            Resumo do Acerto
          </h3>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div className="bg-blue-500/20 rounded-xl p-4 border border-blue-500/30">
              <p className="text-3xl font-bold text-blue-300">
                {itensAcerto.reduce((sum, i) => sum + i.qtd_saida, 0)}
              </p>
              <p className="text-xs text-slate-400 mt-1">Saíram</p>
            </div>
            <div className="bg-emerald-500/20 rounded-xl p-4 border border-emerald-500/30">
              <p className="text-3xl font-bold text-emerald-300">
                {itensAcerto.reduce((sum, i) => sum + i.qtd_vendida, 0)}
              </p>
              <p className="text-xs text-slate-400 mt-1">Vendidos</p>
            </div>
            <div className="bg-amber-500/20 rounded-xl p-4 border border-amber-500/30">
              <p className="text-3xl font-bold text-amber-300">
                {itensAcerto.reduce((sum, i) => sum + i.qtd_retorno_cheio, 0)}
              </p>
              <p className="text-xs text-slate-400 mt-1">Retornaram</p>
            </div>
          </div>
        </div>

        {/* Botão de Enviar */}
        <button
          onClick={handleSubmit}
          disabled={submitting}
          className={`w-full py-4 rounded-xl font-semibold text-white text-lg transition-all duration-200 shadow-lg ${
            submitting
              ? 'bg-slate-600 cursor-not-allowed'
              : 'bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 shadow-emerald-500/30 hover:shadow-emerald-500/50'
          }`}
        >
          {submitting ? (
            <span className="flex items-center justify-center gap-2">
              <Loader className="w-5 h-5 animate-spin" />
              Finalizando...
            </span>
          ) : (
            'FINALIZAR ACERTO'
          )}
        </button>
      </div>
    </div>
  )
}
