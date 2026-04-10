import type { PosOrder, PosOrderItem } from '@/features/orders/types'
import { EmptyState } from '@/shared/ui/EmptyState'
import { KdsTicketItem } from './KdsTicketItem'

interface KdsViewProps {
  kdsByStation: Map<string, Array<{ order: PosOrder; item: PosOrderItem }>>
  formatPrice: (v: number | string) => string
}

const STATION_LABELS: Record<string, { label: string; icon: string }> = {
  any: { label: 'Any', icon: '🍽' },
  grill: { label: 'Grill', icon: '🔥' },
  fryer: { label: 'Fryer', icon: '🍟' },
  bar: { label: 'Bar', icon: '🍸' },
  cold: { label: 'Cold', icon: '🥗' },
  pass: { label: 'Pass', icon: '📣' },
}

export function KdsView({ kdsByStation, formatPrice }: KdsViewProps) {
  if (kdsByStation.size === 0) {
    return (
      <div className="app-panel flex flex-1 items-center justify-center p-8">
        <EmptyState
          title="No tickets sent to kitchen"
          description="Orders with status 'sent' will appear here, grouped by kitchen station."
        />
      </div>
    )
  }

  return (
    <div className="flex min-h-0 flex-1 gap-3 overflow-x-auto pb-1">
      {Array.from(kdsByStation.entries()).map(([station, entries]) => {
        const meta = STATION_LABELS[station] ?? STATION_LABELS.any
        return (
          <div key={station} className="app-panel flex h-full w-72 shrink-0 flex-col">
            <div className="shrink-0 border-b border-line px-4 py-3">
              <div className="flex items-center gap-2">
                <span className="text-lg">{meta.icon}</span>
                <p className="font-semibold text-ink">{meta.label}</p>
                <span className="ml-auto rounded-full bg-accent/10 px-2 py-0.5 font-mono text-xs font-bold text-accent">
                  {entries.length}
                </span>
              </div>
            </div>

            <div className="flex-1 space-y-2 overflow-y-auto p-3">
              {entries.map(({ order, item }) => (
                <KdsTicketItem key={`${order.id}-${item.id}`} order={order} item={item} formatPrice={formatPrice} />
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}
