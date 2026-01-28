import { useEffect, useMemo, useState } from 'react'
import { useLocation } from 'react-router-dom'
import CoronaNavbar from './CoronaNavbar'
import CoronaSidebar from './CoronaSidebar'
import CoronaFooter from './CoronaFooter'

/**
 * CoronaLayout
 * - Replica a estrutura visual do template Corona (sidebar + navbar + main-panel)
 * - Mantém compatibilidade com o app atual (React 18 + Router v6 + Tailwind)
 * - Não depende de Bootstrap: apenas classes próprias (corona-*)
 */
export default function CoronaLayout({
  sidebarTitle = 'Gas Automation',
  sidebarSubtitle = '',
  sidebarContent = null,
  sidebarFooter = null,
  navbarTitle = '',
  children,
}) {
  const location = useLocation()
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false)
  const [isIconOnly, setIsIconOnly] = useState(false)

  // Fecha sidebar mobile ao trocar rota (evita overlay preso)
  useEffect(() => {
    setIsMobileSidebarOpen(false)
  }, [location.pathname])

  const containerClassName = useMemo(() => {
    const classes = ['corona', 'corona-container-scroller']
    if (isIconOnly) classes.push('corona-sidebar-icon-only')
    if (isMobileSidebarOpen) classes.push('corona-sidebar-open')
    return classes.join(' ')
  }, [isIconOnly, isMobileSidebarOpen])

  return (
    <div className={containerClassName}>
      <CoronaSidebar
        title={sidebarTitle}
        subtitle={sidebarSubtitle}
        onCloseMobile={() => setIsMobileSidebarOpen(false)}
        footer={sidebarFooter}
      >
        {sidebarContent}
      </CoronaSidebar>

      <div className="corona-page-body-wrapper">
        <CoronaNavbar
          title={navbarTitle}
          onToggleIconOnly={() => setIsIconOnly((v) => !v)}
          onToggleMobileSidebar={() => setIsMobileSidebarOpen((v) => !v)}
        />

        <main className="corona-main-panel">
          <div className="corona-content-wrapper">{children}</div>
          <CoronaFooter />
        </main>
      </div>
    </div>
  )
}

