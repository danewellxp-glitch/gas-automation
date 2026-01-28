import { useState } from 'react'
import { apiRequest } from '../../utils/api'
import { RefreshCcw, ShieldAlert } from 'lucide-react'

function JsonBox({ value }) {
  if (!value) return null
  return (
    <pre className="mt-3 max-h-80 overflow-auto rounded-lg bg-gray-50 p-3 text-xs text-gray-700">
      {JSON.stringify(value, null, 2)}
    </pre>
  )
}

export default function DebugToolsPanel() {
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const [confirmToken, setConfirmToken] = useState('')
  const [confirmExpires, setConfirmExpires] = useState(null)

  const [simulate, setSimulate] = useState({ phone: '', message: '' })
  const [simulateResult, setSimulateResult] = useState(null)

  const [contextPhone, setContextPhone] = useState('')
  const [contextResult, setContextResult] = useState(null)

  const [fakeOrder, setFakeOrder] = useState({ phone: '', product_code: 'P13', quantity: 1 })
  const [fakeOrderResult, setFakeOrderResult] = useState(null)

  const [reexec, setReexec] = useState({ phone: '', messages: '' })
  const [reexecResult, setReexecResult] = useState(null)

  const ensureToken = () => {
    if (!confirmToken) throw new Error('Gere um confirm_token antes (Confirmação dupla).')
  }

  const requestConfirmToken = async () => {
    try {
      setLoading(true)
      setError('')
      const res = await apiRequest('admin/debug/confirm', { method: 'POST' })
      setConfirmToken(res.confirm_token)
      setConfirmExpires(res.expires_in_seconds)
    } catch (e) {
      setError(e.message || 'Erro ao gerar confirm token')
    } finally {
      setLoading(false)
    }
  }

  const doSimulate = async () => {
    try {
      ensureToken()
      setLoading(true)
      setError('')
      const res = await apiRequest('admin/debug/simulate-message', {
        method: 'POST',
        body: JSON.stringify({
          phone: simulate.phone,
          message: simulate.message,
          confirm_token: confirmToken,
          confirm_text: 'CONFIRM',
        }),
      })
      setSimulateResult(res)
    } catch (e) {
      setError(e.message || 'Erro ao simular mensagem')
    } finally {
      setLoading(false)
    }
  }

  const getContext = async () => {
    try {
      setLoading(true)
      setError('')
      const res = await apiRequest(`admin/debug/context/${encodeURIComponent(contextPhone)}`)
      setContextResult(res)
    } catch (e) {
      setError(e.message || 'Erro ao buscar contexto')
    } finally {
      setLoading(false)
    }
  }

  const resetContext = async () => {
    try {
      ensureToken()
      setLoading(true)
      setError('')
      const res = await apiRequest(`admin/debug/context/${encodeURIComponent(contextPhone)}`, {
        method: 'DELETE',
        body: JSON.stringify({ confirm_token: confirmToken, confirm_text: 'CONFIRM' }),
      })
      setContextResult(res)
    } catch (e) {
      setError(e.message || 'Erro ao resetar contexto')
    } finally {
      setLoading(false)
    }
  }

  const createFakeOrder = async () => {
    try {
      ensureToken()
      setLoading(true)
      setError('')
      const res = await apiRequest('admin/debug/create-fake-order', {
        method: 'POST',
        body: JSON.stringify({
          ...fakeOrder,
          quantity: Number(fakeOrder.quantity),
          confirm_token: confirmToken,
          confirm_text: 'CONFIRM',
        }),
      })
      setFakeOrderResult(res)
    } catch (e) {
      setError(e.message || 'Erro ao criar pedido fake')
    } finally {
      setLoading(false)
    }
  }

  const reexecute = async () => {
    try {
      ensureToken()
      setLoading(true)
      setError('')
      const messages = reexec.messages
        .split('\n')
        .map((s) => s.trim())
        .filter(Boolean)
      const res = await apiRequest('admin/debug/reexecute-state-machine', {
        method: 'POST',
        body: JSON.stringify({
          phone: reexec.phone,
          messages,
          confirm_token: confirmToken,
          confirm_text: 'CONFIRM',
        }),
      })
      setReexecResult(res)
    } catch (e) {
      setError(e.message || 'Erro ao reexecutar state machine')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-semibold text-gray-900">Ferramentas de Debug</h2>
        <p className="text-gray-600">Admin-only • ações perigosas exigem confirmação dupla</p>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>
      )}

      <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
        <div className="flex items-start gap-3">
          <ShieldAlert className="mt-0.5 h-5 w-5" />
          <div>
            <div className="font-semibold">Atenção</div>
            <div className="text-amber-800">
              Use em ambiente controlado. Todas as ações são auditáveis e podem afetar pedidos reais.
            </div>
          </div>
        </div>
      </div>

      <div className="mb-6 rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="text-sm font-semibold text-gray-900">Confirmação dupla</div>
            <div className="text-xs text-gray-500">Gere um token com validade curta para liberar ações perigosas.</div>
          </div>
          <button
            onClick={requestConfirmToken}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-3 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          >
            <RefreshCcw className="h-4 w-4" />
            {loading ? 'Aguarde...' : 'Gerar confirm_token'}
          </button>
        </div>
        {confirmToken && (
          <div className="mt-3 rounded-lg border border-gray-200 bg-gray-50 p-3">
            <div className="text-xs text-gray-600">confirm_token (TTL {confirmExpires}s)</div>
            <div className="mt-1 break-all font-mono text-sm text-gray-900">{confirmToken}</div>
          </div>
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <div className="text-sm font-semibold text-gray-900">Simular mensagem WhatsApp</div>
          <div className="mt-3 space-y-3">
            <input
              value={simulate.phone}
              onChange={(e) => setSimulate((p) => ({ ...p, phone: e.target.value }))}
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm"
              placeholder="Telefone (ex: 5541999999999)"
            />
            <textarea
              value={simulate.message}
              onChange={(e) => setSimulate((p) => ({ ...p, message: e.target.value }))}
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm"
              rows={3}
              placeholder="Mensagem"
            />
            <button
              onClick={doSimulate}
              disabled={loading || !simulate.phone || !simulate.message}
              className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
            >
              Executar
            </button>
          </div>
          <JsonBox value={simulateResult} />
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <div className="text-sm font-semibold text-gray-900">Contexto Redis (chat:{'{phone}'})</div>
          <div className="mt-3 space-y-3">
            <input
              value={contextPhone}
              onChange={(e) => setContextPhone(e.target.value)}
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm"
              placeholder="Telefone"
            />
            <div className="flex flex-wrap gap-2">
              <button
                onClick={getContext}
                disabled={loading || !contextPhone}
                className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                Buscar
              </button>
              <button
                onClick={resetContext}
                disabled={loading || !contextPhone}
                className="rounded-lg bg-amber-600 px-4 py-2 text-sm font-medium text-white hover:bg-amber-700 disabled:opacity-50"
              >
                Resetar contexto
              </button>
            </div>
          </div>
          <JsonBox value={contextResult} />
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <div className="text-sm font-semibold text-gray-900">Criar pedido fake</div>
          <div className="mt-3 space-y-3">
            <input
              value={fakeOrder.phone}
              onChange={(e) => setFakeOrder((p) => ({ ...p, phone: e.target.value }))}
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm"
              placeholder="Telefone"
            />
            <div className="grid gap-2 sm:grid-cols-2">
              <input
                value={fakeOrder.product_code}
                onChange={(e) => setFakeOrder((p) => ({ ...p, product_code: e.target.value }))}
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm"
                placeholder="Produto (ex: P13)"
              />
              <input
                type="number"
                value={fakeOrder.quantity}
                onChange={(e) => setFakeOrder((p) => ({ ...p, quantity: e.target.value }))}
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm"
                min={1}
              />
            </div>
            <button
              onClick={createFakeOrder}
              disabled={loading || !fakeOrder.phone}
              className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
            >
              Criar
            </button>
          </div>
          <JsonBox value={fakeOrderResult} />
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <div className="text-sm font-semibold text-gray-900">Reexecutar state machine (passo a passo)</div>
          <div className="mt-3 space-y-3">
            <input
              value={reexec.phone}
              onChange={(e) => setReexec((p) => ({ ...p, phone: e.target.value }))}
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm"
              placeholder="Telefone"
            />
            <textarea
              value={reexec.messages}
              onChange={(e) => setReexec((p) => ({ ...p, messages: e.target.value }))}
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm"
              rows={5}
              placeholder={'Digite uma mensagem por linha\nEx:\nmenu\nfazer_pedido\nP13'}
            />
            <button
              onClick={reexecute}
              disabled={loading || !reexec.phone || !reexec.messages.trim()}
              className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
            >
              Executar
            </button>
          </div>
          <JsonBox value={reexecResult} />
        </div>
      </div>
    </div>
  )
}

