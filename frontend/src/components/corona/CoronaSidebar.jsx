import { useEffect, useRef } from 'react'

export default function CoronaSidebar({
  title,
  subtitle,
  children,
  footer,
  onCloseMobile,
}) {
  const sidebarRef = useRef(null)

  // Fecha sidebar ao clicar fora (mobile)
  useEffect(() => {
    function onDocClick(e) {
      const root = document.querySelector('.corona')
      if (!root?.classList.contains('corona-sidebar-open')) return
      if (!sidebarRef.current) return
      if (sidebarRef.current.contains(e.target)) return
      onCloseMobile?.()
    }

    document.addEventListener('mousedown', onDocClick)
    return () => document.removeEventListener('mousedown', onDocClick)
  }, [onCloseMobile])

  return (
    <aside ref={sidebarRef} className="corona-sidebar" aria-label="Sidebar">
      <div className="corona-sidebar-brand">
        <div className="corona-brand-mark">GA</div>
        <div className="corona-brand-text">
          <div className="corona-brand-title">{title}</div>
          {subtitle ? <div className="corona-brand-subtitle">{subtitle}</div> : null}
        </div>
        <button
          type="button"
          className="corona-sidebar-close"
          onClick={() => onCloseMobile?.()}
          aria-label="Fechar menu"
        >
          ✕
        </button>
      </div>

      <div className="corona-sidebar-content">
        {children}
      </div>

      {footer ? <div className="corona-sidebar-footer">{footer}</div> : null}
    </aside>
  )
}

