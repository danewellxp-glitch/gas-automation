import { NavLink } from 'react-router-dom'

function SidebarItem({ item, onClick }) {
  const Icon = item.icon
  const isButton = item.type === 'button'

  const base =
    'flex items-center rounded-lg p-2 text-base font-normal text-gray-900 hover:bg-gray-100'
  const active = 'bg-gray-100'

  if (isButton) {
    return (
      <button type="button" onClick={onClick} className={base}>
        {Icon ? <Icon className="h-5 w-5 text-gray-500" /> : null}
        <span className="ml-3">{item.label}</span>
      </button>
    )
  }

  return (
    <NavLink
      to={item.to}
      onClick={onClick}
      className={({ isActive }) => `${base} ${isActive ? active : ''}`}
      end={item.end ?? false}
    >
      {Icon ? <Icon className="h-5 w-5 text-gray-500" /> : null}
      <span className="ml-3">{item.label}</span>
    </NavLink>
  )
}

export default function FlowbiteSidebar({
  navItems = [],
  footer = null,
  isMobileOpen = false,
  onCloseMobile,
}) {
  return (
    <aside
      className={[
        'fixed top-0 left-0 z-20 h-screen w-64 border-r border-gray-200 bg-white pt-16',
        'transition-transform duration-150',
        isMobileOpen ? 'translate-x-0' : '-translate-x-full',
        'lg:translate-x-0',
      ].join(' ')}
      aria-label="Sidebar"
    >
      <div className="flex h-full flex-col overflow-y-auto px-3 pb-4 pt-4">
        <div className="flex-1">
          <ul className="space-y-1">
            {navItems.map((item) => (
              <li key={item.key}>
                <SidebarItem
                  item={item}
                  onClick={() => {
                    onCloseMobile?.()
                    item.onClick?.()
                  }}
                />
              </li>
            ))}
          </ul>
        </div>

        {footer ? (
          <div className="mt-4 border-t border-gray-100 pt-4">{footer}</div>
        ) : null}
      </div>
    </aside>
  )
}

