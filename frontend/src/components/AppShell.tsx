import { NavLink, Outlet } from 'react-router-dom'

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-full px-4 py-2 text-sm font-semibold transition ${
    isActive ? 'bg-ember text-white' : 'bg-white/70 text-ink hover:bg-white'
  }`

export function AppShell() {
  return (
    <div className="min-h-screen">
      <header className="border-b border-black/5 bg-white/60 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div>
            <p className="font-display text-2xl text-ink">Restaurant Hotel POS</p>
            <p className="text-sm text-ink/70">Restaurant-first operations with customer loyalty and future hotel expansion.</p>
          </div>
          <nav className="flex gap-2">
            <NavLink to="/" className={linkClass}>
              Home
            </NavLink>
            <NavLink to="/staff/login" className={linkClass}>
              Staff
            </NavLink>
            <NavLink to="/account/login" className={linkClass}>
              Customer
            </NavLink>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-10">
        <Outlet />
      </main>
    </div>
  )
}
