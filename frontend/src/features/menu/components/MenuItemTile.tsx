import type { MenuItem } from '@/features/menu/types'

interface MenuItemTileProps {
  item: MenuItem & { categoryName: string }
  quantityInTicket: number
  formatPrice: (v: number | string) => string
  disabled: boolean
  onAdd: () => void
}

export function MenuItemTile({ item, quantityInTicket, formatPrice, disabled, onAdd }: MenuItemTileProps) {
  const stationMeta = STATION_META[item.station] ?? STATION_META.any

  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onAdd}
      className="relative flex min-h-[130px] flex-col rounded-2xl border border-line bg-white p-3 text-left transition hover:border-accent disabled:opacity-60"
    >
      {quantityInTicket > 0 && (
        <span className="absolute right-2 top-2 flex h-5 w-5 items-center justify-center rounded-full bg-accent text-[10px] font-bold text-white">
          {quantityInTicket}
        </span>
      )}

      <div className="mb-2 flex items-center gap-2">
        <div className="flex h-10 w-10 items-center justify-center overflow-hidden rounded-lg bg-appbg">
          {item.image_url ? (
            <img alt={item.name} className="h-full w-full object-cover" src={item.image_url} />
          ) : (
            <span className="text-2xl">{stationMeta.icon}</span>
          )}
        </div>
        <span className="rounded-full bg-appbg px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-muted">
          {stationMeta.label}
        </span>
      </div>

      <p className="text-sm font-semibold text-ink">{item.name}</p>
      <p className="text-xs text-muted">{item.categoryName}</p>
      <p className="mt-auto pt-1 text-sm font-bold text-ink">{formatPrice(item.base_price)}</p>
    </button>
  )
}

const STATION_META: Record<string, { label: string; icon: string }> = {
  any: { label: 'Any', icon: '🍽' },
  grill: { label: 'Grill', icon: '🔥' },
  fryer: { label: 'Fryer', icon: '🍟' },
  bar: { label: 'Bar', icon: '🍸' },
  cold: { label: 'Cold', icon: '🥗' },
  pass: { label: 'Pass', icon: '📣' },
}
