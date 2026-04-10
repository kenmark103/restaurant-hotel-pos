import { Link } from 'react-router-dom'

import { useCurrentUser } from '@/shared/hooks/useCurrentUser'
import { useBranches } from '@/features/staff/hooks/useBranches'
import { useTables } from '@/features/tables/hooks/useTables'
import { useSettings } from '@/contexts/SettingsContext'
import { Spinner } from '@/shared/ui/Spinner'

export function DashboardPage() {
  const { data: user, isLoading } = useCurrentUser()
  const { settings, formatPrice } = useSettings()
  const { data: branches } = useBranches()
  const branchId = user?.branch_id ?? null
  const { data: tables } = useTables(branchId)

  if (isLoading) return <Spinner />

  const tableStats = {
    available: tables?.filter((t) => t.status === 'available').length ?? 0,
    occupied:  tables?.filter((t) => t.status === 'occupied').length ?? 0,
    reserved:  tables?.filter((t) => t.status === 'reserved').length ?? 0,
    cleaning:  tables?.filter((t) => t.status === 'cleaning').length ?? 0,
    total:     tables?.length ?? 0,
  }

  return (
    <div className="space-y-5">

      {/* Welcome row */}
      <div className="flex items-center justify-between">
        <div>
          <p className="label">Operations</p>
          <h2 className="mt-1 text-[22px] font-bold tracking-tight text-ink">
            Good {getGreeting()}, {firstName(user?.full_name)}
          </h2>
        </div>
        <Link to="/staff/pos" className="btn-primary">
          <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round"><path d="M12 5v14M5 12h14" /></svg>
          New order
        </Link>
      </div>

      {/* KPI row — placeholders until orders are live */}
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <KpiCard label="Today's Revenue" value={formatPrice(0)} delta="" note="Orders not live yet" />
        <KpiCard label="Covers Today" value="—" delta="" note="Orders not live yet" />
        <KpiCard label="Avg Ticket" value="—" delta="" note="Orders not live yet" />
        <KpiCard label="Open Orders" value="0" delta="" note="Orders not live yet" />
      </div>

      {/* Floor + context row */}
      <div className="grid gap-4 xl:grid-cols-[1fr_320px]">

        {/* Floor snapshot */}
        <div className="card p-5">
          <div className="mb-4 flex items-center justify-between">
            <p className="section-title">Floor snapshot</p>
            <Link to="/staff/tables" className="btn-ghost text-[12px]">
              Manage floor →
            </Link>
          </div>
          {!tables?.length ? (
            <p className="body-sm">No tables set up for this branch yet.</p>
          ) : (
            <>
              {/* Status summary pills */}
              <div className="mb-4 flex flex-wrap gap-2">
                <StatusPill label="Available" count={tableStats.available} tone="success" />
                <StatusPill label="Occupied"  count={tableStats.occupied}  tone="danger" />
                <StatusPill label="Reserved"  count={tableStats.reserved}  tone="warning" />
                <StatusPill label="Cleaning"  count={tableStats.cleaning}  tone="info" />
              </div>

              {/* Table grid */}
              <div className="grid grid-cols-4 gap-2 sm:grid-cols-6 lg:grid-cols-8">
                {tables?.map((table) => (
                  <div
                    key={table.id}
                    title={`${table.table_number} · ${table.capacity} seats · ${table.status}`}
                    className={`flex flex-col items-center justify-center rounded-card border py-3 text-center cursor-pointer transition hover:opacity-80
                      ${table.status === 'available' ? 'border-success/30 bg-success-light'  : ''}
                      ${table.status === 'occupied'  ? 'border-danger/30  bg-danger-light'   : ''}
                      ${table.status === 'reserved'  ? 'border-warning/30 bg-warning-light'  : ''}
                      ${table.status === 'cleaning'  ? 'border-info/30    bg-info-light'     : ''}
                    `}
                  >
                    <span className="font-mono text-[11px] font-bold text-ink">{table.table_number}</span>
                    <span className="mt-0.5 text-[9px] text-muted">{table.capacity}p</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Right column */}
        <div className="space-y-4">
          {/* Session info */}
          <div className="card p-5">
            <p className="section-title mb-3">Session</p>
            <div className="space-y-2">
              <Row label="Signed in as" value={user?.full_name ?? '—'} />
              <Row label="Role"         value={user?.role ?? '—'} />
              <Row label="Branch"       value={user?.branch_id ? `#${user.branch_id}` : 'Unassigned'} />
              <Row label="Currency"     value={`${settings.currency} (${settings.currencySymbol})`} />
              <Row label="Tax"          value={`${settings.taxRate}% · ${settings.taxInclusive ? 'inclusive' : 'exclusive'}`} />
            </div>
          </div>

          {/* Quick links */}
          <div className="card p-5">
            <p className="section-title mb-3">Quick links</p>
            <div className="space-y-1">
              <QuickLink to="/staff/menu"     label="Manage menu & products" />
              <QuickLink to="/staff/tables"   label="Floor plan setup" />
              <QuickLink to="/staff/team"     label="Team management" />
              <QuickLink to="/staff/branches" label="Branch configuration" />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Small helpers ────────────────────────────────────────────────────────────

function getGreeting() {
  const h = new Date().getHours()
  if (h < 12) return 'morning'
  if (h < 18) return 'afternoon'
  return 'evening'
}

function firstName(fullName?: string) {
  return fullName?.split(' ')[0] ?? 'there'
}

function KpiCard({ label, value, delta, note }: { label: string; value: string; delta: string; note?: string }) {
  return (
    <div className="card p-4">
      <p className="label">{label}</p>
      <p className="mt-2 text-2xl font-bold tracking-tight text-ink">{value}</p>
      {note && <p className="mt-1 text-[11px] text-faint">{note}</p>}
    </div>
  )
}

function StatusPill({ label, count, tone }: { label: string; count: number; tone: 'success' | 'danger' | 'warning' | 'info' }) {
  const cls = {
    success: 'bg-success-light text-success-text',
    danger:  'bg-danger-light  text-danger-text',
    warning: 'bg-warning-light text-warning-text',
    info:    'bg-info-light    text-info-text',
  }[tone]
  return (
    <span className={`inline-flex items-center gap-1 rounded-pill px-2.5 py-1 font-mono text-[10px] font-medium ${cls}`}>
      {count} {label}
    </span>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-2 py-1 text-[12px]">
      <span className="text-faint">{label}</span>
      <span className="font-medium text-ink">{value}</span>
    </div>
  )
}

function QuickLink({ to, label }: { to: string; label: string }) {
  return (
    <Link to={to} className="flex items-center justify-between rounded-btn px-2 py-1.5 text-[13px] text-muted transition hover:bg-appbg hover:text-ink">
      {label}
      <svg className="h-3 w-3 text-faint" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}><path d="M9 18l6-6-6-6" /></svg>
    </Link>
  )
}
