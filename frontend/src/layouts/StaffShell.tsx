import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'

import { useLogout } from '@/features/auth/hooks/useAuth'
import { useAuthStore } from '@/store/authStore'
import { useSettings } from '@/contexts/SettingsContext'
import { useWsConnection } from '@/shared/hooks/useWsConnection'

// ─── Nav config ──────────────────────────────────────────────────────────────

interface NavEntry {
  to: string
  label: string
  icon: (active: boolean) => JSX.Element
  roles?: string[]
  section: 'ops' | 'mgmt'
}

const Ico = ({ path, active }: { path: string; active: boolean }) => (
  <svg
    className={`h-[15px] w-[15px] shrink-0 transition-colors ${active ? 'text-accent' : 'text-sidebar-text group-hover:text-slate-300'}`}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={1.8}
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d={path} />
  </svg>
)

const NAV: NavEntry[] = [
  {
    to: '/staff/pos',
    label: 'POS Terminal',
    section: 'ops',
    icon: (a) => <Ico active={a} path="M3 5a2 2 0 012-2h14a2 2 0 012 2v2H3V5zM3 9h18v10a2 2 0 01-2 2H5a2 2 0 01-2-2V9zM9 13h6" />,
  },
  {
    to: '/staff/orders',
    label: 'Orders',
    section: 'ops',
    icon: (a) => <Ico active={a} path="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2M12 12v4M10 14h4" />,
  },
  {
    to: '/staff/tables',
    label: 'Floor Plan',
    section: 'ops',
    icon: (a) => <Ico active={a} path="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />,
  },
  {
    to: '/staff/dashboard',
    label: 'Dashboard',
    section: 'mgmt',
    roles: ['admin', 'manager'],
    icon: (a) => <Ico active={a} path="M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z" />,
  },
  {
    to: '/staff/menu',
    label: 'Menu & Products',
    section: 'mgmt',
    roles: ['admin', 'manager'],
    icon: (a) => <Ico active={a} path="M12 3l1.5 3H18l-3.5 2.5 1.5 4L12 10.5 8 12.5l1.5-4L6 6h4.5L12 3zM5 18h14M5 21h14" />,
  },
  {
    to: '/staff/team',
    label: 'Team',
    section: 'mgmt',
    roles: ['admin', 'manager'],
    icon: (a) => <Ico active={a} path="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2M9 7a4 4 0 100 8 4 4 0 000-8zM23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75" />,
  },
  {
    to: '/staff/branches',
    label: 'Branches',
    section: 'mgmt',
    roles: ['admin'],
    icon: (a) => <Ico active={a} path="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2zM9 22V12h6v10" />,
  },
]

// Page titles for topbar
const PAGE_TITLES: Record<string, { title: string; description: string }> = {
  '/staff/pos':       { title: 'POS Terminal',      description: 'Open a table to start taking orders' },
  '/staff/orders':    { title: 'Orders',             description: 'Live order queue and status flow' },
  '/staff/tables':    { title: 'Floor Plan',         description: 'Table status and occupancy' },
  '/staff/dashboard': { title: 'Dashboard',          description: 'Operations overview' },
  '/staff/menu':      { title: 'Menu & Products',    description: 'Categories, items, and pricing' },
  '/staff/team':      { title: 'Team',               description: 'Staff accounts and branch assignments' },
  '/staff/branches':  { title: 'Branches',           description: 'Operating locations' },
}

// ─── Shell ───────────────────────────────────────────────────────────────────

export function StaffShell() {
  const user = useAuthStore((s) => s.user)
  const logoutMutation = useLogout()
  const navigate = useNavigate()
  const location = useLocation()
  const { settings } = useSettings()

  useWsConnection()

  const role = user?.role ?? ''
  const isAdmin = role === 'admin'
  const isManager = role === 'admin' || role === 'manager'

  const visibleNav = NAV.filter((n) => !n.roles || n.roles.includes(role))
  const opsNav  = visibleNav.filter((n) => n.section === 'ops')
  const mgmtNav = visibleNav.filter((n) => n.section === 'mgmt')
  const isPosRoute = location.pathname.startsWith('/staff/pos')

  const pageMeta = PAGE_TITLES[location.pathname] ?? { title: 'Staff', description: '' }

  const initials = (user?.full_name ?? 'SA')
    .split(' ')
    .map((w) => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()

  const handleLogout = async () => {
    await logoutMutation.mutateAsync()
    navigate('/staff/login', { replace: true })
  }

  return (
    // Lock to viewport height — this is the critical rule for POS chrome
    <div className="flex h-screen overflow-hidden bg-sidebar-bg">

      {/* ── SIDEBAR ──────────────────────────────────────────────────── */}
      <aside
        className="flex h-full w-[220px] shrink-0 flex-col"
        style={{ borderRight: '1px solid #1A2A3A' }}
      >
        {/* Brand */}
        <div className="px-4 pb-4 pt-5" style={{ borderBottom: '1px solid #1A2A3A' }}>
          <p className="font-mono text-[9px] font-medium uppercase tracking-[0.2em] text-sidebar-text">
            POS Platform
          </p>
          <p className="mt-1 text-[15px] font-bold tracking-tight text-slate-100">
            {settings.restaurantName}
          </p>
          <div className="mt-2.5 inline-flex items-center gap-1.5 rounded-md border border-sidebar-border bg-sidebar-hover px-2 py-1 font-mono text-[10px] text-sidebar-text">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-success" />
            {user?.branch_id ? `Branch #${user.branch_id}` : 'HQ'} · Live
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto overflow-x-hidden px-2 py-3 space-y-0.5">
          <p className="mb-1 px-2.5 pt-1 font-mono text-[9px] font-medium uppercase tracking-[0.2em]" style={{ color: '#1E3A52' }}>
            Operations
          </p>
          {opsNav.map((item) => (
            <SideNavLink key={item.to} item={item} />
          ))}

          {mgmtNav.length > 0 && (
            <>
              <div className="my-2 mx-2.5" style={{ height: 1, background: '#1A2A3A' }} />
              <p className="mb-1 px-2.5 font-mono text-[9px] font-medium uppercase tracking-[0.2em]" style={{ color: '#1E3A52' }}>
                Management
              </p>
              {mgmtNav.map((item) => (
                <SideNavLink key={item.to} item={item} />
              ))}
            </>
          )}
        </nav>

        {/* User */}
        <div className="px-2 pb-3 pt-2" style={{ borderTop: '1px solid #1A2A3A' }}>
          <button
            className="group flex w-full items-center gap-2.5 rounded-btn px-2.5 py-2 text-left transition hover:bg-sidebar-hover disabled:opacity-50"
            onClick={() => void handleLogout()}
            disabled={logoutMutation.isPending}
          >
            <div
              className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-[11px] font-bold text-white"
              style={{ background: 'linear-gradient(135deg,#f97316,#ea580c)' }}
            >
              {initials}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-[12px] font-semibold text-slate-200">
                {user?.full_name ?? 'Staff'}
              </p>
              <p className="font-mono text-[10px] uppercase tracking-wide text-sidebar-text">
                {logoutMutation.isPending ? 'Signing out…' : `${role} · Sign out`}
              </p>
            </div>
          </button>
        </div>
      </aside>

      {/* ── MAIN ─────────────────────────────────────────────────────── */}
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden bg-appbg">

        {/* Topbar */}
        <header className="flex h-14 shrink-0 items-center gap-3 border-b border-line bg-panel px-6">
          <div className="flex-1 min-w-0">
            <h1 className="text-[15px] font-semibold text-ink leading-none">{pageMeta.title}</h1>
            {pageMeta.description && (
              <p className="mt-0.5 text-[12px] text-faint leading-none">{pageMeta.description}</p>
            )}
          </div>

          <div className="flex items-center gap-2">
            {/* Quick shortcut to POS */}
            {location.pathname !== '/staff/pos' && (
              <button
                className="btn-primary text-[12px] py-1.5 px-3"
                onClick={() => navigate('/staff/pos')}
              >
                <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                  <path d="M12 5v14M5 12h14" strokeLinecap="round" />
                </svg>
                New Order
              </button>
            )}
          </div>
        </header>

        {/* Scrollable content */}
        <main className={isPosRoute ? 'flex-1 overflow-hidden p-4 md:p-6' : 'flex-1 overflow-y-auto p-6'}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}

function SideNavLink({ item }: { item: NavEntry }) {
  return (
    <NavLink
      to={item.to}
      className={({ isActive }) =>
        `group mb-0.5 flex items-center gap-2.5 rounded-btn px-2.5 py-[7px] text-[13px] font-medium transition-all
        ${isActive
          ? 'border border-accent/20 bg-accent/10 text-accent'
          : 'border border-transparent text-sidebar-text hover:bg-sidebar-hover hover:text-slate-200'
        }`
      }
    >
      {({ isActive }) => (
        <>
          {item.icon(isActive)}
          {item.label}
        </>
      )}
    </NavLink>
  )
}

