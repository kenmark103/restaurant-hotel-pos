import type { StaffRead } from '@/features/staff/types'
import { StaffRow } from './StaffRow'

interface StaffGroupProps {
  title: string
  members: StaffRead[]
  tone: 'success' | 'warning' | 'neutral'
  onDisable: (id: number) => void
  isWorking: boolean
}

export function StaffGroup({ title, members, tone, onDisable, isWorking }: StaffGroupProps) {
  if (!members.length) {
    return null
  }

  return (
    <div className="app-panel p-4">
      <p className="section-title mb-3">
        {title} — {members.length}
      </p>
      <div className="space-y-2">
        {members.map((member) => (
          <StaffRow key={member.id} member={member} tone={tone} onDisable={onDisable} isWorking={isWorking} />
        ))}
      </div>
    </div>
  )
}
