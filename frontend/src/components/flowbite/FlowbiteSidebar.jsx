import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'

// Regular nav item (button or NavLink)
function NavItem({ item, isActive, onClick, darkSidebar = false }) {
  const Icon = item.icon

  const cls = darkSidebar
    ? [
        'w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors',
        isActive
          ? 'bg-white/15 text-white font-medium'
          : 'text-white/60 hover:bg-white/10 hover:text-white',
      ].join(' ')
    : [
        'w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors',
        isActive
          ? 'bg-primary-50 text-primary-600 font-medium dark:bg-primary-950/40 dark:text-primary-400'
          : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-white',
      ].join(' ')

  const iconCls = darkSidebar
    ? `w-4 h-4 shrink-0 ${isActive ? 'text-white' : 'text-white/40'}`
    : `w-4 h-4 shrink-0 ${isActive ? 'text-primary-500' : 'text-gray-400 dark:text-gray-500'}`

  if (item.type === 'button') {
    return (
      <button type="button" onClick={onClick} className={cls}>
        {Icon && <Icon className={iconCls} />}
        <span className="truncate">{item.label}</span>
        {item.badge != null && (
          <span className="ml-auto text-xs font-medium bg-primary-100 text-primary-600 rounded-full px-1.5 py-0.5 dark:bg-primary-950 dark:text-primary-400">
            {item.badge}
          </span>
        )}
      </button>
    )
  }

  return (
    <NavLink
      to={item.to}
      end={item.end ?? false}
      onClick={onClick}
      className={({ isActive: a }) =>
        darkSidebar
          ? [
              'w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors',
              a ? 'bg-white/15 text-white font-medium' : 'text-white/60 hover:bg-white/10 hover:text-white',
            ].join(' ')
          : [
              'w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors',
              a
                ? 'bg-primary-50 text-primary-600 font-medium dark:bg-primary-950/40 dark:text-primary-400'
                : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-white',
            ].join(' ')
      }
    >
      {Icon && <Icon className={darkSidebar ? 'w-4 h-4 shrink-0 text-white/40' : 'w-4 h-4 shrink-0 text-gray-400 dark:text-gray-500'} />}
      <span className="truncate">{item.label}</span>
    </NavLink>
  )
}

// Collapsible group nav item
function GroupNavItem({ item, activeKey, onChildClick, initialOpen, darkSidebar = false }) {
  const [open, setOpen] = useState(initialOpen)
  const hasActiveChild = item.children?.some(c => c.key === activeKey)
  const Icon = item.icon

  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className={darkSidebar
          ? [
              'w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors',
              hasActiveChild ? 'text-white font-medium' : 'text-white/60 hover:bg-white/10 hover:text-white',
            ].join(' ')
          : [
              'w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors',
              hasActiveChild
                ? 'text-primary-600 font-medium dark:text-primary-400'
                : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-white',
            ].join(' ')}
      >
        {Icon && (
          <Icon className={darkSidebar
            ? `w-4 h-4 shrink-0 ${hasActiveChild ? 'text-white' : 'text-white/40'}`
            : `w-4 h-4 shrink-0 ${hasActiveChild ? 'text-primary-500' : 'text-gray-400 dark:text-gray-500'}`}
          />
        )}
        <span className="flex-1 truncate text-left">{item.label}</span>
        <ChevronRight
          className={`w-3.5 h-3.5 transition-transform duration-150 ${open ? 'rotate-90' : ''} ${
            darkSidebar
              ? (hasActiveChild ? 'text-white/60' : 'text-white/20')
              : (hasActiveChild ? 'text-primary-400' : 'text-gray-300 dark:text-gray-600')
          }`}
        />
      </button>

      {open && item.children?.length > 0 && (
        <div className={`ml-3 mt-0.5 pl-3 space-y-0.5 ${darkSidebar ? 'border-l border-white/10' : 'border-l border-gray-200 dark:border-gray-700'}`}>
          {item.children.map(child => (
            <NavItem
              key={child.key}
              item={child}
              isActive={activeKey === child.key}
              onClick={() => onChildClick(child)}
              darkSidebar={darkSidebar}
            />
          ))}
        </div>
      )}
    </div>
  )
}

// Groups nav items by section label
function groupItems(items) {
  const groups = []
  let current = { title: null, items: [] }
  for (const item of items) {
    if (item.section !== undefined && item.section !== current.title) {
      if (current.items.length) groups.push(current)
      current = { title: item.section, items: [] }
    }
    current.items.push(item)
  }
  if (current.items.length) groups.push(current)
  return groups
}

export default function FlowbiteSidebar({
  navItems = [],
  footer = null,
  isMobileOpen = false,
  onCloseMobile,
  activeKey = null,
  logo = null,
  appName = 'GasMaster',
  userInfo = null, // { name, role, onLogout } — enables dark premium header style
}) {
  const groups = groupItems(navItems)
  const isDark = !!userInfo

  return (
    <aside
      className={[
        'fixed top-0 left-0 z-20 h-screen w-56',
        isDark
          ? 'bg-[#14283b] border-r border-[#14283b] text-white'
          : 'bg-white border-r border-gray-200 dark:bg-gray-900 dark:border-gray-800',
        'flex flex-col',
        'transition-transform duration-200',
        isMobileOpen ? 'translate-x-0' : '-translate-x-full',
        'lg:translate-x-0',
      ].join(' ')}
      aria-label="Sidebar"
    >
      {isDark ? (
        /* Premium dark header — logo + user card + logout */
        <div className="flex flex-col items-center pt-14 px-5 pb-5 border-b border-white/10">
          <img
            src={logo}
            alt={appName}
            className="h-[110px] object-contain max-w-full mb-5 brightness-0 invert opacity-90"
          />
          <div className="w-full bg-white/5 rounded-xl border border-white/10 p-3 text-center mb-3">
            <h2 className="text-[9px] font-bold text-white/50 tracking-widest uppercase mb-1">Operador Logado</h2>
            <p className="text-sm font-bold text-white truncate w-full" title={userInfo.name}>
              {userInfo.name}
            </p>
            <span className="mt-1.5 inline-flex items-center rounded-full bg-[#f54e00]/20 px-2.5 py-0.5 text-[10px] font-medium text-[#f54e00] capitalize">
              {userInfo.role || 'Operador'}
            </span>
          </div>
          <button
            onClick={userInfo.onLogout}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-red-500/10 px-3 py-2 text-xs font-semibold text-red-400 hover:bg-red-500/20 hover:text-red-300 transition-colors"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path><polyline points="16 17 21 12 16 7"></polyline><line x1="21" y1="12" x2="9" y2="12"></line></svg>
            Sair do Sistema
          </button>
        </div>
      ) : (
        /* Default light header — brand logo/name aligned with navbar */
        <div className="h-12 shrink-0 flex items-center px-4 border-b border-gray-100 dark:border-gray-800">
          {logo ? (
            <img
              src={logo}
              alt={appName}
              className="h-8 w-auto object-contain"
            />
          ) : (
            <span className="font-semibold text-sm text-gray-900 dark:text-white">{appName}</span>
          )}
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-4">
        {groups.map((group, gi) => (
          <div key={gi}>
            {group.title && (
              <p className={`px-3 mb-1 text-[10px] font-semibold uppercase tracking-widest ${isDark ? 'text-white/30' : 'text-gray-400 dark:text-gray-600'}`}>
                {group.title}
              </p>
            )}
            <ul className="space-y-0.5">
              {group.items.map((item) => (
                <li key={item.key}>
                  {item.type === 'group' ? (
                    <GroupNavItem
                      item={item}
                      activeKey={activeKey}
                      initialOpen={item.children?.some(c => c.key === activeKey)}
                      darkSidebar={isDark}
                      onChildClick={(child) => {
                        onCloseMobile?.()
                        child.onClick?.()
                      }}
                    />
                  ) : (
                    <NavItem
                      item={item}
                      isActive={activeKey === item.key}
                      darkSidebar={isDark}
                      onClick={() => {
                        onCloseMobile?.()
                        item.onClick?.()
                      }}
                    />
                  )}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {footer && (
        <div className="px-3 py-3 border-t border-gray-100 dark:border-gray-800">
          {footer}
        </div>
      )}
    </aside>
  )
}
