import { useMemo, useState } from 'react'
import { Menu, X, LogOut } from 'lucide-react'

export default function FlowbiteNavbar({
  appName,
  pageTitle,
  userEmail,
  onLogout,
  onToggleSidebar,
  rightSlot = null,
}) {
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false)

  const initials = useMemo(() => {
    if (!userEmail) return 'U'
    const part = userEmail.split('@')[0] || 'U'
    return part.slice(0, 2).toUpperCase()
  }, [userEmail])

  return (
    <nav className="fixed top-0 z-30 w-full border-b border-gray-200 bg-white">
      <div className="px-4 py-3 lg:px-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onToggleSidebar}
              className="inline-flex items-center rounded-lg p-2 text-gray-600 hover:bg-gray-100 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-gray-200 lg:hidden"
              aria-label="Abrir menu"
            >
              <Menu className="h-6 w-6" />
            </button>

            <div className="flex items-center gap-3">
              <div className="h-9 w-9 rounded-lg bg-primary-600 text-white grid place-items-center font-semibold">
                GA
              </div>
              <div className="min-w-0">
                <div className="text-sm font-semibold text-gray-900 leading-4">{appName}</div>
                {pageTitle ? (
                  <div className="text-xs text-gray-500 truncate">{pageTitle}</div>
                ) : null}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {rightSlot}

            {/* User */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setIsUserMenuOpen((v) => !v)}
                className="flex items-center gap-3 rounded-lg p-2 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-gray-200"
                aria-label="Menu do usuário"
              >
                <div className="hidden text-right sm:block">
                  <div className="text-sm font-medium text-gray-900">Conta</div>
                  <div className="text-xs text-gray-500">{userEmail || '—'}</div>
                </div>
                <div className="h-9 w-9 rounded-full bg-gray-900 text-white grid place-items-center text-sm font-semibold">
                  {initials}
                </div>
              </button>

              {isUserMenuOpen ? (
                <>
                  <div
                    className="fixed inset-0 z-40"
                    onClick={() => setIsUserMenuOpen(false)}
                    aria-hidden="true"
                  />
                  <div className="absolute right-0 z-50 mt-2 w-56 overflow-hidden rounded-lg border border-gray-200 bg-white shadow-lg">
                    <div className="px-4 py-3">
                      <div className="text-xs text-gray-500">Logado como</div>
                      <div className="text-sm font-medium text-gray-900 truncate">{userEmail || '—'}</div>
                    </div>
                    <div className="border-t border-gray-100" />
                    <button
                      type="button"
                      onClick={() => {
                        setIsUserMenuOpen(false)
                        onLogout?.()
                      }}
                      className="flex w-full items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                    >
                      <LogOut className="h-4 w-4" />
                      Sair
                    </button>
                  </div>
                </>
              ) : null}
            </div>
          </div>
        </div>
      </div>
    </nav>
  )
}

