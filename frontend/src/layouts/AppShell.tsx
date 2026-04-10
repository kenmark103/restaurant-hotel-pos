import { Link, Outlet } from 'react-router-dom'

export function AppShell() {
  return (
    <div className="min-h-screen bg-appbg">
      <header className="border-b border-line bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-muted">Guest Services</p>
            <p className="mt-1 font-display text-2xl font-semibold text-ink">Restaurant Hotel POS</p>
          </div>
          <Link className="rounded-xl border border-line px-3 py-2 text-sm font-medium text-muted transition hover:border-ink hover:text-ink" to="/staff/login">
            Staff portal
          </Link>
        </div>
      </header>
      <main className="mx-auto flex min-h-[calc(100vh-73px)] max-w-7xl items-center px-6 py-8">
        <Outlet />
      </main>
    </div>
  )
}
