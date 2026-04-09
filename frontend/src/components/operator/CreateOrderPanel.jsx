/**
 * Painel para Criar Pedidos Manualmente
 * Para operadores que recebem pedidos por telefone
 */

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { getProducts, getCustomers, createCustomer, createOrder } from '../../services/api'

const inputCls = 'w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:border-blue-500 dark:focus:border-blue-400'

export default function CreateOrderPanel() {
  const navigate = useNavigate()

  const [products, setProducts] = useState([])

  const [customerData, setCustomerData] = useState({
    name: '',
    phone: '',
    cpf: '',
    cep: '',
    address: '',
    bairro: '',
    city: 'Curitiba',
    state: 'PR',
    numero: '',
    complemento: '',
    pontoReferencia: ''
  })

  const [orderItems, setOrderItems] = useState([])
  const [paymentMethod, setPaymentMethod] = useState('dinheiro')
  const [tipoOperacao, setTipoOperacao] = useState('troca')
  const [notes, setNotes] = useState('')
  const [searchingCustomer, setSearchingCustomer] = useState(false)
  const [searchingCep, setSearchingCep] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchProducts()
  }, [])

  const fetchProducts = async () => {
    try {
      setLoading(true)
      const data = await getProducts()
      setProducts(data)
    } catch (error) {
      console.error('Erro ao buscar produtos:', error)
    } finally {
      setLoading(false)
    }
  }

  const searchCep = async (cep) => {
    const cleanCep = cep.replace(/\D/g, '')
    if (cleanCep.length !== 8) return
    try {
      setSearchingCep(true)
      let response = await fetch(`https://brasilapi.com.br/api/cep/v1/${cleanCep}`)
      if (!response.ok) {
        response = await fetch(`https://viacep.com.br/ws/${cleanCep}/json/`)
      }
      if (response.ok) {
        const data = await response.json()
        const street = data.street || data.logradouro || ''
        const neighborhood = data.neighborhood || data.bairro || ''
        const city = data.city || data.localidade || 'Curitiba'
        const state = data.state || data.uf || 'PR'
        if (!data.erro) {
          setCustomerData(prev => ({ ...prev, address: street, bairro: neighborhood, city, state }))
        }
      }
    } catch (error) {
      console.error('Erro ao buscar CEP:', error)
    } finally {
      setSearchingCep(false)
    }
  }

  const searchCustomer = async (phone) => {
    const cleanPhone = phone.replace(/\D/g, '')
    if (cleanPhone.length < 10) return
    try {
      setSearchingCustomer(true)
      const data = await getCustomers({ phone: cleanPhone })
      if (data && data.length > 0) {
        const customer = data[0]
        const address = customer.address || {}
        setCustomerData({
          name: customer.name || '',
          phone: customer.phone || cleanPhone,
          cpf: customer.cpf_cnpj || '',
          cep: address.cep || '',
          address: address.street || '',
          bairro: address.bairro || '',
          city: address.city || 'Curitiba',
          state: address.state || 'PR',
          numero: address.number || '',
          complemento: address.complement || '',
          pontoReferencia: address.reference || ''
        })
      } else {
        setCustomerData(prev => ({ ...prev, phone: cleanPhone }))
      }
    } catch (error) {
      console.error('Erro ao buscar cliente:', error)
    } finally {
      setSearchingCustomer(false)
    }
  }

  const addProduct = (product) => {
    const existing = orderItems.find(item => item.product_id === product.id)
    if (existing) {
      setOrderItems(orderItems.map(item =>
        item.product_id === product.id ? { ...item, quantity: item.quantity + 1 } : item
      ))
    } else {
      setOrderItems([...orderItems, {
        product_id: product.id,
        product_name: product.name,
        price: product.price,
        quantity: 1
      }])
    }
  }

  const updateQuantity = (productId, newQuantity) => {
    if (newQuantity <= 0) {
      removeProduct(productId)
    } else {
      setOrderItems(orderItems.map(item =>
        item.product_id === productId ? { ...item, quantity: newQuantity } : item
      ))
    }
  }

  const removeProduct = (productId) => {
    setOrderItems(orderItems.filter(item => item.product_id !== productId))
  }

  const calculateTotal = () => {
    return orderItems.reduce((sum, item) => sum + (item.price * item.quantity), 0)
  }

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!customerData.name || !customerData.phone) {
      toast.error('Nome e telefone são obrigatórios')
      return
    }
    if (orderItems.length === 0) {
      toast.error('Adicione pelo menos um produto')
      return
    }
    if (!customerData.address) {
      toast.error('Endereço é obrigatório')
      return
    }
    try {
      setSubmitting(true)
      let customerId = null
      const cleanPhone = customerData.phone.replace(/\D/g, '')
      try {
        const existingCustomers = await getCustomers({ phone: cleanPhone })
        if (existingCustomers && existingCustomers.length > 0) {
          customerId = existingCustomers[0].id
        }
      } catch (err) {}

      if (!customerId) {
        const customerPayload = {
          phone: cleanPhone,
          name: customerData.name,
          cpf_cnpj: customerData.cpf || null,
          address: {
            street: customerData.address,
            number: customerData.numero || '',
            complement: customerData.complemento || '',
            bairro: customerData.bairro || '',
            city: customerData.city || 'Curitiba',
            state: customerData.state || 'PR',
            cep: customerData.cep || null,
            reference: customerData.pontoReferencia || ''
          }
        }
        try {
          const newCustomer = await createCustomer(customerPayload)
          customerId = newCustomer.id
        } catch (err) {
          const errorMsg = err.response?.data?.detail || 'Erro desconhecido'
          toast.error(`Erro ao criar cliente: ${errorMsg}`)
          return
        }
      }

      const itemsWithCodes = []
      for (const item of orderItems) {
        const product = products.find(p => p.id === item.product_id)
        if (product) {
          itemsWithCodes.push({ product_code: product.code, quantity: item.quantity })
        }
      }

      const orderPayload = {
        customer_id: customerId,
        items: itemsWithCodes,
        payment_method: paymentMethod,
        tipo_operacao: tipoOperacao,
        delivery_address: {
          street: customerData.address,
          number: customerData.numero || '',
          complement: customerData.complemento || '',
          bairro: customerData.bairro || '',
          city: customerData.city || 'Curitiba',
          state: customerData.state || 'PR',
          cep: customerData.cep || null
        },
        delivery_bairro: customerData.bairro || null,
        notes: notes || null
      }

      const order = await createOrder(orderPayload)
      toast.success(`Pedido #${order.order_number || order.id} criado com sucesso!`)
      navigate('/operador')
    } catch (error) {
      console.error('Erro ao criar pedido:', error)
      const errorMsg = error.response?.data?.detail || error.message
      toast.error(`Erro ao criar pedido: ${errorMsg}`)
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="text-gray-600 dark:text-gray-400 mt-4">Carregando...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-100">📞 Criar Pedido Manual</h2>
        <p className="text-gray-600 dark:text-gray-400">Registrar pedidos recebidos por telefone ou presencialmente</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Dados do Cliente */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm p-6">
          <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-5 flex items-center gap-2">
            <span className="text-lg">👤</span> Dados do Cliente
          </h3>

          <div className="grid grid-cols-2 gap-4">
            {/* Telefone */}
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                Telefone *
              </label>
              <div className="flex gap-2">
                <input
                  type="tel"
                  value={customerData.phone}
                  onChange={(e) => setCustomerData({...customerData, phone: e.target.value})}
                  onBlur={(e) => searchCustomer(e.target.value)}
                  className={inputCls}
                  placeholder="5541999999999"
                  required
                />
                {searchingCustomer && (
                  <div className="flex items-center px-4 bg-blue-100 dark:bg-blue-900/30 rounded-lg text-sm text-blue-600 dark:text-blue-400 whitespace-nowrap">
                    🔍 Buscando...
                  </div>
                )}
              </div>
              <p className="text-xs text-green-600 dark:text-green-400 mt-1">
                ✅ Busca automática se telefone já cadastrado
              </p>
            </div>

            {/* Nome */}
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                Nome Completo *
              </label>
              <input
                type="text"
                value={customerData.name}
                onChange={(e) => setCustomerData({...customerData, name: e.target.value})}
                className={inputCls}
                placeholder="João da Silva"
                required
              />
            </div>

            {/* CPF */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">CPF</label>
              <input
                type="text"
                value={customerData.cpf}
                onChange={(e) => setCustomerData({...customerData, cpf: e.target.value})}
                className={inputCls}
                placeholder="000.000.000-00"
              />
            </div>

            {/* CEP */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">CEP</label>
              <div className="relative">
                <input
                  type="text"
                  value={customerData.cep}
                  onChange={(e) => setCustomerData({...customerData, cep: e.target.value})}
                  onBlur={(e) => searchCep(e.target.value)}
                  className={inputCls}
                  placeholder="80000-000"
                  maxLength="9"
                />
                {searchingCep && (
                  <div className="absolute right-3 top-1/2 -translate-y-1/2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                  </div>
                )}
              </div>
              <p className="text-xs text-amber-600 dark:text-amber-400 mt-1">
                ✨ Preenche endereço automaticamente
              </p>
            </div>

            {/* Endereço */}
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                Endereço (Rua) *
              </label>
              <input
                type="text"
                value={customerData.address}
                onChange={(e) => setCustomerData({...customerData, address: e.target.value})}
                className={inputCls}
                placeholder="Rua Exemplo"
                required
              />
            </div>

            {/* Bairro */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Bairro</label>
              <input
                type="text"
                value={customerData.bairro}
                onChange={(e) => setCustomerData({...customerData, bairro: e.target.value})}
                className={inputCls}
                placeholder="Centro"
              />
            </div>

            {/* Número */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Número *</label>
              <input
                type="text"
                value={customerData.numero}
                onChange={(e) => setCustomerData({...customerData, numero: e.target.value})}
                className={inputCls}
                placeholder="123"
                required
              />
            </div>

            {/* Cidade */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Cidade</label>
              <input
                type="text"
                value={customerData.city}
                onChange={(e) => setCustomerData({...customerData, city: e.target.value})}
                className={inputCls}
                placeholder="Curitiba"
              />
            </div>

            {/* Estado */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Estado</label>
              <input
                type="text"
                value={customerData.state}
                onChange={(e) => setCustomerData({...customerData, state: e.target.value})}
                className={inputCls}
                placeholder="PR"
                maxLength="2"
              />
            </div>

            {/* Complemento */}
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Complemento</label>
              <input
                type="text"
                value={customerData.complemento}
                onChange={(e) => setCustomerData({...customerData, complemento: e.target.value})}
                className={inputCls}
                placeholder="Apto 101"
              />
            </div>

            {/* Ponto de Referência */}
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Ponto de Referência</label>
              <input
                type="text"
                value={customerData.pontoReferencia}
                onChange={(e) => setCustomerData({...customerData, pontoReferencia: e.target.value})}
                className={inputCls}
                placeholder="Próximo ao mercado"
              />
            </div>
          </div>
        </div>

        {/* Produtos */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm p-6">
          <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-5 flex items-center gap-2">
            <span className="text-lg">📦</span> Produtos
          </h3>

          <div className="grid grid-cols-3 gap-4 mb-6">
            {products.map((product) => {
              const inCart = orderItems.find(i => i.product_id === product.id)
              return (
                <button
                  key={product.id}
                  type="button"
                  onClick={() => addProduct(product)}
                  className={`relative p-5 rounded-xl transition text-center border-2 ${
                    inCart
                      ? 'bg-blue-50 dark:bg-blue-900/30 border-blue-500 dark:border-blue-400'
                      : 'bg-gray-50 dark:bg-gray-700 border-gray-200 dark:border-gray-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:border-blue-400 dark:hover:border-blue-500'
                  }`}
                >
                  {inCart && (
                    <span className="absolute top-2 right-2 bg-blue-500 text-white text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center">
                      {inCart.quantity}
                    </span>
                  )}
                  <div className="text-3xl mb-2">🔥</div>
                  <p className="font-semibold text-gray-800 dark:text-gray-100 mb-1 text-sm">{product.name}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mb-2 line-clamp-2">{product.description}</p>
                  <p className="text-xl font-bold text-blue-600 dark:text-blue-400">{formatCurrency(product.price)}</p>
                  <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">Clique para adicionar</p>
                </button>
              )
            })}
          </div>

          {products.length === 0 && (
            <div className="text-center py-8 bg-gray-50 dark:bg-gray-700 rounded-lg">
              <p className="text-gray-500 dark:text-gray-400">📦 Nenhum produto disponível</p>
              <p className="text-sm text-gray-400 dark:text-gray-500 mt-2">Entre em contato com o administrador</p>
            </div>
          )}

          {/* Itens do Pedido */}
          {orderItems.length > 0 && (
            <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
              <h4 className="font-semibold text-gray-700 dark:text-gray-300 mb-3 text-sm">Itens selecionados:</h4>
              <div className="space-y-2">
                {orderItems.map((item) => (
                  <div key={item.product_id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg border border-gray-200 dark:border-gray-600">
                    <div className="flex-1">
                      <p className="font-medium text-gray-900 dark:text-white text-sm">{item.product_name}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">{formatCurrency(item.price)} × {item.quantity} = <span className="font-semibold text-gray-700 dark:text-gray-300">{formatCurrency(item.price * item.quantity)}</span></p>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => updateQuantity(item.product_id, item.quantity - 1)}
                        className="w-7 h-7 bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded-lg hover:bg-red-200 dark:hover:bg-red-900/50 font-bold text-sm"
                      >−</button>
                      <span className="w-6 text-center font-bold text-gray-900 dark:text-white text-sm">{item.quantity}</span>
                      <button
                        type="button"
                        onClick={() => updateQuantity(item.product_id, item.quantity + 1)}
                        className="w-7 h-7 bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 rounded-lg hover:bg-green-200 dark:hover:bg-green-900/50 font-bold text-sm"
                      >+</button>
                      <button
                        type="button"
                        onClick={() => removeProduct(item.product_id)}
                        className="ml-1 px-2.5 py-1 bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded-lg hover:bg-red-200 dark:hover:bg-red-900/50 text-xs font-medium"
                      >Remover</button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Operação e Pagamento */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm p-6">
          <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-5 flex items-center gap-2">
            <span className="text-lg">🔄</span> Operação e Pagamento
          </h3>

          <div className="space-y-4">
            {/* Tipo de Operação */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                Tipo de Operação *
              </label>
              <select
                value={tipoOperacao}
                onChange={(e) => setTipoOperacao(e.target.value)}
                className={inputCls}
                required
              >
                <option value="troca">🔄 TROCA - Cliente tem vasilhame (troca vazio por cheio)</option>
                <option value="venda">🆕 VENDA - Cliente sem vasilhame (paga caução)</option>
                <option value="retira">🏪 RETIRA - Cliente busca na loja</option>
              </select>
              <p className="text-xs mt-1">
                {tipoOperacao === 'troca' && <span className="text-green-600 dark:text-green-400">✅ Cliente já possui vasilhame e irá trocar</span>}
                {tipoOperacao === 'venda' && <span className="text-amber-600 dark:text-amber-400">⚠️ Cliente não tem vasilhame - cobrar caução</span>}
                {tipoOperacao === 'retira' && <span className="text-blue-600 dark:text-blue-400">📍 Sem entrega - cliente retira no local</span>}
              </p>
            </div>

            {/* Forma de Pagamento */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                Forma de Pagamento *
              </label>
              <select
                value={paymentMethod}
                onChange={(e) => setPaymentMethod(e.target.value)}
                className={inputCls}
                required
              >
                <option value="dinheiro">💵 Dinheiro</option>
                <option value="cartao_credito">💳 Cartão de Crédito</option>
                <option value="cartao_debito">💳 Cartão de Débito</option>
              </select>
            </div>

            {/* Observações */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                Observações
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className={inputCls}
                rows="3"
                placeholder="Troco para R$ 100,00, entregar antes das 18h, etc."
              />
            </div>
          </div>
        </div>

        {/* Total e Botões */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm p-6">
          <div className="flex items-center justify-between mb-6">
            <span className="text-lg font-semibold text-gray-700 dark:text-gray-300">Total do pedido</span>
            <span className="text-3xl font-bold text-green-600 dark:text-green-400">
              {formatCurrency(calculateTotal())}
            </span>
          </div>

          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => navigate('/operador')}
              className="flex-1 px-6 py-3 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition font-medium border border-gray-200 dark:border-gray-600"
            >
              ⬅️ Voltar
            </button>
            <button
              type="submit"
              disabled={submitting || orderItems.length === 0}
              className="flex-1 px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {submitting ? '⏳ Criando...' : '✅ Criar Pedido'}
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}
