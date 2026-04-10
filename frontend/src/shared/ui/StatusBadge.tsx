type BadgeTone = 'neutral' | 'info' | 'success' | 'warning' | 'danger'

interface StatusBadgeProps {
  label: string
  tone?: BadgeTone
  uppercase?: boolean
}

const toneClassMap: Record<BadgeTone, string> = {
  neutral: 'bg-gray-100 text-gray-700',
  info: 'bg-accent/10 text-accent',
  success: 'bg-success/10 text-success',
  warning: 'bg-warning/10 text-warning',
  danger: 'bg-danger/10 text-danger',
}

export function StatusBadge({ label, tone = 'neutral', uppercase = true }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-3 py-1 text-[11px] font-semibold ${uppercase ? 'uppercase tracking-[0.16em]' : ''} ${toneClassMap[tone]}`}
    >
      {label}
    </span>
  )
}
