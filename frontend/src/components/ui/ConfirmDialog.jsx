import { useState, useCallback, createContext, useContext } from 'react'
import BaseModal from './BaseModal'

const ConfirmCtx = createContext(null)

export function useConfirm() {
  const ctx = useContext(ConfirmCtx)
  if (!ctx) throw new Error('useConfirm deve ser usado dentro de ConfirmProvider')
  return ctx
}

export function ConfirmProvider({ children }) {
  const [state, setState] = useState(null)

  const confirm = useCallback((opts) => {
    return new Promise((resolve) => {
      setState({ ...opts, resolve })
    })
  }, [])

  const close = (result) => {
    state?.resolve?.(result)
    setState(null)
  }

  return (
    <ConfirmCtx.Provider value={confirm}>
      {children}
      {state && (
        <BaseModal onClose={() => close(false)} maxWidth="max-w-sm">
          <div className="p-6">
            <h3 className="text-base font-semibold text-gray-900 mb-2">
              {state.title || 'Confirmar ação'}
            </h3>
            {state.message && (
              <p className="text-sm text-gray-600 mb-4">{state.message}</p>
            )}
            <div className="flex gap-2">
              <button
                onClick={() => close(false)}
                className="flex-1 px-4 py-2 rounded-lg border border-gray-200 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
              >
                {state.cancelLabel || 'Cancelar'}
              </button>
              <button
                onClick={() => close(true)}
                className={`flex-1 px-4 py-2 rounded-lg text-white text-sm font-medium transition-colors ${
                  state.danger
                    ? 'bg-red-600 hover:bg-red-700'
                    : 'bg-gray-900 hover:bg-gray-800'
                }`}
              >
                {state.confirmLabel || 'Confirmar'}
              </button>
            </div>
          </div>
        </BaseModal>
      )}
    </ConfirmCtx.Provider>
  )
}
