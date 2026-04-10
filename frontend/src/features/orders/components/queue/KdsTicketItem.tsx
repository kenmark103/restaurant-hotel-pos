import type { PosOrder, PosOrderItem } from '@/features/orders/types'

interface KdsTicketItemProps {
  order: PosOrder
  item: PosOrderItem
  formatPrice: (v: number | string) => string
}

export function KdsTicketItem({ order, item, formatPrice }: KdsTicketItemProps) {
  const elapsed = formatElapsed(order.created_at)
  const isUrgent = elapsedMinutes(order.created_at) >= 15

  return (
    <div className={`rounded-xl border p-3 ${isUrgent ? 'border-danger/30 bg-danger/5' : 'border-line bg-white'}`}>
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-xs font-bold text-muted">#{order.id}</span>
        {order.table_id != null && <span className="text-xs text-muted">T{order.table_id}</span>}
        <span className={`font-mono text-xs font-semibold ${isUrgent ? 'text-danger' : 'text-faint'}`}>{elapsed}</span>
      </div>

      <p className="mt-1.5 text-sm font-semibold text-ink">
        {item.quantity > 1 && (
          <span className="mr-1.5 rounded bg-accent/10 px-1.5 py-0.5 font-mono text-xs font-bold text-accent">x{item.quantity}</span>
        )}
        {item.menu_item_name}
      </p>

      {item.variant_name ? <p className="mt-1 text-xs text-muted">{item.variant_name}</p> : null}
      <p className="mt-1 text-xs text-muted">{formatPrice(item.line_total)}</p>
      {item.note && <p className="mt-1 text-xs text-info-text">Note: {item.note}</p>}
    </div>
  )
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
