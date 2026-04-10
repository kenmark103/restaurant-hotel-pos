import type { PosOrder, PosOrderItem } from '@/features/orders/types'
import { StatusBadge } from '@/shared/ui/StatusBadge'

interface OrderDetailProps {
  order: PosOrder
  formatPrice: (v: number | string) => string
  isWorking: boolean
  onSend: () => void
  onHold: () => void
  onVoid: () => void
}

export function OrderDetail({ order, formatPrice, isWorking, onSend, onHold, onVoid }: OrderDetailProps) {
  const activeItems = order.items.filter((i) => !i.is_voided)
  const voidedItems = order.items.filter((i) => i.is_voided)

  return (
    <div className="flex h-full flex-col gap-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="app-label">Order #{order.id}</p>
          <div className="mt-1 flex items-center gap-2">
            <StatusBadge label={order.status} tone={orderTone(order.status)} />
            {order.table_id != null && (
              <span className="rounded-lg bg-appbg px-2 py-1 text-xs font-semibold text-muted">Table {order.table_id}</span>
            )}
          </div>
          <p className="mt-1 text-xs text-faint">Opened {formatElapsed(order.created_at)} ago</p>
        </div>
        <p className="font-mono text-lg font-bold text-ink">{formatPrice(order.total_amount)}</p>
      </div>

      <div className="flex-1 space-y-1.5">
        {activeItems.map((item) => (
          <DetailLineItem key={item.id} item={item} formatPrice={formatPrice} voided={false} />
        ))}
        {voidedItems.length > 0 && (
          <>
            <p className="pt-1 text-[11px] font-semibold uppercase tracking-wide text-faint">Voided</p>
            {voidedItems.map((item) => (
              <DetailLineItem key={item.id} item={item} formatPrice={formatPrice} voided />
            ))}
          </>
        )}
      </div>

      <div className="rounded-xl border border-line bg-appbg p-3 space-y-1">
        <TotalRow label="Subtotal" value={formatPrice(order.subtotal)} />
        <TotalRow label="Tax" value={formatPrice(order.tax_amount)} />
        <TotalRow label="Total" value={formatPrice(order.total_amount)} strong />
        {order.payment_method && (
          <TotalRow label="Paid via" value={`${order.payment_method.replace('_', ' ')} - ${formatPrice(order.amount_paid ?? 0)}`} />
        )}
      </div>

      {(order.status === 'open' || order.status === 'sent') && (
        <div className="flex flex-col gap-2">
          {order.status === 'open' && (
            <button
              type="button"
              disabled={isWorking || activeItems.length === 0}
              onClick={onSend}
              className="w-full rounded-xl bg-accent px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
            >
              Send to kitchen
            </button>
          )}
          {order.status === 'sent' && (
            <button
              type="button"
              disabled={isWorking}
              onClick={onHold}
              className="w-full rounded-xl border border-warning/30 bg-warning/10 px-4 py-2.5 text-sm font-semibold text-warning-text disabled:opacity-50"
            >
              Move to hold
            </button>
          )}
          <button
            type="button"
            disabled={isWorking}
            onClick={onVoid}
            className="w-full rounded-xl border border-danger/30 bg-danger/5 px-4 py-2.5 text-sm font-semibold text-danger disabled:opacity-50"
          >
            Void order
          </button>
        </div>
      )}
    </div>
  )
}

function DetailLineItem({
  item,
  formatPrice,
  voided,
}: {
  item: PosOrderItem
  formatPrice: (v: number | string) => string
  voided: boolean
}) {
  return (
    <div className={`flex items-start justify-between gap-2 rounded-lg px-3 py-2 ${voided ? 'opacity-40' : 'bg-appbg'}`}>
      <div>
        <p className={`text-sm font-semibold ${voided ? 'line-through text-muted' : 'text-ink'}`}>{item.menu_item_name}</p>
        {item.variant_name ? <p className="text-xs text-muted">{item.variant_name}</p> : null}
        {item.note && <p className="text-xs text-info-text">Note: {item.note}</p>}
        {voided && item.void_reason && <p className="text-xs text-danger">Void: {item.void_reason}</p>}
      </div>
      <div className="text-right">
        <p className="font-mono text-sm font-bold text-ink">{formatPrice(item.line_total)}</p>
        <p className="text-xs text-muted">x{item.quantity}</p>
      </div>
    </div>
  )
}

function TotalRow({ label, value, strong = false }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className={strong ? 'font-semibold text-ink' : 'text-muted'}>{label}</span>
      <span className={strong ? 'font-mono font-bold text-ink' : 'font-mono text-ink'}>{value}</span>
    </div>
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
