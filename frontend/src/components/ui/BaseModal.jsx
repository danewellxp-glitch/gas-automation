import { useEffect } from 'react'

export default function BaseModal({
  children,
  onClose,
  maxWidth = 'max-w-md',
  closeOnBackdrop = true,
}) {
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose?.() }
    window.addEventListener('keydown', onKey)
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = prevOverflow
    }
  }, [onClose])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 animate-fade-in p-4"
      onClick={closeOnBackdrop ? onClose : undefined}
    >
      <div
        className={`bg-white rounded-xl shadow-xl w-full ${maxWidth} animate-scale-in`}
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  )
}
