import { createContext, useCallback, useContext, useState } from 'react'

const ToastCtx = createContext(null)

export function useToast() {
  const ctx = useContext(ToastCtx)
  if (!ctx) throw new Error('useToast deve ser usado dentro de ToastProvider')
  return ctx
}

const TYPE_STYLES = {
  success: 'bg-emerald-50 border-emerald-200 text-emerald-800',
  error:   'bg-red-50 border-red-200 text-red-700',
  warning: 'bg-amber-50 border-amber-200 text-amber-800',
  info:    'bg-white border-gray-200 text-gray-700',
}

export function ToastProvider({ children }) {
  const [items, setItems] = useState([])

  const push = useCallback((message, type = 'info', durationMs = 3500) => {
    const id = Date.now() + Math.random()
    setItems((s) => [...s, { id, message, type }])
    setTimeout(() => {
      setItems((s) => s.filter((x) => x.id !== id))
    }, durationMs)
    return id
  }, [])

  const dismiss = useCallback((id) => {
    setItems((s) => s.filter((x) => x.id !== id))
  }, [])

  const api = {
    push,
    dismiss,
    success: (msg, d) => push(msg, 'success', d),
    error:   (msg, d) => push(msg, 'error', d),
    warning: (msg, d) => push(msg, 'warning', d),
    info:    (msg, d) => push(msg, 'info', d),
  }

  return (
    <ToastCtx.Provider value={api}>
      {children}
      <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none">
        {items.map((t) => (
          <div
            key={t.id}
            role="status"
            onClick={() => dismiss(t.id)}
            className={`pointer-events-auto cursor-pointer px-4 py-2.5 rounded-lg border text-sm shadow-sm animate-slide-in-right max-w-sm ${TYPE_STYLES[t.type] || TYPE_STYLES.info}`}
          >
            {t.message}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  )
}
