/**
 * Página de Acerto de Carga do Motorista
 * Permite registrar retornos e vendas do dia
 */

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { driverApi } from '../../utils/driverApi'

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
        const data = await driverApi.getCargaAtual()

        if (!data.tem_carga) {
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
        const itensIniciais = data.carga.itens.map(item => ({
          produto_id: item.produto_id,
          produto_nome: item.produto_nome || 'Produto',
          produto_codigo: item.produto_codigo || '',
          qtd_saida: item.qtd_saida,
          qtd_retorno_cheio: 0,
          qtd_retorno_vazio: 0,
          qtd_vendida: item.qtd_saida // Por padrão, assume que vendeu tudo
        }))
        setItensAcerto(itensIniciais)

      } catch (err) {
        console.error('Erro ao carregar carga:', err)
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchCarga()
  }, [])

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
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">📦</div>
          <p className="text-gray-600">Carregando carga...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full text-center">
          <div className="text-6xl mb-4">📭</div>
          <h2 className="text-xl font-bold text-gray-800 mb-4">Sem Carga Ativa</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <button
            onClick={() => navigate('/driver/dashboard')}
            className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700"
          >
            Voltar ao Dashboard
          </button>
        </div>
      </div>
    )
  }

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
        <h1 className="text-2xl font-bold text-gray-800">Acerto de Carga</h1>
        <p className="text-sm text-gray-500">
          Saída: {carga?.data_saida ? new Date(carga.data_saida).toLocaleString('pt-BR') : 'N/A'}
        </p>
      </div>

      <div className="max-w-2xl mx-auto px-4 space-y-4">
        {/* Instruções */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h3 className="font-semibold text-blue-800 mb-2">Como fazer o acerto:</h3>
          <ul className="text-sm text-blue-700 space-y-1">
            <li>• Informe quantos produtos <strong>voltaram cheios</strong></li>
            <li>• Informe quantos <strong>vazios</strong> você trouxe de volta</li>
            <li>• O sistema calcula automaticamente o <strong>vendido</strong></li>
          </ul>
        </div>

        {/* Lista de Itens */}
        {itensAcerto.map((item, index) => (
          <div key={item.produto_id} className="bg-white rounded-lg shadow p-4">
            <div className="flex justify-between items-start mb-3">
              <div>
                <h3 className="font-semibold text-gray-800">{item.produto_nome}</h3>
                {item.produto_codigo && (
                  <span className="text-sm text-gray-500">{item.produto_codigo}</span>
                )}
              </div>
              <span className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm font-medium">
                Saiu: {item.qtd_saida}
              </span>
            </div>

            <div className="grid grid-cols-3 gap-3">
              {/* Retornou Cheio */}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Retornou Cheio
                </label>
                <input
                  type="number"
                  min="0"
                  max={item.qtd_saida}
                  value={item.qtd_retorno_cheio}
                  onChange={(e) => {
                    handleItemChange(index, 'qtd_retorno_cheio', e.target.value)
                    // Recalcular vendido
                    setTimeout(() => calcularVendido(index), 0)
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-center text-lg font-semibold focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* Retornou Vazio */}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Vazios Trocados
                </label>
                <input
                  type="number"
                  min="0"
                  value={item.qtd_retorno_vazio}
                  onChange={(e) => handleItemChange(index, 'qtd_retorno_vazio', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-center text-lg font-semibold focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* Vendido (calculado) */}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Vendido
                </label>
                <input
                  type="number"
                  min="0"
                  max={item.qtd_saida}
                  value={item.qtd_vendida}
                  onChange={(e) => handleItemChange(index, 'qtd_vendida', e.target.value)}
                  className="w-full px-3 py-2 border border-green-300 rounded-lg text-center text-lg font-semibold bg-green-50 text-green-700 focus:ring-2 focus:ring-green-500"
                />
              </div>
            </div>

            {/* Validação visual */}
            {item.qtd_vendida + item.qtd_retorno_cheio !== item.qtd_saida && (
              <p className="text-xs text-orange-600 mt-2">
                Atenção: Vendido ({item.qtd_vendida}) + Retorno Cheio ({item.qtd_retorno_cheio}) = {item.qtd_vendida + item.qtd_retorno_cheio} (Saída: {item.qtd_saida})
              </p>
            )}
          </div>
        ))}

        {/* Observações */}
        <div className="bg-white rounded-lg shadow p-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Observações (opcional)
          </label>
          <textarea
            value={observacoes}
            onChange={(e) => setObservacoes(e.target.value)}
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            placeholder="Ex: Cliente X não estava em casa, produto Y danificado..."
          />
        </div>

        {/* Resumo */}
        <div className="bg-gray-800 text-white rounded-lg shadow p-4">
          <h3 className="font-semibold mb-3">Resumo do Acerto</h3>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <p className="text-2xl font-bold text-blue-400">
                {itensAcerto.reduce((sum, i) => sum + i.qtd_saida, 0)}
              </p>
              <p className="text-xs text-gray-400">Saíram</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-green-400">
                {itensAcerto.reduce((sum, i) => sum + i.qtd_vendida, 0)}
              </p>
              <p className="text-xs text-gray-400">Vendidos</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-yellow-400">
                {itensAcerto.reduce((sum, i) => sum + i.qtd_retorno_cheio, 0)}
              </p>
              <p className="text-xs text-gray-400">Retornaram</p>
            </div>
          </div>
        </div>

        {/* Botão de Enviar */}
        <button
          onClick={handleSubmit}
          disabled={submitting}
          className={`w-full py-4 rounded-lg font-semibold text-white text-lg ${
            submitting
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-green-600 hover:bg-green-700 active:bg-green-800'
          }`}
        >
          {submitting ? 'Finalizando...' : 'FINALIZAR ACERTO'}
        </button>
      </div>
    </div>
  )
}
