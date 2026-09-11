import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const links = [
  { to: '/', label: 'Dashboard', icon: '◧' },
  { to: '/transactions', label: 'Transactions', icon: '☰' },
  { to: '/upload', label: 'Upload', icon: '⇧' },
]

function navClass({ isActive }: { isActive: boolean }) {
  return `flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
    isActive
      ? 'bg-series-1/10 text-series-1'
      : 'text-text-secondary hover:bg-surface-3 hover:text-text-primary'
  }`
}

/**
 * App shell: a sidebar on desktop, a top bar with a horizontal nav row on
 * narrow screens. There's no drawer or hamburger because there are only
 * three destinations — they fit on one row, and a row nobody has to open
 * beats a menu they do.
 */
export function Layout() {
  const { user, logout } = useAuth()

  const brand = (
    <div className="flex items-center gap-2">
      <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-series-1 text-sm font-bold text-white">
        $
      </span>
      <span className="text-sm font-semibold text-text-primary">Expense Tracker</span>
    </div>
  )

  return (
    <div className="flex min-h-screen flex-col bg-surface-2 md:flex-row">
      {/* Mobile / tablet header */}
      <header className="border-b border-border bg-surface-1 px-4 py-3 md:hidden">
        <div className="flex items-center justify-between gap-3">
          {brand}
          <button
            onClick={logout}
            className="rounded-lg px-2 py-1.5 text-sm text-text-secondary hover:bg-surface-3"
          >
            Sign out
          </button>
        </div>
        <nav className="mt-3 flex gap-1 overflow-x-auto">
          {links.map((link) => (
            <NavLink key={link.to} to={link.to} end={link.to === '/'} className={navClass}>
              <span aria-hidden className="text-base">
                {link.icon}
              </span>
              {link.label}
            </NavLink>
          ))}
        </nav>
      </header>

      {/* Desktop sidebar */}
      <aside className="hidden w-56 shrink-0 flex-col border-r border-border bg-surface-1 px-3 py-5 md:flex">
        <div className="mb-6 px-2">{brand}</div>

        <nav className="flex flex-1 flex-col gap-1">
          {links.map((link) => (
            <NavLink key={link.to} to={link.to} end={link.to === '/'} className={navClass}>
              <span aria-hidden className="text-base">
                {link.icon}
              </span>
              {link.label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-border pt-3">
          <p className="truncate px-2 text-xs text-text-muted">{user?.email}</p>
          <button
            onClick={logout}
            className="mt-1 w-full rounded-lg px-2 py-1.5 text-left text-sm text-text-secondary hover:bg-surface-3"
          >
            Sign out
          </button>
        </div>
      </aside>

      <main className="min-w-0 flex-1 px-4 py-5 md:px-8 md:py-6">
        <Outlet />
      </main>
    </div>
  )
}
