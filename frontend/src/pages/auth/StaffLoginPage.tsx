import { useNavigate } from 'react-router-dom'

import { useSettings } from '@/contexts/SettingsContext'
import { StaffLoginForm } from '@/features/auth/components/StaffLoginForm'
import { useStaffLogin } from '@/features/auth/hooks/useAuth'
import { useAuthStore } from '@/store/authStore'

export function StaffLoginPage() {
  const navigate = useNavigate()
  const loginMutation = useStaffLogin()
  const { settings } = useSettings()

  const handleSubmit = async (payload: { email: string; password: string }) => {
    await loginMutation.mutateAsync(payload)
    const user = useAuthStore.getState().user
    const role = user?.role
    if (role === 'admin' || role === 'manager') {
      navigate('/staff/dashboard', { replace: true })
    } else {
      navigate('/staff/pos', { replace: true })
    }
  }

  return (
    <div className="flex h-screen overflow-hidden bg-sidebar-bg">
      <div
        className="hidden lg:flex lg:w-[420px] lg:shrink-0 lg:flex-col lg:justify-between lg:p-10"
        style={{ borderRight: '1px solid #1A2A3A' }}
      >
        <div>
          <p className="font-mono text-[9px] font-medium uppercase tracking-[0.2em] text-sidebar-text">
            POS Platform
          </p>
          <p className="mt-2 text-2xl font-bold tracking-tight text-slate-100">{settings.restaurantName}</p>
        </div>

        <div className="space-y-6">
          <Feature icon="RT" title="Real-time floor" body="Tables, orders, and kitchen updates stay in sync across all terminals." />
          <Feature icon="RBAC" title="Role-based access" body="Servers see the POS. Managers see everything. Credentials never touch localStorage." />
          <Feature icon="BI" title="Operational intelligence" body="Revenue, covers, and ticket averages available from day one." />
        </div>

        <p className="font-mono text-[10px] text-sidebar-text">(c) {new Date().getFullYear()} {settings.restaurantName}</p>
      </div>

      <div className="flex flex-1 items-center justify-center px-6">
        <div className="w-full max-w-sm">
          <div className="mb-8 lg:hidden">
            <p className="font-mono text-[9px] font-medium uppercase tracking-[0.2em] text-sidebar-text">POS Platform</p>
            <p className="mt-1 text-xl font-bold text-slate-100">{settings.restaurantName}</p>
          </div>

          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-sidebar-text">Staff access</p>
          <h1 className="mt-2 text-2xl font-bold tracking-tight text-slate-100">Sign in</h1>
          <p className="mt-1 text-[13px] text-slate-500">Accounts are provisioned internally.</p>

          <div className="mt-8">
            <StaffLoginForm
              dark
              error={loginMutation.isError ? 'Login failed - check your credentials.' : null}
              isLoading={loginMutation.isPending}
              onSubmit={handleSubmit}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

function Feature({ icon, title, body }: { icon: string; title: string; body: string }) {
  return (
    <div className="flex gap-3">
      <span className="mt-0.5 text-[11px] font-mono leading-none text-slate-400">{icon}</span>
      <div>
        <p className="text-[13px] font-semibold text-slate-300">{title}</p>
        <p className="mt-0.5 text-[12px] leading-5 text-slate-500">{body}</p>
      </div>
    </div>
  )
}
