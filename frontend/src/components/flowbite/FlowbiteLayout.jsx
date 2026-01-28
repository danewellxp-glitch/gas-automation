import { useEffect, useMemo, useState } from 'react'
import FlowbiteNavbar from './FlowbiteNavbar'
import FlowbiteSidebar from './FlowbiteSidebar'

/**
 * Layout baseado no Flowbite Admin Dashboard (Tailwind).
 * - Tema claro por padrão (sem dark mode)
 * - Sidebar fixa no desktop, drawer no mobile
 * - Conteúdo do menu vem via `navItems`
 */
export default function FlowbiteLayout({
  appName = 'Gas Automation',
  pageTitle = '',
  navItems = [],
  sidebarFooter = null,
  rightSlot = null,
  userEmail = '',
  onLogout,
  children,
}) {
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false)

  useEffect(() => {
    // trava scroll quando sidebar mobile aberta
    if (isMobileSidebarOpen) {
      document.body.style.overflow = 'hidden'
      return () => {
        document.body.style.overflow = ''
      }
    }
    document.body.style.overflow = ''
  }, [isMobileSidebarOpen])

  const backdrop = useMemo(() => {
    if (!isMobileSidebarOpen) return null
    return (
      <div
        className="fixed inset-0 z-10 bg-gray-900/50 lg:hidden"
        onClick={() => setIsMobileSidebarOpen(false)}
        aria-hidden="true"
      />
    )
  }, [isMobileSidebarOpen])

  return (
    <div className="min-h-screen bg-gray-50">
      <FlowbiteNavbar
        appName={appName}
        pageTitle={pageTitle}
        userEmail={userEmail}
        onLogout={onLogout}
        onToggleSidebar={() => setIsMobileSidebarOpen((v) => !v)}
        rightSlot={rightSlot}
      />

      {backdrop}

      <FlowbiteSidebar
        navItems={navItems}
        footer={sidebarFooter}
        isMobileOpen={isMobileSidebarOpen}
        onCloseMobile={() => setIsMobileSidebarOpen(false)}
      />

      {/* Content */}
      <main className="pt-16 lg:ml-64">
        <div className="p-4 sm:p-6">{children}</div>
      </main>
    </div>
  )
}

