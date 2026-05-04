import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent, within } from '@testing-library/react'

import MovementLog from '../MovementLog'

const products = [
  { id: 1, code: 'P13' },
  { id: 2, code: 'P20' },
]

const at = (mins) => new Date(Date.now() - mins * 60 * 1000).toISOString()

const sampleMovements = [
  { id: 'm1', movement_type: 'compra', stock_product_id: 1, direction: 'entrada', quantity: 50, notes: 'Lote 1', created_at: at(60) },
  { id: 'm2', movement_type: 'venda', stock_product_id: 2, direction: 'saida', quantity: 3, notes: '', created_at: at(45) },
  { id: 'm3', movement_type: 'carga_veiculo', stock_product_id: 1, direction: 'saida', quantity: 10, notes: null, created_at: at(30) },
  { id: 'm4', movement_type: 'ajuste_entrada', stock_product_id: 2, direction: 'entrada', quantity: 2, notes: 'Conferência', created_at: at(15) },
]

describe('MovementLog', () => {
  it('renders the empty state with Inbox icon when there are no movements', () => {
    const { container } = render(<MovementLog movements={[]} products={products} />)
    expect(screen.getByText(/Nenhuma movimentação registrada hoje/i)).toBeInTheDocument()
    expect(screen.getByText(/As movimentações aparecerão aqui/i)).toBeInTheDocument()
    expect(container.querySelector('svg.lucide-inbox')).toBeInTheDocument()
  })

  it('renders all movements by default with mapped icons and product codes', () => {
    const { container } = render(<MovementLog movements={sampleMovements} products={products} />)
    expect(screen.getByText('Compra')).toBeInTheDocument()
    expect(screen.getByText('Venda')).toBeInTheDocument()
    expect(screen.getByText('Carga Veículo')).toBeInTheDocument()
    expect(screen.getByText('Ajuste +')).toBeInTheDocument()
    expect(screen.getAllByText('P13').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('P20').length).toBeGreaterThanOrEqual(1)
    // signed quantities
    expect(screen.getByText('+50')).toBeInTheDocument()
    expect(screen.getByText('-3')).toBeInTheDocument()
    // four lucide icons in tbody (one per row)
    expect(container.querySelectorAll('tbody svg').length).toBe(sampleMovements.length)
  })

  it('filters by Compras chip', () => {
    render(<MovementLog movements={sampleMovements} products={products} />)
    fireEvent.click(screen.getByRole('tab', { name: 'Compras' }))
    expect(screen.getByText('Compra')).toBeInTheDocument()
    expect(screen.queryByText('Venda')).not.toBeInTheDocument()
    expect(screen.queryByText('Carga Veículo')).not.toBeInTheDocument()
    expect(screen.queryByText('Ajuste +')).not.toBeInTheDocument()
  })

  it('filters by Cargas (carga_veiculo + retorno_veiculo)', () => {
    const movements = [
      ...sampleMovements,
      { id: 'm5', movement_type: 'retorno_veiculo', stock_product_id: 2, direction: 'entrada', quantity: 4, notes: '', created_at: at(5) },
    ]
    render(<MovementLog movements={movements} products={products} />)
    fireEvent.click(screen.getByRole('tab', { name: 'Cargas' }))
    expect(screen.getByText('Carga Veículo')).toBeInTheDocument()
    expect(screen.getByText('Retorno Veículo')).toBeInTheDocument()
    expect(screen.queryByText('Compra')).not.toBeInTheDocument()
  })

  it('filters by Ajustes (entrada/saida/devolucao/perda)', () => {
    const movements = [
      ...sampleMovements,
      { id: 'm6', movement_type: 'ajuste_saida', stock_product_id: 1, direction: 'saida', quantity: 1, notes: '', created_at: at(4) },
      { id: 'm7', movement_type: 'devolucao_cliente', stock_product_id: 1, direction: 'entrada', quantity: 2, notes: '', created_at: at(3) },
      { id: 'm8', movement_type: 'perda', stock_product_id: 2, direction: 'saida', quantity: 1, notes: '', created_at: at(2) },
    ]
    render(<MovementLog movements={movements} products={products} />)
    fireEvent.click(screen.getByRole('tab', { name: 'Ajustes' }))
    expect(screen.getByText('Ajuste +')).toBeInTheDocument()
    expect(screen.getByText('Ajuste -')).toBeInTheDocument()
    expect(screen.getByText('Devolução')).toBeInTheDocument()
    expect(screen.getByText('Perda')).toBeInTheDocument()
    expect(screen.queryByText('Compra')).not.toBeInTheDocument()
    expect(screen.queryByText('Venda')).not.toBeInTheDocument()
    expect(screen.queryByText('Carga Veículo')).not.toBeInTheDocument()
  })

  it('shows the empty-filter state when active filter has no matches', () => {
    const movements = [sampleMovements[0]] // só compra
    render(<MovementLog movements={movements} products={products} />)
    fireEvent.click(screen.getByRole('tab', { name: 'Vendas' }))
    expect(screen.getByText(/Nenhuma movimentação neste filtro/i)).toBeInTheDocument()
    expect(screen.getByText(/Tente outro filtro acima/i)).toBeInTheDocument()
  })

  it('marks the active chip with aria-selected and primary styling', () => {
    render(<MovementLog movements={sampleMovements} products={products} />)
    const todos = screen.getByRole('tab', { name: 'Todos' })
    expect(todos).toHaveAttribute('aria-selected', 'true')
    expect(todos.className).toMatch(/bg-primary-500/)

    const vendas = screen.getByRole('tab', { name: 'Vendas' })
    expect(vendas).toHaveAttribute('aria-selected', 'false')
    expect(vendas.className).toMatch(/bg-slate-100/)

    fireEvent.click(vendas)
    expect(vendas).toHaveAttribute('aria-selected', 'true')
    expect(todos).toHaveAttribute('aria-selected', 'false')
  })

  it('falls back to a slice of the product id when product is not in the map', () => {
    const orphan = {
      id: 'm-orphan',
      movement_type: 'compra',
      stock_product_id: 'abcd1234efgh5678',
      direction: 'entrada',
      quantity: 1,
      notes: '',
      created_at: at(1),
    }
    render(<MovementLog movements={[orphan]} products={products} />)
    expect(screen.getByText('abcd1234')).toBeInTheDocument()
  })

  it('renders unknown movement types with a fallback label and Inbox icon', () => {
    const unknown = {
      id: 'm-unknown',
      movement_type: 'tipo_x',
      stock_product_id: 1,
      direction: 'entrada',
      quantity: 1,
      notes: '',
      created_at: at(1),
    }
    const { container } = render(<MovementLog movements={[unknown]} products={products} />)
    expect(screen.getByText('tipo_x')).toBeInTheDocument()
    const tbodyIcons = container.querySelectorAll('tbody svg')
    expect(tbodyIcons.length).toBe(1)
  })

  it('shows "-" for empty notes', () => {
    const movement = sampleMovements[1] // notes: ''
    render(<MovementLog movements={[movement]} products={products} />)
    const row = screen.getByText('Venda').closest('tr')
    expect(within(row).getByText('-')).toBeInTheDocument()
  })

  it('uses emerald for entrada and rose for saida quantity coloring', () => {
    render(<MovementLog movements={sampleMovements} products={products} />)
    const plus = screen.getByText('+50')
    const minus = screen.getByText('-3')
    expect(plus.className).toMatch(/text-emerald-700/)
    expect(plus.className).toMatch(/font-bold/)
    expect(minus.className).toMatch(/text-rose-700/)
  })

  it('has no dark-mode classes (white-bg compliant)', () => {
    const { container } = render(<MovementLog movements={sampleMovements} products={products} />)
    const html = container.innerHTML
    expect(html).not.toMatch(/text-gray-400/)
    expect(html).not.toMatch(/border-gray-700/)
    expect(html).not.toMatch(/bg-gray-700/)
    // text-white only allowed on the active filter chip (bg-primary-500)
    const tableHtml = container.querySelector('table')?.outerHTML ?? ''
    expect(tableHtml).not.toMatch(/text-white/)
  })
})
