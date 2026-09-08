import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const links = [
  { to: '/', label: 'Dashboard', icon: '◧' },
  { to: '/transactions', label: 'Transactions', icon: '☰' },
  { to: '/upload', label: 'Upload', icon: '⇧' },
]

export function Layout() {
  const { user, logout } = useAuth()

  return (
    <div className="flex min-h-screen bg-surface-2">
      <aside className="flex w-56 shrink-0 flex-col border-r border-border bg-surface-1 px-3 py-5">
        <div className="mb-6 flex items-center gap-2 px-2">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-series-1 text-sm font-bold text-white">
            $
          </span>
          <span className="text-sm font-semibold text-text-primary">Expense Tracker</span>
        </div>

        <nav className="flex flex-1 flex-col gap-1">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-series-1/10 text-series-1'
                    : 'text-text-secondary hover:bg-surface-3 hover:text-text-primary'
                }`
              }
            >
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

      <main className="min-w-0 flex-1 px-8 py-6">
        <Outlet />
      </main>
    </div>
  )
}
