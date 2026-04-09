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
  activeNavKey = null,
  variant = 'default', // 'default' ou 'owner'
}) {
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false)
  const [isDark, setIsDark] =      useState(() => localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches))

  // Inicializar Dark Mode
  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark')
      localStorage.theme = 'dark'
    } else {
      document.documentElement.classList.remove('dark')
      localStorage.theme = 'light'
    }
  }, [isDark])

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
    <div className={`min-h-screen relative overflow-hidden transition-colors duration-300 ${variant === 'owner' ? 'bg-slate-50 dark:bg-slate-950' : 'bg-gray-50 dark:bg-gray-900'}`}>
      {/* Premium Background Mesh (Owner only) */}
      {variant === 'owner' && (
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          <div className="absolute -top-[10%] -left-[10%] h-[500px] w-[500px] rounded-full bg-primary-500/10 blur-[100px] animate-pulse" />
          <div className="absolute -bottom-[10%] -right-[10%] h-[600px] w-[600px] rounded-full bg-blue-500/10 blur-[120px]" />
          <div className="absolute top-[30%] left-[20%] h-[300px] w-[300px] rounded-full bg-orange-400/5 blur-[80px]" />
        </div>
      )}

      <FlowbiteNavbar
        appName={appName}
        pageTitle={pageTitle}
        userEmail={userEmail}
        onLogout={onLogout}
        onToggleSidebar={() => setIsMobileSidebarOpen((v) => !v)}
        isDark={isDark}
        onToggleDark={() =>         setIsDark(v => !v)}
        rightSlot={rightSlot}
      />

      {backdrop}

      <FlowbiteSidebar
        navItems={navItems}
        footer={sidebarFooter}
        isMobileOpen={isMobileSidebarOpen}
        onCloseMobile={() => setIsMobileSidebarOpen(false)}
        activeKey={activeNavKey}
        variant={variant}
      />

      {/* Content */}
      <main className="pt-16 lg:ml-64 relative z-10">
        <div className="p-4 sm:p-6">{children}</div>
      </main>
    </div>
  )
}

