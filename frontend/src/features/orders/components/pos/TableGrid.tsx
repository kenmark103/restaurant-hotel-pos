import type { PosOrder } from '@/features/orders/types'
import type { TableRecord } from '@/features/tables/types'

export type TableWithOrder = TableRecord & { activeOrder: PosOrder | null }

interface TableGridProps {
  className?: string
  tables: TableWithOrder[]
  activeOrderId: number | null
  isWorking: boolean
  onSelect: (table: TableWithOrder) => void
}

export function TableGrid({ className = '', tables, activeOrderId, isWorking, onSelect }: TableGridProps) {
  return (
    <section className={`flex min-h-0 flex-col rounded-xl border border-line bg-panel ${className}`}>
      <div className="shrink-0 border-b border-line px-3 py-2.5">
        <p className="text-sm font-semibold text-ink">Tables</p>
        <p className="text-xs text-muted">Tap to open or select ticket</p>
      </div>
      <div className="flex-1 overflow-y-auto p-3">
        {tables.length === 0 ? (
          <p className="text-xs text-muted">No tables. Add them in Floor Plan.</p>
        ) : (
          <div className="grid grid-cols-2 gap-2">
            {tables.map((table) => (
              <TableButton
                key={table.id}
                table={table}
                activeOrderId={activeOrderId}
                isWorking={isWorking}
                onSelect={onSelect}
              />
            ))}
          </div>
        )}
      </div>
    </section>
  )
}

function TableButton({
  table,
  activeOrderId,
  isWorking,
  onSelect,
}: {
  table: TableWithOrder
  activeOrderId: number | null
  isWorking: boolean
  onSelect: (table: TableWithOrder) => void
}) {
  return (
    <button
      className={tableCardClass(table, activeOrderId)}
      disabled={isWorking || table.status === 'cleaning'}
      onClick={() => onSelect(table)}
      type="button"
    >
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-semibold text-ink">{table.table_number}</p>
        {table.activeOrder ? (
          <span className="rounded-full bg-white/70 px-1.5 py-0.5 text-[10px] font-semibold text-faint">
            {formatElapsed(table.activeOrder.created_at)}
          </span>
        ) : null}
      </div>
      <p className="mt-1 text-xs text-muted">{table.capacity} seats</p>
      <p className="mt-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-faint">
        {table.activeOrder ? `Ticket #${table.activeOrder.id}` : table.status}
      </p>
    </button>
  )
}

function tableCardClass(table: TableWithOrder, activeOrderId: number | null): string {
  const base = 'rounded-xl border px-3 py-3 text-left transition disabled:cursor-not-allowed disabled:opacity-60'
  const selected = table.activeOrder?.id != null && table.activeOrder.id === activeOrderId

  if (selected) {
    return `${base} border-accent bg-accent/10`
  }

  if (table.activeOrder?.status === 'sent') {
    return `${base} border-info/40 bg-info/10`
  }

  if (table.activeOrder?.status === 'open') {
    return `${base} border-warning/40 bg-warning/10`
  }

  if (table.status === 'cleaning') {
    return `${base} border-warning/40 bg-warning/10`
  }

  if (table.status === 'reserved') {
    return `${base} border-info/35 bg-info/10`
  }

  if (table.status === 'occupied') {
    return `${base} border-danger/30 bg-danger/10`
  }

  return `${base} border-success/35 bg-success/10 hover:border-success/55`
}

function formatElapsed(timestamp: string): string {
  const createdAt = new Date(timestamp)
  const deltaMs = Date.now() - createdAt.getTime()
  const totalMinutes = Math.max(0, Math.floor(deltaMs / 60000))

  if (totalMinutes < 60) {
    return `${totalMinutes}m`
  }

  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  return `${hours}h ${minutes}m`
}
