import type { MenuItemWithCategory, Station } from '@/features/menu/types'

interface MenuItemCardProps {
  item: MenuItemWithCategory
  formatPrice: (v: number | string) => string
  isBusy: boolean
  onEdit: () => void
  onToggle: () => void
}

const STATION_LABELS: Record<Station, string> = {
  any: 'Any',
  grill: 'Grill',
  fryer: 'Fryer',
  bar: 'Bar',
  cold: 'Cold',
  pass: 'Pass',
}

export function MenuItemCard({ item, formatPrice, isBusy, onEdit, onToggle }: MenuItemCardProps) {
  return (
    <div className={`app-panel overflow-hidden ${item.is_available ? '' : 'opacity-65'}`}>
      <div className="flex h-32 items-center justify-center bg-appbg">
        {item.image_url ? (
          <img alt={item.name} className="h-full w-full object-cover" src={item.image_url} />
        ) : (
          <span className="text-sm font-semibold text-muted">No image</span>
        )}
      </div>
      <div className="p-3">
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm font-semibold text-ink">{item.name}</p>
          <p className="text-sm font-semibold text-ink">{formatPrice(item.base_price)}</p>
        </div>
        <p className="mt-1 text-xs text-muted">{item.categoryName}</p>
        {item.description ? <p className="mt-2 line-clamp-2 text-xs text-muted">{item.description}</p> : null}

        <div className="mt-3 flex items-center justify-between gap-2">
          <span className="rounded-full bg-appbg px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-muted">
            {STATION_LABELS[(item.station as Station) ?? 'any']}
          </span>
          <button
            className="rounded-lg border border-line px-2 py-1 text-xs font-semibold text-muted hover:border-accent/50 hover:text-ink"
            disabled={isBusy}
            onClick={onEdit}
            type="button"
          >
            Edit
          </button>
        </div>

        <button
          className={`mt-2 w-full rounded-lg border px-2 py-1.5 text-xs font-semibold transition ${
            item.is_available
              ? 'border-warning/30 bg-warning/10 text-warning-text hover:bg-warning/20'
              : 'border-success/30 bg-success/10 text-success-text hover:bg-success/20'
          }`}
          disabled={isBusy}
          onClick={onToggle}
          type="button"
        >
          {item.is_available ? 'Mark unavailable (86)' : 'Mark available'}
        </button>
      </div>
    </div>
  )
}
