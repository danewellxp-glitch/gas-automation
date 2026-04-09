import { useEffect, useMemo, useState } from 'react'
import FlowbiteNavbar from './FlowbiteNavbar'
import FlowbiteSidebar from './FlowbiteSidebar'

/**
 * Layout principal — design Preline-inspired.
 * Navbar fixa no topo (h-12), sidebar fixa na esquerda (w-56).
 * Suporte a dark mode, mobile drawer, e grupos de nav com seção.
 */
export default function FlowbiteLayout({
  appName = 'GasMaster',
  logo = null,
  pageTitle = '',
  navItems = [],
  sidebarFooter = null,
  rightSlot = null,
  userEmail = '',
  onLogout,
  children,
  activeNavKey = null,
  sidebarUserInfo = null, // { name, role, onLogout } — enables dark premium sidebar
}) {
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)
  const [isDark, setIsDark] = useState(
    () => document.documentElement.classList.contains('dark')
  )

  // Sync dark mode class + localStorage
  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark')
      localStorage.setItem('hs_theme', 'dark')
    } else {
      document.documentElement.classList.remove('dark')
      localStorage.setItem('hs_theme', 'light')
    }
  }, [isDark])

  // Lock body scroll when mobile sidebar is open
  useEffect(() => {
    if (mobileSidebarOpen) {
      document.body.style.overflow = 'hidden'
      return () => { document.body.style.overflow = '' }
    }
    document.body.style.overflow = ''
  }, [mobileSidebarOpen])

  const backdrop = useMemo(() => {
    if (!mobileSidebarOpen) return null
    return (
      <div
        className="fixed inset-0 z-10 bg-gray-900/40 backdrop-blur-sm lg:hidden"
        onClick={() => setMobileSidebarOpen(false)}
        aria-hidden="true"
      />
    )
  }, [mobileSidebarOpen])

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <FlowbiteNavbar
        appName={appName}
        pageTitle={pageTitle}
        userEmail={userEmail}
        onLogout={onLogout}
        onToggleSidebar={() => setMobileSidebarOpen(v => !v)}
        isDark={isDark}
        onToggleDark={() => setIsDark(v => !v)}
        rightSlot={rightSlot}
      />

      {backdrop}

      <FlowbiteSidebar
        navItems={navItems}
        footer={sidebarFooter}
        isMobileOpen={mobileSidebarOpen}
        onCloseMobile={() => setMobileSidebarOpen(false)}
        activeKey={activeNavKey}
        logo={logo}
        appName={appName}
        userInfo={sidebarUserInfo}
      />

      {/* Main content — offset for sidebar (desktop) and navbar */}
      <main className="lg:pl-56 pt-12 min-h-screen">
        <div className="p-5 sm:p-6">
          {children}
        </div>
      </main>
    </div>
  )
}
