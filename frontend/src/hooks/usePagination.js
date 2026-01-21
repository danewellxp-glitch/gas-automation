import { useState, useCallback, useEffect, useRef } from 'react'

/**
 * Hook para gerenciar paginação com infinite scroll.
 * 
 * @param {Function} fetchFunction - Função que busca dados (async function(page, pageSize))
 * @param {Object} options - Opções de configuração
 * @param {number} options.pageSize - Tamanho da página (padrão: 30)
 * @param {boolean} options.enabled - Se deve carregar automaticamente (padrão: true)
 * @param {Array} options.dependencies - Dependências que resetam a paginação
 * 
 * @returns {Object} - Estado e funções da paginação
 */
export function usePagination(fetchFunction, options = {}) {
  const {
    pageSize = 30,
    enabled = true,
    dependencies = [],
  } = options

  const [data, setData] = useState([])
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(0)
  const [hasNext, setHasNext] = useState(false)
  const [hasPrev, setHasPrev] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [initialLoad, setInitialLoad] = useState(true)

  // Ref para evitar duplicate requests
  const isLoadingRef = useRef(false)

  const loadPage = useCallback(async (pageNumber, append = false) => {
    if (isLoadingRef.current || !enabled) return

    isLoadingRef.current = true
    setLoading(true)
    setError(null)

    try {
      const response = await fetchFunction(pageNumber, pageSize)
      
      // Validar resposta
      if (!response || typeof response !== 'object') {
        throw new Error('Resposta inválida do servidor')
      }

      const { items = [], total: totalItems = 0, total_pages = 0, has_next = false, has_prev = false } = response

      if (append) {
        // Infinite scroll: adicionar novos itens
        setData(prev => [...prev, ...items])
      } else {
        // Nova busca: substituir itens
        setData(items)
      }

      setTotal(totalItems)
      setTotalPages(total_pages)
      setHasNext(has_next)
      setHasPrev(has_prev)
      setPage(pageNumber)
      setInitialLoad(false)

    } catch (err) {
      console.error('Erro ao carregar página:', err)
      setError(err.message || 'Erro ao carregar dados')
    } finally {
      setLoading(false)
      isLoadingRef.current = false
    }
  }, [fetchFunction, pageSize, enabled])

  // Carregar primeira página automaticamente
  useEffect(() => {
    if (enabled && initialLoad) {
      loadPage(1, false)
    }
  }, [enabled, initialLoad, loadPage])

  // Reset quando dependências mudarem
  useEffect(() => {
    if (dependencies.length > 0) {
      setData([])
      setPage(1)
      setInitialLoad(true)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependencies)

  // Funções de controle
  const nextPage = useCallback(() => {
    if (hasNext && !loading) {
      loadPage(page + 1, true)
    }
  }, [hasNext, loading, page, loadPage])

  const prevPage = useCallback(() => {
    if (hasPrev && !loading) {
      loadPage(page - 1, false)
    }
  }, [hasPrev, loading, page, loadPage])

  const goToPage = useCallback((pageNumber) => {
    if (pageNumber >= 1 && pageNumber <= totalPages && !loading) {
      loadPage(pageNumber, false)
    }
  }, [totalPages, loading, loadPage])

  const refresh = useCallback(() => {
    setData([])
    setPage(1)
    setInitialLoad(true)
  }, [])

  const addItem = useCallback((item) => {
    setData(prev => [item, ...prev])
    setTotal(prev => prev + 1)
  }, [])

  const updateItem = useCallback((id, updater) => {
    setData(prev => prev.map(item => 
      item.id === id ? (typeof updater === 'function' ? updater(item) : updater) : item
    ))
  }, [])

  const removeItem = useCallback((id) => {
    setData(prev => prev.filter(item => item.id !== id))
    setTotal(prev => Math.max(0, prev - 1))
  }, [])

  return {
    // Dados
    data,
    total,
    page,
    pageSize,
    totalPages,
    hasNext,
    hasPrev,
    
    // Estado
    loading,
    error,
    initialLoad,
    isEmpty: data.length === 0 && !loading && !initialLoad,
    
    // Funções
    nextPage,
    prevPage,
    goToPage,
    refresh,
    addItem,
    updateItem,
    removeItem,
  }
}

/**
 * Hook para infinite scroll - carrega mais itens automaticamente ao scrollar.
 * 
 * @param {Object} paginationState - Estado retornado por usePagination
 * @param {Object} options - Opções de configuração
 * @param {number} options.threshold - Distância do fundo para carregar (px, padrão: 500)
 * 
 * @returns {Object} - Ref para o container e estado
 */
export function useInfiniteScroll(paginationState, options = {}) {
  const { threshold = 500 } = options
  const { hasNext, loading, nextPage } = paginationState
  
  const containerRef = useRef(null)
  const [isNearBottom, setIsNearBottom] = useState(false)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = container
      const distanceFromBottom = scrollHeight - scrollTop - clientHeight
      
      setIsNearBottom(distanceFromBottom < threshold)
      
      // Auto-load se estiver perto do fundo
      if (distanceFromBottom < threshold && hasNext && !loading) {
        nextPage()
      }
    }

    container.addEventListener('scroll', handleScroll)
    
    // Verificar inicialmente
    handleScroll()

    return () => container.removeEventListener('scroll', handleScroll)
  }, [hasNext, loading, nextPage, threshold])

  return {
    containerRef,
    isNearBottom,
  }
}

export default usePagination
