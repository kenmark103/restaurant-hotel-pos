/**
 * features/orders/components/pos/VariantSelector.tsx
 *
 * Modal shown when a user taps a menu item that has active variants.
 * The user picks a size before the item is added to the ticket.
 */

import type { MenuItemVariant, MenuItemWithCategory } from '@/features/menu/types'

interface VariantSelectorProps {
  item: MenuItemWithCategory
  formatPrice: (v: number | string) => string
  onSelect: (item: MenuItemWithCategory, variant: MenuItemVariant) => void
  onClose: () => void
}

export function VariantSelector({
  item,
  formatPrice,
  onSelect,
  onClose,
}: VariantSelectorProps) {
  const activeVariants = item.variants.filter((v) => v.is_active)

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center"
      onClick={onClose}
    >
      <div
        className="w-full max-w-sm rounded-t-2xl bg-white p-5 shadow-xl sm:rounded-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4">
          <p className="text-base font-bold text-ink">{item.name}</p>
          <p className="mt-0.5 text-sm text-muted">Select a size to add to ticket</p>
        </div>

        <div className="flex flex-col gap-2">
          {activeVariants.map((variant) => (
            <button
              key={variant.id}
              type="button"
              onClick={() => onSelect(item, variant)}
              className="flex items-center justify-between rounded-xl border border-line px-4 py-3 text-left transition hover:border-accent hover:bg-accent/5 active:scale-[0.98]"
            >
              <span className="font-semibold text-ink">{variant.name}</span>
              <span className="text-sm font-bold text-accent">
                {formatPrice(variant.sell_price)}
              </span>
            </button>
          ))}
        </div>

        <button
          type="button"
          onClick={onClose}
          className="mt-4 w-full rounded-xl border border-line py-2.5 text-sm font-semibold text-muted hover:text-ink"
        >
          Cancel
        </button>
      </div>
    </div>
  )
}