import type { PosOrder } from '@/features/orders/types'
import { StatusBadge } from '@/shared/ui/StatusBadge'

interface OrderCardProps {
  order: PosOrder
  isSelected: boolean
  formatPrice: (v: number | string) => string
  onClick: () => void
}

export function OrderCard({ order, isSelected, formatPrice, onClick }: OrderCardProps) {
  const activeItems = order.items.filter((i) => !i.is_voided)
  const elapsed = formatElapsed(order.created_at)

  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full rounded-xl border p-3 text-left transition ${
        isSelected ? 'border-accent bg-accent/10' : 'border-line bg-white hover:border-accent/40'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm font-bold text-ink">#{order.id}</span>
          {order.table_id != null && (
            <span className="rounded-lg bg-appbg px-2 py-0.5 text-xs font-semibold text-muted">Table {order.table_id}</span>
          )}
        </div>
        <StatusBadge label={order.status} tone={orderTone(order.status)} />
      </div>

      <div className="mt-2 flex items-center justify-between gap-2">
        <p className="text-xs text-muted">
          {activeItems.length} item{activeItems.length !== 1 ? 's' : ''}
          {activeItems.length > 0 &&
            ` · ${activeItems
              .slice(0, 2)
              .map((i) => i.menu_item_name)
              .join(', ')}${activeItems.length > 2 ? '…' : ''}`}
        </p>
        <p className="font-mono text-sm font-bold text-ink">{formatPrice(order.total_amount)}</p>
      </div>

      <div className="mt-1.5 flex items-center justify-between gap-2">
        <span className="text-[11px] text-faint">{elapsed} ago</span>
        {order.note && <span className="truncate text-[11px] text-info-text">Note: {order.note}</span>}
      </div>
    </button>
  )
}

function orderTone(status: PosOrder['status']): 'neutral' | 'info' | 'success' | 'warning' | 'danger' {
  if (status === 'open') {
    return 'warning'
  }
  if (status === 'sent') {
    return 'info'
  }
  if (status === 'closed') {
    return 'success'
  }
  if (status === 'voided') {
    return 'danger'
  }
  return 'neutral'
}

function elapsedMinutes(timestamp: string): number {
  return Math.floor((Date.now() - new Date(timestamp).getTime()) / 60000)
}

function formatElapsed(timestamp: string): string {
  const mins = elapsedMinutes(timestamp)
  if (mins < 60) {
    return `${mins}m`
  }
  return `${Math.floor(mins / 60)}h ${mins % 60}m`
}
