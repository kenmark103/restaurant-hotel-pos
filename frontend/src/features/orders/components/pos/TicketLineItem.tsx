import type { PosOrderItem } from '@/features/orders/types'

interface TicketLineItemProps {
  item: PosOrderItem
  isWorking: boolean
  isOrderOpen: boolean
  formatPrice: (v: number | string) => string
  onIncrement: (item: PosOrderItem) => void
  onDecrement: (item: PosOrderItem) => void
  onVoid: (item: PosOrderItem) => void
  onPointerDown: (item: PosOrderItem) => void
  onPointerUp: () => void
  onPointerLeave: () => void
}

export function TicketLineItem({
  item,
  isWorking,
  isOrderOpen,
  formatPrice,
  onIncrement,
  onDecrement,
  onVoid,
  onPointerDown,
  onPointerUp,
  onPointerLeave,
}: TicketLineItemProps) {
  return (
    <div
      className="rounded-xl border border-line bg-white px-3 py-3"
      onPointerDown={() => onPointerDown(item)}
      onPointerLeave={onPointerLeave}
      onPointerUp={onPointerUp}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-ink">{item.menu_item_name}</p>
          {item.variant_name ? <p className="text-xs text-muted">{item.variant_name}</p> : null}
          <p className="text-xs text-muted">{formatPrice(item.unit_price)} each</p>
          {item.note ? <p className="mt-1 text-xs text-info-text">Note: {item.note}</p> : null}
        </div>
        <p className="text-sm font-semibold text-ink">{formatPrice(item.line_total)}</p>
      </div>

      <div className="mt-2 flex items-center justify-between gap-2">
        <div className="inline-flex items-center gap-2">
          <button
            className="h-7 w-7 rounded-lg border border-line text-sm font-semibold text-ink disabled:opacity-50"
            disabled={isWorking || !isOrderOpen}
            onClick={(event) => {
              event.stopPropagation()
              onDecrement(item)
            }}
            type="button"
          >
            -
          </button>
          <span className="text-sm font-semibold text-ink">{item.quantity}</span>
          <button
            className="h-7 w-7 rounded-lg border border-line text-sm font-semibold text-ink disabled:opacity-50"
            disabled={isWorking || !isOrderOpen}
            onClick={(event) => {
              event.stopPropagation()
              onIncrement(item)
            }}
            type="button"
          >
            +
          </button>
        </div>

        <button
          className="text-xs font-semibold text-danger disabled:opacity-50"
          disabled={isWorking || !isOrderOpen}
          onClick={(event) => {
            event.stopPropagation()
            onVoid(item)
          }}
          type="button"
        >
          Void line
        </button>
      </div>
    </div>
  )
}
