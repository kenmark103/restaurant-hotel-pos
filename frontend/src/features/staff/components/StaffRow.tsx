import type { StaffRead } from '@/features/staff/types'
import { StatusBadge } from '@/shared/ui/StatusBadge'

interface StaffRowProps {
  member: StaffRead
  tone: 'success' | 'warning' | 'neutral'
  onDisable: (id: number) => void
  isWorking: boolean
}

export function StaffRow({ member, tone, onDisable, isWorking }: StaffRowProps) {
  const initials = member.full_name
    .split(' ')
    .map((w: string) => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()

  return (
    <div className="flex items-center gap-3 rounded-xl border border-line bg-white p-3">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-appbg text-xs font-bold text-muted">
        {initials}
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-semibold text-ink">{member.full_name}</p>
          <StatusBadge label={member.role} tone={tone} />
        </div>
        <p className="truncate text-xs text-muted">{member.email}</p>
      </div>

      {member.branch_id && (
        <span className="hidden shrink-0 rounded-lg bg-appbg px-2 py-1 text-xs font-semibold text-muted sm:block">
          Branch #{member.branch_id}
        </span>
      )}

      {member.status !== 'disabled' && (
        <button
          type="button"
          disabled={isWorking}
          onClick={() => onDisable(member.id)}
          className="shrink-0 rounded-lg border border-danger/20 px-2 py-1.5 text-xs font-semibold text-danger hover:bg-danger/5 disabled:opacity-50"
        >
          Disable
        </button>
      )}
    </div>
  )
}
