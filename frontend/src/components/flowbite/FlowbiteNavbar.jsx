import { useState, useMemo } from 'react'
import { Menu, Bell, Sun, Moon, LogOut, ChevronDown, Flame } from 'lucide-react'

export default function FlowbiteNavbar({
  appName = 'GasMaster',
  pageTitle = '',
  userEmail = '',
  onLogout,
  onToggleSidebar,
  isDark = false,
  onToggleDark,
  rightSlot = null,
}) {
  const [menuOpen, setMenuOpen] = useState(false)

  const initials = useMemo(() => {
    if (!userEmail) return 'U'
    return (userEmail.split('@')[0] || 'U').slice(0, 2).toUpperCase()
  }, [userEmail])

  return (
    <header className="fixed top-0 inset-x-0 z-30 flex items-center h-12 bg-white border-b border-gray-200 px-4 dark:bg-gray-900 dark:border-gray-800">

      {/* Left side */}
      <div className="flex items-center gap-2 min-w-0">
        {/* Hamburger – mobile only */}
        <button
          type="button"
          onClick={onToggleSidebar}
          className="lg:hidden p-1.5 rounded-md text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
          aria-label="Abrir menu"
        >
          <Menu className="w-4 h-4" />
        </button>

        {/* Logo mark — visible only on mobile (desktop: sidebar owns the brand) */}
        <div className="flex items-center gap-2 shrink-0 lg:hidden">
          <span className="inline-flex items-center justify-center w-7 h-7 rounded-lg bg-primary-500">
            <Flame className="w-4 h-4 text-white" />
          </span>
          <span className="font-semibold text-sm text-gray-900 dark:text-white">
            {appName}
          </span>
        </div>

        {/* Page breadcrumb divider – desktop */}
        {pageTitle && (
          <>
            <span className="hidden lg:block h-4 w-px bg-gray-200 dark:bg-gray-700 mx-1" />
            <span className="hidden lg:block text-sm text-gray-500 dark:text-gray-400 truncate max-w-[200px]">
              {pageTitle}
            </span>
          </>
        )}
      </div>

      {/* Right side */}
      <div className="flex items-center gap-1.5 ml-auto">
        {rightSlot}

        {/* Dark mode toggle */}
        <button
          type="button"
          onClick={onToggleDark}
          className="p-1.5 rounded-md text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
          aria-label="Alternar tema"
        >
          {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>

        {/* Vertical divider */}
        <span className="h-5 w-px bg-gray-200 dark:bg-gray-700 mx-1" />

        {/* User menu */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setMenuOpen(v => !v)}
            className="flex items-center gap-2 py-1 px-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 focus:outline-none"
          >
            <span className="w-7 h-7 rounded-full bg-gray-900 dark:bg-gray-700 text-white text-xs font-semibold grid place-items-center shrink-0">
              {initials}
            </span>
            <span className="hidden sm:flex items-center gap-1 text-sm text-gray-700 dark:text-gray-300 max-w-[140px]">
              <span className="truncate">{userEmail || '—'}</span>
              <ChevronDown className="w-3 h-3 shrink-0 text-gray-400" />
            </span>
          </button>

          {menuOpen && (
            <>
              <div
                className="fixed inset-0 z-40"
                onClick={() => setMenuOpen(false)}
                aria-hidden="true"
              />
              <div className="absolute right-0 z-50 mt-1.5 w-56 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-lg overflow-hidden">
                <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700">
                  <p className="text-xs text-gray-400 dark:text-gray-500">Logado como</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{userEmail || '—'}</p>
                </div>
                <div className="p-1">
                  <button
                    type="button"
                    onClick={() => { setMenuOpen(false); onLogout?.() }}
                    className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
                  >
                    <LogOut className="w-4 h-4 text-gray-400" />
                    Sair
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
